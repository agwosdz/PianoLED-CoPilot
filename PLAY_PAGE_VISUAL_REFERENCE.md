# Play Page - Visual Reference & UI Guide

## Page Layout

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                                                                                ║
║                            🎹 Piano Playback                                   ║
║                                                                                ║
║  ┌──────────────────────────────────────────────────────────────────────────┐ ║
║  │ Uploaded MIDI Files                                                      │ ║
║  ├──────────────────────────────────────────────────────────────────────────┤ ║
║  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐              │ ║
║  │  │ Classical.mid  │  │ JazzBlues.mid  │  │ ModernSong.mid │  ...        │ ║
║  │  │ 12.5 KB        │  │ 8.3 KB         │  │ 25.7 KB        │              │ ║
║  │  └────────────────┘  └────────────────┘  └────────────────┘              │ ║
║  └──────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
║  ┌──────────────────────────────────────────────────────────────────────────┐ ║
║  │ Playback Controls                                                        │ ║
║  ├──────────────────────────────────────────────────────────────────────────┤ ║
║  │  [▶ Play]  [⏹ Stop]        0:15 / 3:24                                 │ ║
║  │  ┌────────────────────────────────────────────────────────────────────┐  │ ║
║  │  │███████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ │ ║
║  │  └────────────────────────────────────────────────────────────────────┘  │ ║
║  └──────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
║  ┌──────────────────────────────────────────────────────────────────────────┐ ║
║  │ MIDI Visualization                                                       │ ║
║  ├──────────────────────────────────────────────────────────────────────────┤ ║
║  │ Timeline:                                                                │ ║
║  │ ┌────────────────────────────────────────────────────────────────────┐  │ ║
║  │ │  │     │     │     │     │ ║ │  │   ┌─ Red ─┐              │     │  │ ║
║  │ │  │     │  ┌──Blue──┐    │ ║ │  │   │ Green │              │     │  │ ║
║  │ │  └─ Yellow─┘        │    │ ║ │  │   └─ Purple ┴─ Orange ─┐│     │  │ ║
║  │ │  0:00    0:30   1:00 1:30 2:00 2:30     3:00                3:24  │  │ ║
║  │ └────────────────────────────────────────────────────────────────────┘  │ ║
║  │                                                                           │ ║
║  │ Piano Keyboard:                                                          │ ║
║  │ ┌────────────────────────────────────────────────────────────────────┐  │ ║
║  │ │  ┌────┐ ┌────┐     ┌────┐ ┌────┐  ┌────┐     ┌────┐ ┌────┐ ║ │  │ ║
║  │ │  │ C# │ │ D# │     │ F# │ │ G# │  │ A# │     │ C# │ │ D# │ ║ │  │ ║
║  │ │  └────┘ └────┘     └────┘ └────┘  └────┘     └────┘ └────┘ ║ │  │ ║
║  │ │ ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐║ │  │ ║
║  │ │ │ C  │ D  │ E  │ F  │ G  │ A  │ B  │ C  │ D  │ E  │ F  │ G ║║ │  │ ║
║  │ │ └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘║ │  │ ║
║  │ │ A0                                                          C8 ║ │  │ ║
║  │ │ (Keys lighting up in colors as notes play)                   ║ │  │ ║
║  │ └────────────────────────────────────────────────────────────────────┘  │ ║
║  └──────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

## Component States

### File Selection Grid
```
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ Classical.mid        │ JazzBlues.mid        │ ModernSong.mid       │
│ 12.5 KB              │ 8.3 KB               │ 25.7 KB              │
│ (Hover)              │ (Active/Selected)    │ (Default)            │
│ Hover: Light up      │ Golden border        │ Light bg             │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

### Playback Control States
```
┌─────────────────┬──────────────────┬──────────────────┐
│ [▶ Play]        │ [⏸ Pause]       │ [⏹ Stop]        │
│ (Ready)         │ (Playing)        │ (Playing)        │
│ Gold gradient   │ Gold gradient    │ Red gradient     │
│ Enabled         │ Enabled          │ Enabled          │
└─────────────────┴──────────────────┴──────────────────┘

