# MIDI Playback Isolation - Code Flow Documentation

## Initialization Flow

### Step 1: Services Created in `backend/app.py` (lines 140-156)
```
┌─────────────────────────────────────────────────────────────┐
│ Line 145: playback_service = PlaybackService(...)           │
│ Line 146: midi_input_manager = MIDIInputManager(...)        │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Line 151: midi_input_manager.initialize_services()         │
│ Creates: USB MIDI service, rtpMIDI service                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Line 155: midi_input_manager.set_playback_status_callback()│
│ Callback: playback_service.is_playback_active              │
└─────────────────────────────────────────────────────────────┘
```

### Step 2: Callback Registration
**Function:** `MIDIInputManager.set_playback_status_callback(callback)`
- Location: `backend/midi_input_manager.py`, lines ~173-183
- Stores callback: `self._playback_status_callback = callback`
- Propagates to USB service: `usb_service.set_playback_status_callback(callback)`

**Function:** `USBMIDIInputService.set_playback_status_callback(callback)`
- Location: `backend/usb_midi_service.py`, lines ~168-176
- Stores callback: `self._playback_status_callback = callback`
- Logs: "USB MIDI service playback status callback registered"

---

## Runtime Flow: Keyboard Input Processing

### When USB MIDI Message Arrives

```
┌──────────────────────────────────────────────────────┐
│ USB MIDI Device (Keyboard) sends note_on message    │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│ USBMIDIInputService._processing_loop()               │
│ Location: backend/usb_midi_service.py, line 338     │
│                                                      │
│ 1. Drain messages from port                         │
│ 2. For each message:                                │
│    - Check playback status                          │
│    - Pass update_leds flag to processor             │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│ Check Playback Status (lines 350-356)               │
│                                                      │
│ playback_active = False                             │
│ if self._playback_status_callback:                  │
│     playback_active = self._playback_status_callback()
│                                                      │
│ Calls: playback_service.is_playback_active()        │
│ Returns: True if state == PlaybackState.PLAYING    │
│          False otherwise                            │
└────────────┬──────────────────────────────────────────┘
             │
             ▼
      ┌──────┴──────┐
      │             │
   Playing      Not Playing
      │             │
      ▼             ▼
 ┌────────────┐ ┌──────────────┐
 │update_leds │ │update_leds   │
 │ = False    │ │ = True       │
 └─────┬──────┘ └──────┬───────┘
       │               │
       └───────┬───────┘
               │
               ▼
   ┌─────────────────────────────────┐
   │ MidiEventProcessor.handle_message()
   │ backend/midi/midi_event_processor.py
   │ Line 107: def handle_message(
   │              msg, timestamp, update_leds=True)
   └──────────┬────────────────────────┘
              │
              ▼
   ┌──────────────────────────────────┐
   │ Parse message type               │
   │ (note_on, note_off, etc.)        │
   └──────────┬───────────────────────┘
              │
              ▼
   ┌───────────────────────────────────────┐
   │ Route to handler with update_leds flag │
   │                                        │
   │ if note_on: _handle_note_on(...,      │
   │             update_leds=update_leds)  │
   │ else: _handle_note_off(...,           │
   │       update_leds=update_leds)        │
   └───────────┬─────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
    Playing          Not Playing
       │                │
       ▼                ▼
  ┌─────────┐      ┌──────────────┐
  │SKIP LEDs│      │Update LEDs   │
  │Process  │      │Normally      │
  │event    │      │              │
  └────┬────┘      └────┬─────────┘
       │                │
       ▼                ▼
    Handler Functions
    (lines ~333-390)
```

---

## Detailed: Handler Functions

### `_handle_note_on()` - Lines 333-371

```python
def _handle_note_on(self, note, velocity, channel, timestamp, update_leds=True):
    
    # Step 1: Map MIDI note to LED indices
    led_indices = self._map_note_to_leds(note)
    
    # Step 2: Calculate color and brightness
    color = self._get_note_color(note)
    brightness = self._velocity_to_brightness(velocity)
    final_color = tuple(...)
    
    # Step 3: CONDITIONAL LED UPDATE ⭐
    if self._led_controller and update_leds:  # ← Check update_leds flag
        logger.info("MIDI_PROCESSOR: NOTE_ON note=%d ...", note)
        for led_index in led_indices:
            self._led_controller.turn_on_led(led_index, final_color)
        self._led_controller.show()
    elif not update_leds:
        logger.debug("Skipping LED update for note %d (playback active)", note)
    
    # Step 4: Track active note (always done)
    self._active_notes[note] = {
        'velocity': velocity,
        'timestamp': timestamp,
        'led_indices': led_indices,
        ...
    }
    
    # Step 5: Return event (always done)
    return ProcessedMIDIEvent(...)
```

### `_handle_note_off()` - Lines 373-390

```python
def _handle_note_off(self, note, channel, timestamp, update_leds=True):
    
    # Step 1: Get previously tracked note info
    note_info = self._active_notes.pop(note, None)
    led_indices = note_info.get('led_indices') if note_info else []
    
    # Step 2: CONDITIONAL LED UPDATE ⭐
    if self._led_controller and led_indices and update_leds:
        logger.info("MIDI_PROCESSOR: NOTE_OFF note=%d ...", note)
        for led_index in led_indices:
            self._led_controller.turn_off_led(led_index)
        self._led_controller.show()
    elif not update_leds and led_indices:
        logger.debug("Skipping LED update for note %d (playback active)", note)
    
    # Step 3: Lookup LED mapping if not tracked
    if not led_indices:
        led_indices = self._map_note_to_leds(note)
    
    # Step 4: Return event (always done)
    return ProcessedMIDIEvent(...)
```

