# LED Trim Implementation - New Approach

## Overview

We've implemented a new, cleaner approach to handle LED customization by introducing **`trim_left`** and **`trim_right`** fields that control how many LEDs to exclude from the left and right sides of the LED strip. This provides a simpler, more intuitive way to adjust LED allocation without the complexity of individual offset systems.

## Architecture

### Design Principles

1. **Simplicity**: Two fields (`trim_left` and `trim_right`) are easier to understand and manage than complex offset logic
2. **Per-Key Independence**: Trim values work alongside existing per-key offset logic
3. **Scalability**: Trim values adjust the available LED pool for all keys uniformly

## Implementation Details

### Backend Changes

#### 1. Settings Schema (`backend/services/settings_service.py`)

Added two new fields to the `calibration` section:

```python
'trim_left': {'type': 'number', 'default': 0, 'min': 0, 'max': 100, 'description': 'Number of LEDs to trim from the left side of the strip'},
'trim_right': {'type': 'number', 'default': 0, 'min': 0, 'max': 100, 'description': 'Number of LEDs to trim from the right side of the strip'},
```

**Type**: Integer (0-100 range)
**Default**: 0 for both
**Scope**: Global calibration settings

#### 2. API Endpoints (`backend/api/calibration.py`)

##### GET `/api/calibration/status`
Updated to include `trim_left` and `trim_right` fields in response:
```json
{
  "start_led": 0,
  "end_led": 245,
  "trim_left": 0,
  "trim_right": 0,
  "key_offsets": {...}
}
```

##### PUT `/api/calibration/trim-left`
Sets left side trim value
- **Request**: `{ "trim_left": <number> }`
- **Validation**: 0-100 range
- **Response**: Returns updated value and broadcasts via WebSocket

##### PUT `/api/calibration/trim-right`
Sets right side trim value
- **Request**: `{ "trim_right": <number> }`
- **Validation**: 0-100 range
- **Response**: Returns updated value and broadcasts via WebSocket

### Frontend Changes

#### 1. Calibration Store (`frontend/src/lib/stores/calibration.ts`)

**Type Definition**:
```typescript
export interface CalibrationState {
  enabled: boolean;
  calibration_enabled: boolean;
  start_led: number;
  end_led: number;
  trim_left: number;      // NEW
  trim_right: number;     // NEW
  key_offsets: Record<number, number>;
  calibration_mode: 'none' | 'assisted' | 'manual';
  last_calibration: string | null;
}
```

**Default State**:
```typescript
const defaultCalibrationState: CalibrationState = {
  enabled: false,
  calibration_enabled: false,
  start_led: 0,
  end_led: 245,
  trim_left: 0,           // NEW
  trim_right: 0,          // NEW
  key_offsets: {},
  calibration_mode: 'none',
  last_calibration: null
};
```

**New Methods**:
```typescript
async setTrimLeft(trimLeft: number): Promise<void>
async setTrimRight(trimRight: number): Promise<void>
```

**Exported Functions**:
```typescript
export const setTrimLeft = (trimLeft: number): Promise<void>
export const setTrimRight = (trimRight: number): Promise<void>
```

#### 2. Data Flow

1. **Load**: Server provides `trim_left` and `trim_right` via `/api/calibration/status`
2. **Store**: Values stored in `calibrationState` reactive store
3. **UI**: Components subscribe to `$calibrationState.trim_left` and `$calibrationState.trim_right`
4. **Update**: User changes trigger `setTrimLeft()` or `setTrimRight()` calls
5. **Persist**: Changes saved to backend and broadcast via WebSocket

## Integration Points

### LED Mapping Logic (Next Phase)

The trim values should be used when calculating the effective LED range:

```typescript
// Effective range after trimming
effectiveStart = start_led + trim_left
effectiveEnd = end_led - trim_right
effectiveLEDs = Array.from({ length: effectiveEnd - effectiveStart + 1 }, (_, i) => effectiveStart + i)
```

### Per-Key Adjustments

Trim values work independently from per-key offsets:
- **Trim**: Affects the overall LED pool available to all keys
- **Key Offsets**: Adjust individual key positions within the trimmed range

## Files Modified

| File | Changes |
|------|---------|
| `backend/services/settings_service.py` | Added `trim_left` and `trim_right` to calibration schema |
| `backend/api/calibration.py` | Added `/trim-left` and `/trim-right` endpoints |
| `frontend/src/lib/stores/calibration.ts` | Added trim fields to types, state, and exported functions |

## Next Steps

### Phase 2: Frontend UI

Add trim controls to CalibrationSection2 or CalibrationSection3:
- Number inputs for `trim_left` and `trim_right` (0-100 range)
- Visual preview showing trimmed LED range
- Real-time updates as values change

### Phase 3: Mapping Integration

Update LED mapping functions to apply trim values:
- Modify `getKeyLedMappingWithRange()` to respect trim values
- Update all functions that calculate LED allocations
- Test across all 88 piano keys

### Phase 4: Testing & Validation

- Test trim values with various configurations
- Ensure key offsets work correctly with trim values
- Verify WebSocket broadcasts work
- Test edge cases (trim_left + trim_right > total LEDs)

## Benefits

✅ **Cleaner Architecture**: Simple two-field system vs complex offset logic
✅ **Intuitive Control**: Users understand "trim left/right" immediately
✅ **Flexible**: Works with existing per-key offset system
✅ **Database-Backed**: Persisted in settings, survives restarts
✅ **Broadcast-Ready**: WebSocket events for real-time UI updates

## Testing Checklist

- [ ] Settings saved to database correctly
- [ ] API endpoints return correct values
- [ ] WebSocket broadcasts work
- [ ] Frontend store updates correctly
- [ ] Trim values affect LED mapping calculations
- [ ] Per-key offsets still work independently
- [ ] Edge cases handled (max values, negative inputs)
