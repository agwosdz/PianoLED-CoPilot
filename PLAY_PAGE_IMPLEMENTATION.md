# Play Page Implementation Guide

## Overview

The new **Play Page** provides a beautiful visual representation of MIDI playback with:

1. **MIDI File Selection** - Browse and select uploaded MIDI files
2. **Playback Controls** - Play, pause, and stop buttons with time display
3. **Timeline Visualization** - See notes as they play over time
4. **Virtual Piano Keyboard** - Interactive 88-key piano that lights up with active notes

## Features

### File Selection
- Grid view of uploaded MIDI files
- Shows filename and file size
- Click to select and start playback
- Active file is highlighted with a golden border

### Playback Controls
- **Play/Pause Button** - Toggle playback state
- **Stop Button** - Stop playback and reset
- **Time Display** - Current time / Total duration in MM:SS format
- **Progress Bar** - Clickable progress indicator (future enhancement)

### MIDI Timeline Visualization
- **Horizontal timeline** showing entire MIDI file
- **Colored note bars** representing individual notes
  - Each note has a unique color based on pitch (red=C, through rainbow to purple=B)
  - Opacity based on velocity (louder = more opaque)
  - Width represents note duration
  - Position represents timing
- **Grid lines** for time reference (one per second)
- **Current time indicator** - Golden vertical line showing playback position

### Virtual Piano Keyboard
- **88-key piano** (A0 to C8, full standard piano range)
- **White keys** rendered in light gray/white
- **Black keys** rendered in dark/black
- **Real-time highlighting** - Keys light up when notes are actively playing
- **Color-coded by pitch** - Active keys show their color based on MIDI note
- **Hover effects** - Visual feedback on mouse over

## Architecture

### Frontend (Svelte)

**File:** `frontend/src/routes/play/+page.svelte`

**Key Components:**
- File selection grid
- Playback control buttons
- Time display and progress bar
- MIDI timeline visualization with colored note bars
- Interactive 88-key virtual piano

**Key Functions:**
- `getNoteColor(note)` - Returns color for MIDI note (0-11 in octave)
- `isWhiteKey(note)` - Determines if note is white or black key
- `getNoteXPercent(note)` - X position on keyboard (0-100%)
- `getNoteWidthPercent(note)` - Width based on key type
- `getNotePosition(note)` - 0-87 position on 88-key keyboard
- `formatTime(seconds)` - Converts seconds to MM:SS format

**State Variables:**
- `playbackStatus` - Current playback state from backend
- `notes` - Array of note visualizations from MIDI file
- `uploadedFiles` - List of available MIDI files
- `selectedFile` - Currently selected file path
- `isPlaying` - Current playback state
- `currentTime` - Current playback position in seconds
- `totalDuration` - Total MIDI file duration in seconds

**Polling Strategy:**
- Fetches playback status every 100ms
- Updates notes timeline when file selected
- Reloads file list every 5 seconds

### Backend (Python/Flask)

**File:** `backend/api/play.py`

**Endpoints:**

#### GET `/api/uploaded-midi-files`
Returns list of uploaded MIDI files.
```json
[
  {
    "filename": "song.mid",
    "path": "/path/to/song.mid",
    "size": 5120
  }
]
```

#### GET `/api/midi-notes?filename=song.mid`
Extracts and returns MIDI notes from a file for visualization.
```json
{
  "notes": [
    {
      "note": 60,
      "startTime": 0.0,
      "duration": 0.5,
      "velocity": 100
    }
  ],
  "tempo": 120,
  "total_duration": 180.5
}
```

**Notes:**
- Uses `MIDIParser` to parse the file
- Extracts note events, tempo, and duration
- Returns data in visualization-ready format

#### GET `/api/playback-status`
Returns current playback state.
```json
{
  "state": "playing|paused|idle",
  "current_time": 15.5,
  "total_duration": 180.5,
  "filename": "song.mid",
  "progress_percentage": 8.6,
  "error_message": null
}
```

#### POST `/api/play`
Start playback of a MIDI file.
```json
{
  "filename": "song.mid"
}
```

#### POST `/api/pause`
Pause current playback.
```json
{
  "success": true
}
```

#### POST `/api/stop`
Stop playback and reset.
```json
{
  "success": true
}
```

### Integration with Existing Services

The Play page integrates with:

1. **PlaybackService** - Manages MIDI playback state
   - `play(filepath)` - Start playback
   - `pause()` - Pause playback
   - `stop()` - Stop playback
   - Properties: `state`, `current_time`, `total_duration`, `progress_percentage`

2. **MIDIParser** - Parses MIDI files
   - Extracts note events with timing and velocity
   - Respects canonical LED mapping (adjusted with offsets, trims, selections)
   - Returns structured note data

3. **SettingsService** - Accesses runtime settings
   - Used by MIDI parser for calibration adjustments

## Color Scheme

