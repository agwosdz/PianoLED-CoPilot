# Quick Test: Progression Fix Verification

**Changes Made**: Fixed note progression not advancing by extending timing window and handling empty expected notes

**Test This Now**: 5-minute verification

---

## What Was Fixed

### Problem 1: Timing window only looked forward
- **Before**: Checked `current_time` to `current_time + 0.5s`
- **After**: Checks `current_time - 1.0s` to `current_time + 0.5s`
- **Result**: Includes currently playing notes

### Problem 2: No handling for empty expected notes
- **Before**: If no notes expected, system would try to pause
- **After**: If no notes expected, automatically continues
- **Result**: Playback doesn't get stuck when skipping measures

### Problem 3: Added debugging to see what's happening
- **New**: DEBUG logs show exactly what notes are expected vs played
- **Result**: Easy to diagnose if there are still issues

---

## Test Now (5 Minutes)

### Step 1: Start Backend with Debug Logging
```bash
cd h:\Development\Copilot\PianoLED-CoPilot

# Option A: Set environment variable
set LOG_LEVEL=DEBUG
python -m backend.app

# Option B: Or just run normally (INFO level is sufficient)
python -m backend.app
```

### Step 2: Load MIDI File & Enable Learning Mode
1. Open frontend (http://localhost:5000)
2. Load a MIDI file (start with something simple)
3. Enable "Learning Mode" on playback page
4. Press Play

### Step 3: Watch What Happens
**Expected behavior**:
1. Playback PAUSES at first measure
2. LEDs show expected notes (dim colors - coral/blue)
3. Play the required notes on your keyboard
4. LEDs brighten as you play correctly
5. **When all notes played → Playback AUTO-ADVANCES**
6. Next measure starts
7. Repeat

### Step 4: Verify in Logs
```bash
# In another terminal, watch logs:
tail -f backend/logs/playback.log | grep "Learning mode"

# You should see progression like:
# DEBUG [0.10s]: Expected L:[60, 62, 65] R:[72, 76], Played L:[], Satisfied: False
# DEBUG [0.20s]: Expected L:[60, 62, 65] R:[72, 76], Played L:[60, 62, 65], Satisfied: True
# INFO: ✓ All required notes satisfied
# DEBUG [0.50s]: Expected L:[64, 67] R:[71], ...  (NEW MEASURE!)
```

---

## Verification Checklist

| Check | What to Look For | Status |
|-------|---|---|
| **Playback pauses** | First measure stops playing | ✓/✗ |
| **LEDs show notes** | Dim coral (left) or blue (right) colors | ✓/✗ |
| **LEDs brighten** | Each played note makes LED brighter | ✓/✗ |
| **Auto-advances** | Playback continues without user clicking anything | ✓/✗ |
| **Next measure shows** | New expected notes appear on LEDs | ✓/✗ |
| **No manual intervention** | Can play 3+ measures straight through | ✓/✗ |
| **Logs show progress** | DEBUG logs show changing times/expected notes | ✓/✗ |

---

## If Progression Still Doesn't Work

### Check 1: Are there notes in the MIDI file?
```bash
grep "Learning mode check" backend/logs/playback.log | head -5

# Should show Expected with note numbers, like:
# Expected L:[60, 62, 65]

# If you see:
# Expected L:[] R:[]
# → Problem: No notes found in timing window
```

### Check 2: Is time progressing at all?
```bash
grep "check at" backend/logs/playback.log | tail -20

# Times should increase: 0.10 → 0.11 → 0.12 ... 0.50 → 0.51
# If stuck at one time: Playback is paused and not advancing
```

### Check 3: Are user notes being recorded?
```bash
grep "record_midi_note\|Played L:" backend/logs/playback.log | head -10

# Should show user's played notes like:
# Played L:[60, 62, 65]

# If empty: MIDI input not reaching backend
```

### Check 4: Is satisfaction being detected?
```bash
grep "Satisfied:" backend/logs/playback.log | head -10

# Should show transition from False → True:
# Satisfied: False
# Satisfied: False
# Satisfied: True  ← This triggers auto-advance
```

---

## Common Scenarios After Fix

### Scenario 1: ✅ Progression Works
```
[User plays note 60] 
DEBUG: Played L:[60], Satisfied: False
DEBUG: Played L:[60, 62], Satisfied: False
DEBUG: Played L:[60, 62, 65], Satisfied: True
INFO: ✓ All required notes satisfied
[Playback auto-advances to next measure]
```

### Scenario 2: ❌ Time Not Progressing
```
DEBUG: check at 0.10s: Expected L:[60] ...
DEBUG: check at 0.10s: Expected L:[60] ...  ← STUCK at 0.10s
DEBUG: check at 0.10s: Expected L:[60] ...

Fix: Check if user is paused, try playing notes
```

### Scenario 3: ❌ No Notes Found
```
DEBUG: check at 0.10s: Expected L:[] R:[] ...

Fix: Check MIDI file has notes, try different file
```

### Scenario 4: ✅ Progressing but Need to Play Notes
```
DEBUG: check at 0.10s: Expected L:[60]
[You don't play anything]
DEBUG: check at 0.50s: No expected notes, continuing playback ← AUTO-CONTINUES!

This is correct - if no notes expected, playback continues
```

---

## If You Want More Detailed Logging

Edit `backend/playback_service.py` and add these lines around line 905:

```python
logger.info(f"=== LEARNING MODE CHECK START ===")
logger.info(f"Current time: {self._current_time:.2f}s")
logger.info(f"Window: {window_start:.2f}s to {window_end:.2f}s")
logger.info(f"Total events in file: {len(self._note_events)}")

# After finding expected notes:
logger.info(f"Expected notes found: {expected_left_notes | expected_right_notes}")

# After checking played notes:
logger.info(f"Played notes found: {played_left_notes | played_right_notes}")

logger.info(f"=== CHECK COMPLETE: Satisfied={all_satisfied} ===")
```

This will give you detailed per-check information in logs.

---

## Test Files

If your MIDI file isn't working, create a simple test:

```python
# Simple test MIDI (1 measure, 4 notes):
# Time 0.0: Note 60 (C)
# Time 0.25: Note 62 (D)
# Time 0.50: Note 64 (E)
# Time 0.75: Note 67 (G)
# Duration: 1.0 second

# When you load this:
# - Playback pauses at 0.0
# - You play C, D, E, G
# - All 4 play → Satisfaction reached
# - Playback continues past 1.0 (moves to next measure or ends)
```

---

## Code Reference

**File**: `backend/playback_service.py`
**Method**: `_check_learning_mode_pause()`
**Lines**: 882-1014

**Key Changes**:
- Line 911: Window start now `self._current_time - 1.0` (includes past notes)
- Lines 974-988: Added debug logging
- Lines 1013-1015: Auto-continue when no expected notes

---

## Success Indicators

After fix, you should see in logs:
- ✅ Times progressing: `0.10s → 0.11s → ... → 0.50s → 0.51s`
- ✅ Expected notes found: `Expected L:[60, 62, 65]`
- ✅ User notes recorded: `Played L:[60, 62, 65]`
- ✅ Satisfaction achieved: `Satisfied: True`
- ✅ Auto-advance: `✓ All required notes satisfied`
- ✅ Next measure: `No expected notes at 0.50s, continuing playback`

---

## Report Back With

If progression still isn't working after this fix, please provide:

1. **First 10 lines of logs**:
   ```bash
   grep "Learning mode check" backend/logs/playback.log | head -10
   ```

2. **Current time range**:
   ```bash
   grep "check at" backend/logs/playback.log | head -5 && echo "..." && grep "check at" backend/logs/playback.log | tail -5
   ```

3. **Expected vs played**:
   ```bash
   grep "Expected L:" backend/logs/playback.log | head -3
   grep "Played L:" backend/logs/playback.log | head -3
   ```

4. **Satisfaction transitions**:
   ```bash
   grep "Satisfied:" backend/logs/playback.log | head -20
   ```

---

**Next**: Run test and let me know if progression is now working! 🎹
