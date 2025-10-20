# MIDI Playback Isolation - Testing Guide

## Quick Overview
When MIDI file playback is active, USB keyboard input will **NOT** update the LEDs. This prevents visual interference between playback and keyboard input.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│             USB MIDI Keyboard Input                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
        ┌─────────────────────┐
        │ Check Playback?     │
        └────────┬────────────┘
                 │
         ┌───────┴───────┐
         │               │
    Playing           Not Playing
         │               │
    ┌────▼────┐      ┌───▼─────┐
    │Skip LEDs │      │Update   │
    │Only MIDI │      │LEDs     │
    │processed │      │Normally │
    └─────────┘      └─────────┘
```

## Testing Scenarios

### Scenario 1: Keyboard Input While IDLE
**Expected:** Keyboard LEDs work normally

1. Start the backend
2. Connect USB MIDI keyboard (or ensure it's connected)
3. In Play tab, check that device appears in dropdown
4. Press keys on keyboard
5. ✅ **Expected:** LEDs light up for each key press

### Scenario 2: Playback Active → Keyboard Input Suppressed
**Expected:** Keyboard input is ignored, playback continues

1. Load a MIDI file (use Play tab upload)
2. Start playback
3. Observe playback LEDs animating
4. **While playback is active**, press keys on connected keyboard
5. ✅ **Expected:** 
   - Playback LEDs continue normally
   - Keyboard does NOT trigger LED updates
   - No visual conflicts
   - Backend logs: "USB MIDI: Playback active - skipping LED update"

### Scenario 3: Resume Keyboard After Playback Ends
**Expected:** Keyboard control resumes

1. Let MIDI file play to completion
2. Playback automatically stops (state = IDLE)
3. Press keys on keyboard
4. ✅ **Expected:** LEDs respond to keyboard again

### Scenario 4: Pause Playback → Resume Keyboard
**Expected:** Keyboard control works when paused

1. Start MIDI file playback
2. While playing, pause (state = PAUSED)
3. Press keys on keyboard
4. ✅ **Expected:** 
   - LEDs respond to keyboard
   - Playback remains paused (no LED animation)
5. Resume playback
6. Keyboard input again suppressed

### Scenario 5: Stop Playback → Resume Keyboard
**Expected:** Keyboard control works after stop

1. Start playback
2. Stop playback (state = IDLE)
3. Press keyboard keys
4. ✅ **Expected:** LEDs respond

## Debug Logging

When testing, check backend logs for these messages:

### Playback Active (Suppression Working)
```
DEBUG: USB MIDI: Playback active - skipping LED update for MIDI from keyboard
DEBUG: Skipping LED update for note 60 (playback active)
```

### Playback Inactive (Normal Operation)
```
INFO: MIDI_PROCESSOR[...]: NOTE_ON note=60 velocity=100 led_count=246 leds=[...]
```

### Callback Registration
```
INFO: Registered playback status callback - USB MIDI LEDs will be suppressed during MIDI file playback
```

## What Should NOT Change

- ✅ Playback LED visualization works normally
- ✅ Keyboard can still be used for MIDI output (if enabled)
- ✅ WebSocket events are still sent for keyboard input
- ✅ No frontend changes needed
- ✅ Settings work normally

## Troubleshooting

### Issue: Keyboard LEDs still appear during playback
**Solution:** 
1. Check backend logs for callback registration message
2. Verify playback_service is initialized
3. Confirm PlaybackState enum exists and is being set correctly
4. Check if playback_service.is_playback_active() returns True

### Issue: Keyboard LEDs don't work when idle
**Solution:**
1. Verify USB MIDI service is running (check status endpoint)
2. Check that playback_service.is_playback_active() returns False when idle
3. Verify keyboard device is selected in Play tab

### Issue: Errors in backend logs
**Solution:**
1. Check that all modified files are syntactically correct
2. Verify callback is set: `midi_input_manager.set_playback_status_callback(...)`
3. Check MidiEventProcessor.handle_message receives update_leds parameter

## Performance Impact

- ✅ Minimal: One boolean check per MIDI message
- ✅ No LED flickering or delays
- ✅ No database queries
- ✅ No network calls

## Architecture

```
playback_service.is_playback_active()
        ↓
        └─→ midi_input_manager.set_playback_status_callback()
                ↓
                └─→ usb_midi_service.set_playback_status_callback()
                        ↓
                        └─→ _processing_loop() checks callback
                                ↓
                                └─→ midi_event_processor.handle_message(update_leds=False/True)
                                        ↓
                                        └─→ _handle_note_on(update_leds=...)
                                        └─→ _handle_note_off(update_leds=...)
```

## Files to Monitor During Testing

1. **Backend Logs:**
   - Check for "Registered playback status callback" message
   - Monitor LED update suppression logs

2. **Browser Console:**
   - Check for any MIDI-related errors
   - Verify device dropdown works

3. **Network Tab:**
   - Verify playback status updates
   - Check MIDI event messages are still sent

## Success Criteria

- ✅ Keyboard LEDs work when idle
- ✅ Keyboard LEDs suppressed during playback
- ✅ Playback LEDs display correctly
- ✅ No visual conflicts
- ✅ Backend logs show suppression
- ✅ No performance degradation
