# 🔍 Diagnostic: Notes Not Being Processed

**Issue**: Notes are not being processed / matched  
**Status**: Enhanced logging added for diagnosis  
**Next Step**: Run backend and share logs

---

## What Was Just Added

I've added **detailed verbose logging** to help us understand where the problem is:

### 1. In `record_midi_note_played()` (Line 866)
```python
logger.info(f"🎵 RECORDING NOTE: {note} ({hand} hand) at playback time {playback_time:.3f}s")
logger.info(f"   └─ {hand} queue now has {len(queue)} notes")
```

**What to look for**: Should show `🎵 RECORDING NOTE:` when you press keys

### 2. In `_check_learning_mode_pause()` (Every ~500ms)
```python
logger.info(f"📊 Learning mode check at {self._current_time:.2f}s:"
           f" Expected L:{sorted(expected_left_notes)} R:{sorted(expected_right_notes)}"
           f" | Played L:{sorted(played_left_notes)} R:{sorted(played_right_notes)}"
           f" | L.queue:{len(self._left_hand_notes_queue)} R.queue:{len(self._right_hand_notes_queue)}")
```

**What to look for**: Should show expected vs played notes

---

## Test Procedure (Now with Enhanced Logging)

### Step 1: Start Backend
```bash
python -m backend.app
```

### Step 2: In Another Terminal, Watch Logs
```bash
tail -f backend/logs/playback.log | grep -E "RECORDING|📊"
```

This will show ONLY the diagnostic messages.

### Step 3: Load MIDI & Enable Learning Mode
1. Open http://localhost:5000
2. Load MIDI file
3. Enable learning mode
4. Press play

### Step 4: Play Some Notes
When playback pauses, play the required notes.

---

## What To Look For

### Good Signs ✓
```
🎵 RECORDING NOTE: 60 (left hand) at playback time 0.50s
   └─ left queue now has 1 notes: [(60, '0.50s')]

📊 Learning mode check at 0.50s: Expected L:[60, 62, 65] R:[72] | Played L:[60] R:[] | L.queue:1 R.queue:0
```

### Problem Signs ❌

**No recording at all**:
```
(nothing shows up when you press keys)
```
→ Fix: `record_midi_note_played()` not being called

**Recording shows but queue empty**:
```
🎵 RECORDING NOTE: 60 (left hand) at playback time 0.50s
   └─ left queue now has 0 notes  ← WRONG!
```
→ Fix: Something clearing queue immediately

**Learning mode checks don't appear**:
```
(no 📊 messages at all)
```
→ Fix: Learning mode not enabled OR notes not getting through

**Queue shows notes but "Played" is empty**:
```
📊 Learning mode check at 0.50s: Expected L:[60, 62, 65] | Played L:[] | L.queue:1
```
→ Fix: Timing window not matching notes in queue

---

## Possible Issues to Check

### Issue 1: Learning Mode Not Enabled
```bash
# Check settings:
curl http://localhost:5000/api/settings | grep -A5 learning_mode
```

Should show:
```json
"learning_mode": {
  "enabled": true,
  "left_hand_wait": true,
  ...
}
```

**Fix if wrong**: Enable via UI or API

### Issue 2: No Recording Messages Appear
```bash
grep "RECORDING NOTE" backend/logs/playback.log
```

If empty: `record_midi_note_played()` not called

**Check**:
1. Is MIDI input working? (Press keys on keyboard)
2. Is playback_service connected? Check logs for "Registered playback"

### Issue 3: Queue Empty
```bash
grep "queue now has 0" backend/logs/playback.log
```

**Check**: Is something clearing the queue? Look for clearing logic

### Issue 4: Timing Window Not Matching
```bash
grep "Played L:\[\]" backend/logs/playback.log
```

Shows notes in queue but not being matched

**Check**: Are times in the acceptance window?

---

## Quick Diagnostics Commands

```bash
# Show all recording attempts
grep "RECORDING NOTE" backend/logs/playback.log

# Show all pause checks
grep "📊 Learning mode" backend/logs/playback.log

# Show errors
grep -i "error\|exception" backend/logs/playback.log | grep -i "learning\|record"

# Show learning mode loads
grep "Learning mode enabled" backend/logs/playback.log

# Show playback service connection
grep "Registered playback" backend/logs/playback.log
```

---

## How to Share Results

When you run the test, please provide:

1. **Full log output** (5-10 lines):
   ```bash
   tail -100 backend/logs/playback.log | grep -E "RECORDING|📊|Learning|Registered"
   ```

2. **When you pressed notes, did you see 🎵?**

3. **When playback was at time 0.5s, did you see📊?**

4. **What did the Expected vs Played show?**

---

## Most Likely Scenarios

### Scenario A: Notes Not Recording
`record_midi_note_played()` never called

**Why**: Playback service not connected to MIDI input manager

**Check**:
```bash
grep "Registered playback service" backend/logs/playback.log
```

**Fix**: Verify `set_playback_service()` called in app.py

### Scenario B: Notes Recording but Not Matching
Notes in queue but not appearing in "Played"

**Why**: Time window calculation wrong OR notes cleared too early

**Check**:
```bash
grep "queue now has" backend/logs/playback.log
grep "Played L:" backend/logs/playback.log
```

**Compare**: Do queue sizes match what appears in "Played"?

### Scenario C: Learning Mode Not Enabled
Settings not loaded properly

**Why**: Settings service not initialized OR learning mode disabled

**Check**:
```bash
grep "Learning mode enabled" backend/logs/playback.log
```

**Fix**: Enable learning mode via UI

---

## Next Steps

1. **Run with enhanced logging**: `python -m backend.app`
2. **Watch logs**: `tail -f backend/logs/playback.log`
3. **Load MIDI and enable learning mode**
4. **Press notes and watch for 🎵 and 📊**
5. **Share what you see**

---

**Key Points**:
- Look for `🎵 RECORDING NOTE` when you press keys
- Look for `📊 Learning mode check` every ~500ms
- Compare what's in "Played" vs "Expected"
- Share exact log output if not working

Ready to test! 🎹
