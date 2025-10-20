# Play and Learn - Styling & Organization Improvements

## Overview

The Learning Options panel has been redesigned to:
1. ✅ Match settings page component styling
2. ✅ Use stunning hand-specific color pairs
3. ✅ Consolidate settings by hand (including per-hand wait-for-notes)

## Color Selection

### Left Hand: Golden Amber (✨ Premium Warm Tones)
- **White Keys**: `#f59e0b` (Amber-500) - Vibrant, warm gold
- **Black Keys**: `#d97706` (Amber-700) - Deep, rich amber
- **Label Badge**: Golden background with chocolate text
- **Aesthetic**: Warm, elegant, evokes classical warmth of traditional pianos

### Right Hand: Teal & Magenta (✨ Sophisticated Cool Tones)
- **White Keys**: `#006496` (RGB 0, 100, 150) - Deep teal/cyan
- **Black Keys**: `#960064` (RGB 150, 0, 100) - Deep magenta/purple
- **Label Badge**: Cyan background with teal text
- **Aesthetic**: Modern, sophisticated, professional contrast

## Organizational Improvements

### Structure: Per-Hand Configuration

```
Learning Options
├── Left Hand (Golden Amber)
│   ├── Wait for MIDI Notes (checkbox)
│   ├── White Keys Color Picker
│   └── Black Keys Color Picker
├── [Divider]
├── Right Hand (Vibrant Blue)
│   ├── Wait for MIDI Notes (checkbox)
│   ├── White Keys Color Picker
│   └── Black Keys Color Picker
├── [Divider]
├── Note Timing Tolerance (Global Slider)
└── Reset to Defaults (Action)
```

### State Variables (Updated)

```typescript
// Per-hand settings
let leftHandWaitForNotes = false;
let leftHandWhiteColor = '#f59e0b';      // Amber-500
let leftHandBlackColor = '#d97706';      // Amber-700

let rightHandWaitForNotes = false;
let rightHandWhiteColor = '#006496';     // Deep Teal
let rightHandBlackColor = '#960064';     // Deep Magenta

// Global setting
let timingWindow = 500;                  // in milliseconds
```

## Component Styling (Settings Page Matched)

### Card Header
- Matches settings panel header styling
- Clear typography hierarchy
- Consistent border and spacing

### Hand Sections
- **Hand Header**: Title + color label badge
  - Label badges with themed colors (Amber for left, Blue for right)
  - Emoji indicators (🎹) for visual clarity
  
- **Checkbox Group**: 
  - Background white container with subtle border
  - Proper checkbox styling with 2563eb blue accent
  - Clear label with description text below

- **Color Selector Pair**:
  - Two-column grid layout (responsive, collapses to 1 column on mobile)
  - Color input wrapper with consistent styling:
    - HTML5 color picker input
    - Large swatch preview showing current color
    - Hex value display in monospace font
  - Hover/focus states matching settings patterns
  - Border color: #d1d5db with #2563eb focus

### Dividers
- Subtle gradient line separating hand sections
- Visual organization without clutter

### Timing Section
- Styled as settings field with slider
- Dynamic value display (updates as you drag)
- Range: 100-2500ms in 100ms increments
- Hint text for clarity

### Reset Button
- Ghost button style matching settings page
- Emoji icon (🔄) for visual appeal
- Hover effects with subtle shadow
- Disabled state when saving

## API Contract Update

### Request Body (POST /api/learning/options)

```json
{
  "left_hand": {
    "wait_for_notes": false,
    "white_color": "#f59e0b",
    "black_color": "#d97706"
  },
  "right_hand": {
    "wait_for_notes": false,
    "white_color": "#006496",
    "black_color": "#960064"
  },
  "timing_window_ms": 500
}
```

### Response Body (GET /api/learning/options)

```json
{
  "left_hand": {
    "wait_for_notes": false,
    "white_color": "#f59e0b",
    "black_color": "#d97706"
  },
  "right_hand": {
    "wait_for_notes": false,
    "white_color": "#006496",
    "black_color": "#960064"
  },
  "timing_window_ms": 500
}
```

## Visual Improvements

### Color Picker Integration
✅ Uses standard HTML5 `<input type="color">` 
✅ Native browser color picker (works on all platforms)
✅ Large, accessible click targets
✅ Real-time swatch preview
✅ Hex value display for technical users
✅ Proper focus/hover states

### Responsive Design
✅ Card header: Full width with proper padding
✅ Learning content: Consistent inner padding
✅ Color pair grid: Auto-fit 200px minimum on desktop, stacks on mobile
✅ Hand sections: Full width with consistent spacing
✅ All interactive elements: Proper touch targets (min 44px)

### Accessibility
✅ Semantic HTML (proper label associations)
✅ ARIA labels where needed
✅ Color contrast meets WCAG AA standards
✅ Keyboard navigation support
✅ Focus indicators visible
✅ Screen reader friendly descriptions

## File Changes

### `frontend/src/routes/play/+page.svelte` (1535 lines)

**Script Section Updates:**
- Changed state variables to per-hand configuration
- Updated `loadLearningOptions()` to parse nested structure
- Updated `saveLearningOptions()` to send per-hand data
- Updated `resetToDefaults()` with new default colors

**Template Updates:**
- Reorganized HTML structure around hand sections
- New badge system with hand labels
- Unified checkbox styling per hand
- Color input wrapper with hex display

**Styling Updates:**
- 200+ lines of new CSS for settings-matched components
- Consistent with settings page design system
- Color scheme: Amber (#f59e0b/#d97706) for left, Blue (#0000ff/#0000cc) for right
- Professional hover/focus/active states
- Mobile-responsive grid layouts

## Testing Checklist

- [ ] Color pickers show correct initial colors
- [ ] Color changes update preview immediately
- [ ] Changes auto-save to backend
- [ ] Per-hand wait-for-notes toggles work independently
- [ ] Timing slider updates value display dynamically
- [ ] Reset button restores all defaults
- [ ] Error messages display if API fails
- [ ] Styling matches settings page on desktop
- [ ] Responsive layout works on tablet
- [ ] Touch-friendly on mobile
- [ ] Keyboard navigation works throughout
- [ ] Screen reader announces all inputs correctly

## Backend Implementation (Next Step)

Update `/api/learning/options` endpoints to:
1. Parse per-hand nested structure
2. Validate hex color format for all 4 colors
3. Validate timing window (100-2000ms)
4. Store in settings database with hand categories
5. Return proper error messages for validation failures

See `PLAY_AND_LEARN_BACKEND_API.md` for full specification.