### MIDI Note Colors (by pitch class)
- **C** - Red (#ff0000)
- **C#** - Orange (#ff7f00)
- **D** - Yellow (#ffff00)
- **D#** - Yellow-Green (#7fff00)
- **E** - Green (#00ff00)
- **F** - Green-Cyan (#00ff7f)
- **F#** - Cyan (#00ffff)
- **G** - Cyan-Blue (#007fff)
- **G#** - Blue (#0000ff)
- **A** - Blue-Purple (#7f00ff)
- **A#** - Purple (#ff00ff)
- **B** - Purple-Red (#ff007f)

### UI Colors
- Background: Dark gradient (#1a1a1a → #2d2d2d)
- Accent: Gold (#ffd700)
- Text: White/light gray
- Borders: Transparent white

## Styling

### Desktop Layout
- Full-width container with dark background
- Grid-based file selection (auto-fill with 250px min width)
- Horizontal timeline visualization (150px height)
- Large piano keyboard visualization (120px height)
- Responsive controls section

### Mobile Layout
- Single column file list
- Reduced timeline height (100px)
- Smaller piano keyboard (80px)
- Adjusted font sizes and padding

## Usage Flow

1. **Navigate to Play page** via sidebar or direct URL
2. **View uploaded MIDI files** in grid layout
3. **Click a file** to select and load
4. **Visualization updates** showing:
   - All notes from the file in the timeline
   - Piano keyboard ready for playback
5. **Click Play** to start playback
   - Timeline shows current position indicator
   - Piano keys light up in real-time as notes play
   - Colors indicate pitch relationships
6. **Pause/Resume** playback with Play button
7. **Stop** to reset and clear visualization
8. **Select another file** to switch MIDI files

## Real-time Synchronization

The page maintains real-time sync with playback:

- **100ms polling** updates current time and progress
- **Immediate response** to Play/Pause/Stop actions
- **Smooth animation** of current time indicator
- **Dynamic key highlighting** based on actual note timing
- **Velocity-based opacity** for visual emphasis on loud notes

## Performance Considerations

- **Lazy loading** of MIDI notes (only loaded when file selected)
- **Efficient rendering** using CSS positioning (no canvas)
- **Debounced updates** via polling interval
- **Minimal DOM manipulation** (only timeline and keys update)
- **CSS transitions** for smooth animations
- **Calculated positioning** (no large data structures)

## Future Enhancements

1. **Clickable progress bar** - Seek to specific time
2. **Zoom controls** - For timeline and keyboard
3. **Note filtering** - Show only certain ranges
4. **Recording/saving** - Record playback as LED sequence
5. **Multiple file support** - Concurrent playback
6. **Audio playback** - Sync with actual MIDI audio
7. **Keyboard shortcuts** - Space for play/pause, etc.
8. **Touch support** - Mobile-friendly keyboard interaction

## Testing

### Manual Testing Checklist
- [ ] File list loads correctly
- [ ] Clicking file selects it and highlights
- [ ] Play button works and playback starts
- [ ] Timeline updates during playback
- [ ] Piano keys light up correctly
- [ ] Color matches note pitch
- [ ] Pause/Resume works
- [ ] Stop resets properly
- [ ] Progress bar updates smoothly
- [ ] Time display is accurate
- [ ] Mobile layout is responsive
- [ ] No console errors

### Test Files
- Use MIDI files from Listen page
- Test various tempos (60, 120, 200 BPM)
- Test various durations (short, medium, long)
- Test dense note sequences
- Test single notes

## Navigation Integration

The Play page is now integrated into the main navigation:
- Icon: ▶️
- Label: Play
- Description: Visual MIDI playback with piano
- Position: Between Listen and Settings

## File Structure
```
frontend/
└── src/
    └── routes/
        └── play/
            └── +page.svelte       # Main Play page component

backend/
└── api/
    └── play.py                    # Play API endpoints
```

## Dependencies

**Frontend:**
- Svelte framework
- Socket.IO for status updates
- Standard Fetch API for REST calls

**Backend:**
- Flask
- MIDIParser (existing service)
- PlaybackService (existing service)
- SettingsService (existing service)

## Security Considerations

- **Path traversal prevention** - Filename sanitization with `Path.name`
- **File existence checks** - Verify file exists before processing
- **MIME type validation** - Accept only .mid files (enforced by file system)
- **Input validation** - All parameters validated before use
- **Error handling** - Graceful error responses without exposing paths

## Troubleshooting

### Notes not showing
- Verify MIDI file is valid
- Check `/api/midi-notes` response in network tab
- Ensure parser is reading note events correctly

### Piano not lighting up
- Check `currentTime` vs `note.startTime + note.duration`
- Verify playback status is updating
- Check that notes array is populated

### Playback not starting
- Verify file is selected
- Check Play button is enabled
- Check backend playback service is running
- Review browser console for errors

### Timeline not updating
- Check 100ms polling is working
- Verify `/api/playback-status` endpoint
- Check that `current_time` is changing

## API Response Examples

### Successful File List
```json
[
  {
    "filename": "Classical.mid",
    "path": "/path/to/Classical.mid",
    "size": 4096
  },
  {
    "filename": "Jazz.mid",
    "path": "/path/to/Jazz.mid",
    "size": 5120
  }
]
```

### Successful MIDI Notes
```json
{
  "notes": [
    {
      "note": 60,
      "startTime": 0.0,
      "duration": 0.5,
      "velocity": 85
    },
    {
      "note": 64,
      "startTime": 0.5,
      "duration": 0.5,
      "velocity": 90
    },
    {
      "note": 67,
      "startTime": 1.0,
      "duration": 1.0,
      "velocity": 100
    }
  ],
  "tempo": 120,
  "total_duration": 2.0
}
```

### Active Playback Status
```json
{
  "state": "playing",
  "current_time": 15.234,
  "total_duration": 180.5,
  "filename": "song.mid",
  "progress_percentage": 8.44,
  "error_message": null
}
```

---

**Created:** October 19, 2025
**Implementation Status:** ✅ Complete
**Tests:** Manual testing recommended
**Production Ready:** Yes (pending manual testing)
