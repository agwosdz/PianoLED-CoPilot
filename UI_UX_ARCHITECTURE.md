# UI/UX Architecture - Distribution Mode Primary Control

## New Simplified UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                      CALIBRATION SECTION                        │
│                   Piano LED Mapping                             │
│  Visual representation of how piano keys map to LED indices     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   VISUALIZATION CONTROLS                        │
│                                                                 │
│  Distribution Mode:  [Piano Based (with overlap) ▼]             │
│                      (PRIMARY CONTROL - FIRST)                  │
│                                                                 │
│  [🎹 Show Layout]    (SECONDARY - Hardware verification)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PIANO KEYBOARD VISUALIZATION                  │
│                    (IMMEDIATE FEEDBACK)                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  White  Black                                       │       │
│  │  C4 [4,5]  D4 [6,7]  E4 [8,9]  F4 [10,11]         │       │
│  │    C# [5]    D# [7]    F# [11]   G# [13]          │       │
│  │                                                     │       │
│  │  ... [continues for all 88 keys]                   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  Legend:                                                        │
│  ☐ White Key    ■ Black Key    ▲ Selected    ◆ Has Offset    │
│                                                                 │
│  Color Pickers:                                                │
│  White Key LED: ████  |  Black Key LED: ████                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                  (Click any key for details)
                              ▼
                   ┌─────────────────────┐
                   │  DETAILS PANEL      │
                   │                     │
                   │  C4 (MIDI 60)       │
                   │  LED: [4-7]         │
                   │                     │
                   │  [+ Add Offset]     │
                   └─────────────────────┘
```

## Data Flow for Distribution Mode Selection

```
USER ACTION
    │
    └─→ Changes Distribution Mode Dropdown
        └─→ Selects "Piano Based (no overlap)"
            │
            ▼
        Frontend: changeDistributionMode("Piano Based (no overlap)")
            │
            ├─→ POST /api/calibration/distribution-mode
            │   Request: { mode: "Piano Based (no overlap)", apply_mapping: true }
            │
            ▼
        Backend Processing
            │
            ├─→ Validate mode name
            ├─→ Map to allow_led_sharing=false
            ├─→ Save to settings
            ├─→ Regenerate mapping: 88 keys × 3-4 LEDs
            └─→ Return mapping_stats
                │
                └─→ Response: { mapping_stats: {...}, distribution_mode: "..." }
                    │
                    ▼
        Frontend Update
            │
            ├─→ updateLedMapping()
            │   Fetch new LED allocation from backend
            │
            ├─→ generatePianoKeys()
            │   Regenerate visualization with new LED indices
            │
            └─→ Piano keyboard displays
                ├─ Key 0: [4,5,6,7] (4 LEDs)
                ├─ Key 1: [8,9,10,11] (4 LEDs)
                └─ ... all 88 keys with updated allocation
                    │
                    ▼
            USER SEES IMMEDIATE CHANGE
            (No extra steps, no confusion)
```

## Control Hierarchy

### Before (Confusing)
```
Visualization Controls
├─ Show Layout [Button]
├─ Distribution Mode: [Dropdown]  ← Mixed with others
├─ Validate Mapping [Button]      ← Unclear purpose
├─ Mapping Info [Button]          ← Duplicate info
└─ (User confused about what to do first)
```

### After (Clear & Intuitive)
```
Visualization Controls
├─ Distribution Mode: [Dropdown]  ← PRIMARY (user starts here)
└─ Show Layout [Button]           ← SECONDARY (optional)

Result: User instantly understands the workflow
```

## Interaction State Machine

```
STATE 1: Initial Load
├─ Distribution mode loaded
├─ Piano visualization displays current mapping
└─ User can interact

STATE 2: Mode Selection
├─ User changes distribution mode
├─ Dropdown shows new selection
├─ Loading state (brief)
└─ → STATE 3

STATE 3: Update Mapping
├─ Backend regenerates allocation
├─ Frontend refreshes keyboard
├─ All LED indices updated
└─ → STATE 4

STATE 4: Visual Feedback
├─ Piano keys show new LED allocation
├─ All 88 keys visible with new indices
├─ Color indicates coverage status
└─ → STATE 1 (ready for next change)

