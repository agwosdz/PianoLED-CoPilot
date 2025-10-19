# Enhanced LED Customization - Visual Guide

## UI Layout

### Complete Form with LED Customization

```
┌─────────────────────────────────────────────────────────┐
│  Per-Key Adjustment Form                                │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  MIDI Note (0-127):           [___________]             │
│                                                           │
│  Offset (LEDs):               [_____]                   │
│                                                           │
│  ☐ Customize LED allocation for this key               │
│                                                           │
│  (If user enters MIDI note and checks box:)             │
│                                                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Currently Assigned LEDs (Click to Reallocate)     │  │
│  │ Count: 4 LEDs                                 [4]  │  │
│  ├───────────────────────────────────────────────────┤  │
│  │                                                     │  │
│  │  [120] [121] [122] [123]  ← Large green buttons   │  │
│  │                                                     │  │
│  │  Hint: Click an LED to move it to the adjacent key │  │
│  │                                                     │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ Manual LED Selection (Optional)                    │  │
│  │                                                     │  │
│  │  [120][121][122]...[246]  ← Small buttons         │  │
│  │  (Some are yellow = currently assigned)           │  │
│  │                                                     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│                     [✓ Add Adjustment]                   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## LED Button States

### Current Allocation Grid

```
Green (Active - Still Selected)    Red (Removed - Will Reallocate)
┌─────────────────┐               ┌─────────────────┐
│   120           │               │   122           │
│                 │               │       ✕         │
│  (Click to      │               │  (Click to      │
│   reallocate)   │               │   reallocate)   │
└─────────────────┘               └─────────────────┘
Status: Assigned                   Status: Removed
Color: Green gradient              Color: Red gradient
Shadow: Normal                      Shadow: Faded


Manual Selection Grid
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│  120            │  │  121         │  │  125         │
│                 │  │  ✓           │  │  (Yellow)    │
│  (Unmodified)   │  │  (Selected)   │  │  (Current)   │
└─────────────────┘  └──────────────┘  └──────────────┘
Status: Default      Status: Selected   Status: Current
Color: White         Color: Green       Color: Yellow
Border: Gray         Border: Dark Green Border: Orange
```

## Visual States Explained

### State 1: Initial Display (MIDI Selected, Manual Grid Collapsed)

```
┌────────────────────────────────────┐
│  MIDI: [60] Offset: [2]            │
│  ☑ Customize LED allocation        │
│                                     │
│  Currently Assigned LEDs Count: 4   │
│  [120][121][122][123]  (Green)     │
│  "Click an LED to move it to the    │
│   adjacent key"                     │
│                                     │
│  [Expand manual grid ▼]             │
│  [✓ Add Adjustment]                │
└────────────────────────────────────┘

Action: User clicks LED 122
Result: LED 122 turns red with ✕
        Feedback shows it will move to key 61
```

### State 2: LED Removed (After Click)

```
┌────────────────────────────────────┐
│  Currently Assigned LEDs Count: 4   │
│  [120][121][122][123]              │
│         (Green) (Red:✕) (Green)    │
│                                     │
│  Manual LED Selection               │
│  [120][121][122][123][124]...      │
│  (120-121-123: unselected/current)  │
│  (122: yellow/current - will move)  │
│  [✓ Add Adjustment]                │
└────────────────────────────────────┘

Colors in Manual Grid:
- 120: White (not selected)
- 121: White (not selected)
- 122: Yellow (currently assigned, will leave)
- 123: White (not selected)
- 124: Blue (selected in custom)
```

### State 3: Manual Selection Override

```
┌────────────────────────────────────┐
│  Currently Assigned: [120,121,122,123]
│  Custom Selection:   [121,122,123,125]
│                                     │
│  Current Allocation:                │
│  [120][121][122][123]              │
│  (120 will be removed)              │
│  (121, 122, 123 stay)              │
│                                     │
│  Manual Grid:                       │
│  ... [122][123][124][125][126]...  │
│      (Yellow)(Yellow)(Blue)(Blue)(White)
│                                     │
│  Manual selection added LED 125     │
│  Total will be: [121,122,123,125]  │
└────────────────────────────────────┘
```

## User Interaction Flow

### Flow 1: Click & Reallocate

```
User enters MIDI note 60
    ↓
Current LEDs shown: 120, 121, 122, 123
    ↓
User clicks on LED 120
    ↓
Visual feedback:
├─ 120 turns red
├─ Checkmark appears on 120
└─ Message: "LED 120 will be reallocated to key 59"
    ↓
User clicks "✓ Add Adjustment"
    ↓
System saves:
├─ MIDI 60: offset = 2, LEDs = [121, 122, 123]
└─ MIDI 59: gets LED 120
    ↓
Success message shown
```

### Flow 2: Manual Override

```
User enters MIDI note 60
    ↓
Current LEDs: 120, 121, 122, 123
    ↓
User scrolls down in manual grid
    ↓
User clicks LED 125 (yellow, currently elsewhere)
    ↓
