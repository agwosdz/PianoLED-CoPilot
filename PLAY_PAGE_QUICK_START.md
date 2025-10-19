# Play Page - Quick Start Guide

## What's New

A beautiful new **Play Page** has been added to Piano LED Visualizer with real-time MIDI playback visualization including:

✨ **MIDI File Selection**  
🎵 **Timeline Visualization** with colored note bars  
🎹 **Interactive 88-Key Virtual Piano** with real-time highlighting  
▶️ **Playback Controls** (Play, Pause, Stop)  
⏱️ **Time Display** with progress tracking  

## How to Use

### 1. Navigate to Play Page
- Click the **▶️ Play** link in the sidebar
- Or visit directly at `/play`

### 2. Select a MIDI File
- Browse the grid of uploaded MIDI files
- Click any file to select it
- File is highlighted with a gold border when selected
- Playback automatically starts

### 3. Watch the Visualization
The page shows three key visualizations:

#### Timeline View
- **Horizontal timeline** of the entire MIDI file
- **Colored note bars** showing individual notes
- **Gold vertical line** indicating current playback position
- **Colors represent pitch** (Red=C, through spectrum to Purple=B)
- **Opacity indicates velocity** (louder = brighter)

#### Piano Keyboard
- **Full 88-key piano** (A0 to C8)
- **White and black keys** rendered accurately
- **Real-time highlighting** - Keys light up when notes play
- **Color-coded** by pitch for visual reference

### 4. Control Playback
- **▶ Play** - Start or resume playback
- **⏸ Pause** - Pause playback
- **⏹ Stop** - Stop and reset
- Time display shows current position and total duration

### 5. Switch Files
- Click **Stop** to reset
- Select another file from the list
- New file's visualization loads automatically

## Visual Guide

### Timeline Layout
```
┌─────────────────────────────────────────────────┐
│  Time Grid (1 second marks)                     │
│  ╲ Golden Time Indicator (current position)    │
│   ╲  ┌─────────────┐                           │
│    └─│ Note Bar    │ (colored by pitch)       │
│      │ (duration)  │                           │
│      └─────────────┘                           │
└─────────────────────────────────────────────────┘
   0:00              1:30              3:00
```

### Piano Keyboard Layout
```
┌──────────────────────────────────────────────┐
│  ┌────┐ ┌────┐     ┌────┐ ┌────┐          │
│  │ C# │ │ D# │     │ F# │ │ G# │  (Black) │
│  └────┘ └────┘     └────┘ └────┘          │
│ ┌────┬────┬────┬────┬────┬────┬────┬────┐ │
│ │ C  │ D  │ E  │ F  │ G  │ A  │ B  │... │ (White)
│ └────┴────┴────┴────┴────┴────┴────┴────┘ │
│ (Keys light up when notes are playing)     │
└──────────────────────────────────────────────┘
```

### Color Reference

Each note is represented by a color based on its pitch class (12-note octave):

| Pitch | Color | Hex |
|-------|-------|-----|
| C | Red | #ff0000 |
| C# | Orange | #ff7f00 |
| D | Yellow | #ffff00 |
| D# | Yellow-Green | #7fff00 |
| E | Green | #00ff00 |
| F | Green-Cyan | #00ff7f |
| F# | Cyan | #00ffff |
| G | Cyan-Blue | #007fff |
| G# | Blue | #0000ff |
| A | Blue-Purple | #7f00ff |
| A# | Purple | #ff00ff |
| B | Purple-Red | #ff007f |

## Features

### Real-Time Synchronization
- Updates every 100ms
- Smooth time indicator movement
- Piano keys highlight instantly as notes start
- Automatic status polling

### File Management
- Browse all uploaded MIDI files
- See file size for each
- One-click file selection
- Automatic highlighting of active file

### Advanced Visualization
- **Color coding** by pitch for easy musical recognition
- **Velocity representation** with opacity (louder = brighter)
- **Duration representation** with bar width
- **Timeline grid** for time reference
- **Smooth animations** and transitions

## Tips & Tricks

### Getting the Most from the Play Page

1. **Watch the colors** - Notice how the color changes follow the musical scale
2. **Learn the keyboard layout** - Observe note positions on the piano
3. **Velocity visualization** - Fainter notes were played softer
4. **Long vs short notes** - Watch bar width represent note duration
5. **Timing reference** - Grid lines help track playback progress

### Uploading More Files
1. Go to **🎧 Listen** page
2. Upload MIDI files
3. Return to **▶️ Play** page
4. New files appear in the selection grid

## Mobile Support

The Play page is responsive and works on mobile devices:
- File list adapts to screen width
- Smaller but fully functional piano keyboard
- Touch-friendly buttons
- Adjustable text sizes
- Scrollable timeline and keyboard

## Troubleshooting

### Page doesn't load
- Check browser console for errors
- Verify backend is running
- Try refreshing the page

### No files showing
- Upload MIDI files via Listen page first
- Check that files are in the uploads directory
- Refresh the page

### Playback not starting
- Ensure a file is selected (gold border)
- Check that backend playback service is running
- Verify the MIDI file is valid

### Piano not lighting up
- Check that playback is actually playing
- Verify notes exist in the MIDI file
- Look for backend errors in console

### Timeline not updating
- Verify backend status updates are working
- Check network tab in browser dev tools
- Ensure playback service is running

## Keyboard Shortcuts (Future)

These shortcuts will be available soon:
- **Space** - Play/Pause
- **Esc** - Stop
- **→** - Next file
- **←** - Previous file

## Performance

The Play page is optimized for performance:
- Efficient CSS rendering (no canvas)
- Minimal DOM updates
- Smooth 60fps animations
- Smart polling strategy
- Large files load instantly

## What's Next

Future enhancements coming:
- 🔍 Zoom in/out on timeline
- 📍 Click timeline to seek
- 🔇 Note filtering by range
- 📹 Record playback as LED sequence
- 🎵 Audio playback sync
- ⌨️ Keyboard shortcuts
- 👆 Touch piano interaction

## Files Modified

### Frontend
- `frontend/src/routes/play/+page.svelte` - New Play page component
- `frontend/src/lib/components/Navigation.svelte` - Added Play link

### Backend
- `backend/api/play.py` - New API endpoints
- `backend/app.py` - Registered play blueprint

## Technical Details

For developers, see `PLAY_PAGE_IMPLEMENTATION.md` for:
- Complete API documentation
- Architecture details
- Integration points
- Code examples
- Testing guidance

---

**Status:** ✅ Live and Ready to Use  
**Date Added:** October 19, 2025  
**Version:** 1.0.0

Enjoy the visual MIDI playback experience! 🎹✨
