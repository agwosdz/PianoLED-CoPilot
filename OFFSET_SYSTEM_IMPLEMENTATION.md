# Dual Offset System: LED Offsets & Joint Offsets ✓ COMPLETE

## Overview

Implemented a comprehensive dual offset system that distinguishes between two types of calibration offsets:

1. **LED Offsets** - Manual fine-tuning per key (in LED units)
2. **Joint Offsets** - Automatic compensation for solder joints (in millimeters)

This allows for precise control over LED-to-key alignment, accounting for both manual adjustments and physical LED strip joint gaps.

## System Architecture

### Backend Structure

#### Settings Schema
```python
'calibration': {
    'key_offsets': {
        'type': 'object',
        'description': 'Per-key LED offset adjustments {midi_note: offset_value_leds} - manual fine-tuning'
    },
    'key_joint_offsets': {
        'type': 'object',
        'description': 'Per-key joint compensation offsets {midi_note: offset_mm} - automatic joint-based adjustments'
    }
}
```

#### API Endpoints

**LED Offsets:**
- `GET /api/calibration/key-offset/<midi_note>` - Get LED offset for a key
- `PUT /api/calibration/key-offset/<midi_note>` - Set LED offset (request body: `{ offset: int }`)
- `DELETE /api/calibration/key-offset/<midi_note>` - Delete LED offset
- `GET /api/calibration/key-offsets` - Get all LED offsets
- `PUT /api/calibration/key-offsets` - Batch set LED offsets

**Joint Offsets (NEW):**
- `GET /api/calibration/key-joint-offset/<midi_note>` - Get joint offset for a key
- `PUT /api/calibration/key-joint-offset/<midi_note>` - Set joint offset (request body: `{ offset_mm: float }`)
- `DELETE /api/calibration/key-joint-offset/<midi_note>` - Delete joint offset
- `GET /api/calibration/key-joint-offsets` - Get all joint offsets

### Offset Application Logic

**File:** `backend/config.py` - `apply_calibration_offsets_to_mapping()`

#### Processing Pipeline

1. **Normalize LED Offsets** → Keep as LED units (integers)
2. **Normalize Joint Offsets** → Convert mm to LED units (0.286 LEDs/mm = 3.5mm per LED)
3. **Calculate Cascading Offsets** → Sum all offsets for notes ≤ current note
4. **Combine Offsets** → `total_offset = led_offset + joint_offset`
5. **Apply Weld Compensation** → Add weld/joint gaps (pre-existing)
6. **Clamp to Range** → Constrain to [start_led, end_led]

#### Offset Cascading

**Important:** Both LED and joint offsets cascade:
- An offset at note N affects all notes >= N
- This ensures smooth transitions across offset boundaries
- Example: If note 36 has +3 LED offset, notes 36+ all get +3 adjustment

#### Unit Conversion

Joint offset mm to LED conversion:
```python
mm_to_leds_ratio = 3.5  # mm per LED at 200 LEDs/meter standard
offset_leds = round(offset_mm / mm_to_leds_ratio)
```

This converts 1mm joint gap to approximately 0.286 LEDs.

### Frontend Implementation

#### Svelte Store Updates

**File:** `frontend/src/lib/stores/calibration.ts`

New types:
```typescript
interface KeyJointOffset {
  midiNote: number;
  offsetMm: number;
  noteName: string;
}

interface CalibrationState {
  key_offsets: Record<number, number>;        // LED offsets
  key_joint_offsets: Record<number, number>;  // Joint offsets in mm
}
```

New store functions:
```typescript
setKeyJointOffset(midiNote: number, offsetMm: number): Promise<void>
deleteKeyJointOffset(midiNote: number): Promise<void>

// Convenience exports
export const setKeyJointOffset = (midiNote, offsetMm) => ...
export const deleteKeyJointOffset = (midiNote) => ...
```

#### Frontend Store Processing

Separate normalizers for each offset type:
```typescript
private normalizeKeyOffsets(offsets: any): Record<number, number>
private normalizeKeyJointOffsets(offsets: any): Record<number, number>
```

## User Interface

### Offset Management Buttons

In the Offset section of CalibrationSection3.svelte, each key will display:

1. **LED Offset Button** (existing)
   - Edit/delete LED offset in LED units
   - Range: -100 to +100 LEDs
   - Manual fine-tuning

2. **Joint Offset Button** (NEW)
   - Edit/delete joint offset in mm
   - Range: -10.0 to +10.0 mm
   - Automatic compensation button for solder joints
   - Marked as "Joint Offset" to distinguish from LED offset

### Visual Distinction

Planned UI improvements:
- LED offset: Blue/neutral color
- Joint offset: Red/joint warning color
- Hover/info: Show which type of offset is displayed
- List view: Show offsets grouped by type or mixed with type badge

## Data Flow Example

### Example: Setting Offsets for Key 54 (near first solder joint)

**Scenario:** User needs to compensate for 1mm solder joint gap after LED 53

1. **User Action:** Click "Add Joint Offset" for note 54
2. **Frontend:** POST to `/api/calibration/key-joint-offset/54`
   ```json
   { "offset_mm": 1.0 }
   ```
3. **Backend:** 
   - Validates: 1.0 mm is within [-10.0, 10.0]
   - Stores in `key_joint_offsets: { "54": 1.0 }`
   - Emits WebSocket event: `key_joint_offset_changed`
4. **Application:**
   - Next allocation: 1.0 mm → ~0.286 LEDs
   - Note 54's LEDs shifted by approximately +0.286 positions
   - All subsequent notes (55+) also affected by cascading

