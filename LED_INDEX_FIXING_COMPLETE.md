# LED Index Fixing - Complete

## Summary

Fixed LED placement calculations to use **relative indices** (0 to usable_range-1) for the spacing formula, while maintaining **absolute indices** (4 to 249) for hardware control.

## Problem

The LED placement calculation was using absolute physical LED indices, which created incorrect spacing. Example:
- LED 4 was calculated at: `4 * 5mm = 20mm` (WRONG)
- Should be: `0 * 5mm = 0mm` (relative)

## Solution

### Three Commits

**1. Use Relative LED Indices for Spacing Calculation**
- Modified `LEDPlacementCalculator.__init__()` to calculate `led_strip_offset = led_physical_width / 2` by default
- Updated `calculate_led_placements()` to accept `start_led` and `end_led` parameters
- Changed loop to use `relative_idx in range(start_led, end_led + 1)` for positioning

**2. Allow Default led_strip_offset**
- Updated `PhysicalMappingAnalyzer` to accept `Optional[float]` for `led_strip_offset`
- Modified calibration API to only pass `led_strip_offset` if explicitly provided
- Allows proper default calculation: `1.75mm = 3.5mm / 2`

**3. Convert Indices in Analysis**
- `analyze_mapping()` now converts absolute indices to relative for internal calculations
- Calculate `usable_led_count = end_led - start_led + 1` 
- Call `calculate_led_placements()` with `start_led=0` and `end_led=usable_count-1`
- Convert absolute → relative for calculations: `rel_idx = abs_idx - start_led`
- Convert relative → absolute for output: `abs_idx = rel_idx + start_led`

## Key Changes

### config_led_mapping_physical.py

**LEDPlacementCalculator:**
```python
# Before: hardcoded offset
led_strip_offset: float = 1.75

# After: calculated from LED width
led_strip_offset = led_strip_offset if led_strip_offset is not None else (led_physical_width / 2)
```

**calculate_led_placements():**
```python
# Before: absolute indices
for led_idx in range(led_count):
    led_center = strip_start_mm + (led_idx * spacing) + offset

# After: relative indices
usable_led_count = end_led - start_led + 1
for rel_idx in range(start_led, end_led + 1):
    led_center = strip_start_mm + (rel_idx * spacing) + offset
```

**analyze_mapping():**
```python
# Convert absolute → relative
rel_led_indices = [idx - start_led for idx in abs_led_indices if start_led <= idx <= end_led]

# Use for calculations
symmetry_score = calculate_symmetry_score(key_geom, rel_led_indices, led_placements)

# Output absolute for hardware
"led_indices": abs_led_indices,  # Still absolute in output
```

### api/calibration.py

```python
# Only use explicit or stored value, let default work
led_strip_offset = None
if 'led_strip_offset' in data:
    led_strip_offset = float(data['led_strip_offset'])
elif settings_service.get_setting('calibration', 'led_strip_offset'):
    led_strip_offset = float(...)
# If None, defaults to led_physical_width/2 in LEDPlacementCalculator
```

## Result

✅ LED placements calculated with correct relative spacing
✅ Absolute indices preserved for hardware reference (4, 5, 6, ..., 249)
✅ Default offset automatically calculated from LED physical width
✅ Backward compatible with stored settings values
✅ Internal calculations use clean 0-based relative indices
✅ Output maintains absolute indices for clarity

## Testing

```bash
# Endpoint returns correct geometry with proper spacing
curl http://192.168.1.225:5001/api/calibration/physical-analysis

# Key 0: LED indices [4, 5, 6, 7, 8] (absolute)
# These LEDs now positioned at correct mm relative to first usable LED
```

## Next Steps

Ready to:
1. Add actual offset back to physical positions for real placement
2. Verify LED-to-key alignment quality improves with correct spacing
3. Calibrate overhang and coverage metrics
