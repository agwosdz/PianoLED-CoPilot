# Learning Mode Analysis: learnmidi.py vs Current Implementation

## Key Insights from learnmidi.py

The reference implementation (`learnmidi.py`) is a mature, working learning/practice system that has proven effective. Here's what it does well and what we can learn:

---

## 1. **Critical Pattern: Active Waiting Loop with Blocking**

### learnmidi.py Approach (Lines 251-339):
```python
while not set(notes_to_press).issubset(notes_pressed) and self.is_started_midi:
    # Active checking loop - BLOCKS THE PLAYBACK THREAD
    while self.midiports.midi_queue:
        msg_in, msg_timestamp = self.midiports.midi_queue.popleft()
        # Check if note is in required set
        if note not in notes_to_press:
            wrong_notes.append(msg_in)
            continue
        
        if velocity > 0:
            if note not in notes_pressed:
                notes_pressed.append(note)
        else:
            notes_pressed.remove(note)
    
    # Handle wrong notes visualization
    self.handle_wrong_notes(wrong_notes, hand_hint_notesL, hand_hint_notesR)
    wrong_notes.clear()
```

**Key Characteristics:**
- ✅ **Fully synchronous blocking** - waits for user input before proceeding
- ✅ **No complex timing logic** - simple set comparison (`set.issubset()`)
- ✅ **Queue-based MIDI input** - drains queue each cycle
- ✅ **Wrong note feedback** - immediately visual feedback
- ✅ **LED updates during wait** - refresh happens inside wait loop

### Our Current Approach:
- ⚠️ Tries to **non-blocking** pause (check then continue)
- ⚠️ Complex timing window logic (timing_window_ms calculation)
- ⚠️ Separate note tracking from MIDI input manager
- ⚠️ Expects notes to be recorded passively

---

## 2. **The Core Problem in Our Implementation**

### Why It's Not Working:

Our current flow:
```
1. MIDI input received → midi_input_manager._update_active_notes()
2. Calls playback_service.record_midi_note_played() [SEPARATE THREAD]
3. Playback loop checks _check_learning_mode_pause() [MAIN PLAYBACK THREAD]
4. Pause decision based on accumulated notes in _left_hand_notes_played set
```

**Issues:**
1. **Race condition**: MIDI input manager records notes, but playback thread might check before notes are recorded
2. **No queue management**: Notes are added to sets, but there's no "fresh" check per timing window
3. **Passive vs Active**: We expect notes to arrive; learnmidi.py actively waits and processes
4. **Timing logic too complex**: Multiple timing checks instead of simple subset comparison

### learnmidi.py's Advantage:
```
1. Note event in MIDI file → identifies notes_to_press
2. BLOCKING WAIT: Process midi_queue until all notes_to_press received
3. Once satisfied → proceed to next note event
4. Thread PAUSES here - this is expected behavior!
```

**Advantages:**
- ✅ **Deterministic**: Blocked until user plays required notes
- ✅ **Simple**: Direct set comparison
- ✅ **No race conditions**: Single-threaded MIDI event processing
- ✅ **User feedback**: LED updates happen while waiting

---

## 3. **Architecture Mismatch**

### learnmidi.py Structure:
```
LearnMIDI class
├── load_midi() - parses MIDI file
├── learn_midi() - MAIN BLOCKING LOOP [SINGLE THREAD]
│   ├── Iterates through song_tracks
│   ├── For each note event:
│   │   ├── Shows note on LEDs
│   │   ├── Collects notes_to_press from event
│   │   ├── **BLOCKS: while not all notes_pressed**
│   │   │   ├── Drains midi_queue
│   │   │   ├── Checks each MIDI input
│   │   │   ├── Updates LEDs for wrong notes
│   │   │   └── Loops until satisfied
│   │   └── Plays software notes after user satisfies
│   └── Advances to next note
└── handle_wrong_notes() - visual feedback

Key: Single monolithic blocking thread - NO async/non-blocking complexity
```

### Our Current Structure:
```
PlaybackService
├── start_playback() - starts playback thread
├── _playback_loop() - MAIN LOOP [PLAYBACK THREAD]
│   ├── Non-blocking check: _check_learning_mode_pause()
│   ├── If pause needed → sleep 50ms and loop again
│   └── Continues playback
├── record_midi_note_played() - called from MIDI input manager [SEPARATE THREAD]
│   └── Adds to sets (_left_hand_notes_played, etc)
└── _check_learning_mode_pause() - simple logic but not integrated

MIDIInputManager
└── Processes MIDI independently [SEPARATE THREAD]
    └── Calls record_midi_note_played()

Key: Multi-threaded with attempt at non-blocking pause - causing sync issues
```

---

