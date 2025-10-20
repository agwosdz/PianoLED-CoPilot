# MIDI Playback Isolation - Suppress USB Keyboard LEDs During File Playback

## Summary
When a MIDI file is being played back, the system now automatically suppresses LED updates from connected USB MIDI devices (keyboards). This prevents keyboard input from interfering with the playback visualization.

## Problem
- When playing a MIDI file with LED visualization, if a user presses keys on a connected USB MIDI keyboard, those LED updates would interfere with the playback visualization
- Both the playback and keyboard input would try to update the same LEDs, causing visual conflicts

## Solution
A callback-based system that checks playback status before processing USB MIDI events:

1. **PlaybackService** exposes an `is_playback_active()` method
2. **MIDIInputManager** maintains a reference to this callback
3. **USBMIDIInputService** checks the callback before updating LEDs
4. **MidiEventProcessor** respects an `update_leds` flag when handling MIDI messages

## Changes Made

### 1. `backend/playback_service.py`
Added method to check if playback is currently active:
```python
def is_playback_active(self) -> bool:
    """Check if playback is currently active (playing, not paused or idle)"""
    return self._state == PlaybackState.PLAYING
```

### 2. `backend/midi_input_manager.py`
- Added `_playback_status_callback` field to store the callback
- Added `set_playback_status_callback()` method to register the callback
- Added `is_playback_active()` method to check playback status

```python
def set_playback_status_callback(self, callback: Optional[Callable[[], bool]]) -> None:
    """Set a callback to check if MIDI file playback is active."""
    self._playback_status_callback = callback
    # Propagate callback to USB service if available
    if self._usb_service and hasattr(self._usb_service, 'set_playback_status_callback'):
        self._usb_service.set_playback_status_callback(callback)
```

### 3. `backend/usb_midi_service.py`
- Added `_playback_status_callback` field
- Added `set_playback_status_callback()` method
- Modified `_processing_loop()` to check playback status before updating LEDs

```python
def _processing_loop(self) -> None:
    # Check if MIDI file playback is active
    playback_active = False
    if self._playback_status_callback:
        try:
            playback_active = self._playback_status_callback()
        except Exception as e:
            logger.debug(f"Error checking playback status: {e}")
    
    for msg, msg_timestamp in drained:
        # Skip LED updates when playback is active
        if playback_active:
            logger.debug("USB MIDI: Playback active - skipping LED update")
            processed_events = self._event_processor.handle_message(msg, msg_timestamp, update_leds=False)
        else:
            processed_events = self._event_processor.handle_message(msg, msg_timestamp)
```

### 4. `backend/midi/midi_event_processor.py`
- Modified `handle_message()` to accept `update_leds` parameter
- Modified `_handle_note_on()` and `_handle_note_off()` to conditionally skip LED updates

```python
def handle_message(self, msg, timestamp: Optional[float] = None, update_leds: bool = True):
    """
    Process a MIDI message, optionally skipping LED updates.
    
    Args:
        update_leds: Set to False during playback to suppress keyboard LED updates
    """
    # ... process message with update_leds flag passed to handlers
```

### 5. `backend/app.py`
Register the callback during initialization:
```python
# Register playback status callback with MIDI input manager
if midi_input_manager and playback_service:
    midi_input_manager.set_playback_status_callback(playback_service.is_playback_active)
    logger.info("Registered playback status callback...")
```

## Behavior

### When Playback is IDLE/PAUSED
- USB MIDI keyboard input updates LEDs normally
- Full LED visualization for keyboard input

### When Playback is PLAYING
- USB MIDI keyboard input is **processed** but **not visualized on LEDs**
- Keyboard note events are still tracked and can be used for MIDI output
- Only the MIDI file playback LEDs are displayed
- No conflicts between playback and keyboard visualization

## Benefits
✅ Clean separation of playback and keyboard visualization
✅ No LED conflicts during file playback
✅ Keyboard input is still processed (useful for MIDI output scenarios)
✅ Automatic behavior - no user configuration needed
✅ Minimal performance impact (single boolean check per MIDI event)

## Testing

### Test 1: Keyboard LEDs Work When Idle
1. Start app
2. Connect USB MIDI keyboard
3. Press keys
4. ✓ LEDs light up for keyboard input

### Test 2: Keyboard LEDs Suppressed During Playback
1. Load MIDI file and start playback
2. While playback is active, press keys on USB MIDI keyboard
3. ✓ No LED response from keyboard
4. ✓ Playback LEDs continue normally
5. ✓ Pause playback
6. ✓ Keyboard LEDs work again

### Test 3: Resume Keyboard Control After Playback
1. Play MIDI file until completion
2. Once idle, press keyboard keys
3. ✓ LEDs respond to keyboard again

## Files Modified
- `backend/playback_service.py` - Added `is_playback_active()` method
- `backend/midi_input_manager.py` - Added callback registration
- `backend/usb_midi_service.py` - Added callback check in processing loop
- `backend/midi/midi_event_processor.py` - Added `update_leds` parameter support
- `backend/app.py` - Registered callback during initialization

## Implementation Notes
- The callback is checked **per MIDI message** (very lightweight)
- No changes needed to frontend
- Works with any connected USB MIDI device
- Playback state is checked in real-time (no caching)
- Graceful fallback if callback is not set

## Future Enhancements
- Could add a settings option to disable this behavior
- Could implement partial suppression (e.g., different keyboard region)
- Could add logging for playback LED conflicts