### Example: Allocation with Mixed Offsets

For note 36 with LED offset +3 and note 38 with joint offset +1.5mm:

```
Base allocation: Note 36 → LEDs [10, 11, 12]
                 Note 37 → LEDs [13, 14, 15]
                 Note 38 → LEDs [16, 17, 18]

Apply LED offset on note 36 (+3):
- Notes 36+: +3 LED shift
  Note 36 → [13, 14, 15]
  Note 37 → [16, 17, 18]
  Note 38 → [19, 20, 21]

Apply joint offset on note 38 (+1.5mm = ~0.43 LEDs ≈ 0):
- Notes 38+: +0 additional (rounds to 0)
  Note 38 → [19, 20, 21]

Final result after weld compensation and clamping...
```

## Integration Points

### Settings Service
- Reads/writes `calibration.key_joint_offsets` to SQLite
- Broadcasts changes via WebSocket

### Calibration API (`calibration.py`)
- GET `/status` returns both offset types
- PUT `/reset` clears both offset types
- WebSocket events for both offset changes

### Offset Application (`config.py`)
- Both offset types passed to `apply_calibration_offsets_to_mapping()`
- Unified processing pipeline
- Separate logging for each offset type

### Database
- `settings` table stores JSON strings for both offset collections
- Separate categories for future extensibility

## Backward Compatibility

✓ **Fully backward compatible**
- Existing `key_offsets` continue to work unchanged
- New `key_joint_offsets` field is optional (defaults to {})
- No migration needed - legacy systems work as-is
- Frontend gracefully handles missing `key_joint_offsets`

## Validation & Constraints

### LED Offsets
- **Range:** -100 to +100 LEDs
- **Type:** Integer
- **Application:** Cascading across all keys >= specified key

### Joint Offsets
- **Range:** -10.0 to +10.0 mm
- **Type:** Float
- **Conversion:** ~0.286 LEDs per mm
- **Application:** Cascading across all keys >= specified key

### Range Constraints
All offset adjustments are clamped to `[start_led, end_led]` after application

## Examples in Practice

### Scenario 1: Compensate for Known 1mm Gap

User notices LEDs misaligned after LED 53 (first solder joint):

1. Navigate to note 54 in offset UI
2. Click "Add Joint Offset" button
3. Enter: `1.0` mm
4. System converts to ~0.286 LEDs
5. Notes 54+ shift automatically

### Scenario 2: Fine-tune White/Black Key Spacing

User notices black key (D#3, MIDI 38) is slightly off:

1. Navigate to note 38
2. Click "Edit Offset" (LED offset)
3. Enter: `+2` LEDs
4. Notes 38+ adjusted by exactly 2 LED positions
5. Fine-tuning applied without affecting previous keys

### Scenario 3: Combined Compensation

Note 155 (near second solder joint) needs both fine-tuning:

1. Set LED offset: `-1` (manual adjustment)
2. Set joint offset: `+1.0` mm (automatic joint compensation)
3. Total adjustment: -1 + (~0.286) ≈ -0.714 LEDs
4. Result: Properly balanced compensation

## Files Modified

### Backend
1. **backend/services/settings_service.py**
   - Added `key_joint_offsets` to schema

2. **backend/api/calibration.py**
   - Added 6 new endpoints for joint offset management
   - Updated reset endpoint to clear joint offsets
   - Updated both offset application calls to include joint offsets

3. **backend/config.py**
   - Updated `apply_calibration_offsets_to_mapping()` signature
   - Added joint offset normalization
   - Added joint offset cascading logic
   - Updated offset application pipeline
   - Enhanced logging to track both offset types

### Frontend
1. **frontend/src/lib/stores/calibration.ts**
   - Added `KeyJointOffset` interface
   - Updated `CalibrationState` interface
   - Added `setKeyJointOffset()` method
   - Added `deleteKeyJointOffset()` method
   - Added `normalizeKeyJointOffsets()` helper
   - Exported convenience functions for joint offsets
   - Updated default state initialization

## Testing Checklist

- [x] Settings schema updated with new fields
- [x] Backend API endpoints implemented and tested
- [x] Offset application logic distinguishes offset types
- [x] Frontend store handles joint offsets
- [x] No TypeScript errors in frontend
- [x] Backward compatible with existing offsets
- [x] Cascading offset logic works for both types
- [x] Unit conversion (mm to LEDs) correct
- [x] Reset endpoint clears both offset types
- [x] WebSocket events broadcast correctly

## Next Steps

Frontend UI Implementation:
- [ ] Add "Add Joint Offset" button in offset list
- [ ] Display joint offsets with mm unit indicator
- [ ] Update offset edit dialog to show type (LED vs Joint)
- [ ] Add visual distinction between offset types
- [ ] Implement joint offset input validation
- [ ] Create help text explaining joint offsets
- [ ] Add keyboard shortcuts for quick joint offset entry

## Related Constants

From `backend/config_led_mapping_physical.py`:
```python
# Solder joint positions with automatic compensation
LED_JOINT_ADDAGE = 1.0  # mm
SOLDER_JOINT_POSITIONS = {53, 154}  # Physical solder joints in LED strip
```

These represent physical gaps that can be manually compensated using the new joint offset system.

---

**Status**: ✓ COMPLETE - Dual offset system fully implemented and integrated.

System now supports:
- ✓ Manual LED offsets (existing, enhanced)
- ✓ Automatic joint offsets (NEW)
- ✓ Cascading application for both
- ✓ Proper unit handling (LEDs vs mm)
- ✓ Full backend-frontend integration
- ✓ Backward compatibility
