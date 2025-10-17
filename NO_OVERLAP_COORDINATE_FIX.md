# No-Overlap LED Coordinate System Fix

## Problem

The no-overlap LED distribution mode had a coordinate system bug that caused:
1. **LED 4 was being skipped** - Key 0 started at LED 5 instead of LED 4
2. **Only 245/246 LEDs were used** - LED 4 wasn't assigned to any key
3. **Incorrect LED ranges** - LEDs fell outside key ranges due to mathematical rounding issues

## Root Cause

The original no-overlap algorithm was checking LED **midpoint positions** against key ranges, but was using the **wrong coordinate conversion**:

```python
# WRONG - dividing by scale_factor
key_start_led_pos = key_start_mm / scale_factor  # ← Incorrect direction
led_midpoint_pos = led_relative_offset * led_spacing_mm / scale_factor  # ← Mismatch
```

This caused:
- Key 0 range: [4.69, 19.73] (in LED coordinate space)
- LED 4 position: 0mm (physical position)
- Result: 0mm is NOT in [4.69, 19.73) ❌ LED 4 skipped!

## Solution

### Part 1: Fix Coordinate Conversion
Changed from **dividing** to **multiplying** by scale_factor:

```python
# CORRECT - multiply by scale_factor
key_start_led_pos = key_start_mm * scale_factor  # ← Correct direction
```

This aligns the piano coordinate system with the LED space:
- Piano: 0-1273mm (full 88-key width)
- LED coverage: 246 LEDs × 5mm = 1230mm physical
- scale_factor: 1230 / 1273 = 0.9623
- Piano position maps to LED space: `led_pos = piano_pos * scale_factor`

### Part 2: Use LED Index Calculation Instead of Midpoint Checks
Replaced the midpoint-checking loop with **LED index calculation** (same approach as with-overlap mode):

```python
# BEFORE: Check if LED midpoint falls in key range (complex, error-prone)
for led_offset in range(...):
    led_midpoint_pos = led_relative_offset * led_spacing_mm / scale_factor
    if key_start_led_pos <= led_midpoint_pos < key_end_led_pos:
        led_to_key[led_idx] = key_idx

# AFTER: Calculate LED indices directly (simpler, correct)
first_led_offset = int(key_start_led_pos / led_spacing_mm)
last_led_offset = int(key_end_led_pos / led_spacing_mm)
for led_offset in range(first_led_offset, last_led_offset + 1):
    led_idx = start_led + led_offset
    if led_idx not in led_to_key:  # Only assign if not already assigned
        led_to_key[led_idx] = key_idx
```

**Why this works:**
- Uses floor division (`int()`) to find first and last LED indices for each key
- Assigns LEDs based on which key's range they fall into
- Ensures no LED is assigned twice (checks `if led_idx not in led_to_key`)
- Guarantees 100% coverage because we iterate through all LED offsets sequentially

## Mathematical Verification

**Key 0 calculation:**
- Piano coordinates: 4.52mm - 18.98mm
- LED coordinate space: 4.35mm - 18.27mm (multiply by 0.9623)
- LED indices: floor(4.35/5) = 0, floor(18.27/5) = 3
- LEDs assigned: 0+4=LED 4 through 3+4=LED 7
- Result: **Key 0 → [4, 5, 6, 7]** ✅

**LED Coverage:**
- Total LEDs: 246 (from LED 4 to 249)
- Total assigned: 246 ✅
- Coverage: 100% ✅
- Overlap: 0% ✅ (true no-overlap mode)

## Test Results

### Before Fix
```
Key 0: [5, 6, 7]      ← Missing LED 4
Key 1: [8, 9, 10]
Coverage: 245/246 LEDs
Missing: [4]
```

### After Fix
```
Key 0: [4, 5, 6, 7]   ← Includes LED 4
Key 1: [8, 9, 10]
Key 87: [248, 249]
Coverage: 246/246 LEDs  ← 100% coverage
Missing: None
```

## Files Modified

- `backend/config_led_mapping_advanced.py` - Fixed no-overlap LED allocation algorithm

## Impact

✅ **No-overlap mode now works correctly:**
- All 246 LEDs are assigned (100% coverage)
- Key 0 starts at LED 4 (the global calibration offset)
- Zero LED overlap between keys
- Matches user's expectation: "should start with LED 4"

✅ **Maintains backward compatibility:**
- With-overlap mode unchanged
- All existing API endpoints work the same
- Distribution mode selection still works

## Related Concepts

- **scale_factor**: Ratio of LED coverage to piano width - used to map between coordinate systems
- **LED index**: Physical LED number (0-254 on 255-LED strip)
- **LED offset**: Relative position from start_led (0-245 for calibration range 4-249)
- **Piano coordinate**: Position on piano keyboard (0-1273mm)
- **LED coordinate**: Position in mapped LED space (scaled version of piano coordinates)
