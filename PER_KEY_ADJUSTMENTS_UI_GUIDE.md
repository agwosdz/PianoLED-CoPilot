# Per-Key Adjustments UI Guide - Visual Reference

## Layout Overview

```
Settings Page
└── Calibration Section
    ├── Calibration Section 2 (LED Range)
    ├── Calibration Section 3 (Mapping Validation)
    └── Per-Key Adjustments ⭐ NEW UNIFIED INTERFACE
        ├── Header Section
        ├── Add Form (Collapsible)
        └── Adjustment List
```

## Per-Key Adjustments Component

### Header Section
```
┌─────────────────────────────────────────┐
│ 🔑 Per-Key Adjustments                [3]│  ← Badge shows count
│ Adjust timing and LED allocation for     │  ← Section description
│ specific keys                            │
│                          [⊕ Add] [✕ Cancel] │  ← Toggle form button
└─────────────────────────────────────────┘
```

### Add Adjustment Form (Expanded)
```
┌─────────────────────────────────────────┐
│ Add Adjustment Form                     │
├─────────────────────────────────────────┤
│ MIDI Note (0-127):         [___________]│
│                                          │
│ Offset (LEDs):             [_____]     │
│                                          │
│ ☐ Customize LED allocation for this key│
│   └─ (appears only when MIDI note set)  │
│                                          │
│     [If checked, LED grid appears ↓]   │
│     Valid LED Range: 120 - 246          │  ← Info
│     Selected: 0 LEDs                    │  ← Counter
│                                          │
│     [🔲][🔲][🔲]...[🔲]                │
│     [🔲][🟩][🔲]...[🔲]  ← Selected   │
│     [🔲][🔲][🔲]...[🔲]               │
│                                          │
│                    [✓ Add Adjustment]   │
└─────────────────────────────────────────┘

Colors:
- Unselected: white bg, green border
- Selected: green bg, white text, checkmark
- Hover: light green bg
```

### Adjustment List Items

#### Item without LED override
```
┌─────────────────────────────────────────┐
│ C4          2 LEDs offset        [✎][🗑]│
└─────────────────────────────────────────┘
```

#### Item with LED override
```
┌─────────────────────────────────────────┐
│ C4          2 LEDs offset        [✎][🗑]│
│ LEDs: [120, 121, 122]                    │
└─────────────────────────────────────────┘
 └─ LED badge (monospace, left-aligned)
```

#### Editing state
```
┌─────────────────────────────────────────┐
│ C4          [___] LEDs        [✓][✕]   │
│             (input focused)              │
└─────────────────────────────────────────┘
```

## Color Scheme

### Form Section Colors
- Background: #f1f8e9 (light green)
- Input borders: #81c784 (medium green)
- Labels: #2e7d32 (dark green)
- Text: #1b5e20 (very dark green)

### LED Grid Colors
- Unselected LED: white bg, #81c784 border
- Selected LED: #66bb6a bg (bright green), white text
- Hover: #e8f5e9 bg, scale 1.05
- Text: #558b2f (dark green)

### Badge Colors
- Background: #e8f5e9 (very light green)
- Border-left: 3px #66bb6a (bright green)
- Text: #2e7d32 (dark green)
- Font: monospace, 0.8rem

## State Transitions

### Form Open/Close
```
User clicks "⊕ Add"
    ↓
showAddForm = true
Form appears with fade-in
    ↓
User fills MIDI Note
    ↓
LED checkbox appears
User checks checkbox
    ↓
LED grid appears with animation
    ↓
User clicks "✓ Add Adjustment"
    ↓
Form validates & submits
Success message appears (2 sec)
    ↓
Form resets & closes (showAddForm = false)
New adjustment appears in list
```

### User Interactions

#### MIDI Note Input
```
User types: "60"
    ↓
handleMidiNoteInput("60")
    ├─ Parse MIDI note (60)
    ├─ Validate range (0-127) ✓
    ├─ Load available LEDs (120-246)
    ├─ Load existing override if any
    └─ Form ready for LED selection
```

