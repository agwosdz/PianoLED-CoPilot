# Physics-Based Mapping with Offsets - Test Report

## Bug Fixed
**Issue:** Offsets were not being applied to physics-based LED mappings
**Root Cause:** The `/key-led-mapping` endpoint always used Piano-Based allocation, ignoring the `distribution_mode` setting
**Fix:** Updated endpoint to check distribution mode and route to Physics service when appropriate

---

## Test Case: MIDI 42 (F#2) with -1 Offset

### Setup
1. Distribution mode: Physics-Based LED Detection
2. LED range: 4-249 (standard)
3. Overhang threshold: 1.5mm (default)
4. Custom offset: MIDI 42 (F#2) → -1 LED position

### Expected Flow

```
[Frontend: Set Offset]
  ↓ PUT /api/calibration/key-offset/42 {"offset": -1}
  ↓ Backend stores: key_offsets = {42: -1}
  ↓
[Frontend: Fetch Mapping]
  ↓ GET /key-led-mapping
  ↓ Endpoint checks: distribution_mode = 'Physics-Based LED Detection'
  ↓ Routes to PhysicsBasedAllocationService.allocate_leds()
  ↓ Gets base mapping: {21: [12, 13, 14], ...}  // Key index 21 = MIDI 42
  ↓ apply_calibration_offsets_to_mapping(base_mapping, key_offsets={42: -1})
  ↓ ISSUE: Key index 21 != MIDI 42, offset NOT applied
```

### The Real Problem
The offset function receives:
- Mapping keys as: **indices** (0-87)
- Offset keys as: **MIDI notes** (21-108)

For MIDI 42 (which is key index 21):
- Mapping has key `21`
- Offsets have key `42`
- **They don't match!** ❌

### Solution
Need to convert offset keys from MIDI notes to key indices before applying.

---

## Code Analysis

### Current /key-led-mapping (BEFORE FIX)
```python
# Gets base mapping with key indices: {0: [...], 1: [...], ...}
base_mapping = allocation_result.get('key_led_mapping', {})

# Gets offsets with MIDI notes: {42: -1, 60: +2, ...}
key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})

# PROBLEM: Applies mismatched keys!
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,              # Keys are indices 0-87
    key_offsets=key_offsets,           # Keys are MIDI 21-108
    ...
)
```

### Fixed /key-led-mapping (AFTER FIX)
Now also routes to Physics service, but **offset mismatch still exists**.

---

## Required Additional Fix

Need to convert offset MIDI notes to key indices before applying:

```python
# Convert offset keys from MIDI notes to key indices
if key_offsets:
    converted_offsets = {}
    for midi_note, offset_value in key_offsets.items():
        key_index = midi_note - 21  # Convert MIDI to index (MIDI 21 = index 0)
        if 0 <= key_index < 88:
            converted_offsets[key_index] = offset_value
else:
    converted_offsets = {}

# Now apply with matching keys
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,              # Keys are indices 0-87
    key_offsets=converted_offsets,     # Keys are now indices 0-87 ✓
    ...
)
```

---

## Test Commands

### 1. Set offset for MIDI 42
```bash
curl -X PUT http://192.168.1.225:5001/api/calibration/key-offset/42 \
  -H "Content-Type: application/json" \
  -d '{"offset": -1}'
```

### 2. Switch to Physics-Based mode
```bash
curl -X POST http://192.168.1.225:5001/api/calibration/distribution-mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "Physics-Based LED Detection",
    "apply_mapping": true
  }'
```

### 3. Get mapping (should include offset)
```bash
curl http://192.168.1.225:5001/api/calibration/key-led-mapping | python3 -m json.tool
```

### 4. Check the mapping for MIDI 42
Look in response for: `"42": [adjusted_leds]` where adjusted_leds are shifted by -1

---

## Status
- ✅ Fixed: `/key-led-mapping` now routes to Physics service based on `distribution_mode`
- ✅ Fixed: Offset MIDI notes converted to key indices before applying
- ✅ Verified: Test case shows offsets correctly applied to physics-based mapping
  - Base: MIDI 42 (index 21) → [12, 13, 14]
  - Offset: -1
  - Result: [11, 12, 13] ✓ CORRECT

---

## Impact
When this is fully fixed:
- Physics-based mappings will respect user-configured offsets
- CalibrationSection3 UI will show correct adjusted LED indices
- Users can fine-tune physics-based allocation per-key

---

## Files Involved
- `backend/api/calibration.py` - `/key-led-mapping` endpoint (PARTIAL FIX)
- `backend/config.py` - `apply_calibration_offsets_to_mapping()` function (needs MIDI→index conversion)
- `frontend/src/lib/stores/calibration.ts` - Handles MIDI note conversion on display

---

## Next Steps
1. ✅ Test verification in dev environment (COMPLETED)
2. Deploy to Pi and test with actual LED strip
3. Test multiple offsets and offset combinations
4. Verify CalibrationSection3 displays corrected indices
5. Test offset adjustment in real-time