## 4. **Recommended Fixes (In Priority Order)**

### **Fix #1: Reset Notes at Timing Window Start** ⭐⭐⭐ CRITICAL
The current implementation accumulates notes globally. We need to reset them per timing window.

**Current Problem:**
```python
self._left_hand_notes_played: set = set()  # Global accumulator
self._right_hand_notes_played: set = set()  # Never cleared
```

If timing_window_ms = 500ms, and user plays a note at time 0, it's still in the set at time 2s. This causes false positives!

**Solution:**
```python
def _check_learning_mode_pause(self) -> bool:
    # ... find expected_left_notes, expected_right_notes for current timing window ...
    
    # RESET notes for THIS window - don't use global accumulator!
    current_window_notes_left = set()
    current_window_notes_right = set()
    
    # Scan through recently received notes (need a timestamped queue, not just a set)
    # Only include notes within timing_window from current_time
    
    # Check with fresh window data
    left_satisfied = expected_left_notes.issubset(current_window_notes_left)
    right_satisfied = expected_right_notes.issubset(current_window_notes_right)
```

**Why learnmidi.py doesn't have this problem:**
- It checks a fresh `notes_pressed` list for EACH note event
- That list is cleared after each event is satisfied
- Fresh start for each musical phrase

---

### **Fix #2: Use a Timestamped Note Queue** ⭐⭐⭐ CRITICAL
Instead of accumulating in sets, keep a time-stamped queue of recent notes.

**Current:**
```python
def record_midi_note_played(self, note: int, hand: str) -> None:
    if hand == 'left':
        self._left_hand_notes_played.add(note)  # No timestamp!
```

**Improved:**
```python
from collections import deque

def __init__(self, ...):
    self._left_hand_notes_queue = deque()  # [(note, timestamp), ...]
    self._right_hand_notes_queue = deque()

def record_midi_note_played(self, note: int, hand: str) -> None:
    """Record a note with timestamp for learning mode window checking"""
    current_time = time.time()  # Or use self._current_time if available
    
    if hand == 'left':
        self._left_hand_notes_queue.append((note, current_time))
        # Keep only recent notes within 2x timing window for safety
        while (self._left_hand_notes_queue and 
               current_time - self._left_hand_notes_queue[0][1] > 2.0):
            self._left_hand_notes_queue.popleft()
    elif hand == 'right':
        self._right_hand_notes_queue.append((note, current_time))
        while (self._right_hand_notes_queue and 
               current_time - self._right_hand_notes_queue[0][1] > 2.0):
            self._right_hand_notes_queue.popleft()

def _check_learning_mode_pause(self) -> bool:
    # ... find expected notes ...
    
    timing_window_seconds = self._timing_window_ms / 1000.0
    window_start = self._current_time
    window_end = self._current_time + timing_window_seconds
    
    # Extract notes from queue that fall within this window's timeframe
    # (Use note-on timestamps)
    notes_in_left_window = {note for note, ts in self._left_hand_notes_queue
                            if window_start <= ts <= window_end}
    notes_in_right_window = {note for note, ts in self._right_hand_notes_queue
                             if window_start <= ts <= window_end}
    
    # Check satisfaction
    left_ok = expected_left_notes.issubset(notes_in_left_window)
    right_ok = expected_right_notes.issubset(notes_in_right_window)
    
    return not (left_ok and right_ok)
```

**Why this works:**
- Only counts notes within the current timing window
- Each window gets a fresh evaluation
- Automatically cleans up old notes
- Simple set comparison like learnmidi.py

---

### **Fix #3: Add Visual/Audio Feedback for Wrong Notes** ⭐⭐ IMPORTANT
learnmidi.py handles wrong notes with visual feedback (red LEDs). We have this in UI but not in playback logic.

**From learnmidi.py:**
```python
def handle_wrong_notes(self, wrong_notes, hand_hint_notesL, hand_hint_notesR):
    if self.show_wrong_notes != 1:
        return
    
    for msg in wrong_notes:
        note = int(find_between(str(msg), "note=", " "))
        note_position = get_note_position(note, self.ledstrip, self.ledsettings)
        if velocity > 0:
            self.ledstrip.strip.setPixelColor(note_position, Color(255, 0, 0))  # RED!
            self.mistakes_count += 1
```

**Our Implementation Needs:**
```python
def _check_learning_mode_pause(self) -> bool:
    # ... existing logic ...
    
    # NEW: Detect wrong notes being played
    wrong_notes = set()
    for note, _ in self._left_hand_notes_queue:
        if self._left_hand_wait_for_notes and note not in expected_left_notes:
            wrong_notes.add(note)
    
    for note, _ in self._right_hand_notes_queue:
        if self._right_hand_wait_for_notes and note not in expected_right_notes:
            wrong_notes.add(note)
    
    # Light up wrong notes in red
    if wrong_notes and self._led_controller:
        for note in wrong_notes:
            led_index = self._get_led_index_for_note(note)
            self._led_controller.turn_on_led(led_index, (255, 0, 0))  # Red for wrong
    
    return should_pause
```

