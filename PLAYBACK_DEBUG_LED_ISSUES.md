# MIDI Playback Isolation - Debugging LEDs Not Lighting Up

## Issue
LEDs not lighting up when device is connected and playback is inactive.

## Root Cause Analysis

The LED issue could be caused by several factors:

1. **LED Controller Not Initialized** - `_led_controller` is None in MidiEventProcessor
2. **USB MIDI Service Not Started** - No listener active
3. **MIDI Device Not Connected** - Check device dropdown
4. **LED Mapping Issue** - No LEDs mapped for the MIDI note
5. **Callback Interfering** - Playback status check failing

## Debug Steps

### Step 1: Check Backend Logs

Push to Pi and restart backend, then check logs:

```bash
# On Pi:
systemctl restart piano-led-backend
journalctl -u piano-led-backend -n 100 -f
```

### Step 2: Look for These Specific Log Messages

#### Should See (On Startup):
```
INFO: Registered playback status callback - USB MIDI LEDs will be suppressed during MIDI file playback
```

If this message is NOT present:
- playback_service is not initialized
- midi_input_manager not initialized
- They're not being passed correctly

#### Should See (When Pressing Keyboard):
```
DEBUG: USB MIDI raw message | type=note_on note=60 velocity=100 channel=0 time=... | callback=INACTIVE
DEBUG: USB MIDI: No callback set - updating LEDs normally (default behavior)
INFO: MIDI_PROCESSOR[...]: NOTE_ON note=60 velocity=100 led_count=246 leds=[...]
```

If you see instead:
```
DEBUG: Cannot update LED for note 60 - LED controller is None
```
→ **Problem: LED controller not passed to processor**

If you see:
```
DEBUG: Skipping LED update for note 60 (playback active)
```
→ **Problem: Playback callback thinks playback is active when it's not**

If you see NOTHING at all:
→ **Problem: USB MIDI service not listening**

### Step 3: Verify Callback Status

Add temporary debug code to check if callback is set. In the logs, look for:

```
USB MIDI processing loop started (..., callback=set)
```

or

```
USB MIDI processing loop started (..., callback=NOT SET)
```

If it says "NOT SET":
- The callback registration failed
- Check if `playback_service` is None
- Check if `midi_input_manager` is None

### Step 4: Verify LED Controller

Check if LED controller is properly initialized:

```bash
# In backend logs, look for:
INFO: LED controller and effects manager initialized successfully with 246 LEDs
```

If not present, LED controller failed to initialize.

### Step 5: Check Device Connection

From Play page:
1. Go to Play tab
2. Look for device dropdown
3. Check if USB MIDI device is listed
4. Select the device

If device not listed:
- Device not connected
- USB MIDI service not started
- Device enumeration failed

### Step 6: Manual Test

```python
# In Python on the Pi:
from backend.usb_midi_service import USBMIDIInputService
from backend.led_controller import LEDController

# Check if services create without errors
try:
    led = LEDController()
    print(f"LED Controller: OK ({led.num_pixels} LEDs)")
except Exception as e:
    print(f"LED Controller: FAILED - {e}")

try:
    usb = USBMIDIInputService(led_controller=led)
    print("USB MIDI Service: OK")
except Exception as e:
    print(f"USB MIDI Service: FAILED - {e}")
```

## Common Issues and Solutions

### Issue: "Cannot update LED - LED controller is None"

**Cause:** LED controller not being passed to MidiEventProcessor

**Solution:** 
1. Check that `led_controller` is not None when creating USBMIDIInputService
2. Verify LEDs are enabled in settings
3. Check LED controller initialization logs

### Issue: "Skipping LED update (playback active)"  when playback IS NOT ACTIVE

**Cause:** `is_playback_active()` returning True incorrectly

**Cause:** playback_service state is not IDLE/PAUSED

**Solution:**
1. Check what state playback_service is in
2. Verify PlaybackState enum is correct
3. Check if playback never finished/stopped properly

Add debug code to check state:
```python
# In playback_service
logger.info(f"Playback state: {self._state.value}")
```

### Issue: No MIDI messages received

**Cause:** USB MIDI service not listening

**Solution:**
1. Check if device is selected in Play tab
2. Verify USB MIDI service started successfully
3. Check device is actually connected: `mido.get_input_names()`

### Issue: Playback callback not registered

**Check logs for:**
```
INFO: Registered playback status callback...
```

If missing:
1. Check if `playback_service` is None
2. Check if `midi_input_manager` is None
3. Check if `initialize_services()` was called

## Log Output Examples

### ✅ Good - Playback Inactive, LEDs Should Update

```
DEBUG: USB MIDI processing loop started (processor_id=140735..., callback=set)
DEBUG: USB MIDI drained 1 message(s)
DEBUG: USB MIDI raw message | type=note_on note=60 velocity=100 channel=0 time=... | callback=INACTIVE
DEBUG: USB MIDI: No callback set - updating LEDs normally (default behavior)
INFO: MIDI_PROCESSOR[140735...]: NOTE_ON note=60 velocity=100 led_count=246 leds=[123]
```

### ❌ Bad - LED Controller Missing

```
DEBUG: USB MIDI raw message | type=note_on note=60 velocity=100 channel=0 time=... | callback=NOT SET
DEBUG: Cannot update LED for note 60 - LED controller is None
```

### ❌ Bad - Playback Active (But Shouldn't Be)

```
DEBUG: USB MIDI raw message | type=note_on note=60 velocity=100 channel=0 time=... | callback=ACTIVE
INFO: USB MIDI: Playback active (ACTIVE) - skipping LED update for MIDI from keyboard
```

### ❌ Bad - No Callback Set

```
DEBUG: USB MIDI processing loop started (processor_id=140735..., callback=NOT SET)
```

## New Debug Logging Added

I've enhanced the logging to show:

1. **Callback status**: Shows if callback is set or not
2. **LED controller status**: Shows if controller exists
3. **Update conditions**: Shows why LED update was skipped
4. **Detailed conditions**: Shows all flags at every step

## Testing After Fix

1. Restart backend
2. Check for "Registered playback status callback" in logs
3. Connect USB MIDI device
4. Press keys
5. Look for "MIDI_PROCESSOR: NOTE_ON" messages
6. Verify LEDs light up

## Quick Checklist

- [ ] Backend starts without errors
- [ ] "Registered playback status callback" appears in logs  
- [ ] USB MIDI device shows in Play tab dropdown
- [ ] When you press keys, you see "USB MIDI raw message" in logs
- [ ] You see "MIDI_PROCESSOR: NOTE_ON" log messages
- [ ] LEDs light up when you press keys
- [ ] Playback is not active (check state: IDLE or PAUSED)

If any of these fail, refer to the corresponding section above.

## Next Steps After Debugging

Once you identify the issue from the logs:

1. **LED Controller None**: Check LED initialization in app.py
2. **Callback Not Set**: Verify playback_service and midi_input_manager initialized
3. **No MIDI Messages**: Check device connection and USB service
4. **Playback thinks active**: Check playback state transitions
5. **Performance issue**: Check LED I/O performance

Let me know what logs you see and I can help identify the exact issue!
