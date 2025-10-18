# UI/UX Visual Guide - Pitch Adjustment in Parameters Grid

## Before (Incorrect)
```
Advanced Physics Parameters
┌─────────────────────────────────────────────────┐
│ White Key Width    │  Black Key Width           │
│ ◇◇◇◇◇◇◇◇ 22.0mm  │ ◇◇◇◇◇◇ 12.0mm             │
├─────────────────────────────────────────────────┤
│ Key Gap            │  LED Width                 │
│ ◇◇ 1.0mm          │ ◇◇ 2.0mm                   │
├─────────────────────────────────────────────────┤
│ Overhang Threshold                              │ ← Only 5 params
│ ◇◇◇ 1.5mm                                      │
└─────────────────────────────────────────────────┘

[Separate section below]
Pitch Adjustment Status
┌─────────────────────────────────────────────────┐
│ ⬛ Adjusted                                      │
│ Theoretical: 5.0000 mm                          │
│ Calibrated: 5.0100 mm                           │
│ Difference: 0.0100 mm (0.20%)                   │
│ Reason: Actual LED range...                     │
└─────────────────────────────────────────────────┘
```

**Problems:**
- ❌ Pitch display separated from parameters
- ❌ Different styling and layout
- ❌ User has to scroll to see pitch info
- ❌ Not obvious which parameters were adjusted
- ❌ Verbose and takes up space

---

## After (Correct) ✓
```
Advanced Physics Parameters
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ White Key Width      │ Black Key Width      │ Key Gap              │
│ ◇◇◇◇◇◇◇ 22.0 mm     │ ◇◇◇◇◇◇ 12.0 mm      │ ◇◇ 1.0 mm            │
└──────────────────────┴──────────────────────┴──────────────────────┘

┌──────────────────────┬──────────────────────┬──────────────────────┐
│ LED Physical Width   │ Overhang Threshold   │ Pitch Adjustment ⬛   │
│ ◇◇ 2.0 mm            │ ◇◇◇ 1.5 mm           │ ⬛ Adjusted          │
│                      │                      │ Used:   5.0100 mm    │
│                      │                      │ Theory: 5.0000 mm    │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

**Benefits:**
- ✅ Pitch display fills the empty 3rd cell in row 2
- ✅ All 6 items fit perfectly in 3x2 grid
- ✅ Consistent layout and styling
- ✅ All info visible at once
- ✅ Easy to scan: badge shows status immediately
- ✅ Compact: only essential info shown
- ✅ Same cell size as other parameters

---

## State Indicators

### Case 1: Pitch Adjustment Needed (Typical)

**Scenario**: User sets LED range that requires different pitch

```
Advanced Physics Parameters
┌──────────────────────┬──────────────────────┐
│ Overhang Threshold   │ Pitch Adjustment     │
│ ◇◇◇ 1.5 mm           │┌────────────────────┐│
│                      ││ ⬛ Adjusted        ││ ← Yellow bg
│                      ││                    ││
│                      ││ Used:   5.0100 mm  ││
│                      ││ Theory: 5.0000 mm  ││
│                      │└────────────────────┘│
└──────────────────────┴──────────────────────┘