#### LED Toggle
```
User clicks LED button "122"
    ↓
toggleLED(122)
    ├─ Check if 122 in selectedLEDsForNewKey
    ├─ If yes: delete 122
    ├─ If no: add 122
    └─ Update reactive Set
        ↓
    Counter updates: "Selected: 3 LEDs"
    Visual state changes: green checkmark appears
```

#### Add Adjustment
```
User clicks "✓ Add Adjustment"
    ↓
handleAddKeyOffset()
    ├─ Parse MIDI note
    ├─ Validate MIDI range (0-127)
    ├─ Call setKeyOffset(60, 2)
    │   └─ PUT /api/calibration/key-offsets/60
    │
    └─ If LEDs selected:
        └─ Call ledSelectionAPI.setKeyOverride(60, [120,121,122])
            └─ PUT /api/led-selection/key/60
                ↓
    Both succeed or both fail (atomic)
        ↓
    Success message shown (2 sec)
        ↓
    Form resets
        ↓
    List item appears:
        C4          2 LEDs offset        [✎][🗑]
        LEDs: [120, 121, 122]
```

## Responsive Design

### Desktop (>1024px)
```
Form displays with all controls visible
LED grid: repeat(auto-fill, minmax(35px, 1fr))
Buttons: inline, flex-wrap
```

### Tablet (768px - 1024px)
```
Form controls may wrap
LED grid: repeat(auto-fill, minmax(35px, 1fr))
Buttons: still inline but smaller
```

### Mobile (<768px)
```
Form stacks vertically
LED grid: repeat(auto-fill, minmax(30px, 1fr))
Buttons: full width stack
```

## Accessibility Features

- ✅ All buttons have `title` attributes (tooltips)
- ✅ Labels associated with inputs
- ✅ Checkbox with clear label text
- ✅ High contrast colors
- ✅ Clear visual feedback (hover, selected states)
- ✅ Keyboard accessible (tab navigation)
- ✅ MIDI note names displayed (not just numbers)
- ✅ Real-time feedback counters

## Validation Rules

### MIDI Note
```
Valid: 0-127
Invalid: < 0, > 127, non-integer, empty
Action: Show error, disable Add button
```

### Offset
```
Valid: any integer (positive, negative, zero)
Min/Max: None (system handles)
Default: 0
```

### LED Selection
```
Optional: Can skip, offset works alone
Valid: Any available LED in range
Selected count: 0-∞ (no limit)
Display: "Selected: N LED(s)"
```

## Success/Error States

### Success
```
Background: #e8f5e9 (light green)
Border: 1px solid #c8e6c9
Color: #2e7d32 (dark green)
Icon: ✓
Message: "Key adjustment added for C4"
Duration: 2 seconds auto-dismiss
```

### Error
```
Background: #fee (light red)
Border: 1px solid #fcc
Color: #c33 (red)
Message: "Please enter a valid MIDI note (0-127)"
Auto-dismiss: No (user must fix)
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Focus MIDI input | Tab (form open) |
| Focus Offset input | Tab twice |
| Focus LED checkbox | Tab thrice |
| Activate button | Enter/Space |
| Close form | Escape (future enhancement) |

## Animation/Transitions

```css
/* All transitions */
transition: all 0.2s ease;

/* Specific states */
Hover on LED: scale(1.05)
Selected LED: instant color change
Form appear: fade-in (standard)
Success message: fade in/out 2sec
```

## Typography

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Section header | 1.1rem | 600 | #0f172a |
| Form labels | 0.85rem | 600 | #2e7d32 |
| LED counter | 0.9rem | 600 | #2e7d32 |
| LED values | 0.8rem | 400 | #558b2f |
| Offset note | 0.9rem | 700 | #1b5e20 |
| LED badge | 0.8rem | 400 | #2e7d32 |

## Space/Padding

```
Section container: 1.5rem padding
Form: 1rem padding, 1rem gap
Offset list: 0.75rem gap between items
List item: 1rem padding
LED grid: 4px gap between buttons
LED info: 0.75rem margin-bottom
```

---

**Note**: All colors, sizes, and transitions follow the project's existing design system and can be modified via CSS variables if needed.
