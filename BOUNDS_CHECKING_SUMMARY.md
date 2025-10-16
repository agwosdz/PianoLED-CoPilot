# LED Index Bounds Checking - Visual Summary

## The Issue
```
255 LEDs available (indices 0-254)
Global offset: +4

Last key before offset:  LED 251
Last key after offset:   LED 251 + 4 = 255  ❌ OUT OF BOUNDS!
                         Should be: 254 ✅
```

## The Solution
```
┌─────────────────────────────────────────────────────┐
│ Apply Offset:   adjusted_idx = base_idx + offset   │
│ Check Bounds:   if adjusted_idx > max → clamp it   │
│ Result:         clamped_idx = min(adjusted, 254)   │
└─────────────────────────────────────────────────────┘

Example: LED 251 + 4 offset
  1. adjusted = 251 + 4 = 255
  2. Check: 255 > 254? YES
  3. Clamp: min(255, 254) = 254 ✅
```

## Implementation Locations

### 1. Backend Mapping Function
**File:** `backend/config.py` (line 718)
```python
def apply_calibration_offsets_to_mapping(mapping, global_offset=0, 
                                         key_offsets=None, led_count=None):
    # ... For each LED index:
    adjusted_idx = idx + global_offset
    # Clamp to valid range
    if max_led_idx is not None:
        adjusted_idx = max(0, min(adjusted_idx, max_led_idx))
```

### 2. Calibration API Endpoint
**File:** `backend/api/calibration.py` (line 539)
```python
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=auto_mapping,
    global_offset=global_offset,
    key_offsets=key_offsets,
    led_count=led_count  # ← Enables bounds checking
)
```

### 3. Frontend Visualization
**File:** `frontend/src/lib/components/CalibrationSection3.svelte`
- Calls `getKeyLedMapping()` from backend
- Displays clamped LED indices from backend response
- Piano visualization shows accurate, bounded values

## Bounds Checking Rules

| Scenario | Input | Output | Status |
|----------|-------|--------|--------|
| Normal case | LED 100 + 4 | LED 104 | ✅ Within [0-254] |
| Edge case | LED 251 + 4 | LED 254 | ✅ Clamped to max |
| Multiple LEDs | [251-254] + 4 | [254, 254, 254, 254] | ✅ All clamped |
| No bounds param | LED 255 + 4 | LED 259 | ⚠️ No clamping (backward compat) |

## Key Features
✅ LED indices always valid: [0, led_count-1]
✅ Backward compatible: `led_count=None` skips bounds checking
✅ Hardware safe: Prevents out-of-bounds access
✅ Graceful degradation: Over-offset keys map to last LED

## Testing
Run: `python test_bounds_checking.py`
- Verifies clamping with 255 LEDs and +4 offset
- Tests edge cases with multiple LEDs per key
- Confirms backward compatibility without bounds param
