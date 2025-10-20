# MIDI Playback Isolation - Initialization Verification

## Initialization Chain

The system must initialize services in the correct order for LEDs to work when playback is inactive.

### Correct Order

```
1. PlaybackService created
   └─ Has: _state = PlaybackState.IDLE
   └─ Method: is_playback_active() → returns False

2. MIDIInputManager created (singleton)
   └─ Has: _playback_status_callback = None
   └─ Has: _usb_service = None

3. LED Controller created
   └─ Initializes: Physical LED interface
   └─ num_pixels set correctly

4. MidiEventProcessor created (inside USB service)
   └─ References: LED controller
   └─ Has: _led_controller reference

5. USBMIDIInputService created (by MIDIInputManager.initialize_services())
   └─ References: LED controller
   └─ References: MidiEventProcessor
   └─ Has: _playback_status_callback = None

6. Callback Registered
   └─ midi_input_manager.set_playback_status_callback(playback_service.is_playback_active)
   └─ Propagates to: usb_midi_service
   └─ USB service now has: _playback_status_callback = playback_service.is_playback_active

7. USB Service Starts Listening
   └─ MIDI messages can be received
   └─ LED updates can happen
```

## Verification Checklist

### 1. Check PlaybackService

**Code location:** `backend/app.py` line 146
**Expected log:**
```
INFO: PlaybackService initialized with 246 LEDs, MIDI output: False
```

**If missing:**
- PlaybackService failed to initialize
- Check error logs for PlaybackService.__init__ exceptions

**Verify method exists:**
```python
assert hasattr(playback_service, 'is_playback_active')
assert callable(playback_service.is_playback_active)
assert playback_service.is_playback_active() == False  # Should be False on startup
```

### 2. Check MIDIInputManager

**Code location:** `backend/app.py` line 147
**Expected log:**
```
INFO: Unified MIDI Input Manager initialized
INFO: Broadcasting initial status update...
```

**If missing:**
- MIDIInputManager failed to initialize (singleton)
- Check if MIDIInputManager import is None

**Verify:**
```python
assert midi_input_manager is not None
assert hasattr(midi_input_manager, '_playback_status_callback')
```

### 3. Check LED Controller

**Code location:** `backend/app.py` lines 95-106
**Expected log:**
```
INFO: LED controller and effects manager initialized successfully with 246 LEDs
```

**If missing:**
- LEDs disabled or hardware not available
- Check if led.enabled = False in settings

**Verify:**
```python
assert led_controller is not None
assert led_controller.num_pixels == 246  # or your LED count
```

### 4. Check MidiEventProcessor Created

**Code location:** `backend/usb_midi_service.py` line 76
**Expected log:**
```
INFO: MidiEventProcessor created (id=...)
```

**If missing:**
- USB MIDI service failed to initialize
- Check if mido library installed

**Verify:**
```python
assert hasattr(usb_midi_service, '_event_processor')
assert usb_midi_service._event_processor is not None
```

### 5. Check initialize_services()

**Code location:** `backend/app.py` line 155
**Expected log:**
```
INFO: USB MIDI service initialized (exclusive instance) [service_id=..., processor_id=...]
INFO: rtpMIDI service initialized
```

**If missing:**
- Services failed to initialize
- Check specific error messages in logs

**Verify:**
```python
assert midi_input_manager._usb_service is not None
assert midi_input_manager._rtpmidi_service is not None (if rtpMIDI enabled)
```

### 6. Check Callback Registration ⭐ CRITICAL

**Code location:** `backend/app.py` line 161
**Expected log:**
```
INFO: Registered playback status callback - USB MIDI LEDs will be suppressed during MIDI file playback
```

**If MISSING - This is the most common issue:**
- Callback registration failed or was skipped
- Check if playback_service is None
- Check if midi_input_manager is None

**Debug code:**
```python
print(f"playback_service: {playback_service}")
print(f"midi_input_manager: {midi_input_manager}")
print(f"playback_service.is_playback_active: {playback_service.is_playback_active if playback_service else 'N/A'}")
print(f"midi_input_manager._playback_status_callback: {midi_input_manager._playback_status_callback if midi_input_manager else 'N/A'}")
```

**Expected output:**
```
playback_service: <PlaybackService object>
midi_input_manager: <MIDIInputManager object>
playback_service.is_playback_active: <method>
midi_input_manager._playback_status_callback: <method>  # Should be playback_service.is_playback_active
```

### 7. Check USB Service Has Callback

**In processing loop:** `backend/usb_midi_service.py` line 338
**Expected log:**
```
DEBUG: USB MIDI processing loop started (processor_id=..., callback=set)
```

**If shows `callback=NOT SET`:**
- Callback not propagated to USB service
- Check `set_playback_status_callback()` method

**Verify:**
```python
print(f"usb_midi_service._playback_status_callback: {usb_midi_service._playback_status_callback}")
# Should NOT be None
assert usb_midi_service._playback_status_callback is not None
assert callable(usb_midi_service._playback_status_callback)
```

## Full Initialization Log Example

Here's what you should see on startup:

```
INFO: LED controller and effects manager initialized successfully with 246 LEDs
INFO: MidiEventProcessor created (id=12345678)
INFO: Unified MIDI Input Manager initialized
INFO: Broadcasting initial status update...
INFO: USB MIDI service initialized (exclusive instance) [service_id=87654321, processor_id=12345678]
INFO: rtpMIDI service initialized [...]
INFO: Registered playback status callback - USB MIDI LEDs will be suppressed during MIDI file playback
```

