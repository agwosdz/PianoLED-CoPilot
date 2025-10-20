# Learning Mode Fix - Implementation Summary & Testing Guide

## ✅ Changes Implemented

### 1. **Timestamped Queue System** (CRITICAL FIX)
**File:** `backend/playback_service.py`

**Problem Fixed:**
- Old behavior: Notes accumulated in global sets forever
- New behavior: Notes stored with timestamps in queues, automatically cleaned up after 5 seconds

**Changes:**
```python
# BEFORE:
self._left_hand_notes_played: set = set()
self._right_hand_notes_played: set = set()

# AFTER:
from collections import deque
self._left_hand_notes_queue: deque = deque()  # [(note, timestamp), ...]
self._right_hand_notes_queue: deque = deque()
self._last_queue_cleanup = time.time()
```

**Why this matters:**
- Each timing window now gets only relevant notes
- Notes older than 5 seconds are automatically removed
- No more false positives from notes played earlier in the song

---

### 2. **Per-Window Note Filtering** (CRITICAL FIX)
**File:** `backend/playback_service.py` - `_check_learning_mode_pause()` method

**Problem Fixed:**
- Old behavior: Checked global note sets regardless of timing
- New behavior: Only counts notes within the current timing window (±acceptance window)

**Key Logic:**
```python
# Extract notes from queues that fall within the CURRENT timing window
acceptance_window_seconds = max(timing_window_seconds, 0.5)
acceptance_start = self._current_time - acceptance_window_seconds
acceptance_end = self._current_time + timing_window_seconds

for note, timestamp in self._left_hand_notes_queue:
    if acceptance_start <= timestamp <= acceptance_end:
        played_left_notes.add(note)

# Then simple check:
left_satisfied = expected_left_notes.issubset(played_left_notes)
```

**Why this works:**
- Matches learnmidi.py approach: simple set subset comparison
- Only counts fresh notes in the window
- Includes acceptance window for user reaction time
- No complex state machine needed

---

### 3. **Enhanced Diagnostic Logging**
**Files:** `backend/playback_service.py` and `backend/midi_input_manager.py`

**Changes:**
- Upgraded logs from `debug` to `info` level for visibility
- Added queue size tracking: "queue size: {len(queue)}"
- Added connection status verification in `set_playback_service()`
- Added ERROR-level logs for integration failures
- Added `[LEARNING MODE]` tags for easy grep searching

**Example logs you'll see:**
```
INFO: ✓ Playback service reference registered for learning mode integration
INFO: [LEARNING MODE] RIGHT hand note 72 recorded for playback service
INFO: Learning mode: Waiting for left hand at 1.23s. Expected: [48, 50], Played: [48]
INFO: Learning mode: Wrong notes played: [60, 62]
```

---

### 4. **Queue Cleanup & Memory Management**
**File:** `backend/playback_service.py` - `record_midi_note_played()` method

**Features:**
- Notes are stored with absolute timestamps (via `time.time()`)
- Cleanup runs every 1 second (not every note for performance)
- Removes notes older than 5 seconds automatically
- Logs queue size for monitoring

```python
# Periodic cleanup of old notes (older than 5 seconds)
if current_time - self._last_queue_cleanup > 1.0:  # Cleanup every 1 second
    while (self._left_hand_notes_queue and 
           current_time - self._left_hand_notes_queue[0][1] > 5.0):
        self._left_hand_notes_queue.popleft()
```

---

## 🧪 How to Test

### **Test Setup:**
1. Start the Flask backend: `python -m backend.app`
2. Monitor logs in real-time (grep for `LEARNING` or `INFO`)
3. Open the frontend Play/Learn page

### **Test Case 1: Verify Integration is Connected**

**Steps:**
1. Check server logs immediately after startup
2. Look for: `✓ Playback service reference registered for learning mode integration`

**Expected Output:**
```
INFO: Playback service reference registered for learning mode integration
```

**If you see:**
```
✗ Playback service reference set to None
```
→ Connection failed, check `backend/app.py` line where `set_playback_service()` is called

---

### **Test Case 2: MIDI Note Recording**

**Steps:**
1. Load a MIDI file and start playback
2. Enable "Wait for MIDI Notes" for right hand
3. Play a note on your keyboard (any MIDI device)
4. Check server logs