Color: Yellow gradient (#fef3c7 → #fde68a)
Badge: Yellow "Adjusted" (#fcd34d)
Meaning: System auto-calibrated pitch to achieve coverage
```

### Case 2: Pitch Already Optimal

**Scenario**: User's parameters align perfectly with theory

```
Advanced Physics Parameters
┌──────────────────────┬──────────────────────┐
│ Overhang Threshold   │ Pitch Adjustment     │
│ ◇◇◇ 1.5 mm           │┌────────────────────┐│
│                      ││ ⬜ Optimal         ││ ← Gray bg
│                      ││                    ││
│                      ││ Used:   5.0000 mm  ││
│                      ││ Theory: 5.0000 mm  ││
│                      │└────────────────────┘│
└──────────────────────┴──────────────────────┘

Color: Gray gradient (#f3f4f6 → #e5e7eb)
Badge: Gray "Optimal" (#d1d5db)
Meaning: No pitch adjustment needed
```

---

## User Experience Flow

### Step 1: Initial Load
```
User opens Physics-Based LED Detection mode
        ↓
System loads default parameters
        ↓
Grid displays 5 parameters (W key, B key, gap, LED, overhang)
        ↓
Pitch display: NOT shown yet (no info loaded)
```

### Step 2: Modify Parameters
```
User adjusts parameters (e.g., changes overhang threshold)
        ↓
"Apply Changes" button becomes enabled
        ↓
✓ Apply Changes → pressed
```

### Step 3: Backend Processing
```
Backend receives new parameters
        ↓
STEP 1: Generate initial mapping
        ↓
STEP 2: Detect coverage gap
        ↓
STEP 3: Calculate pitch adjustment
        ↓
        If gap detected:
          └─→ Regenerate mapping with new pitch
        ↓
Response: pitch_calibration_info { was_adjusted, used, theory, ... }
```

### Step 4: Frontend Display
```
Response received with pitch_calibration_info
        ↓
pitchCalibrationInfo = response data
        ↓
Pitch display component renders:
  - Background: Yellow if was_adjusted, Gray if not
  - Badge: "Adjusted" if was_adjusted, "Optimal" if not
  - Values: Shows used vs theory pitch
        ↓
User sees: "Oh, the system adjusted pitch to achieve coverage!"
```

---

## Visual States

### Grid Cell Layout (Pitch Adjustment)

```
Normal State:
┌────────────────────────────┐
│ Label: "Pitch Adjustment"  │  ← 0.9rem, 600 weight
├────────────────────────────┤
│ ⬛ Adjusted               │  ← Status badge
├────────────────────────────┤
│ Used:   5.0100 mm         │  ← Value row 1
├────────────────────────────┤
│ Theory: 5.0000 mm         │  ← Value row 2
└────────────────────────────┘
```

### Badge Variations

```
ADJUSTED:              OPTIMAL:
┌──────────────┐      ┌──────────────┐
│ ⬛ Adjusted  │      │ ⬜ Optimal    │
└──────────────┘      └──────────────┘
Yellow badge          Gray badge
Small caps,           Small caps,
bold text             bold text
```

### Value Display

```
Used:   5.0100 mm
├─ Left: Gray label (0.8rem, 600 weight)
└─ Right: Dark monospace value (0.8rem, 700 weight)

Theory: 5.0000 mm
├─ Left: Gray label (0.8rem, 600 weight)
└─ Right: Dark monospace value (0.8rem, 700 weight)

Format: {pitch}.{4 decimal places} mm
Example: 5.0100 mm (not 5.01 or 5.01 mm)
```

---

## Responsive Behavior

### Desktop (Wide)
```
3 columns, 2 rows:
┌─────────────┬─────────────┬─────────────┐
│  W Key      │  B Key      │  Key Gap    │
├─────────────┼─────────────┼─────────────┤
│ LED Width   │ Overhang    │  Pitch ⬛    │
└─────────────┴─────────────┴─────────────┘

All 6 items visible at once in perfect grid
```

### Tablet (Medium)
```
2 columns:
┌──────────────┬──────────────┐
│  Parameter   │  Parameter   │
├──────────────┼──────────────┤
│  Parameter   │  Parameter   │
├──────────────┼──────────────┤
│  Parameter   │  Pitch ⬛     │
└──────────────┴──────────────┘

Still visible, small scroll if needed
```

### Mobile (Narrow)
```
1 column:
┌──────────────┐
│  Parameter   │
├──────────────┤
│  Parameter   │
├──────────────┤
│  Parameter   │
├──────────────┤
│  Parameter   │
├──────────────┤
│  Parameter   │
├──────────────┤
│  Pitch ⬛     │
└──────────────┘

Vertical stack, scroll to see all
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **In Grid** | Pitch is a system-determined parameter, belongs with other parameters |
| **6th Cell** | Last position, pairs with Overhang Threshold as complementary info |
| **Yellow/Gray** | Matches adjustment indicator pattern used elsewhere in UI |
| **Compact** | Shows only badge + 2 values, no verbose explanation |
| **Used/Theory** | Clear what pitch is being used vs what theory says |
| **Monospace** | Values in technical font for precision feel |
| **Read-only** | User can't adjust pitch directly (it's auto-calculated) |
| **Always Present** | After first parameter change, always visible to show state |

---

## Summary

The pitch adjustment display is now:
- **Where it belongs**: In the parameters grid
- **How it looks**: Yellow (adjusted) or gray (optimal)
- **What it shows**: Used pitch vs theoretical pitch
- **Why it matters**: Clear indication of system auto-calibration
- **Easy to understand**: Single glance tells the story

✅ **Perfect integration achieved!**
