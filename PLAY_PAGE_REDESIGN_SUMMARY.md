# Play Page - Redesigned with Unified Playback Card

## Status
✅ **COMPLETE** - Play page now uses consolidated `playback-card` design matching the Listen page

## Major Changes

### Before
- Separate sections for file selection, playback controls, progress bar, and now playing
- Basic button styling
- "Now Playing" in a separate card section
- MIDI input section below the now playing info

### After
- **Unified `playback-card` section** consolidating all playback UI
- Professional rounded button controls (circular design)
- Integrated connection status indicator
- Now playing info directly in the card header
- MIDI input controls within the same card

## Key Structural Improvements

### 1. Playback Card Header (`playback-top`)
```
┌─────────────────────────────────────────────┐
│ "Now Playing" Badge    [Disconnected Badge] │
│ Track Title                                  │
│ Playing Status                              │
└─────────────────────────────────────────────┘
```

- Uses a "Now Playing" pill badge (blue background)
- Shows filename as title (1.9rem, bold)
- Track status below title
- Connection indicator on the right side
  - `connected`: Green background
  - `disconnected`: Light blue background
  - `error`: Red background

### 2. Playback Controls (`playback-controls`)
```
┌──────────────┐  ┌──────────────┐
│      ▶       │  │      ■       │
│  (Primary)   │  │  (Secondary) │
└──────────────┘  └──────────────┘
```

- Two circular buttons (3.25rem diameter)
- **Primary button (blue gradient)**:
  - Plays/pauses music
  - Active state shows blue glow ring
  - Hover: Lifts up slightly
- **Secondary button (gray)**:
  - Stops playback
  - Same hover/active treatment

### 3. Timeline (`timeline`)
- Thick progress bar (12px height)
- Blue gradient fill
- Time display on both ends (left: current, right: total)
- Smooth transitions

### 4. MIDI Input Section (within card)
- Integrated seamlessly below timeline
- Same design as Listen page
- Label + toggle + status
- Device selector with refresh button
- Disconnect button when connected

## CSS Classes Added/Modified

### New Playback Card Classes
- `.playback-card` - Main container with flex column layout
- `.playback-top` - Header with now playing + connection status
- `.now-playing` - Container for title and metadata
- `.label` - Blue pill badge
- `.track-title` - Large title with ellipsis
- `.track-meta` - Metadata text (status, size, etc)
- `.connection-indicator` - Status badge (connected/disconnected)
- `.connection-indicator.connected` - Green background
- `.connection-indicator.disconnected` - Blue background
- `.playback-controls` - Inline flex container for buttons
- `.control-button` - Base button style (circular)
- `.control-button.primary` - Blue gradient play button
- `.control-button.primary.active` - Glow effect when playing
- `.timeline` - Progress container
- `.timeline-track` - Background track
- `.timeline-fill` - Progress fill (gradient blue)
- `.timeline-meta` - Time labels

### Removed Classes (replaced by playback-card)
- `.controls-group` ✗
- `.btn`, `.btn-play`, `.btn-stop` ✗
- `.time-display` ✗
- `.progress-bar`, `.progress-fill` ✗
- `.now-playing-file`, `.now-playing-status` ✗

## Layout Structure

```
Play Page
├── h1: MIDI Playback
├── section: Select File to Play
│   └── UploadedFileList component
│
└── section.playback-card (NEW UNIFIED DESIGN)
    ├── .playback-top
    │   ├── .now-playing
    │   │   ├── .label (Now Playing badge)
    │   │   ├── .track-title (filename)
    │   │   └── .track-meta (status)
    │   └── .connection-indicator
    │
    ├── .playback-controls
    │   ├── .control-button.primary (Play/Pause)
    │   └── .control-button (Stop)
    │
    ├── .timeline
    │   ├── .timeline-track
    │   │   └── .timeline-fill (progress)
    │   └── .timeline-meta (times)
    │
    ├── .playback-notice (error if any)
    │
    └── .midi-input-section
        ├── .midi-input-header
        ├── .midi-device-selector
        ├── .disconnect-button
        └── .midi-error (if any)
```

## Design Consistency

### Color System (from Listen page)
- Primary Blue: `#2563eb`
- Connected Green: `#dcfce7` / `#166534`
- Disconnected Blue: `#dbeafe` / `#1d4ed8`
- Error Red: `#fee2e2` / `#991b1b`
- Text: `#0f172a`, `#475569`

### Spacing (from Listen page)
- Gap between controls: `1.5rem`
- Button size: `3.25rem` diameter
- Timeline height: `12px`
- Border radius (buttons): `999px` (fully rounded)
- Border radius (other): `0.375rem` (subtle)

### Typography
- Title: `1.9rem`, `font-weight: 700`, `#0f172a`
- Label: `0.75rem`, pill-shaped badge
- Time text: `0.85rem`
- Status text: `0.9rem`

## State Management

### Reactive Displays
```javascript
// Now Playing badge appears based on:
- `selectedFile` - if file selected, shows name
- `isPlaying` - shows Play or Paused status

// Connection indicator shows:
- `midiInputConnected` - Green = Connected, Blue = Disconnected

// Device selector shows when:
- `midiInputEnabled` === true

// Disconnect button shows when:
- `midiInputConnected` === true
```

## API Integration

✅ All APIs working:
- `/api/playback-status` - 100ms polling
- `/api/midi-input/devices` - Load device list
- `/api/midi-input/start` - Connect to device
- `/api/midi-input/stop` - Disconnect device
- `/api/midi-input/status` - 1000ms polling

## Browser Features

### Accessibility
- ✅ `.visually-hidden` class for screen readers
- ✅ Buttons have `aria-hidden` for icons + `visually-hidden` labels
- ✅ Proper `id` and `for` attributes on labels
- ✅ Disabled state handling

### Interactive States
- ✅ Hover: Buttons lift slightly + shadow increases
- ✅ Active/Playing: Primary button shows glow ring
- ✅ Disabled: Reduced opacity, no-pointer cursor
- ✅ Focus: Inherited from browser

### Responsive
- ✅ Flexbox layout adapts to screen size
- ✅ Text wrapping for long filenames
- ✅ Touch-friendly button sizes (3.25rem = ~52px)

## Files Modified
- `frontend/src/routes/play/+page.svelte` (HTML + CSS)

## Next Steps (Optional)

1. ✅ Unified playback card design - DONE
2. ✅ Matching Listen page styling - DONE
3. ✅ MIDI input controls integrated - DONE
4. Consider: Keyboard shortcuts (spacebar to play/pause)
5. Consider: Seek bar interactivity (click to seek)
6. Consider: Visualizer integration (future)

## Visual Summary

**Playback Card Now Features:**
- 🎯 Professional circular button controls
- 📊 Large progress bar with gradient
- 🎧 Connection status indicator
- ⌨️ Keyboard-accessible UI
- 🎨 Matches Listen page design system
- 📱 Responsive layout
- ♿ Accessibility-first approach

