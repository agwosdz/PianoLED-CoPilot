# Per-Key Adjustments: LED Selection + Timing Integration

## Overview
LED Selection Override has been fully integrated into Individual Key Offsets in CalibrationSection3. Users can now adjust both timing (offset) and LED allocation for each key from a single unified interface.

## What Changed

### 1. CalibrationSection3 Component
**File**: `frontend/src/lib/components/CalibrationSection3.svelte`

#### New Imports
```typescript
import { ledSelectionState, ledSelectionAPI } from '$lib/stores/ledSelection';
```

#### New State Variables
```typescript
// LED Selection for Individual Keys
let selectedLEDsForNewKey: Set<number> = new Set();
let availableLEDsForForm: number[] = [];
let showLEDGrid = false;
```

#### New Functions
- `handleMidiNoteInput(midiNoteStr)` - Updates available LEDs when MIDI note is selected
- `toggleLED(ledIndex)` - Toggle individual LEDs on/off in the form

#### Updated Functions
- `resetAddForm()` - Now resets LED selection state too
- `handleAddKeyOffset()` - Saves both timing offset AND LED override simultaneously

#### UI Changes
- Section renamed: "Individual Key Offsets" → "Per-Key Adjustments"
- Form now includes optional LED grid selector below offset input
- Checkbox to "Customize LED allocation for this key"
- When checked, shows LED grid with all available LEDs
- Offset items now display LED overrides (if any) below timing info

### 2. Settings Page Updates
**File**: `frontend/src/routes/settings/+page.svelte`

- Removed `LEDSelectionPanel` import (integrated into CalibrationSection3)
- Removed standalone wrapper div
- Removed styling for `led-selection-wrapper`

## User Workflow

### Adding a Per-Key Adjustment
1. **Click "⊕ Add" button** → Opens form
2. **Enter MIDI note** (e.g., 60 for Middle C)
3. **Enter timing offset** (in LED units, can be negative)
4. **Optionally: Check "Customize LED allocation"**
   - LED grid appears with available LEDs
   - Toggle individual LEDs on/off
   - Real-time counter shows selected count
5. **Click "✓ Add Adjustment"**
   - Both offset and LED override saved

### Editing Adjustments
- Click **✎ Edit** to modify offset
- If LED override exists, it displays below offset value
- To change LED allocation, delete adjustment and re-add with new LEDs

### Deleting Adjustments
- Click **🗑 Delete** to remove both offset and LED override for that key

## Data Structure

### Per-Key Data Stored
```
calibration_state.key_offsets[midiNote] = offset (integer)
ledSelectionState.overrides[midiNote] = [led1, led2, ...] (array)
```

Both are saved simultaneously when "Add Adjustment" is clicked.

## UI Components

### Form Section
- **MIDI Note Input**: Number field (0-127)
- **Offset Input**: Number field with sign (positive/negative)
- **LED Customize Checkbox**: Toggle LED grid visibility
- **LED Grid** (when checked):
  - Compact grid display (35px buttons)
  - Shows valid LED range
  - Real-time selection counter
  - Checkmark indicates selected LEDs

### Adjustment List
Each item shows:
- **Key Name**: MIDI note name (e.g., "C4")
- **Offset Value**: "±X LEDs offset"
- **LED Badge** (if override): `[120, 121, 122, ...]` in monospace font
- **Edit/Delete buttons**

### Visual Design
- **Form**: Light green background (#f1f8e9)
- **LED Grid**: Muted green scheme
- **Selected LEDs**: Bright green (#66bb6a)
- **Badges**: Monospace font, small size for compactness

## Styling Added

```css
/* LED Selection Styles */
.led-selection-label { /* Checkbox with label */ }
.led-selection-section { /* Form section background */ }
.led-info { /* Range and count info */ }
.led-grid-compact { /* Grid layout */ }
.led-button-compact { /* Individual LED buttons */ }
.led-button-compact.selected { /* Selected state */ }

/* Updated offset display */
.offset-main { /* Main offset info line */ }
.led-override-badge { /* LED override display */ }
.offsets-description { /* Section subtitle */ }
```

## API Integration

### Endpoints Used
```
PUT /api/calibration/key-offsets/<midi_note>    # Save timing offset
PUT /api/led-selection/key/<midi_note>          # Save LED override
DELETE /api/calibration/key-offsets/<midi_note> # Delete offset
DELETE /api/led-selection/key/<midi_note>       # Delete override
```

Both are called together when user adds an adjustment.

## Data Flow

### Adding Adjustment
```
User Input
    ↓
handleAddKeyOffset()
    ├─→ await setKeyOffset(midiNote, newKeyOffset)
    │       └─→ PUT /api/calibration/key-offsets/<midi_note>
    │
    ├─→ if (selectedLEDsForNewKey.size > 0)
    │       └─→ await ledSelectionAPI.setKeyOverride(midiNote, ledArray)
    │           └─→ PUT /api/led-selection/key/<midi_note>
    │
    └─→ resetAddForm()
        Show success message
```

### Display Adjustment
```
For each key in keyOffsetsList:
  Display: Key Name | Offset Value
  
  if ledSelectionState.overrides[midiNote] exists:
    Display: LED Badge with allocated LEDs
```

## Testing Checklist

- [ ] Navigate to Settings → Calibration → Per-Key Adjustments
- [ ] Click "⊕ Add" button
- [ ] Enter MIDI note (e.g., 60)
- [ ] Enter offset (e.g., 2 or -1)
- [ ] Check "Customize LED allocation for this key"
- [ ] LED grid appears with available LEDs
- [ ] Toggle several LEDs on/off
- [ ] Verify "Selected: X LEDs" updates
- [ ] Click "✓ Add Adjustment"
- [ ] Verify adjustment appears in list
- [ ] Verify both offset AND LED badge show
- [ ] Edit adjustment - verify offset updates
- [ ] Delete adjustment - verify both offset and LED override removed
- [ ] Verify changes persist on page reload

## Benefits of Integration

1. **Unified Interface**: Both adjustments in one form, not separate panels
2. **Reduced Cognitive Load**: No jumping between different sections
3. **Atomic Operations**: Offset + LED allocation saved together
4. **Better Organization**: Related adjustments grouped by key
5. **Space Efficient**: No separate panel needed in main UI
6. **Logical Grouping**: Users think of per-key adjustments as a unit

## Backward Compatibility

- Existing key offsets continue to work
- Existing LED overrides continue to work
- Can add either offset, LED override, or both to a key
- No data migration needed

## File Changes Summary

### Modified Files
1. `frontend/src/lib/components/CalibrationSection3.svelte`
   - Added LED selection store imports
   - Added LED state management
   - Extended form with optional LED grid
   - Updated list display to show LED overrides
   - Added comprehensive styling

2. `frontend/src/routes/settings/+page.svelte`
   - Removed LEDSelectionPanel import
   - Removed wrapper div
   - Removed wrapper styles

### Unmodified (Already Functional)
- `frontend/src/lib/stores/ledSelection.ts` - Works as-is
- `backend/api/led_selection.py` - Works as-is
- `backend/services/led_selection_service.py` - Works as-is

## Future Enhancements

1. **Bulk Operations**: Select multiple keys and apply same LED allocation
2. **Presets**: Save/load common adjustment patterns
3. **Visual Preview**: Show physical representation of LED-to-key mapping
4. **Undo/Redo**: Navigate through adjustment history
5. **LED Density Override**: Per-key LED count adjustment
6. **Validation**: Warn if LEDs overlap excessively