---

## Playback Status Check: `playback_service.is_playback_active()`

### Location
`backend/playback_service.py`, lines ~1031-1033

### Implementation
```python
def is_playback_active(self) -> bool:
    """Check if playback is currently active (playing, not paused or idle)"""
    return self._state == PlaybackState.PLAYING
```

### What Sets `_state`
```
PlaybackState enum:
- IDLE     = Playback not started or stopped
- PLAYING  = File is playing ✓ (returns True)
- PAUSED   = File is paused (returns False)
- ERROR    = Error occurred (returns False)

State transitions:
IDLE → PLAYING (start_playback)
       ↓
     PAUSED (pause_playback)
       ↓
     PLAYING (resume/start_playback)
       ↓
     IDLE (stop_playback)
```

---

## Call Chain Summary

### Full Call Chain for Keyboard Input During Playback

```
┌─ User presses key on USB MIDI keyboard
│
├─ mido library detects message
│
├─ USBMIDIInputService._processing_loop() (line 338)
│
├─ playback_active = playback_status_callback() (line 351)
│  └─ Calls: playback_service.is_playback_active() ✓
│     └─ Returns: True (state == PLAYING)
│
├─ MidiEventProcessor.handle_message(..., update_leds=False) (line 358)
│
├─ Determines message type (note_on) → calls _handle_note_on
│  └─ _handle_note_on(..., update_leds=False) (line 117)
│
├─ Checks: if self._led_controller and update_leds: (line 324)
│  └─ CONDITION FALSE because update_leds=False
│  └─ LEDs are NOT updated ✓
│
├─ Tracks active note (line 347) ✓
│
├─ Returns ProcessedMIDIEvent (line 353) ✓
│
├─ Event broadcast to WebSocket (line 363)
│  └─ Frontend still receives MIDI event info
│
└─ Processing complete - no LED changes
```

---

## State Diagram: Playback States

```
                ┌──────────────┐
                │    IDLE      │◄─────────────────────┐
                └──────┬───────┘                       │
                       │ start_playback()             │
                       │ (file loaded)                │
                       ▼                              │
                ┌──────────────┐                      │
        ┌──────►│   PLAYING    │                      │
        │       └──────┬───────┘                      │
        │              │                              │
        │ resume()      │ pause_playback()      stop_playback()
        │              ▼                       │      │
        │       ┌──────────────┐               │      │
        │       │    PAUSED    │───────────────┘      │
        │       └──────────────┘                      │
        │                                              │
        └──────────────────────────────────────────────┘

When state == PLAYING:
├─ is_playback_active() returns True
├─ Keyboard LEDs are SUPPRESSED
└─ Playback LEDs display normally

When state == PAUSED or IDLE:
├─ is_playback_active() returns False
├─ Keyboard LEDs work NORMALLY
└─ No playback LEDs visible
```

---

## Key Control Points

### 1. Registration Point
**File:** `backend/app.py`
**Line:** 155
**Code:** `midi_input_manager.set_playback_status_callback(playback_service.is_playback_active)`

### 2. Check Point
**File:** `backend/usb_midi_service.py`
**Lines:** 350-356
**What:** Check if playback is active before each MIDI message processing

### 3. Conditional LED Update Point
**File:** `backend/midi/midi_event_processor.py`
**Lines:** 324-325 (note_on), 381-383 (note_off)
**What:** Only update LEDs if `update_leds=True`

### 4. Playback Status Method
**File:** `backend/playback_service.py`
**Lines:** 1031-1033
**What:** Return whether playback is currently playing

---

## Debug Logging Points

```
1. Initialization:
   backend/app.py (line 156):
   "Registered playback status callback..."

2. During Processing:
   backend/usb_midi_service.py (line 354):
   "USB MIDI: Playback active - skipping LED update"

3. In Handler:
   backend/midi/midi_event_processor.py (line 327, 384):
   "Skipping LED update for note X (playback active)"

4. Normal Operation:
   backend/midi/midi_event_processor.py (line 321, 378):
   "MIDI_PROCESSOR: NOTE_ON/NOTE_OFF note=X ..."
```

---

## Error Handling

```python
# In _processing_loop (lines 351-354)
try:
    playback_active = self._playback_status_callback()
except Exception as e:
    logger.debug(f"Error checking playback status: {e}")
    # Default to False if callback fails
    playback_active = False

# Result: If callback fails, assumes playback NOT active
#         → LEDs will be updated normally
#         → Safe fallback
```

---

## Performance Characteristics

- **Check Frequency:** Once per MIDI message
- **Execution Time:** ~1 microsecond (boolean property check)
- **Memory Impact:** One callback reference (~8 bytes)
- **Call Overhead:** ~100 nanoseconds (function call)
- **LED Update Skipping:** Prevents 1-10ms of LED controller I/O

**Total Impact:** Negligible, with actual LED I/O savings during playback
