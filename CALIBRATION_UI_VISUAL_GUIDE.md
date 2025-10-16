# CalibrationSection3 UI - Visual Guide

## Layout & Components

```
┌─────────────────────────────────────────────────────────────────┐
│                   CALIBRATION SECTION 3                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  VISUALIZATION CONTROLS (UPDATED)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [🎹 Show Layout] [Distribution: ⯯] [Color Pickers...]   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  PIANO KEYBOARD (88 KEYS)                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [W] [W][B][W][B][W] [W] [W][B][W][B][W][B][W] ...      │  │
│  │  C1  C#1 D1 D#1 E1  F1  F#1 G1 G#1 A1 A#1 B1           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  SELECTED KEY DETAILS (if any key is selected)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Visualization Controls Section - EXPANDED

### Component Breakdown

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     VISUALIZATION CONTROLS                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  Row 1: Show Layout Button                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ [🎹 Show Layout]                                    OR [✓ Layout V...] │ │
│  │                                                                        │ │
│  │ Toggles layout visualization. Text changes based on state.           │ │
│  │ Automatically dismisses when user clicks any piano key.              │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Row 2: Distribution Mode Selector                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ Distribution Mode: [Proportional ⯯]                                   │ │
│  │                    [Fixed]                                            │ │
│  │                    [Custom]                                           │ │
│  │                                                                        │ │
│  │ Dropdown to select LED distribution strategy.                         │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Row 3: Color Selectors (NEW)                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  White Key LED Color:          Black Key LED Color:                  │ │
│  │  ┌─────────┐                   ┌─────────┐                           │ │
│  │  │ [COLOR] │ RGB(0, 100, 150)  │ [COLOR] │ RGB(150, 0, 100)         │ │
│  │  └─────────┘                   └─────────┘                           │ │
│  │   (Cyan/Blue)                   (Magenta/Pink)                       │ │
│  │                                                                        │ │
│  │  Click color square to open native color picker                      │ │
│  │  RGB values update in real-time                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Row 4: Validation & Info Buttons (EXISTING)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ [✓ Validate Mapping]  [📊 Mapping Info]                             │ │
│  │                                                                        │ │
│  │ Load validation results and mapping statistics                       │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Color Picker Detailed View

### Visual Layout

```
┌─────────────────────────────────────────────┐
│  White Key LED Color:                       │
│  ┌──────────────────────────────────────┐   │
│  │ ┌──────────┐  RGB(0, 100, 150)       │   │
│  │ │          │                          │   │
│  │ │ [COLOR]  │  [Cyan/Blue example]    │   │
│  │ │          │                          │   │
│  │ └──────────┘                          │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  Features:                                  │
│  • Click on color box to open picker       │
│  • Drag across color spectrum to select    │
│  • Adjust brightness/saturation           │
│  • See RGB values immediately              │
│  • Live update to visualization           │
│                                             │
│  On Change:                                │
│  1. Browser color picker opens            │
│  2. User selects new color                │
│  3. RGB values instantly convert          │
│  4. WHITE_KEY_COLOR state updates         │
│  5. Layout viz (if active) updates        │
│  6. Console logs change for debugging     │
│                                             │
└─────────────────────────────────────────────┘
```

### Browser Color Picker (Native)

```
When user clicks the color input:
┌──────────────────────────────────────┐
│  Color Picker Dialog (OS Native)      │
│                                      │
│  ┌────────────────────────────────┐ │
│  │  Color Spectrum                │ │
│  │                                │ │
│  │  [Gradient selector area]      │ │
│  │                                │ │
│  └────────────────────────────────┘ │
│                                      │
│  Hue: ─────●────────── (slider)    │
│  Sat: ─────●────────── (slider)    │
│  Lum: ─────●────────── (slider)    │
│                                      │
│  Hex: #0064969 ↔ RGB: 0, 100, 150 │
│                                      │
│  [ OK ]  [ Cancel ]                │
│                                      │
└──────────────────────────────────────┘

After selection → Component updates instantly
```

---

## Feature 1: Layout Visualization Auto-Dismiss

### Workflow

```
STEP 1: Initial State
┌──────────────────────────────────────────┐
│ Button: [🎹 Show Layout]                │
│ LEDs: Off                               │
│ Piano: All keys white (unselected)     │
└──────────────────────────────────────────┘
                    ↓ USER CLICKS BUTTON
┌──────────────────────────────────────────┐
│ Button: [✓ Layout Visible]              │
│ LEDs: WHITE_KEY_COLOR + BLACK_KEY_COLOR│
│ Piano: Visual with colored LEDs         │
└──────────────────────────────────────────┘
                    ↓ USER CLICKS ANY KEY
┌──────────────────────────────────────────┐
│ Button: [🎹 Show Layout]                │
│ LEDs: Off (visualization dismissed)     │
│ Piano: Normal state, selected key shown │
└──────────────────────────────────────────┘
```

### Code Flow

```
User clicks piano key
         ↓
handleKeyClick(midiNote)
         ↓
ALSO calls: handleKeyPressWhileVisualizingLayout(event)
         ↓
IF layoutVisualizationActive === true
         ↓
THEN: toggleLayoutVisualization()
         ↓
Calls: await turnOffAllLeds()
         ↓
Sets: layoutVisualizationActive = false
       showingLayoutVisualization = false
         ↓
Button updates: "🎹 Show Layout" (reactive)
         ↓
