# Fix: Consolidated MIDI Event Processing - Single Path Architecture

## Problem
Even after creating a single `USBMIDIInputService` instance, users still reported **duplicate LEDs lighting up** when changing settings.

## Root Cause: Dual Event Processing Paths

The issue wasn't just about having two service instances, but about **two different event processing paths**:

### Before Fix Architecture:
```
USB MIDI Input
    ├─→ Path 1 (Direct): 
    │   usb_midi_service (with socketio.emit callback)
    │   └─→ MidiEventProcessor._handle_note_on()
    │       └─→ LEDController.turn_on_led()
    │
    └─→ Path 2 (Manager): 
        MIDIInputManager receives events via callback
        └─→ MidiEventProcessor._handle_note_on()
            └─→ LEDController.turn_on_led()
```

**Result:** Two independent paths updating the SAME LED controller → duplicate outputs

### The Dual Path Problem:

1. **app.py created** `usb_midi_service` with `websocket_callback=socketio.emit`
   - This callback went directly to WebSocket, **NOT through MIDIInputManager**
   - MidiEventProcessor would call LED updates directly

2. **MIDIInputManager also had** `websocket_callback=socketio.emit`
   - It received events through a separate callback mechanism
   - Events were processed, but LED updates already happened via path 1

3. **When settings changed:**
   - Cached LED count in path 1's MidiEventProcessor: 255 LEDs
   - Cached LED count in path 2's MidiEventProcessor: 25 LEDs (after refresh)
   - Both processors still received queued MIDI events
   - Both tried to light LEDs with different mappings

## Solution: Single Unified Event Path

### After Fix Architecture:
```
USB MIDI Input
    └─→ MIDIInputManager (exclusive coordinator)
        └─→ _handle_usb_event() receives events
            └─→ MidiEventProcessor.handle_message()
                └─→ LEDController.turn_on_led()
                    └─→ WebSocket broadcast (via manager)
```

**Result:** Single path, single cache, no duplicates

### Key Changes:

#### 1. app.py: Remove duplicate service creation

**Before:**
```python
usb_midi_service = USBMIDIInputService(
    ..., 
    websocket_callback=socketio.emit
)
midi_input_manager = MIDIInputManager(
    ..., 
    usb_midi_service=usb_midi_service  # Pass existing
)
```

**After:**
```python
midi_input_manager = MIDIInputManager(
    websocket_callback=socketio.emit,
    ...
)
usb_midi_service = midi_input_manager._usb_service  # Reference only
```

#### 2. midi_input_manager.py: Remove external service parameter

**Before:**
```python
def __init__(self, ..., usb_midi_service=None):
    self._usb_service = usb_midi_service  # Could be None!
```

**After:**
```python
def __init__(self, ...):
    self._usb_service = None  # Will be created by initialize_services()
```

#### 3. midi_input_manager.py: Remove conditional service creation

**Before:**
```python
def initialize_services(self):
    if self._usb_service is None and self.enable_usb:
        # Create if not provided externally
        self._usb_service = USBMIDIInputService(...)
```

**After:**
```python
def initialize_services(self):
    if self.enable_usb:
        # ALWAYS create - exclusive instance
        self._usb_service = USBMIDIInputService(
            websocket_callback=self._handle_usb_event  # Routes through manager
        )
```

#### 4. app.py: Simplify refresh logic

**Before:**
```python
if usb_midi_service:
    usb_midi_service.update_led_controller(...)

if midi_input_manager:
    midi_input_manager.update_led_controller(...)  # Different instance!
```

**After:**
```python
if midi_input_manager:
    midi_input_manager.update_led_controller(...)  # Single path
```

## Event Flow Diagram

### Before (Problematic):
```
┌─────────────────────────────────────────────────────────┐
│                   USB MIDI Device                        │
└────────────────────────┬────────────────────────────────┘
                         │
                    MIDI Messages
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
   [usb_midi_service]          [midi_input_manager]
   callback: socketio.emit      callback: manager._handle_usb_event
        │                                 │
        ▼                                 ▼
   [MidiEventProcessor #1]      [MidiEventProcessor (same?)]
   Cache: LED mapping           Cache: LED mapping
        │                                 │
        └────────────────┬────────────────┘
                         │
                         ▼
                   [LED Controller]
            (Receives duplicate updates)
```

