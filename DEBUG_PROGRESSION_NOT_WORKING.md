# Debug Guide: Notes Not Progressing

**Issue**: Notes are not progressing on push (playback not advancing to next measure)

**Root Causes Identified & Fixed**:
1. ✅ Timing window was only looking forward (not including currently playing notes)
2. ✅ Empty expected notes set was blocking progression
3. ⏳ Need to verify with detailed logging

---

## What Was Fixed

### Fix 1: Timing Window Extended (Lines 905-918)

**Before**:
```python
window_start = self._current_time
window_end = self._current_time + timing_window_seconds
```

**After**:
```python
window_start = self._current_time - 1.0  # Look back 1 second
window_end = self._current_time + timing_window_seconds
```

**Why**: 
- Old: Only looked at notes starting AFTER current time
- New: Includes notes that started up to 1 second ago
- Result: Catches currently playing notes

### Fix 2: Handle Empty Expected Notes (Lines 976-988)

**Before**:
```python
if all_satisfied and (expected_left_notes or expected_right_notes):
    return False
# No handling for empty expected notes
```

**After**:
```python
if all_satisfied and has_expected_notes:
    return False
# NEW:
if not has_expected_notes:
    logger.debug(f"No expected notes at {self._current_time:.2f}s, continuing playback")
    return False
```

**Why**:
- Old: If no expected notes, would try to pause (wrong!)
- New: If no expected notes, automatically continues playback
- Result: Playback advances when no notes are needed

### Fix 3: Added Debug Logging (Lines 974-980)

```python
logger.debug(f"Learning mode check at {self._current_time:.2f}s: "
            f"Expected L:{sorted(expected_left_notes)} R:{sorted(expected_right_notes)}, "
            f"Played L:{sorted(played_left_notes)} R:{sorted(played_right_notes)}, "
            f"Satisfied: {all_satisfied}")
```

**Why**: Shows exactly what the system sees at each time point

---

## How to Test the Fix

### 1. Enable Debug Logging

Add this to your backend startup or config:
```bash
export LOG_LEVEL=DEBUG
python -m backend.app
```

Or modify `backend/app.py` to set logger level:
```python
logging.getLogger().setLevel(logging.DEBUG)
```

### 2. Check the Logs

Look for these patterns:

**Good** (should see this):
```
DEBUG [14:45:23] Learning mode check at 0.10s: Expected L:[60, 62, 65] R:[72, 76], Played L:[] R:[], Satisfied: False
DEBUG [14:45:23] Learning mode pausing at 0.10s
DEBUG [14:45:24] Learning mode check at 0.11s: Expected L:[60, 62, 65] R:[72, 76], Played L:[60, 62, 65] R:[72, 76], Satisfied: True
INFO  [14:45:24] Learning mode: ✓ All required notes satisfied at 0.11s. Left: [60, 62, 65], Right: [72, 76]
DEBUG [14:45:24] No expected notes at 0.15s, continuing playback
```

**Problem** (If you see this):
```
DEBUG [14:45:23] Learning mode check at 0.10s: Expected L:[] R:[], Played L:[] R:[], Satisfied: True
DEBUG [14:45:23] No expected notes at 0.10s, continuing playback
```
→ System isn't finding notes at all → Check MIDI file or timing

### 3. What Each Log Line Means

| Log | Meaning | Action |
|-----|---------|--------|
| `Expected L:[60] R:[]` | System found note 60 to play on left hand | ✓ Good |
| `Expected L:[] R:[]` | System found NO notes to play | ❌ Check window |
| `Played L:[60]` | User played note 60 | ✓ Good |
| `Played L:[]` | No notes recorded from user | ❌ Check MIDI input |
| `Satisfied: True` | All expected notes played | ✓ Will proceed |
| `Satisfied: False` | Still waiting for notes | ✓ Will pause |

---

## Diagnostic Checklist

### Step 1: Verify MIDI File Has Notes
```bash
# Check backend logs for note parsing
grep "Note" backend/logs/*.log | head -20
# Should show timing and note numbers
```

### Step 2: Check Learning Mode Settings
```bash
curl http://localhost:5000/api/playback/status | jq '.learning_mode'
# Should show:
# {
#   "enabled": true,
#   "left_hand_wait": true,
#   "right_hand_wait": true
# }
```

### Step 3: Watch Timing in Real-time
```bash
tail -f backend/logs/playback.log | grep "Learning mode check"
# Should show continuous checking like:
# Learning mode check at 0.10s: Expected L:[60, 62, 65] R:[72, 76]...
# Learning mode check at 0.11s: Expected L:[60, 62, 65] R:[72, 76]...
# Learning mode check at 0.50s: Expected L:[] R:[]...  (moved to next measure)
# Learning mode check at 0.51s: Expected L:[64, 67] R:[71]...  (new notes found!)
```

### Step 4: Check Current Time Progress
```bash
tail -f backend/logs/playback.log | grep "check at"
# Times should increase: 0.10s → 0.11s → 0.12s ... 0.50s → 0.51s
# If stuck at same time: playback is paused indefinitely (bug)
# If jumping: timing is correct
```

---

## Common Issues & Solutions

### Issue 1: "Learning mode check" logs never appear

**Cause**: Learning mode not enabled

