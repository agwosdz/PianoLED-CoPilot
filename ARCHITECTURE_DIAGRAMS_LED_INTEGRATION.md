# Architecture Diagram: LED Adjustments Integration

## Before vs After

### BEFORE: Separate Interfaces
```
┌─────────────────────────────────────┐
│      SETTINGS → CALIBRATION         │
├─────────────────────────────────────┤
│  Individual Key Offsets             │
│  ┌──────────────────────────┐       │
│  │ MIDI Note: [___]         │       │
│  │ Offset: [___]            │       │
│  │ [✓ Add Offset]           │       │
│  └──────────────────────────┘       │
│  Adjustments:                        │
│  • C4 | 2 LEDs offset               │
│  • D4 | -1 LEDs offset              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│    LED Selection Override Panel     │
│    ┌────────────────────────────┐   │
│    │ 🎹 Step 1: Select Key      │   │
│    │ [21]...[60]...[108]        │   │
│    │                            │   │
│    │ Step 2: Select LEDs        │   │
│    │ [120][121][122]...         │   │
│    │ [✓ Apply] [Clear] [Cancel] │   │
│    └────────────────────────────┘   │
└─────────────────────────────────────┘

⚠️ Problem: Users jump between two sections
⚠️ Problem: Related adjustments feel disconnected
⚠️ Problem: Mental model split
```

### AFTER: Unified Interface
```
┌──────────────────────────────────────┐
│    SETTINGS → CALIBRATION            │
├──────────────────────────────────────┤
│  Per-Key Adjustments ⭐              │
│  "Adjust timing and LED allocation"  │
│  ┌────────────────────────────────┐  │
│  │ MIDI Note: [___]               │  │
│  │ Offset: [___]                  │  │
│  │ ☐ Customize LED allocation     │  │
│  │                                │  │
│  │ (If checked:)                  │  │
│  │ Valid Range: 120-246           │  │
│  │ [120][121][122]...             │  │
│  │ Selected: 3 LEDs               │  │
│  │                                │  │
│  │ [✓ Add Adjustment]             │  │
│  └────────────────────────────────┘  │
│  Adjustments:                         │
│  • C4 | 2 LEDs offset                │
│    LEDs: [120, 121, 122]             │
│  • D4 | -1 LEDs offset               │
└──────────────────────────────────────┘

✅ Solution: Single unified interface
✅ Solution: Related adjustments together
✅ Solution: Clear mental model
✅ Solution: Atomic operations
```

## Data Flow Architecture

### Single Adjustment Operation
```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                               │
│  MIDI Note: 60  |  Offset: 2  |  LEDs: [120,121,122]      │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              CalibrationSection3.svelte                     │
│  handleAddKeyOffset()                                        │
│  ├─ Validate MIDI note (0-127)                             │
│  └─ Check if valid ──┐                                     │
└────────┬────────────────────────────────────────────────────┘
         │ Valid
         ▼
┌─────────────────────────────────────────────────────────────┐
│           ATOMIC TRANSACTION                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐      ┌──────────────────────┐    │
│  │  setKeyOffset()     │      │ ledSelectionAPI      │    │
│  │                     │      │ .setKeyOverride()    │    │
│  │ calibration_state   │      │                      │    │
│  │ .key_offsets[60]=2  │      │ ledSelection_state   │    │
│  │                     │      │ .overrides[60]=      │    │
│  │ PUT /api/          │      │ [120,121,122]       │    │
│  │ calibration/       │      │                      │    │
│  │ key-offsets/60     │      │ PUT /api/            │    │
│  │                     │      │ led-selection/       │    │
│  └──────────┬──────────┘      │ key/60               │    │
│             │                  └──────────┬──────────┘    │
│             ▼                             ▼                │
│      ✅ Success             ✅ Success                     │
│             │                             │                │
│             └──────────┬──────────────────┘               │
│                        │                                   │
│            Both Succeeded: Continue                        │
│            Either Failed: Rollback                         │
│                                                            │
└────────────────────────┬──────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    ✅ Success                      ❌ Error
    Show Message            Show Error Message
    Reset Form              Keep Form Open
    Update List             User Fixes & Retries
    Display Item
```

## State Management

### Component State (CalibrationSection3)
```
┌────────────────────────────────────────┐
│   FORM STATE                           │
├────────────────────────────────────────┤
│  showAddForm: boolean                  │
│  newKeyMidiNote: string                │
│  newKeyOffset: number                  │
│  showLEDGrid: boolean                  │
│  selectedLEDsForNewKey: Set<number>   │
│  availableLEDsForForm: number[]        │
│  editingKeyNote: number | null         │
│  editingKeyOffset: number              │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│   CALIBRATION STORE                    │
├────────────────────────────────────────┤
│  $calibrationState:                    │
│  ├─ key_offsets[60]: 2                 │
│  ├─ key_offsets[62]: -1                │
│  └─ ...                                │
│                                         │
│  $keyOffsetsList:                      │
│  ├─ { midiNote: 60, offset: 2 }       │
│  ├─ { midiNote: 62, offset: -1 }      │
│  └─ ...                                │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│   LED SELECTION STORE                  │
├────────────────────────────────────────┤
│  $ledSelectionState:                   │
│  ├─ overrides[60]: [120,121,122]      │
│  ├─ overrides[65]: [125,126]          │
│  ├─ validLEDRange: [120, 246]         │
│  └─ ...                                │
└────────────────────────────────────────┘
```

