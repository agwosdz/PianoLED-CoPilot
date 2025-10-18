# Visual Guide: Pitch Adjustment Display Layout

## Advanced Physics Parameters Section Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Advanced Physics Parameters                                  │
│ Fine-tune keyboard geometry for your piano model                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PARAMETERS GRID (4 columns → auto 1 on mobile)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [White Key]    [Black Key]    [Key Gap]    [LED Width]        │
│  Width (mm)     Width (mm)     (mm)         (mm)               │
│  ────────────   ────────────   ────────────  ────────────      │
│  22.0           12.0           1.0          3.5                │
│  ○─────────○    ○─────────○    ○─────────○   ○─────────○      │
│  Default:22.0   Default:12.0   Default:1.0  Default:3.5       │
│                                                                 │
│  [Overhang Threshold]  [Pitch Adjustment Status] ← NEW!        │
│  (mm)                  (Read-only, shows after apply)          │
│  ──────────────────    ──────────────────────────              │
│  1.5                   ┌──────────────────────────┐            │
│  ○─────────○           │ ⚠ ADJUSTED               │            │
│  Default:1.5           │ Theoretical: 5.0000 mm   │            │
│                        │ Calibrated:  5.0200 mm   │            │
│                        │ Difference:  0.0200 mm   │            │
│                        │            (0.40%)       │            │
│                        │                          │            │
│                        │ Actual LED range (247    │            │
│                        │ LEDs) spans 1235mm,      │            │
│                        │ requiring pitch adj...   │            │
│                        └──────────────────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ACTION BUTTONS                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [↻ Reset to Defaults]  [✓ Apply Changes]  [💾 Save Only]     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Two Display States

### State 1: Pitch Was Adjusted (Yellow)

```
┌──────────────────────────────────────┐
│ Pitch Adjustment Status              │  ← Header
├──────────────────────────────────────┤
│ ⚠ ADJUSTED                           │  ← Status Badge
│                                      │
│ ┌────────────────────────────────┐   │
│ │ Theoretical:  5.0000 mm        │   │  ← Pitch Details
│ │ Calibrated:   5.0200 mm        │   │
│ │ Difference:   0.0200 mm (0.40%)│   │
│ └────────────────────────────────┘   │
│                                      │
│ ℹ️ Actual LED range (247 LEDs) spans │  ← Reason
│ 1235mm, requiring pitch adjustment   │
└──────────────────────────────────────┘

Colors:
- Background: #fef3c7 to #fde68a (yellow gradient)
- Border: #fbbf24 (yellow)
- Badge: #fcd34d (bright yellow)
- Text: #92400e, #664d03 (browns)
- Details box: rgba(255,255,255,0.7)
- Detail values: #b45309 (monospace)
```

### State 2: No Adjustment Needed (Gray)

```
┌──────────────────────────────────────┐
│ Pitch Calibration                    │  ← Header
├──────────────────────────────────────┤
│ ✓ NO ADJUSTMENT NEEDED               │  ← Status Badge
│                                      │
│ ℹ️ Pitch matches theoretical         │  ← Reason
│ perfectly                            │
└──────────────────────────────────────┘

Colors:
- Background: #f3f4f6 to #e5e7eb (gray gradient)
- Border: #9ca3af (gray)
- Badge: #d1d5db (light gray)
- Text: #374151, #4b5563 (grays)
```

## Layout Positioning

### In the Parameters Grid

```
┌─ PARAMETERS GRID ─────────────────────────────────────────────┐
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   White     │  │   Black     │  │   Key Gap   │           │
│  │  Key Width  │  │  Key Width  │  │     (mm)    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │     LED     │  │  Overhang   │  │   [space]   │           │
│  │    Width    │  │  Threshold  │  │             │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Pitch Adjustment Status (or Pitch Calibration)          │ │
│  │ Spans full width (grid-column: 1 / -1)                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Mobile Responsive

On screens ≤768px:
- Grid switches to 1 column layout
- Each parameter takes full width
- Pitch calibration box still spans full width
- All content remains readable
- Buttons stack vertically

```
Mobile (1 column):
┌─────────────┐
│ White Key   │
│ Width       │
└─────────────┘
┌─────────────┐
│ Black Key   │
│ Width       │
└─────────────┘
┌─────────────┐
│ Key Gap     │
│ (mm)        │
└─────────────┘
┌─────────────┐
│ LED Width   │
│ (mm)        │
└─────────────┘
┌─────────────┐
│ Overhang    │
│ Threshold   │
└─────────────┘
┌──────────────────────┐
│ Pitch Adjustment Box │
│ (Full width)         │
└──────────────────────┘
```

## Interaction Flow

```
User Input
    ↓
Parameters Change (Slider or Input)
    ↓
physicsParamsChanged = true
    ↓
"Apply Changes" button becomes enabled
    ↓
User Clicks "Apply Changes"
    ↓
savePhysicsParameters() Called
    ↓
POST /api/calibration/physics-parameters
    ↓
Backend Analyzes Mapping
    ↓
auto_calibrate_pitch() Runs
    ↓
Response with pitch_calibration_info
    ↓
Frontend Receives Response
    ↓
pitchCalibrationInfo State Updated
    ↓
Display Box Rendered
    ├─ If was_adjusted = true → Yellow Box
    └─ If was_adjusted = false → Gray Box
    ↓
User Sees Feedback
```

## Accessibility Features

✓ **Semantic HTML**
- Proper heading hierarchy
- Label associations
- Fieldset groupings

✓ **Color + Text**
- Not relying on color alone for status
- Badge text + color
- Supporting icons (⚠️, ✓)

✓ **Read-Only Indication**
- Gray/muted appearance
- No input fields
- Clear it's informational

✓ **Keyboard Navigation**
- All parameters accessible via Tab
- Sliders usable with arrow keys
- Buttons focusable and clickable

## CSS Grid Implementation

```css
.parameters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.pitch-adjustment-box {
  grid-column: 1 / -1;  /* Spans all columns */
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border: 2px solid #fbbf24;
  border-radius: 8px;
  padding: 1rem;
  opacity: 0.95;
}
```

## Summary

The pitch adjustment display box integrates seamlessly into the existing Advanced Physics Parameters section:

✓ Positioned below Key Gap and alongside Overhang Threshold
✓ Spans full width when displayed
✓ Shows two distinct states with clear visual differentiation
✓ Locked/read-only appearance prevents confusion
✓ Provides immediate feedback after Apply Changes
✓ Fully responsive on mobile and tablet
✓ Accessible to keyboard and screen reader users
✓ Professional design that matches existing UI

The layout is clean, informative, and gives users complete transparency about the automatic pitch calibration process.