## Step-by-Step Verification

### On the Pi, Create This Test Script

Create `test_init.py`:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')

# Set up logging
from backend.logging_config import setup_logging
setup_logging()

from backend.playback_service import PlaybackService
from backend.midi_input_manager import MIDIInputManager
from backend.led_controller import LEDController
from backend.services.settings_service import SettingsService

print("\n=== Initialization Verification ===\n")

# 1. Settings Service
try:
    settings = SettingsService()
    print("✅ SettingsService: OK")
except Exception as e:
    print(f"❌ SettingsService: FAILED - {e}")
    sys.exit(1)

# 2. LED Controller
try:
    led = LEDController(settings_service=settings)
    print(f"✅ LEDController: OK ({led.num_pixels} LEDs)")
except Exception as e:
    print(f"❌ LEDController: FAILED - {e}")
    sys.exit(1)

# 3. PlaybackService
try:
    playback = PlaybackService(led_controller=led, settings_service=settings)
    print("✅ PlaybackService: OK")
    print(f"   - is_playback_active(): {playback.is_playback_active()}")
except Exception as e:
    print(f"❌ PlaybackService: FAILED - {e}")
    sys.exit(1)

# 4. MIDIInputManager
try:
    midi_manager = MIDIInputManager(led_controller=led, settings_service=settings)
    print("✅ MIDIInputManager: OK")
    print(f"   - _playback_status_callback: {midi_manager._playback_status_callback}")
except Exception as e:
    print(f"❌ MIDIInputManager: FAILED - {e}")
    sys.exit(1)

# 5. Initialize Services
try:
    midi_manager.initialize_services()
    print("✅ MIDIInputManager.initialize_services(): OK")
    print(f"   - USB service: {midi_manager._usb_service is not None}")
    print(f"   - rtpMIDI service: {midi_manager._rtpmidi_service is not None}")
except Exception as e:
    print(f"❌ initialize_services(): FAILED - {e}")
    sys.exit(1)

# 6. Register Callback
try:
    midi_manager.set_playback_status_callback(playback.is_playback_active)
    print("✅ Callback registered")
    print(f"   - midi_manager callback: {midi_manager._playback_status_callback}")
    print(f"   - USB service callback: {midi_manager._usb_service._playback_status_callback}")
except Exception as e:
    print(f"❌ Callback registration: FAILED - {e}")
    sys.exit(1)

# 7. Verify Callback Works
try:
    result = midi_manager.is_playback_active()
    print(f"✅ Callback execution: OK (result={result})")
except Exception as e:
    print(f"❌ Callback execution: FAILED - {e}")
    sys.exit(1)

print("\n✅ All initialization steps completed successfully!")
print("\nSystem is ready for:")
print("- MIDI input processing")
print("- LED updates")
print("- Playback isolation")
```

Run it:
```bash
cd /home/pi/PianoLED-CoPilot
python3 test_init.py
```

**Expected output:**
```
=== Initialization Verification ===

✅ SettingsService: OK
✅ LEDController: OK (246 LEDs)
✅ PlaybackService: OK
   - is_playback_active(): False
✅ MIDIInputManager: OK
   - _playback_status_callback: None
✅ MIDIInputManager.initialize_services(): OK
   - USB service: True
   - rtpMIDI service: True
✅ Callback registered
   - midi_manager callback: <method is_playback_active...>
   - USB service callback: <method is_playback_active...>
✅ Callback execution: OK (result=False)

✅ All initialization steps completed successfully!
```

## If You See Errors

### Error: "LED controller is None"
- LED controller failed to initialize
- Check if LEDs are disabled in settings
- Check if hardware libs available

### Error: "USBMIDIInputService initialization failed"
- mido library not installed or broken
- Check `python3 -c "import mido; print(mido.get_input_names())"`

### Error: "Callback registration FAILED"
- playback_service or midi_input_manager is None
- Check initialization order

### Error: "Callback execution FAILED"
- Exception thrown by is_playback_active()
- Check PlaybackState enum

## After Verification

Once all checks pass:

1. Restart the backend
2. Connect USB MIDI device
3. Try pressing keys
4. LEDs should light up
5. Check logs for "MIDI_PROCESSOR: NOTE_ON" messages

## Common Misconfigurations

### 1. Callback Not Called in Processing Loop

**Check:** Does USB service use callback correctly?

```python
# Should see in logs:
DEBUG: USB MIDI processing loop started (processor_id=..., callback=set)
# AND
DEBUG: USB MIDI raw message | ... | callback=INACTIVE
```

### 2. LED Controller Passes Through All Layers

**Check:** Does MidiEventProcessor have LED controller?

```python
# In MidiEventProcessor.__init__:
assert self._led_controller is not None  # Must not be None
```

### 3. PlaybackState Initialized Correctly

**Check:** Is initial state IDLE?

```python
# In PlaybackService.__init__:
assert self._state == PlaybackState.IDLE
assert self.is_playback_active() == False
```

## Summary

If LEDs aren't lighting up when playback is inactive:

1. ✅ Check "Registered playback status callback" in logs (CRITICAL)
2. ✅ Verify callback is set in USB service logs
3. ✅ Verify LED controller is not None
4. ✅ Run verification script above to confirm initialization

Once all these check out, the system should work correctly.