When no file selected:
┌─────────────────┬──────────────────┬──────────────────┐
│ [▶ Play]        │ [⏸ Pause]       │ [⏹ Stop]        │
│ (Disabled)      │ (Disabled)       │ (Disabled)       │
│ Gold (50% op)   │ Gold (50% op)    │ Red (50% op)     │
│ Disabled        │ Disabled         │ Disabled         │
└─────────────────┴──────────────────┴──────────────────┘
```

### Timeline Progress States

#### Idle (nothing playing)
```
┌─────────────────────────────────────────────┐
│ Black background with grid lines at 1s      │
│ │    │    │    │    │    │                 │
│ 0s   1s   2s   3s   4s   5s  (no notes)     │
└─────────────────────────────────────────────┘
```

#### With Notes (file loaded)
```
┌─────────────────────────────────────────────┐
│ Black background, notes displayed           │
│ │ Red   │ Blue   │ Gold   │                 │
│ ├─┐     ├─┐     ├─┐                        │
│ │ ├┐    │ ├┐    │ ├┐                       │
│ 0s 1s   2s 3s   4s 5s   (colored by pitch) │
└─────────────────────────────────────────────┘
```

#### During Playback
```
┌─────────────────────────────────────────────┐
│ Gold vertical line indicates current time   │
│ ║                                            │
│ │ Red   ║ Blue   │ Gold   │                 │
│ ├─┐     ║ ├─┐    │ ├─┐                     │
│ │ ├┐    ║ │ ├┐   │ ├┐                      │
│ 0s 1s  1.5s 2s  3s 4s (✨ glowing line)    │
└─────────────────────────────────────────────┘
```

## Piano Keyboard States

### Idle (no notes playing)
```
┌──────────────────────────────────────────────────┐
│ ┌────┐ ┌────┐     ┌────┐ ┌────┐ (Black keys)   │
│ │ ## │ │ ## │     │ ## │ │ ## │               │
│ │ ## │ │ ## │     │ ## │ │ ## │               │
│ └────┘ └────┘     └────┘ └────┘               │
│ ┌────┬────┬────┬────┬────┬────┬────┬────┐     │
│ │ ## │ ## │ ## │ ## │ ## │ ## │ ## │ ## │ (White keys)
│ │ ## │ ## │ ## │ ## │ ## │ ## │ ## │ ## │     │
│ └────┴────┴────┴────┴────┴────┴────┴────┘     │
│ A0                                    (C8)     │
└──────────────────────────────────────────────────┘
```

### During Playback (Notes Highlighted)
```
┌──────────────────────────────────────────────────┐
│ ┌────┐ ┌────┐     ┌────┐ ┌────┐ (Black keys)   │
│ │🔵 │ │ ## │     │🟠  │ │ ## │ (Blue=G#,Orange=D#)
│ │🔵 │ │ ## │     │🟠  │ │ ## │                │
│ └────┘ └────┘     └────┘ └────┘               │
│ ┌────┬────┬────┬────┬────┬────┬────┬────┐     │
│ │🔴 │ ## │🟡 │ ## │🟢 │ ## │🟣 │ ## │ (Red=C, Yellow=D, Green=E, etc)
│ │🔴 │ ## │🟡 │ ## │🟢 │ ## │🟣 │ ## │     │
│ └────┴────┴────┴────┴────┴────┴────┴────┘     │
│ A0                                    (C8)     │
└──────────────────────────────────────────────────┘
(Colors represent pitch; brightness = velocity)
```

## Color Indicators

### Timeline Note Colors
```
┌──────────────────────────────────────────┐
│ Pitch Color Spectrum (12-color wheel)    │
│                                          │
│  C   C# D   D# E   F   F# G   G# A   A# B
│  🔴  🟠  🟡  🟢  🟢  🟡  🔵  🔵  🔵  🟣  🟣  🟤
│  Red  Org Yel Y-G Grn Cyn Cyn Blu Blu Pur Pur Red
│                                          │
└──────────────────────────────────────────┘
```

### Velocity (Opacity)
```
Soft Note (Velocity 40):  ░░░░░░░░░░ (40% opacity)
Medium Note (Velocity 80): ████████░░ (80% opacity)
Loud Note (Velocity 127):  ██████████ (100% opacity)
```

## Responsive Design Breakpoints

### Desktop (>768px)
```
┌─────────────────────────────────────────────────┐
│ Full width layout                               │
│ File grid: auto-fill (250px minimum)           │
│ Timeline: 150px height                         │
│ Piano: 120px height                            │
│ Font sizes: large                              │
└─────────────────────────────────────────────────┘
```

### Tablet (768px-1024px)
```
┌────────────────────────────────────┐
│ Adjusted layout                    │
│ File grid: 2 columns              │
│ Timeline: 120px height            │
│ Piano: 100px height               │
│ Font sizes: medium                │
└────────────────────────────────────┘
```

### Mobile (<768px)
```
┌──────────────────┐
│ Single column    │
│ Files: 1 per row│
│ Timeline: 100px │
│ Piano: 80px     │
│ Fonts: small    │
└──────────────────┘
```

## Interactive Elements

### File Item (Hover)
```
Before:                     After (Hover):
┌────────────────────┐     ┌────────────────────┐
│ ClassicalSong.mid  │     │ ClassicalSong.mid  │ ✨ Light up
│ 12.5 KB            │  →  │ 12.5 KB            │ ✨ Golden border
└────────────────────┘     └────────────────────┘ ✨ Lift up
```

### File Item (Active/Selected)
```
┌────────────────────┐
│ ClassicalSong.mid  │ ✨ Golden background
│ 12.5 KB            │ ✨ Golden border
└────────────────────┘ ✨ Glowing shadow
(Has golden glow around it)
```

### Progress Bar (Interactive - Future)
```
Current:                    Hover (Future):
┌──────────────────────┐    ┌──────────────────────┐
│███████████░░░░░░░░░░│    │███████████░░░░░░░░░░│ 🔍 Cursor changes
│  8%                  │ → │  8% | Seek to 25%   │ 🔍 Shows time on hover
│  0:00  0:30  1:00    │    │  0:00  0:30  1:00   │
└──────────────────────┘    └──────────────────────┘
```

### Piano Keys (Hover)
```
Before:                     After (Hover):
┌─────────────────┐        ┌─────────────────┐
│  ┌────┬────┐   │        │  ┌────┬────┐   │
│  │ ## │ ## │   │     →  │  │ ✨ │ ## │   │ ✨ Bright highlight
│  │ ## │ ## │   │        │  │ ✨ │ ## │   │ ✨ Golden glow
│  └────┴────┘   │        │  └────┴────┘   │
└─────────────────┘        └─────────────────┘
```

## Animation Details

### Timeline Note Bar
```
Entrance: Fade in (200ms)
Duration: Stretches across timeline based on note duration
Exit: Fade out (200ms) when playback passes
```

### Current Time Indicator
```
Movement: Smooth linear progression
Color: Golden (#ffd700)
Glow: Box-shadow with 0.8 opacity
Speed: Moves smoothly with playback
```

### Piano Key Highlight
```
Entrance: Instant color change
Exit: Smooth fade (100ms)
Color: Matches note pitch
Brightness: Based on velocity
```

### Button Hover
```
Hover Effect: Scale 1.05 + shadow
Duration: 300ms ease
State: Normal → Highlighted → Pressed
```

## Dark Theme Colors

```
Primary Background:    #1a1a1a (very dark gray)
Secondary Background:  #2d2d2d (dark gray)
Accent Color:          #ffd700 (gold)
Text Primary:          #ffffff (white)
Text Secondary:        #cbd5e1 (light gray)
Border Color:          rgba(255,255,255,0.1)
Success Green:         #22c55e
Error Red:             #ff6b6b
```

## Typography

```
Page Title (H1):       2.5rem, bold, gold gradient
Section Title (H2):    1.3rem, bold, gold color
Button Text:           1rem, bold, centered
File Name:             1rem, medium weight
Time Display:          1.1rem, bold, gold
```

## Spacing

```
Container Padding:     2rem
Section Padding:       1.5rem
Element Gaps:          1rem (vertical), 0.5rem (horizontal)
Border Radius:         8px (sections), 6px (buttons/items), 4px (keyboard)
Shadow:                0 0 15px rgba(color, 0.5) on hover
```

## Browser Compatibility

```
✅ Chrome/Chromium:    Full support
✅ Firefox:            Full support
✅ Safari:             Full support (iOS 14+)
✅ Edge:               Full support
⚠️  Mobile Browsers:   Touch-optimized, fully responsive
```

## Accessibility Features

```
✅ Keyboard Navigation: Tab through files and buttons
✅ Focus Indicators:    Visible on all interactive elements
✅ Color Contrast:      WCAG AA compliant
✅ Labels:              All buttons and inputs labeled
✅ ARIA Labels:         Navigation sections labeled
✅ Screen Readers:      Semantic HTML structure
```

---

This visual guide provides a comprehensive reference for understanding the Play Page's UI layout, component states, interactions, and styling.
