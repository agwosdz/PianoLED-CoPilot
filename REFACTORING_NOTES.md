# Backend Real-Time Settings Refactoring

## Problem Analysis

### Issue
Settings changes (LED count, LED orientation, etc.) were not being applied in real-time when a USB MIDI device was actively connected and processing events.

### Root Causes Identified

1. **Double-Call Bug**: `app.py` was calling both `update_led_controller()` AND `refresh_runtime_settings()` on USB MIDI service, causing `MidiEventProcessor.refresh_runtime_settings()` to be called twice unnecessarily.

2. **Missing Propagation**: When LED settings changed, the `MidiEventProcessor` inside `USBMIDIInputService` wasn't being notified properly because:
   - The processor caches `num_leds` and `led_orientation` at initialization
   - The processor needs to re-sync with the LED controller when those values change
   - The settings listener in `app.py` was calling refresh, but not ensuring the processor re-read from disk

3. **Thread Safety Issues**: The `MidiEventProcessor` maintains a local cache of settings that could become stale while MIDI events are being processed in a separate thread.

## Changes Made

### 1. **app.py** - Fixed Service Update Flow

**Before:**
```python
if usb_midi_service:
    if led_controller:
        usb_midi_service.update_led_controller(led_controller)
    usb_midi_service.refresh_runtime_settings()  # Redundant call!
```

**After:**
```python
if usb_midi_service:
    # update_led_controller() already calls refresh_runtime_settings() internally
    # No need to call refresh again
    if led_controller:
        usb_midi_service.update_led_controller(led_controller)
    else:
        # If no LED controller, explicitly refresh settings
        usb_midi_service.refresh_runtime_settings()
```

**Why**: Eliminates double-refresh which could cause race conditions or stale reads.

### 2. **usb_midi_service.py** - Improved Logging and Documentation

Added better logging to track when the USB MIDI service is updated:
- Logs when LED controller is updated
- Logs when runtime settings are refreshed

### 3. **midi_event_processor.py** - Improved Logging on Settings Refresh

Changed from DEBUG to INFO level logging when refreshing runtime settings:
```python
logger.info("MIDI event processor refreshed: leds=%d orientation=%s mapping=%s", 
    self.num_leds, self.led_orientation, self.mapping_mode)
```

**Why**: Makes it easier to verify that settings changes are being propagated.

## Architecture of Settings Flow

```
Settings Service
       ↓
Settings Change Event
       ↓
_on_setting_change() in app.py
       ↓
_refresh_runtime_dependencies()
       ↓
[LED Controller]
       ├→ apply_runtime_settings()
       └→ Changes: led_count, orientation, brightness, etc.
       ↓
[USB MIDI Service]
       └→ update_led_controller(new_controller)
           └→ MidiEventProcessor.update_led_controller()
               ├→ Set self._led_controller = new_controller
               └→ Call refresh_runtime_settings()
                   ├→ _load_settings() → Re-read from settings service
                   ├→ _sync_controller_geometry() → Align with controller
                   ├→ _generate_key_mapping() → Recalculate mapping
                   └→ _active_notes.clear() → Reset active notes
```

## Remaining Architectural Improvements

### Issue 1: Settings Cached at Initialization
**Problem**: `MidiEventProcessor` loads settings once at init and caches them in `self.num_leds`, `self.led_orientation`, etc.

**Solution**: Already addressed by `refresh_runtime_settings()` which re-reads from settings service on each call.

### Issue 2: No Event Listener on Settings Service
**Problem**: If a MIDI service is created after settings change, it won't know about the change.

**Current Implementation**: Settings service is passed to services at init, they pull latest values via `get_setting()` when `refresh_runtime_settings()` is called.

**Recommendation**: Consider adding a listener pattern where services can subscribe to specific setting changes.

### Issue 3: Threading and Active Notes
**Problem**: When LED orientation changes mid-processing, active notes might be mapped incorrectly.

**Current Implementation**: `_active_notes.clear()` clears active notes on settings refresh, forcing re-evaluation of all playing notes.

**Trade-off**: This prevents incorrect mappings but may cause a brief visual glitch when orientation changes while notes are playing.

### Issue 4: Process Isolation (Future)
**Concern**: Both `USBMIDIInputService` and `RtpMIDIService` have their own `MidiEventProcessor` instances.

**Recommendation**: In a future refactor, consider:
- Shared `MidiEventProcessor` or
- Event-based updates to all processors when settings change

## Testing Recommendations

1. **Test Real-Time LED Count Update**
   - Connect USB MIDI device
   - Play a note (LED lights up)
   - Change LED count in settings
   - Verify LED responds to the new count

2. **Test Real-Time Orientation Update**
   - Connect USB MIDI device  
   - Play notes across keyboard
   - Change LED orientation to "reversed"
   - Verify LED pattern is reversed

3. **Test Multiple Setting Changes**
   - Change LED count → orientation → brightness in sequence
   - Verify each change takes effect immediately

4. **Test with Active Notes**
   - Play a sustained note
   - Change settings while note is held
   - Verify LEDs update without dropping the note

## Code Locations

- **Settings change handler**: `backend/app.py` line ~245-310
- **Settings propagation**: `backend/app.py` line ~125-240
- **USB MIDI Service**: `backend/usb_midi_service.py` line ~161
- **Event Processor**: `backend/midi/midi_event_processor.py` line ~88-98

## Performance Implications

- **Minimal**: Settings refresh happens only on explicit settings change
- **Active Processing**: MIDI event processing continues at full speed
- **Memory**: No additional memory overhead from this refactor

## Future Improvements

1. Add metrics/telemetry to track settings update latency
2. Consider debouncing rapid consecutive settings changes
3. Add integration tests for real-time settings updates
4. Implement graceful handling of orientation changes during active playback