**Expected Output (for each note played):**
```
INFO: [LEARNING MODE] RIGHT hand note 72 recorded for playback service
INFO: Learning mode: Right hand played note 72, queue size: 1
```

**Diagnostic Checks:**
- Verify the hand is correct (left/right based on note number < 60)
- Verify queue size increases as you play more notes
- Verify queue size decreases over time (cleanup working)

**If no logs appear:**
→ MIDI input not reaching playback service, check:
1. Is MIDI input being received? (check USB MIDI logs)
2. Is playback service pointer set? (check Test Case 1)
3. Is `record_midi_note_played()` being called? (add print statement if needed)

---

### **Test Case 3: Pause Behavior - Single Note Expected**

**Setup:**
1. Find a simple MIDI file with just 1-2 notes per hand
2. Load file, start playback
3. Enable "Wait for MIDI Notes" for RIGHT hand only
4. Set timing window to 2000ms (2 seconds)

**Steps:**
1. Start playback
2. Do NOT play anything on keyboard
3. Observe: Playback should pause (no LED animations should advance)
4. Logs should show:
```
INFO: Learning mode: Waiting for right hand at 0.12s. Expected: [72, 74], Played: []
INFO: Learning mode: Waiting for right hand at 0.18s. Expected: [72, 74], Played: []
INFO: Learning mode: Waiting for right hand at 0.24s. Expected: [72, 74], Played: []
```

**Now play the expected notes:**
1. Play notes 72 and 74 on your keyboard
2. Observe: Playback should resume (continue to next phrase)
3. Logs should show:
```
INFO: [LEARNING MODE] RIGHT hand note 72 recorded for playback service
INFO: [LEARNING MODE] RIGHT hand note 74 recorded for playback service
INFO: Learning mode: Right hand played note 72, queue size: 1
INFO: Learning mode: Right hand played note 74, queue size: 2
```
→ After these notes are recorded, pause should release and playback continues

---

### **Test Case 4: Wrong Note Detection**

**Setup:**
1. Same as Test Case 3
2. Expected notes: [72, 74]

**Steps:**
1. Start playback (should pause waiting for right hand)
2. Play note 60 (wrong note - outside expected set)
3. Check logs - should show:
```
INFO: Learning mode: Wrong notes played: [60]
INFO: Learning mode: Waiting for right hand at 0.24s. Expected: [72, 74], Played: []
```
4. Then play correct notes 72, 74
5. Playback resumes

**Expected Behavior:**
- Wrong note doesn't satisfy the pause condition
- User can keep playing other notes while waiting
- Once correct notes are played, pause releases

---

### **Test Case 5: Timing Window Filtering**

**Setup:**
1. MIDI file with expected notes at time 5.00s: [72, 74]
2. Enable "Wait for MIDI Notes" for right hand
3. Set timing window to 1000ms (1 second)

**Steps:**
1. Start playback
2. When it reaches ~4.00s (before expected notes), pause should NOT occur
3. When it reaches ~5.00s, pause SHOULD occur (timing window: 5.00-6.00s)
4. When it reaches ~7.00s (well past timing window), pause should NOT occur anymore

**Why?**
- At 4.00s: timing window is [4.00-5.00], no expected notes in window
- At 5.00s: timing window is [5.00-6.00], expected notes ARE in window → pause
- At 7.00s: timing window is [7.00-8.00], expected notes were in past window, but old notes removed by cleanup → no pause

**Logs:**
```
DEBUG: Learning mode pausing at 5.01s
DEBUG: Learning mode pausing at 5.15s
DEBUG: Learning mode pausing at 5.30s
[user plays notes]
DEBUG: Learning mode pausing at 7.00s  # Should NOT appear if cleanup working
```

---

### **Test Case 6: Queue Cleanup Verification**

**Setup:**
1. Enable logging for queue operations
2. Play a note on keyboard at time 0s
3. Wait 6 seconds without playing anything else

**Expected Behavior:**
- At 1s: Cleanup runs, but note is < 5s old, stays in queue
- At 2-5s: Note still in queue (queue size: 1)
- At 6s: Cleanup runs, note is > 5s old, removed from queue (queue size: 0)

