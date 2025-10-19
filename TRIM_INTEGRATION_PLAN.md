# LED Trim Integration into Mapping Logic

## Overview
Currently, per-key LED trims are calculated and stored but not applied to the final LED mapping. The trims need to be integrated into the mapping pipeline to produce the correct LED allocation for each key with its custom trims applied.

## Current Flow

```
1. Physics/Piano-based allocation → base_mapping (keys have full assigned LEDs)
   - key 21 → [0, 1, 2, 3]

2. Calibration offsets applied → final_mapping (offsets shift all LEDs)
   - key 21 → [2, 3, 4, 5] (with +2 offset)

3. Frontend displays with trims (NO BACKEND SUPPORT YET)
   - key 21 → [2, 3, 4, 5] base LEDs
   - Frontend calculates: [3, 4] (with left_trim=1, right_trim=0)
```

## Required Changes

### 1. Backend: Store & Return Trim Data

**Location:** `backend/api/calibration.py`
- **Status:** ✅ DONE - `key_led_trims` added to `/api/calibration/status` endpoint

### 2. Backend: Apply Trims in Mapping Generation

**Location:** `backend/config.py` - `apply_calibration_offsets_to_mapping()`

**Current Logic:**
- Takes base mapping with LED ranges per key
- Applies cascading offsets (key_offsets)
- Applies weld compensation
- Returns final mapping with offset LEDs

**New Logic (APPEND after offset application):**
```python
# For each key with trims in key_led_trims:
#   1. Get adjusted indices (already offset)
#   2. Apply trims: slice(left_trim, len - right_trim)
#   3. Return trimmed indices

# For keys without trims: keep original adjusted indices
```

**Algorithm:**
```python
# After offset application for each key:
if key_led_trims and midi_note in key_led_trims:
    trim = key_led_trims[midi_note]
    left_trim = trim.get('left_trim', 0)
    right_trim = trim.get('right_trim', 0)
    
    if adjusted_indices and (left_trim > 0 or right_trim > 0):
        # Calculate trim boundaries
        if right_trim > 0:
            adjusted_indices = adjusted_indices[left_trim:-right_trim]
        else:
            adjusted_indices = adjusted_indices[left_trim:]
```

### 3. Modify get_key_led_mapping Endpoint

**Location:** `backend/api/calibration.py` - `get_key_led_mapping()`

**Change:**
- Pass `key_led_trims` to `apply_calibration_offsets_to_mapping()` 
- Function signature: `apply_calibration_offsets_to_mapping(mapping, start_led, end_led, key_offsets, key_led_trims, led_count, weld_offsets)`

**Current Call:**
```python
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,
    start_led=start_led,
    end_led=end_led,
    key_offsets=converted_offsets,
    led_count=led_count
)
```

**New Call:**
```python
key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})

# Convert trim keys from MIDI notes to key indices (same as offsets)
converted_trims = {}
if key_led_trims:
    for midi_note_str, trim_value in key_led_trims.items():
        try:
            midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
            key_index = midi_note - 21
            if 0 <= key_index < 88:
                converted_trims[key_index] = trim_value
        except (ValueError, TypeError):
            pass

final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,
    start_led=start_led,
    end_led=end_led,
    key_offsets=converted_offsets,
    key_led_trims=converted_trims,
    led_count=led_count
)
```

## Implementation Details

### Where Trim Logic Should Go

**Option A (RECOMMENDED): Apply After All Offsets**
- Location: End of `apply_calibration_offsets_to_mapping()` function
- When: After weld compensation but before clamping to start/end_led
- Benefit: Trims work on already-adjusted indices, consistent with user's view
- Risk: Trims might clip important LEDs that offset moved in

**Option B: Apply Before Offsets**
- Location: Inside `apply_calibration_offsets_to_mapping()` loop before offset calculation
- When: Before applying cascading offset
- Benefit: Trims operate on "pure" base LEDs
- Risk: Offset then trims again? Or trims then offset? Confusing.

**Option C: Apply Entirely Separate**
- Location: New function or endpoint `/api/calibration/key-led-mapping-with-trims`
- When: After final mapping is computed
- Benefit: Modular, testable separately
- Risk: Inconsistent with how backend handles it vs frontend

### Handle Edge Cases

1. **Empty trim (0, 0):** User selected all LEDs - store `{left_trim: 0, right_trim: 0}`
   - Current: Only saves if `left_trim > 0 or right_trim > 0`
   - Need: Always save trim record, even if both are 0

2. **Offset + Trim interaction:**
   - Offset shifts all LEDs: [0,1,2,3] + offset(+2) = [2,3,4,5]
   - Trim then clips: [2,3,4,5] with L1/R1 = [3,4]
   - Order matters! Should be: offset first, then trim

3. **Trim boundaries after offset:**
   - If offset pushes LED below start_led, trim should work with clamped values
   - Example: [0,1,2] + offset(-1) = [-1, 0, 1] → clamped to [0, 1]
   - Then trim L0/R1 = [0]

4. **Adjacent key borrowing:**
   - When key's trims result in fewer LEDs, could borrow from adjacent keys
   - E.g., key 21 trims to [50], key 20 has [48,49,50,51] → keep borrowed LED?
   - For now: Keep separate (no auto-borrowing), user manually adjusts if needed

## Testing Strategy

### Unit Tests
- Test trim calculation with various offset scenarios
- Test edge cases: 0/0 trims, negative offsets, boundary conditions
- Test trim bounds don't exceed available LED range

### Integration Tests
- Save adjustment with trim → verify `/key-led-mapping` includes trim
- Load status → verify `key_led_trims` present in response ✅ (already done)
- Display adjusted indices → verify they match trimmed LEDs ✅ (frontend working)

### Manual Testing
1. Select key, choose 3 LEDs from 4 available
2. Save adjustment
3. Verify adjusted LED range displays correct 3 LEDs
4. Refresh page → verify trims persist
5. Call `/api/calibration/key-led-mapping` → verify response includes trimmed LEDs

## Files to Modify

1. **backend/config.py**
   - `apply_calibration_offsets_to_mapping()` - add `key_led_trims` parameter and logic
   - Line ~793: Function signature
   - Line ~860-930: Per-key adjustment loop

2. **backend/api/calibration.py**
   - `get_key_led_mapping()` - fetch and pass trims
   - Line ~764-910: Get trims from settings, convert MIDI→index, pass to function

3. **backend/api/calibration.py** (optional fix)
   - `set_key_offset()` - always save trims, even if both are 0
   - Line ~422-521: Only saves if `left_trim > 0 or right_trim > 0`
   - Change to: Always save trim record

## Success Criteria

✅ Frontend displays adjusted LED range based on trims
✅ Backend returns trimmed LED allocations in `/key-led-mapping`
✅ Trims persist across page reloads
✅ Trim + offset interaction works correctly
✅ Edge cases handled gracefully

## Next Steps

1. Modify `apply_calibration_offsets_to_mapping()` signature to accept `key_led_trims`
2. Add trim application logic after offset calculation
3. Update `get_key_led_mapping()` to fetch and pass `key_led_trims`
4. Fix `set_key_offset()` to save even 0/0 trims
5. Test with various scenarios