Normal key selection proceeds as usual
```

---

## Feature 2: Visual LEDs Use Key Colors

### Color Application

```
Light Up Process:
┌─────────────────────────────────────┐
│ Layout Visualization Started        │
├─────────────────────────────────────┤
│                                     │
│ COLLECT LEDs:                       │
│  • White key LEDs: []               │
│  • Black key LEDs: []               │
│                                     │
│ FOR each white key → collect LEDs  │
│ FOR each black key → collect LEDs  │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ LIGHT UP:                           │
│  if whiteKeyLeds.length > 0         │
│    → lightUpLedRangeWithColor(      │
│        whiteKeyLeds,                │
│        WHITE_KEY_COLOR              │
│      )                              │
│                                     │
│  if blackKeyLeds.length > 0         │
│    → lightUpLedRangeWithColor(      │
│        blackKeyLeds,                │
│        BLACK_KEY_COLOR              │
│      )                              │
│                                     │
└─────────────────────────────────────┘
```

### Color Values

```
Default Colors:
┌──────────────────────────────────────┐
│ WHITE_KEY_COLOR:                     │
│ • R: 0    (Red)                      │
│ • G: 100  (Green)                    │
│ • B: 150  (Blue)                     │
│ = Cyan/Blue tone                     │
│ = #0064𝟵6                            │
│                                      │
│ BLACK_KEY_COLOR:                     │
│ • R: 150  (Red)                      │
│ • G: 0    (Green)                    │
│ • B: 100  (Blue)                     │
│ = Magenta/Pink tone                  │
│ = #960064                            │
│                                      │
│ User can change via Color Pickers   │
└──────────────────────────────────────┘
```

---

## Feature 3: Color Selectors

### Input Conversion

```
Display Hex:
RGB(r, g, b) → "#{r.toString(16).padStart(2, '0')}..."

Example:
RGB(0, 100, 150)
  → r: 0 → "00"
  → g: 100 → "64"
  → b: 150 → "96"
  → Result: "#006496"

Convert Back:
Hex "#006496"
  → Remove "#": "006496"
  → r: "00" → parseInt(..., 16) → 0
  → g: "64" → parseInt(..., 16) → 100
  → b: "96" → parseInt(..., 16) → 150
  → Result: RGB(0, 100, 150)
```

### State Management

```
Component State:
┌─────────────────────────────────────┐
│ WHITE_KEY_COLOR = {                 │
│   r: 0,    // 0-255                 │
│   g: 100,  // 0-255                 │
│   b: 150   // 0-255                 │
│ }                                   │
│                                     │
│ BLACK_KEY_COLOR = {                 │
│   r: 150,  // 0-255                 │
│   g: 0,    // 0-255                 │
│   b: 100   // 0-255                 │
│ }                                   │
└─────────────────────────────────────┘

User selects new color:
    ↓
Color picker closes
    ↓
on:change handler fires
    ↓
Parse hex to RGB
    ↓
Update WHITE_KEY_COLOR or BLACK_KEY_COLOR
    ↓
Component re-renders
    ↓
RGB label updates
    ↓
Next layout visualization uses new color
```

---

## Styling Hierarchy

```
.color-selectors (flex container)
├─ .color-picker-group (white keys)
│  ├─ label
│  └─ .color-picker-input (flex row)
│     ├─ input[type="color"] (60x40px)
│     └─ .color-label (RGB display)
│
└─ .color-picker-group (black keys)
   ├─ label
   └─ .color-picker-input (flex row)
      ├─ input[type="color"] (60x40px)
      └─ .color-label (RGB display)

Responsive:
  Desktop: Two color pickers side-by-side
  Tablet:  Two color pickers side-by-side (wraps if needed)
  Mobile:  Stacked vertically (flex-wrap: wrap)
```

---

## Interaction Timeline

```
Timeline of User Actions:
═══════════════════════════════════════════════════════════════

T0: Page loads
    ├─ Colors loaded from settings
    ├─ Color picker inputs populated with hex values
    └─ RGB labels show current values

T1: User clicks color picker (white keys)
    ├─ Native color picker dialog opens
    └─ Browser-specific color selection UI appears

T2: User selects new color in picker
    ├─ Hex value selected (e.g., #FF6B35)
    └─ User clicks OK/Done

T3: Color picker closes
    ├─ on:change event fires
    ├─ Hex parsed to RGB: RGB(255, 107, 53)
    ├─ WHITE_KEY_COLOR state updates
    ├─ Component re-renders
    ├─ Input value reflects new hex
    ├─ RGB label shows new values
    └─ Console logs change

T4: User clicks "🎹 Show Layout"
    ├─ Layout visualization activates
    ├─ WHITE_KEY LEDs light in NEW color
    ├─ BLACK_KEY LEDs light in old color (unchanged)
    └─ Button shows "✓ Layout Visible"

T5: User clicks any piano key
    ├─ handleKeyPressWhileVisualizingLayout() detected
    ├─ LEDs turn off
    ├─ Button reverts to "🎹 Show Layout"
    ├─ Key selection proceeds normally
    └─ New color persists for next visualization

T6: User changes black key color
    └─ Same flow as T1-T3

T7: Next layout visualization shows BOTH new colors
```

---

## Summary

### What Changed

| Feature | Before | After |
|---------|--------|-------|
| Layout Button | Toggle on/off, stays on | Auto-dismisses on key click |
| LED Colors | Hardcoded/settings only | Color picker inputs added |
| Color Preview | None in UI | Real-time with label |
| User Control | Limited | Full RGB customization |
| Workflow | Multiple steps | Streamlined |

### Files Modified

- `frontend/src/lib/components/CalibrationSection3.svelte`
  - Added: 1 function, 2 color picker groups, CSS styling
  - Modified: 1 click handler

### Build Status

✅ Compiles without errors  
✅ No TypeScript errors  
✅ No Svelte compilation warnings (except pre-existing)  
✅ Responsive design verified  
✅ Component builds successfully

---

**All changes complete and verified!** ✅
