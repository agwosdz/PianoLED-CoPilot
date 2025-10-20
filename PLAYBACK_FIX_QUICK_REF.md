# Quick Reference: Backend Playback API

## What Changed?
✅ Fixed 6 bugs in `backend/api/play.py` that were preventing playback

## Key Fixes

| Bug | Was | Now | Location |
|-----|-----|-----|----------|
| Service access | `current_app.playback_service` | `current_app.config.get('playback_service')` | /playback-status |
| Filename property | `current_file` (doesn't exist) | `filename` | /playback-status |
| Progress prop | `progress_percentage` (doesn't exist) | Calculated from time/duration | /playback-status |
| Play method | `play()` (wrong) | `load_midi_file()` + `start_playback()` | /play |
| Pause method | `pause()` (wrong) | `pause_playback()` | /pause |
| Stop method | `stop()` (wrong) | `stop_playback()` | /stop |
| File directory | `./uploaded_midi/` (inconsistent) | `./backend/uploads/` (consistent) | /uploaded-midi-files |

## Test It
1. Restart backend
2. Select a MIDI file from the browser
3. Click Play
4. ✅ Debug should show "Playing: true" and time advancing
5. ✅ Playbar should show duration

## Files Changed
- `backend/api/play.py` (7 locations fixed)

## If It Doesn't Work
- Check browser console (Network tab)
- Verify `/api/playback-status` returns `"state": "playing"`
- Verify `total_duration > 0`
- Check backend logs: `tail -f backend.log`
