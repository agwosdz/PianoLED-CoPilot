# Directory Mismatch Bug Fix

## Problem
The playback system had a critical directory mismatch:
- **File browser** (`/uploaded-midi-files`) looked in: `./uploaded_midi/`
- **Playback** (`/play`, `/midi-notes`) looked in: `./backend/uploads/`

### Result
- User could see files in the file browser
- Clicking Play would fail with "File not found"
- API responses showed 404 errors

## Root Cause
The `/uploaded-midi-files` endpoint had a hardcoded default directory instead of using the app's configured `UPLOAD_FOLDER`.

### Code Before
```python
@play_bp.route('/uploaded-midi-files', methods=['GET'])
def get_uploaded_files():
    try:
        midi_dir = Path(current_app.config.get('UPLOADED_MIDI_DIR', './uploaded_midi'))  # ❌ Wrong directory
```

### Code After
```python
@play_bp.route('/uploaded-midi-files', methods=['GET'])
def get_uploaded_files():
    try:
        midi_dir = Path(current_app.config.get('UPLOAD_FOLDER', './backend/uploads'))  # ✓ Correct directory
```

## Impact
- ✅ File browser and playback now use the same directory
- ✅ Files found in browser can now be played
- ✅ All API endpoints consistent

## Testing
After restart, try:
1. Select a MIDI file from the browser
2. Click Play
3. Verify the playback starts (debug shows "Playing: true" and time advances)
