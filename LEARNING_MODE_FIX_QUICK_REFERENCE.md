# Learning Mode Fix - Quick Reference

## 🎯 Problem Solved
**Old Issue:** Learning mode pause wasn't working - playback never paused even when "Wait for MIDI Notes" was enabled.

**Root Cause:** Notes accumulated in global sets and never reset, causing timing window checks to include stale data from earlier in the song.

**Solution:** Implemented timestamped note queues that automatically filter notes to the current timing window and clean up old notes.

---

## 🔧 Three Critical Changes

### Change #1: Timestamped Queues
```python
# BEFORE (BROKEN):
self._left_hand_notes_played: set = set()  # Accumulates forever

# AFTER (FIXED):
self._left_hand_notes_queue: deque = deque()  # [(note, timestamp), ...]
```
**Why it works:** Notes older than 5 seconds auto-delete. Each timing window evaluates fresh data.

### Change #2: Per-Window Filtering
```python
# BEFORE (BROKEN):
left_satisfied = expected_left_notes.issubset(self._left_hand_notes_played)

# AFTER (FIXED):
# Extract only notes within current window:
played_left_notes = {note for note, ts in queue if window_start <= ts <= window_end}
left_satisfied = expected_left_notes.issubset(played_left_notes)
```
**Why it works:** Only counts notes that belong in the current timing window.

### Change #3: Enhanced Logging
```python
# BEFORE (HIDDEN):
logger.debug(f"Learning mode: Waiting for left hand. ...")

# AFTER (VISIBLE):
logger.info(f"[LEARNING MODE] LEFT hand note {note} recorded, queue size: {len(queue)}")
logger.info(f"Learning mode: Waiting for left hand at {time:.2f}s. Expected: [...], Played: [...]")
```
**Why it works:** INFO level ensures logs are visible by default for debugging.

---

## 📊 The Flow Now Works Like This

```
1. User presses note on keyboard
   ↓
2. MIDI input manager receives event
   ↓
3. Calls playback_service.record_midi_note_played(note, hand)
   ↓
4. Playback service adds (note, timestamp) to queue
   ↓
5. Next playback loop iteration checks _check_learning_mode_pause()
   ↓
6. Method extracts notes from queue within timing window only
   ↓
7. Compares with expected notes: subset check
   ↓
8. If all expected notes played → pause releases → playback resumes
   ↓
9. If not all notes → pause continues → playback waits
```

---

## ✅ How to Know It's Working

**Check 1:** After startup, see this in logs:
```
INFO: ✓ Playback service reference registered for learning mode integration
```

**Check 2:** Play a MIDI note, see this in logs:
```
INFO: [LEARNING MODE] RIGHT hand note 72 recorded for playback service
INFO: Learning mode: Right hand played note 72, queue size: 1
```

**Check 3:** Load MIDI file with learning mode enabled, see this in logs:
```
INFO: Learning mode: Waiting for right hand at 1.23s. Expected: [72, 74], Played: []
```

**Check 4:** After playing required notes, see the pause release:
```
DEBUG: Playback resumed (if you had manual pause)
```

---

## 🧪 One-Line Test

1. Enable "Wait for Right Hand" on Play page
2. Load any MIDI file
3. Start playback
4. **Playback should pause (LEDs stop moving)**
5. Play any note on keyboard
6. **Playback should resume (LEDs continue)**

**That's it!** If this works, the fix is working.

---

## 📁 Files Changed

| File | Change | Why |
|------|--------|-----|
| `backend/playback_service.py` | Added deque import, replaced note sets with queues, rewrote pause check | Core fix - implements per-window filtering |
| `backend/midi_input_manager.py` | Enhanced logging in set_playback_service() and _update_active_notes() | Debugging visibility |

---

## 🔄 How Cleanup Works

```python
# Every time a note is recorded:
current_time = time.time()

# Cleanup runs every 1 second (not every note):
if current_time - last_cleanup > 1.0:
    # Remove notes older than 5 seconds
    while queue and current_time - queue[0][1] > 5.0:
        queue.popleft()
    last_cleanup = current_time
```

**Example Timeline:**
- 0s: Play note 72 → queue = [(72, 0)]
- 1s: Cleanup runs, note is 1s old (< 5s) → queue = [(72, 0)]
- 5s: Cleanup runs, note is 5s old (= 5s) → queue = [(72, 0)]
- 6s: Cleanup runs, note is 6s old (> 5s) → queue = [] ✓ Cleaned up

---

## 🎯 Timing Window Example

Assume timing_window_ms = 500ms (0.5 seconds)

**Current playback time: 2.50s**
- Window range: 2.50s to 3.00s
- Expected notes in file within this range: [72, 74]
- User must play 72 and 74 for pause to release

**User plays at 2.45s:**
- Note is in acceptance window (2.00s to 3.00s) ✓
- But timing window hasn't started yet, so note counted for earlier pause

**User plays at 2.55s:**
- Note is in acceptance window AND timing window ✓
- Counts toward this pause

**User plays at 3.10s:**
- Note is after timing window
- Cleanup likely removed it by now
- Doesn't count for this pause

---

## 💡 Why This Approach Works Better

**Like learnmidi.py:**
- ✓ Simple set subset comparison (no complex state machines)
- ✓ Only recent notes matter
- ✓ Fresh evaluation each iteration
- ✓ Deterministic and testable

**Better than before:**
- ✓ Timestamped data (not just notes)
- ✓ Automatic cleanup (not manual)
- ✓ Per-window filtering (not global)
- ✓ Multi-threaded compatible (immutable tuples in queue)

---

## 🐛 If It Still Doesn't Work

**Most likely cause: Playback service not connected**
- Check: See "✓ Playback service registered" in logs?
- If not: Check `backend/app.py` line where `set_playback_service()` is called

**Second most likely: MIDI input not reaching service**
- Check: See "[LEARNING MODE]" logs when you play notes?
- If not: Check if MIDI input is working first (separate issue)

**Third: Window calculation wrong**
- Check: See "Expected: [...]" in logs? Are these notes correct?
- If not: File structure might be unusual, need to debug

---

## 🚀 Next Time You See Pause Issue

1. Open server logs (should be visible in terminal running `python -m backend.app`)
2. Look for:
   - `✓ Playback service registered` ← Integration working
   - `[LEARNING MODE]` ← Notes being recorded
   - `Waiting for left|right hand` ← Pause logic running
3. If any are missing, that's your problem area
4. Refer to Testing Guide for detailed test cases

---

**Implementation Status: ✅ COMPLETE**

Timestamped queues: ✓
Per-window filtering: ✓
Enhanced logging: ✓
Ready for testing: ✓

Good luck! 🎹