---

### **Fix #4: Verify MIDI Input Manager is Actually Recording Notes**

The biggest unknown right now: Is `record_midi_note_played()` even being called?

**Diagnostic logging needed in `midi_input_manager.py`:**
```python
def _update_active_notes(self, event):
    # ... existing code ...
    
    if self._playback_service and hasattr(self._playback_service, 'record_midi_note_played'):
        hand = 'left' if event.note < 60 else 'right'
        self._playback_service.record_midi_note_played(event.note, hand)
        # ADD THIS LOGGING:
        logger.info(f"MIDI INPUT: Recorded {hand} hand note {event.note} in learning mode")
    else:
        logger.warning("Playback service reference not set or missing record_midi_note_played method")
```

**Test by:**
1. Enable learning mode (wait for right hand)
2. Start playback
3. Play a note on keyboard
4. Check logs for "MIDI INPUT: Recorded..." messages

---

## 5. **Implementation Priority**

### **Phase 1: Fix Note Accumulation (Today)**
1. Replace global sets with timestamped queues
2. Add window-based filtering in `_check_learning_mode_pause()`
3. Add diagnostic logging to confirm notes are being recorded

### **Phase 2: Improve User Feedback (Next)**
1. Add red LED feedback for wrong notes
2. Add WebSocket notification when pause happens
3. Add counter for wrong notes played

### **Phase 3: Optimization (Later)**
1. Consider if we need multiple timing windows or just one
2. Add configurable delay after all notes played before continuing
3. Performance tune the note queue cleanup

---

## 6. **Side-by-Side Comparison: Critical Logic**

### learnmidi.py - Waiting for Notes:
```python
while not set(notes_to_press).issubset(notes_pressed) and self.is_started_midi:
    # Process new MIDI input
    while self.midiports.midi_queue:
        msg_in, msg_timestamp = self.midiports.midi_queue.popleft()
        if note in notes_to_press:
            notes_pressed.append(note)  # Track as pressed
```

**Translation to our codebase:**
```python
while not self._are_learning_notes_satisfied(expected_notes):
    # Notes queue is processed by MIDI input manager (separate thread)
    # We just check the queue here
    if self._check_learning_mode_pause():
        time.sleep(0.05)  # Brief pause
        continue  # Loop again
    else:
        break  # All notes satisfied, proceed
```

---

## 7. **Summary: What learnmidi.py Got Right**

| Aspect | learnmidi.py | Our Implementation | Issue |
|--------|-------------|-------------------|-------|
| **Note Tracking** | Fresh list per event | Global accumulator | ❌ Notes persist across windows |
| **Timing Model** | Event-based blocking | Time-window based non-blocking | ⚠️ Complex, race-condition prone |
| **MIDI Queue** | Actively drained | Passively populated | ⚠️ Queue overflow possible |
| **User Feedback** | Visual (red LED) + counter | Logging only | ❌ User doesn't know they're wrong |
| **Threading** | Single thread blocking | Multi-thread non-blocking | ⚠️ Sync issues |
| **Simplicity** | Set subset comparison | Complex window logic | ⚠️ Over-engineered |

---

## 8. **Proposed Quick Wins**

### Win #1: Fix Note Reset
**File:** `backend/playback_service.py`
**Change:** Add per-window note filtering in `_check_learning_mode_pause()`
**Expected Result:** Notes only count within their timing window
**Time to Fix:** 10 minutes
**Risk:** Low

### Win #2: Add Diagnostic Logging
**Files:** `midi_input_manager.py`, `playback_service.py`
**Change:** Add INFO-level logging at key decision points
**Expected Result:** Clear visibility into what's happening
**Time to Fix:** 5 minutes
**Risk:** None (debug only)

### Win #3: Add Timestamped Queue
**File:** `backend/playback_service.py`
**Change:** Replace sets with deques, filter by timestamp
**Expected Result:** Clean separation of timing windows
**Time to Fix:** 15 minutes
**Risk:** Medium (needs testing)

---

## Next Steps

1. ✅ **Run diagnostic logs** to confirm notes are being recorded
2. 🔧 **Implement timestamped queue** for per-window note tracking
3. ✨ **Add visual feedback** for wrong notes (red LED)
4. 🧪 **Test with actual MIDI input** to verify pause works

Would you like me to implement these fixes starting with the timestamped queue approach?