LED 125 now appears selected (blue)
    ↓
User clicks LED 120 in current grid
    ↓
LED 120 turns red (removed)
    ↓
User clicks "✓ Add Adjustment"
    ↓
System saves:
├─ MIDI 60: LEDs = [121, 122, 123, 125]
└─ Source of 125: reallocated from previous owner
```

### Flow 3: Complex Scenario

```
Key 60: Current = [120, 121, 122, 123]
        User removes: [120]
        User adds: [124]
        Final: [121, 122, 123, 124]

Key 61: Current = [124, 125, 126]
        User removes: [125]
        User adds: [128]
        Final: [124, 126, 128]

Result:
- 120 → reallocates to key 59
- 125 → reallocates to key 62
- 124 → remains (appears in both → conflict)
- 128 → comes from somewhere (auto-balanced)

System automatically resolves conflicts
```

## Color Reference Card

```
┌────────────────────────────────────────────────────────┐
│ COLOR MEANINGS IN LED CUSTOMIZATION                   │
├────────────────────────────────────────────────────────┤
│                                                         │
│ 🟢 GREEN (#66bb6a)                                    │
│   Currently assigned to this key                       │
│   Will stay if user saves                              │
│   Large buttons in current allocation grid             │
│                                                         │
│ 🔴 RED (#ef5350)                                      │
│   Currently assigned, but marked for removal           │
│   Will be reallocated to adjacent key                  │
│   Shows ✕ indicator                                    │
│                                                         │
│ 🟡 YELLOW (#fff9c4)                                   │
│   Currently assigned (somewhere else)                  │
│   Shown in manual grid for reference                   │
│   Can click to include in custom allocation            │
│                                                         │
│ 🔵 BLUE (#66bb6a in selected mode)                    │
│   Manually selected in custom allocation              │
│   Will be included when saving                         │
│   Shows ✓ checkmark                                    │
│                                                         │
│ ⚪ WHITE (default)                                     │
│   Not currently assigned                               │
│   Available for manual selection                       │
│   Click to add to custom allocation                    │
│                                                         │
└────────────────────────────────────────────────────────┘
```

## Responsive Design

### Desktop (>1024px)
```
┌─────────────────────────────────────────────────────────┐
│ Current LEDs: [120][121][122][123]   (45px buttons)    │
│ Manual Grid:  [120][121][122]...[246] (35px buttons)   │
└─────────────────────────────────────────────────────────┘
- Both grids visible side-by-side or stacked
- Smooth transitions
```

### Tablet (768px - 1024px)
```
┌──────────────────────────────────┐
│ Current: [120][121][122][123]    │
│ Manual:  [120][121][122]...[246] │
└──────────────────────────────────┘
- Grids stack vertically
- Touch-friendly sizes
```

### Mobile (<768px)
```
┌────────────────────┐
│ Current: 4 LEDs    │
│ [120]              │
│ [121]              │
│ [122]              │
│ [123]              │
│                    │
│ Manual (20 per row)│
│ [120][121][122]... │
└────────────────────┘
- Single column for current
- Reduced button size
- Horizontal scroll for manual
```

## User Hints & Tooltips

```
Hover over current LED button:
  Tooltip: "Click to reallocate LED 120 to adjacent key"
  
Hover over removed LED (red):
  Tooltip: "LED 120 will move to key 59 when saved"
  
Hover over yellow LED (manual grid):
  Tooltip: "LED 125 currently assigned to key 65"
  
Hover over blue LED (manual grid):
  Tooltip: "LED selected in your custom allocation"
```

## Before & After Examples

### Example 1: Simple Reallocation

**Before:**
```
Key 60 (C4): [120, 121, 122, 123]
Key 61 (C#4): [124, 125, 126, 127]
```

**User Action:**
```
Open Key 60 → Remove LED 120 (left edge)
```

**After:**
```
Key 59 (B3): [..., 120]  (LED added)
Key 60 (C4): [121, 122, 123]  (LED removed)
Key 61 (C#4): [124, 125, 126, 127]  (unchanged)
```

### Example 2: Manual Override

**Before:**
```
Key 60: [120, 121, 122, 123]
Key 62: [124, 125, 126, 127]
```

**User Action:**
```
Open Key 60
Remove LED 120
Add LED 124 (from manual grid)
```

**After:**
```
Key 60: [121, 122, 123, 124]  (120 removed, 124 added)
Key 62: [125, 126, 127]  (124 removed)
Key 59: [120]  (received from Key 60)
```

## Accessibility Features

✅ All buttons have descriptive titles (hover tooltips)
✅ Color + shape differentiation (not color alone)
✅ Clear button labels (LED indices)
✅ High contrast colors (WCAG AA compliant)
✅ Keyboard navigable (Tab through buttons)
✅ Large enough touch targets (35px minimum)
✅ Clear visual feedback (hover, active states)

---

**Visual Design Status**: ✅ **COMPLETE AND INTUITIVE**
