# Fix: Duplicate MIDI Processing (Duplicate LEDs)

## Problem Summary
When changing LED settings (LED count, orientation) while USB MIDI devices were connected, users reported that **TWO sets of LEDs light up**:
1. The **old set** following the previous settings (e.g., 255 LEDs normal orientation)
2. The **new set** following the updated settings (e.g., 25 LEDs reversed orientation)

Both sets light up simultaneously, indicating duplicate MIDI event processing.

## Root Cause
The system was creating **TWO independent `USBMIDIInputService` instances** that each had their own `MidiEventProcessor`:

### Before Fix:
```python
# app.py line 113
usb_midi_service = USBMIDIInputService(...)  # Instance #1

# midi_input_manager.py line 176 (inside initialize_services())
self._usb_service = USBMIDIInputService(...)  # Instance #2
```

Both instances:
- Independently listened to USB MIDI input
- Each processed MIDI events to LED commands
- Each maintained their own cached settings state
- When settings changed, only one instance refreshed, the other kept the old cached values

Result: **Each MIDI note triggered LED updates from BOTH instances**, creating duplicate visual output.

### Process Flow (Before Fix):
```
MIDI Input Event
    ├─→ USBMIDIInputService #1 (app.py) 
    │   ├─→ MidiEventProcessor (cached: 255 LEDs, normal)
    │   └─→ LED Controller: Light up LEDs 0-255
    │
    ├─→ USBMIDIInputService #2 (midi_input_manager.py)
    │   ├─→ MidiEventProcessor (cached: 25 LEDs, reversed)
    │   └─→ LED Controller: Light up LEDs 0-25 (reversed)
    │
    └─→ Result: BOTH sets of LEDs light up!
```

## Solution
**Create only ONE `USBMIDIInputService` and share it between components.**

### Changes Made:

1. **`backend/midi_input_manager.py` - Accept existing service**
   - Modified `__init__()` to accept optional `usb_midi_service` parameter
   - Updated `initialize_services()` to skip USB creation if one already provided
   ```python
   def __init__(self, ..., usb_midi_service=None):
       # Reuse provided service to avoid duplicate creation
       self._usb_service = usb_midi_service
   ```

2. **`backend/app.py` - Create single shared instance**
   - Create ONE `usb_midi_service` at startup
   - Pass it to `MIDIInputManager` instead of having manager create another
   ```python
   # Create once
   usb_midi_service = USBMIDIInputService(...)
   # Pass to manager
   midi_input_manager = MIDIInputManager(..., usb_midi_service=usb_midi_service)
   ```

3. **`backend/app.py` - Unified refresh logic**
   - Updated `_refresh_runtime_dependencies()` to coordinate updates properly
   - Only refresh USB service once, then update manager's reference
   - Added detailed logging to track which components are updated

### Process Flow (After Fix):
```
MIDI Input Event
    └─→ USBMIDIInputService #1 (SINGLE SHARED INSTANCE)
        ├─→ MidiEventProcessor 
        │   ├─→ Refreshes settings before each event
        │   └─→ Always uses CURRENT cached settings
        └─→ LED Controller: Light up correct LED set only
```

## Verification

### Service Logs Show Single Instance:
```
Oct 16 07:37:54 - backend.midi_input_manager - INFO - USB MIDI service available
Oct 16 07:37:54 - backend.midi_input_manager - INFO - Initialized 2 MIDI input service(s)
```

Note: No line saying "USB MIDI service created in initialize_services()" - proving the shared instance is being used.

### Expected Behavior After Fix:
✅ Only ONE set of LEDs lights up when playing
✅ Settings changes apply immediately (25 LEDs, 255 LEDs, orientations)
✅ No duplicate LED activity
✅ MIDI mapping updates correctly without double-processing

## Testing Checklist
- [ ] Connect USB MIDI keyboard
- [ ] Play notes - verify only ONE set of LEDs responds
- [ ] Change LED count via settings (255 → 50)
- [ ] Play notes again - verify NEW LED count is respected (only 50 LEDs light up)
- [ ] Change orientation via settings (normal → reversed)
- [ ] Play notes - verify orientation change applied correctly
- [ ] No visual duplication or ghosting

## Files Modified
- `backend/app.py` - Create single shared instance, update refresh logic
- `backend/midi_input_manager.py` - Accept existing service parameter
- Both files synced in version: Oct 16 2025, 07:37:47 EDT

## Deployment
Changes deployed to Raspberry Pi at `192.168.1.225`:
```bash
$ git pull origin main
$ sudo systemctl restart piano-led-visualizer.service
```
