# 🧪 Phase C Testing Quick Reference

**Status:** Ready to test  
**File Modified:** `backend/playback_service.py`  
**Changes:** Queue unification (QueuedNote dataclass + unified queue)

---

## 🎯 Key Changes to Verify

### 1. Queue Structure Changed ✓
**What Changed:**
- Old: Two separate queues (`_left_hand_notes_queue`, `_right_hand_notes_queue`)
- New: Single unified queue (`_note_queue`) with `QueuedNote` objects

**How to Verify:**
```python
# In playback_service.py __init__:
self._note_queue: deque = deque(maxlen=5000)  # Should be ONE queue

# NOT these (should be deleted):
# self._left_hand_notes_queue: deque
# self._right_hand_notes_queue: deque
```

### 2. Recording Method Updated ✓
**What Changed:**
- Old: Branching logic (`if hand == 'left':` ... `elif hand == 'right':`)
- New: Single append with QueuedNote dataclass

**How to Verify:**
```python
# In record_midi_note_played():
queued_note = QueuedNote(note=note, hand=hand, timestamp=playback_time)
self._note_queue.append(queued_note)

# NOT this:
# if hand == 'left':
#     self._left_hand_notes_queue.append((note, playback_time))
```

### 3. Filtering Method Added ✓
**What Changed:**
- New: `_get_queued_notes_in_window()` method consolidates extraction logic

**How to Verify:**
```python
# New method should exist:
def _get_queued_notes_in_window(self, start: float, end: float) -> tuple:
    """Extract notes from unified queue that fall within a timing window"""
    # ... implementation
    return played_left_notes, played_right_notes
```

### 4. Pause Check Updated ✓
**What Changed:**
- Old: Two separate loops extracting left and right notes
- New: Single method call to `_get_queued_notes_in_window()`

**How to Verify:**
```python
# In _check_learning_mode_pause():
played_left_notes, played_right_notes = self._get_queued_notes_in_window(start, end)

# NOT these:
# for note, timestamp in self._left_hand_notes_queue:
#     if acceptance_start <= timestamp <= acceptance_end:
#         played_left_notes.append(note)
```

---

## 🧬 Testing Scenarios

### Scenario 1: Basic Learning Mode Recording
**Test Steps:**
1. Enable learning mode via settings
2. Load MIDI file with simple notes (e.g., C-D-E)
3. Play notes on MIDI input during learning mode pause
4. Verify notes are recorded in `_note_queue`

**Expected Behavior:**
- Notes appear in `_note_queue` as `QueuedNote` objects
- Logging shows: `Queue now has N notes: [(note, timestamp), ...]`
- No errors about missing `_left_hand_notes_queue`

---

### Scenario 2: Learning Mode Pause/Resume
**Test Steps:**
1. Start playback with learning mode enabled
2. Playback pauses at first note (waiting for input)
3. Play correct note on MIDI input
4. Verify playback resumes
5. Verify note was cleared from queue

**Expected Behavior:**
- Playback pauses correctly
- Queue receives note
- After correct note: "Cleared satisfied notes from queue. Removed: 1, Remaining: N"
- Playback resumes

---

### Scenario 3: Queue Cleanup
**Test Steps:**
1. Enable learning mode
2. Play many notes during pause
3. Wait for cleanup interval (should be ~1 second)
4. Verify old notes are removed

**Expected Behavior:**
- Debug log: "Queue cleanup at X.XXs: removed N notes"
- Queue size decreases
- Older notes removed, newer notes preserved

---

### Scenario 4: Multiple Notes in Queue
**Test Steps:**
1. Enable learning mode
2. During pause, play multiple notes rapidly
3. Verify all notes in window are detected
4. Play required notes in sequence
5. Verify all cleared when satisfied

**Expected Behavior:**
- All notes captured in queue
- Correct notes identified from within timing window
- All notes removed together when required notes satisfied

---

### Scenario 5: LED Highlighting During Learning
**Test Steps:**
1. Enable learning mode with LED hardware
2. Trigger learning mode pause
3. Verify LEDs show expected notes (should work same as before)
4. Play wrong notes (outside expected range)
5. Verify LEDs show wrong note flash (should work same as before)

**Expected Behavior:**
- LED highlighting unchanged (Phase A already tested)
- Phase C changes don't affect LED display logic

---

## 🔍 Debugging Checklist

### If Learning Mode Pause Not Working
1. Check queue is being populated: Look for `"RECORDING NOTE:"` logs
2. Check filtering method exists: Search for `_get_queued_notes_in_window`
3. Check method returns correct tuple: Verify `played_left_notes, played_right_notes` format
4. Check window calculation: Verify `window_start` and `window_end` reasonable

### If Queue Growing Unbounded
1. Check `maxlen=5000` is set on deque initialization
2. Verify cleanup is being called: Look for `"Queue cleanup"` logs
3. Check cleanup filter is correct: Should use `qn.timestamp >= cutoff_time`

### If Notes Not Being Cleared
1. Check deque reconstruction: `self._note_queue = deque(qn for qn in ... if ...)`
2. Verify filtering: `qn.note not in notes_to_clear`
3. Check hand assignment: Verify `QueuedNote` has correct hand value

### If TypeError About QueuedNote
1. Verify dataclass imported: Should be defined before PlaybackService class
2. Verify all append calls use QueuedNote: `QueuedNote(note=..., hand=..., timestamp=...)`
3. Check no stray `(note, timestamp)` tuple appends remain

---

## 📊 Logging to Watch

### Key Log Lines (Verify These Appear)
```
✓ "Queue now has N notes: [(note, timestamp), ...]"           # Recording
✓ "Learning mode: Cleared satisfied notes from queue. Removed: N, Remaining: N"  # Clearing
✓ "Queue cleanup at X.XXs: removed N notes"                   # Cleanup
✓ "📊 Learning mode check ... Queue:N"                         # Pause check
```

### Key Log Lines (Should NOT Appear)
```
✗ "Left queue now has"                                        # Old dual-queue logging
✗ "Right queue now has"                                       # Old dual-queue logging
✗ "AttributeError: 'tuple' object has no attribute"          # Tuple vs QueuedNote
✗ "L.queue:N R.queue:N"                                       # Old dual-queue format
```

---

## 🎬 Quick Test Flow

```
1. Start backend: python -m backend.app
2. Open frontend in browser
3. Load MIDI file (e.g., simple 3-note test)
4. Enable learning mode
5. Start playback
6. Wait for pause (should happen at first note)
7. Play first note on MIDI input
   → Check: Log shows "RECORDING NOTE:", Queue grows
8. Play second and third notes
   → Check: All notes in queue, all detected correctly
9. Verify playback resumes after each correct note
   → Check: Log shows "Cleared satisfied notes", Queue shrinks
10. Verify LED highlighting works (should be unchanged)
11. Stop playback and check no errors in console
```

---

## ✅ Sign-Off Criteria

Before declaring Phase C **tested and verified**:

- [ ] Scenario 1 passed (basic recording)
- [ ] Scenario 2 passed (pause/resume)
- [ ] Scenario 3 passed (cleanup)
- [ ] Scenario 4 passed (multiple notes)
- [ ] Scenario 5 passed (LED highlighting)
- [ ] No AttributeError or TypeError
- [ ] All expected log lines appear
- [ ] No "Left queue" or "Right queue" log lines
- [ ] Playback timing unchanged
- [ ] CPU usage still at 60-75% reduction baseline

---

**Ready to Test:** ✅ YES  
**Phase C Code Status:** ✅ COMPLETE  
**Testing Status:** ⏳ READY TO START