## Component Integration

### UI Component Hierarchy
```
Settings Page (+page.svelte)
│
├─ [Other Sections]
│
└─ Calibration Panel
   │
   ├─ CalibrationSection2 (LED Range)
   │  └─ Sets start_led, end_led
   │
   ├─ CalibrationSection3 (Mapping)
   │  └─ Shows current mapping
   │
   └─ Per-Key Adjustments (CalibrationSection3)
      │
      ├─ Form Section
      │  ├─ MIDI Note Input
      │  │  └─ on:input → handleMidiNoteInput()
      │  │     └─ Load available LEDs + existing override
      │  │
      │  ├─ Offset Input
      │  │  └─ bind:value={newKeyOffset}
      │  │
      │  └─ LED Customization (Conditional)
      │     ├─ Checkbox
      │     │  └─ Shows when newKeyMidiNote set
      │     │
      │     └─ LED Grid (Conditional)
      │        ├─ Shows when showLEDGrid == true
      │        ├─ Range Info
      │        ├─ Counter
      │        └─ LED Buttons
      │           └─ on:click → toggleLED()
      │
      ├─ Add Adjustment Button
      │  └─ on:click → handleAddKeyOffset()
      │     ├─ Validate MIDI
      │     ├─ Save offset
      │     ├─ Save LEDs (if selected)
      │     └─ Update lists
      │
      └─ Adjustment List
         ├─ For each adjustment:
         │  ├─ Key name + Offset value
         │  ├─ LED Badge (if override)
         │  ├─ Edit Button → startEditingKeyOffset()
         │  └─ Delete Button → handleDeleteKeyOffset()
         │
         └─ Edit Mode (Conditional)
            └─ Editable offset field
```

## API Integration

### Request/Response Flow
```
Form Submit
│
├─ Request 1: Calibration API
│  │
│  ├─ Endpoint: PUT /api/calibration/key-offsets/60
│  │ Body: { offset: 2 }
│  │
│  ├─ Response: { success: true, midiNote: 60, offset: 2 }
│  │
│  └─ Store Update: calibrationState.key_offsets[60] = 2
│
├─ Request 2: LED Selection API (if LEDs selected)
│  │
│  ├─ Endpoint: PUT /api/led-selection/key/60
│  │ Body: { selected_leds: [120, 121, 122] }
│  │
│  ├─ Response: { success: true, midiNote: 60, leds: [120, 121, 122] }
│  │
│  └─ Store Update: ledSelectionState.overrides[60] = [120, 121, 122]
│
└─ UI Updates
   ├─ Clear form
   ├─ Show success message
   └─ Re-render list
```

## Data Persistence

### Storage Hierarchy
```
┌─────────────────────────────────────────┐
│         Browser Memory                  │
│                                          │
│  Svelte Stores (Reactive)               │
│  ├─ calibrationState                    │
│  ├─ ledSelectionState                   │
│  └─ UI State (form fields)              │
│                                          │
│  (Re-fetched on page load)              │
└──────────────┬──────────────────────────┘
               │ (API calls)
               ▼
┌─────────────────────────────────────────┐
│      Backend Database                   │
│                                          │
│  ├─ calibration.db (SQLite)             │
│  │  └─ calibration table                │
│  │     └─ key_offsets { MIDI: offset }  │
│  │                                       │
│  └─ led_selection.db (or same)         │
│     └─ overrides table                  │
│        └─ { MIDI: [led1, led2, ...] }   │
│                                          │
│  (Persisted)                             │
└─────────────────────────────────────────┘
```

## Atomic Transaction Pattern

### Success Case
```
User clicks "Add"
    ↓
Validate inputs ✓
    ↓
BEGIN TRANSACTION
    ├─ Save offset (calibration DB) ✓
    │   └─ calibration_state.key_offsets[60] = 2
    │
    └─ Save LEDs (led_selection DB) ✓
        └─ ledSelection_state.overrides[60] = [120,121,122]
    ↓
COMMIT
    ↓
Update UI
    ├─ Clear form
    ├─ Show success
    └─ Display new adjustment
```

### Failure Case
```
User clicks "Add"
    ↓
Validate inputs ✓
    ↓
BEGIN TRANSACTION
    ├─ Save offset ✓
    │
    └─ Save LEDs ❌
        └─ API error
    ↓
ROLLBACK
    ├─ Undo offset save
    └─ Restore prior state
    ↓
Update UI
    ├─ Keep form open
    ├─ Show error message
    └─ User can retry/fix
```

## Benefits Visualization

### Complexity Reduced
```
Before:                     After:
┌──────────────────┐        ┌──────────────────┐
│  Interface 1     │        │  Unified         │
│  - 50 LOC        │        │  Interface       │
│  - LED Grid      │   →    │  - 120 LOC       │
│  - Key List      │        │  - Combined      │
├──────────────────┤        │  - Efficient     │
│  Interface 2     │        └──────────────────┘
│  - 50 LOC        │
│  - Offset Form   │        Mental Load: ↓↓↓
│  - Key List      │        User Confusion: ↓↓↓
└──────────────────┘        Maintenance: ↓↓
                            Code Duplication: ↓
```

### User Experience Improved
```
Old:
Settings → Offsets (add offset) → LEDs (add LEDs) ← Not intuitive

New:
Settings → Add adjustment (offset + LEDs together) ← Logical
```

---

**Architecture Status**: ✅ UNIFIED AND OPTIMIZED