**Solution**:
```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"learning_mode": {"enabled": true}}'
```

### Issue 2: Time stuck at 0.10s (not progressing)

**Cause**: Playback paused forever, no expected notes found

**Solution**:
1. Check MIDI file has notes: `grep "Expected L:\|Expected R:" logs.log`
2. Verify timing window: If notes are beyond 1 second, they won't show
3. Try loading a different MIDI file (test file)

### Issue 3: "Expected L:[] R:[]" at every timestamp

**Cause**: MIDI file parser isn't loading notes correctly

**Solution**:
1. Check file exists and is valid MIDI
2. Look for parse errors: `grep -i "error\|exception" logs.log`
3. Try simpler MIDI file (single measure)

### Issue 4: User plays notes but "Played L:[]" shows empty

**Cause**: MIDI input not being recorded

**Solution**:
1. Check MIDI device is connected: `grep "MIDI" logs.log`
2. Verify notes reaching backend: `grep "record_midi_note" logs.log`
3. Check learning mode settings has hands enabled

---

## Step-by-Step Debug Process

### 1. Start Fresh
```bash
# Kill existing backend
# Remove old logs
rm -f backend/logs/*

# Start backend with DEBUG logging
export LOG_LEVEL=DEBUG
python -m backend.app
```

### 2. Load MIDI File & Enable Learning Mode
```bash
# In frontend or via API:
# 1. Load test MIDI file (start with 1-2 measures)
# 2. Enable learning mode
# 3. Press play
```

### 3. Watch Logs in Real-time
```bash
tail -f backend/logs/playback.log | grep "Learning mode"
```

### 4. Expected Sequence
```
[Time 0.00] Learning mode check: Expected L:[60, 62] R:[72, 76]
[Time 0.05] Learning mode check: Expected L:[60, 62] R:[72, 76], Played L:[], R:[]
[Time 0.10] Learning mode pausing at 0.10s
[User plays notes]
[Time 0.15] Learning mode check: Played L:[60, 62] R:[72, 76], Satisfied: True
[Time 0.15] ✓ All required notes satisfied
[Time 0.15] Cleared satisfied notes from queues
[Time 0.20] Learning mode check: Expected L:[64, 67] R:[71] (NEXT MEASURE!)
[Time 0.20] Learning mode pausing at 0.20s
```

### 5. If Stuck
```bash
# Check current time with:
grep "at.*\..*s" backend/logs/playback.log | tail -20
# Should show increasing times

# If time is stuck, playback is paused
# Check why by looking for:
grep "should_pause\|return True\|return False" backend/logs/playback.log
```

---

## Advanced Debugging

### Check Timing Window Calculation
Add this to `_check_learning_mode_pause()` near line 906:

```python
logger.info(f"Timing window: {window_start:.2f}s to {window_end:.2f}s, "
           f"Looking for {len(self._note_events)} total events")
events_in_window = [e for e in self._note_events if window_start <= e.time < window_end]
logger.info(f"Found {len(events_in_window)} events in window: {events_in_window}")
```

### Check Queue State
Add after line 990:

```python
logger.info(f"Queue state: "
           f"left_queue_size={len(self._left_hand_notes_queue)}, "
           f"right_queue_size={len(self._right_hand_notes_queue)}, "
           f"oldest_left={(self._left_hand_notes_queue[0][1] if self._left_hand_notes_queue else 'empty')}, "
           f"oldest_right={(self._right_hand_notes_queue[0][1] if self._right_hand_notes_queue else 'empty')}")
```

---

## Expected Behavior After Fix

1. **Start playback** → Pauses at measure 1
2. **LEDs show expected notes** in dim colors
3. **Play notes** → Each note brightens LED
4. **All notes played** → All LEDs bright
5. **Automatic clearing** → Queues reset
6. **Automatic advancement** → Playback continues
7. **Measure 2 starts** → New expected notes shown
8. **Repeat** for each measure

---

## What to Report if Still Broken

If progression still isn't working, provide:

1. **Logs** (complete sequence):
   ```bash
   tail -50 backend/logs/playback.log > debug_logs.txt
   ```

2. **Current time progression**:
   ```bash
   grep "check at" backend/logs/playback.log | head -30
   ```

3. **Expected notes found**:
   ```bash
   grep "Expected L:" backend/logs/playback.log | head -30
   ```

4. **Satisfaction state**:
   ```bash
   grep "Satisfied:" backend/logs/playback.log | head -20
   ```

5. **Queue clearing**:
   ```bash
   grep "Cleared satisfied" backend/logs/playback.log
   ```

6. **MIDI input received**:
   ```bash
   grep "record_midi_note\|Played L:" backend/logs/playback.log | head -20
   ```

---

## Code Changes Summary

**File**: `backend/playback_service.py`

**Method**: `_check_learning_mode_pause()` (Lines 882-1014)

**Changes**:
1. Lines 905-918: Extended timing window to include past notes
2. Lines 974-988: Added debug logging and empty notes handling
3. Lines 1013-1015: Added auto-continue when no expected notes

**Impact**:
- ✅ Includes currently playing notes in window
- ✅ Doesn't pause when no notes expected
- ✅ Provides detailed logging for debugging

---

**Next Step**: Run the backend with DEBUG logging enabled and share the log output if progression still isn't working.