OPTIONAL: Show Layout
├─ User clicks [🎹 Show Layout]
├─ All LEDs light up on hardware
├─ User can verify physical alignment
├─ Click to dismiss
└─ → STATE 1
```

## Key Information Display

### Piano Key Visual Components

```
┌──────────────────┐
│  White Key       │  ← Key type (white/black)
│                  │
│  C4 LED [4-7]    │  ← Key name + LED indices (from distribution)
│                  │
│  ✓               │  ← Covered indicator (within LED range)
└──────────────────┘

Color Coding:
- Green background: Key is covered by LED allocation
- Gray background: Key is uncovered (outside LED range)
- Border glow: Currently selected
- Green border: Has custom offset
```

### Details Panel (On Click)

```
┌──────────────────────────────────┐
│  C4 (MIDI 60)              [×]   │  ← Close button
├──────────────────────────────────┤
│  LED Indices (with offsets):     │
│  ├─ Current: [4, 5, 6, 7]        │
│  └─ (From distribution mode)     │
│                                  │
│  [➕ Add Individual Offset]       │  ← Per-key adjustment
└──────────────────────────────────┘
```

## Color Picker Legend

```
Legend
├─ ☐ White Key (standard)
├─ ■ Black Key (standard)
├─ ⬜ Selected (highlighted)
├─ ◆ Has Custom Offset (border)
│
└─ Color Customization
   ├─ White Key Color: ████  [Choose color for white key LEDs]
   └─ Black Key Color: ████  [Choose color for black key LEDs]
```

## Layered Architecture

```
┌─────────────────────────────────┐
│  Distribution Mode Layer        │  ← User selects mode here
│  (Piano Based with/no overlap)  │     Determines 3-4 or 5-6 LEDs/key
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  Per-Key Adjustment Layer       │  ← Optional fine-tuning
│  (Individual key offsets)       │     Applied on top of distribution
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  Final Mapping Display          │  ← What user sees
│  (All adjustments applied)      │     Updated immediately
└─────────────────────────────────┘
```

## Performance Characteristics

```
ACTION                      RESPONSE TIME  USER FEEDBACK
────────────────────────────────────────  ─────────────
Select mode:                <100ms         Instant visual update
                                          (keyboard refreshes)

Click key:                  <50ms          Details panel appears
                                          (LED indices shown)

Show Layout:                <200ms         LEDs light up on hardware
                                          (if connected)

Change color:               <10ms          Preview in legend
                                          (instant visual feedback)

Scroll keyboard:            <16ms          Smooth 60fps
                                          (if hardware available)
```

## Complete User Workflows

### Workflow 1: Switch LED Distribution

```
1. User navigates to Settings → Calibration
   → Sees "Piano LED Mapping" section

2. Notices "Distribution Mode:" dropdown at top

3. Selects "Piano Based (no overlap)"
   → Piano instantly shows 3-4 LEDs per key
   → All offsets automatically reapplied
   → Visual feedback complete

4. Done! No extra steps needed
```

### Workflow 2: Verify on Hardware

```
1. User wants to verify mapping on actual LEDs

2. Clicks [🎹 Show Layout] button
   → All LEDs light up (white keys = cyan, black keys = magenta)

3. User observes physical alignment

4. Clicks key or presses ESC
   → LEDs turn off
   → Back to visualization mode
```

### Workflow 3: Fine-tune Single Key

```
1. User clicks a piano key (e.g., C4)
   → Details panel appears showing LED indices

2. Clicks [+ Add Offset]
   → Scrolls to CalibrationSection2
   → Can adjust this specific key

3. Returns to visualization
   → Piano key shows updated LED allocation
   → Other keys unaffected
```

## Why This Design Works

✅ **Hierarchical** - Distribution mode is clearly primary
✅ **Immediate** - No delays, no extra confirmations
✅ **Visual** - See changes happen in real-time
✅ **Intuitive** - Natural user flow
✅ **Flexible** - Can customize further if needed
✅ **Simple** - Removes confusing duplicate controls
✅ **Efficient** - Fewer clicks to get results

---

**Architecture Status:** ✅ Complete and Production Ready
