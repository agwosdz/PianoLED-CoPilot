# Backend Playback API Fix

## Problem
- The playback status wasn't updating (`Playing: false`)
- Progress bar wasn't populating with duration
- Clicking Play didn't change the playback state

## Root Causes

### 1. **Incorrect Property Access**
- Code used `current_app.playback_service` instead of `current_app.config.get('playback_service')`
- Playback service is stored in app config, not as a direct app attribute

### 2. **Wrong Method Names**
- Called `playback_service.play()` and `playback_service.pause()` and `playback_service.stop()`
- Actual methods: `load_midi_file()`, `start_playback()`, `pause_playback()`, `stop_playback()`

### 3. **Wrong Properties**
- Tried to access `playback_service.current_file` instead of `playback_service.filename`
- Tried to access `playback_service.progress_percentage` directly instead of calculating it

## Changes Made to `backend/api/play.py`

### 1. **Fixed /playback-status endpoint**
```python
playback_service = current_app.config.get('playback_service')  # ✓ Correct access
return jsonify({
    'state': playback_service.state.value,  # Converts Enum to string
    'current_time': playback_service.current_time,
    'total_duration': playback_service.total_duration,
    'filename': playback_service.filename,  # ✓ Not current_file
    'progress_percentage': (playback_service.current_time / playback_service.total_duration * 100) if playback_service.total_duration > 0 else 0,  # ✓ Calculate from time
    'error_message': None
})
```

### 2. **Fixed /play endpoint**
```python
# Load the file first
if not playback_service.load_midi_file(str(file_path)):  # ✓ load_midi_file()
    return jsonify({'error': 'Failed to load MIDI file'}), 400

# Then start playback
if not playback_service.start_playback():  # ✓ start_playback()
    return jsonify({'error': 'Failed to start playback'}), 400
```

### 3. **Fixed /pause endpoint**
```python
playback_service.pause_playback()  # ✓ pause_playback() not pause()
```

### 4. **Fixed /stop endpoint**
```python
playback_service.stop_playback()  # ✓ stop_playback() not stop()
```

### 5. **Added Error Handling**
- All endpoints now check if playback_service exists
- Return proper error messages if service is unavailable

## Expected Behavior After Fix

### Workflow:
1. **Select file** → File loads, notes displayed
2. **Click Play**
   - `/play` endpoint called
   - `load_midi_file()` parses MIDI file
   - `start_playback()` begins playback thread
   - `total_duration` populated
   - Debug display shows "Playing: true"
3. **Polling updates**
   - `/playback-status` called every 100ms
   - `current_time` advances
   - `progress_percentage` calculated
   - Debug display updates: time, visible notes count
4. **Notes fall** as currentTime advances
5. **Click Pause** → Playback pauses, can resume
6. **Click Stop** → Playback stops, selection cleared

## Validation

✅ **Playback service properly initialized** in `app.py`
✅ **All endpoints access service correctly** via `config.get()`
✅ **Correct method names used** (load_midi_file, start_playback, etc.)
✅ **Correct properties accessed** (filename, not current_file)
✅ **Progress calculated properly** (current_time / total_duration)
✅ **Error handling** if service unavailable

## Next Steps

1. Restart backend server to load changes
2. Select a MIDI file
3. Click **Play**
4. Watch debug display:
   - Time should advance
   - "Playing: true" should appear
   - Progress bar should fill
5. Notes should fall from top to keyboard

## Additional Fix: Directory Mismatch

### Issue
- `/uploaded-midi-files` endpoint was looking in `./uploaded_midi/` directory (default value)
- `/play`, `/pause`, `/stop` endpoints were looking in `./backend/uploads/` directory (from `UPLOAD_FOLDER`)
- **Result**: Files found by file browser but not found when playing

### Fix Applied
- Updated `/uploaded-midi-files` to use same `UPLOAD_FOLDER` from app.config
- Now both endpoints look in the same location: `./backend/uploads/`

## Testing Checklist

- [ ] Select file → shows as selected
- [ ] Click Play → "Playing: true" appears
- [ ] Progress bar fills
- [ ] Current time advances in debug display
- [ ] Notes appear and fall smoothly
- [ ] Click Pause → playback pauses
- [ ] Click Play again → resumes from paused position
- [ ] Click Stop → stops and clears selection