**Logs:**
```
INFO: Learning mode: Right hand played note 72, queue size: 1  # At 0s
# ... silence for 5 seconds ...
# At 6s:
INFO: Learning mode: Right hand played note 72, queue size: 0  # Queue cleaned up
```

---

## 🔍 What to Look For (Debugging Checklist)

| Issue | Check | Fix |
|-------|-------|-----|
| Pause not working at all | See "✓ Playback service registered" in logs? | Check `app.py` calls `set_playback_service()` |
| Pause working but wrong timing | See expected/played notes in logs? | Verify note counts match expectations |
| Queue not growing | See queue size increasing? | Verify MIDI input is working |
| Queue never shrinks | See queue size decreasing after 6s? | Cleanup logic may be failing |
| Wrong notes not detected | See "Wrong notes played:" in logs? | Feature working, light up red (TODO) |
| Playback never pauses | Expected notes in timing window? | Might be an edge case in window calculation |

---

## 🐛 Common Problems & Solutions

### **Problem: "Playback service reference set to None"**
**Cause:** Line in `app.py` that calls `set_playback_service()` is not executing
**Solution:** 
1. Check `backend/app.py` around line 160
2. Verify playback_service exists before calling
3. Verify MIDI input manager is initialized

### **Problem: No MIDI notes recorded**
**Cause:** MIDI input manager not calling `record_midi_note_played()`
**Solution:**
1. Check if playback_service reference is set (Test Case 1)
2. Verify MIDI input is working (check USB MIDI logs)
3. Check if note is within expected range (should see in logs)

### **Problem: Pause happens but never releases**
**Cause:** Expected notes in file don't match hand classification (< 60 = left, >= 60 = right)
**Solution:**
1. Check logs: "Expected: [notes]" - are these correct?
2. If not, MIDI file might have unconventional note assignment
3. Need to verify actual file structure

### **Problem: Pause releases too early**
**Cause:** Notes from previous section still in queue (cleanup not working)
**Solution:**
1. Verify timestamp-based filtering is working
2. Check acceptance_window calculation
3. Increase timing window or reduce acceptance window

---

## 📊 Expected Behavior Summary

### **With Learning Mode DISABLED:**
- ✓ Playback continues normally
- ✓ MIDI notes may be recorded but not used
- ✓ No pausing occurs

### **With Learning Mode ENABLED (Right Hand):**
- ✓ Playback pauses when notes appear in timing window
- ✓ Pause is released when user plays required notes
- ✓ Wrong notes don't satisfy pause condition
- ✓ Pause resumes if notes played but removed by cleanup

### **With Learning Mode ENABLED (Both Hands):**
- ✓ Both hands must satisfy conditions simultaneously
- ✓ If only one hand plays, playback stays paused
- ✓ Once both hands play required notes, playback continues

---

## 📝 Files Modified

1. **backend/playback_service.py**
   - Added `deque` import
   - Replaced note sets with timestamped queues (line ~140)
   - Updated `start_playback()` to clear new queues (line ~640)
   - Completely rewrote `record_midi_note_played()` with timestamping (line ~850)
   - Completely rewrote `_check_learning_mode_pause()` with window filtering (line ~880)
   - Added enhanced info-level logging throughout

2. **backend/midi_input_manager.py**
   - Enhanced `set_playback_service()` logging (line ~195)
   - Enhanced `_update_active_notes()` note recording logging (line ~568)
   - Changed from debug to info level for visibility

---

## ✨ Next Steps (Future Improvements)

1. **Red LED Feedback for Wrong Notes** (Medium Priority)
   - When wrong note detected, light it up in red
   - `_check_learning_mode_pause()` already detects wrong notes

2. **Mistake Counter & Feedback** (Low Priority)
   - Count mistakes and display to user
   - Reset after successful note sequence

3. **Audio Feedback** (Low Priority)
   - Beep or chime when wrong note played
   - Chime when correct notes played

4. **Performance Optimization** (Low Priority)
   - Pre-compute expected notes for each timing window
   - Cache window calculations to reduce CPU load

---

## 🚀 You're Ready to Test!

The critical fixes are in place. Start with **Test Case 1** to verify integration, then **Test Case 3** to verify pause behavior.

**Good luck!** 🎹