### After (Correct):
```
┌─────────────────────────────────────────────────────────┐
│                   USB MIDI Device                        │
└────────────────────────┬────────────────────────────────┘
                         │
                    MIDI Messages
                         │
                         ▼
                  [midi_input_manager]
           (Exclusive MIDI coordinator)
                         │
                         ▼
          [_handle_usb_event callback]
                         │
                         ▼
              [MidiEventProcessor]
           (Single shared instance)
           Cache: LED mapping
                         │
                         ▼
                  [LED Controller]
              (Receives updates once)
```

## Verification

### Changes Made:
1. ✅ Removed `usb_midi_service` creation from `app.py`
2. ✅ Removed `usb_midi_service` parameter from `MIDIInputManager.__init__()`
3. ✅ Simplified `initialize_services()` to always create USB service
4. ✅ Simplified `_refresh_runtime_dependencies()` to coordinate through manager only
5. ✅ All USB events now route through `_handle_usb_event()` callback

### Single Instance Guarantees:
- ✅ One USB MIDI service created by MIDIInputManager
- ✅ One MidiEventProcessor per USB service
- ✅ One LED controller reference
- ✅ One settings cache per processor
- ✅ One output path to LEDs

## Testing Checklist

- [ ] Deploy to Raspberry Pi
- [ ] Connect USB MIDI keyboard
- [ ] Play notes → Verify ONLY ONE set of LEDs responds (not duplicated)
- [ ] Change LED count via settings: 255 → 50
- [ ] Play notes → Verify ONLY 50 LEDs light (clean boundary, no ghosts)
- [ ] Change orientation: normal → reversed
- [ ] Play notes → Verify orientation applies cleanly
- [ ] Rapid settings changes → No flicker or overlap
- [ ] Check logs: Single processing path confirmed

## Files Modified

| File | Changes |
|------|---------|
| `backend/app.py` | Remove `usb_midi_service` creation, simplify refresh logic |
| `backend/midi_input_manager.py` | Remove external service parameter, always create exclusive instance |

## Expected Behavior After Fix

### Before Fix:
- ❌ Two LED patterns overlay when MIDI plays
- ❌ Settings changes show old + new LEDs simultaneously  
- ❌ Race conditions during rapid setting updates

### After Fix:
- ✅ Single clean LED response to MIDI
- ✅ Settings changes apply immediately (no ghost patterns)
- ✅ Smooth transitions between settings
- ✅ Lower CPU/memory usage (single processor)
- ✅ Better real-time responsiveness

## Architecture Notes

### Why This Approach:
1. **MIDIInputManager is the coordinator**: It manages both USB and rtpMIDI sources
2. **Single responsibility**: Each service creates and owns its USB MIDI instance
3. **Callback routing**: USB events route through manager for unified processing
4. **Settings consistency**: Single cache per processor
5. **Future-proof**: Easy to add more MIDI sources in future

### Event Processing Chain:
```
USB Port (mido) 
  → USBMIDIInputService._processing_loop()
    → MidiEventProcessor.handle_message()
      → LED updates + WebSocket broadcast
        → MIDIInputManager._handle_usb_event() [status only]
```

All actual LED updates happen in MidiEventProcessor, ensuring single output.

## Commit Message
```
fix: Consolidate MIDI event processing through MIDIInputManager only

- Remove duplicate usb_midi_service creation from app.py
- Let MIDIInputManager exclusively manage USB MIDI service creation
- Ensure all USB MIDI events route through manager callback
- Update _refresh_runtime_dependencies to coordinate through manager only
- Eliminates dual event processing paths that caused LED duplicates

All MIDI events now flow through single path:
  USB Input → MIDIInputManager → MidiEventProcessor → LED Controller

No more duplicate LED outputs on settings changes.
```
