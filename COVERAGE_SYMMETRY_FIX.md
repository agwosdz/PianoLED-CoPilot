# Coverage and Symmetry Fix - Exposed Surface Calculations

## Problem

Coverage and symmetry calculations were using the full key physical range (start_mm to end_mm), which includes areas where black keys are cut into white keys. This gave inaccurate metrics for the actual visible LED coverage.

## Solution

Updated three calculation methods to use exposed ranges:

1. **calculate_overhang()** - Measures LED overhang beyond visible playing surface
2. **calculate_coverage_amount()** - Measures actual LED coverage on visible surface  
3. **calculate_symmetry_score()** - Scores LED centering relative to visible surface

## Implementation Details

### What is "Exposed Surface"?

For **white keys**:
- Full range: start_mm to end_mm (includes cuts for adjacent black keys)
- Exposed: The visible playing surface after cuts are applied
- Example: A0 (key 0) has no left cut but may have right cut
- Example: C8 (key 87) has left cut but no right cut

For **black keys**:
- Full range and exposed range are the same (no cuts)
- Positioned between white keys with 1mm gap
- Example: A#0 sits between A0 and B0

### Code Changes

**calculate_overhang():**
```python
# OLD: Used full key range
left_overhang = max(0, key_geometry.start_mm - led_start)
right_overhang = max(0, led_end - key_geometry.end_mm)

# NEW: Uses exposed surface
exposed_start = getattr(key_geometry, '_exposed_start', key_geometry.start_mm)
exposed_end = getattr(key_geometry, '_exposed_end', key_geometry.end_mm)
left_overhang = max(0, exposed_start - led_start)
right_overhang = max(0, led_end - exposed_end)
```

**calculate_coverage_amount():**
```python
# OLD: Used full key range
overlap_start = max(key_geometry.start_mm, led.start_mm)
overlap_end = min(key_geometry.end_mm, led.end_mm)

# NEW: Uses exposed surface
exposed_start = getattr(key_geometry, '_exposed_start', key_geometry.start_mm)
exposed_end = getattr(key_geometry, '_exposed_end', key_geometry.end_mm)
overlap_start = max(exposed_start, led.start_mm)
overlap_end = min(exposed_end, led.end_mm)
```

**calculate_symmetry_score():**
```python
# OLD: Compared to key center and width
deviation = abs(led_center - key_geometry.center_mm)
key_half_width = key_geometry.width_mm / 2

# NEW: Compares to exposed center and width
exposed_center = (exposed_start + exposed_end) / 2
exposed_width = exposed_end - exposed_start
deviation = abs(led_center - exposed_center)
exposed_half_width = exposed_width / 2
```

## Key Points

✅ **Handles special cases:**
- A0 (key 0): No left cut, so full left edge is visible
- C8 (key 87): No right cut, so full right edge is visible
- Black keys: No cuts, so full surface is visible

✅ **Uses existing stored values:**
- `_exposed_start`, `_exposed_end`, `_exposed_center` are already calculated
- Falls back to full range if exposed values not present

✅ **Backward compatible:**
- Uses getattr() with fallbacks to ensure old geometries still work
- Doesn't change the data structure, only calculation logic

## Testing Results

Sample key metrics after fix:
- **A0** (no left cut): Coverage=9.9mm, Symmetry=0.678, L/R overhang: 6.8/2.2mm
- **A#0** (black key): Coverage=0mm, Symmetry=0.000, L/R overhang: 39.0/0.0mm
- **C1** (white): Coverage=8.0mm, Symmetry=0.875, L/R overhang: 9.0/7.5mm
- **C8** (no right cut): Coverage=0mm, Symmetry=0.000, L/R overhang: 39.5/0.0mm

Note: Low coverage on black keys and end keys suggests LED assignment algorithm may need improvement, but the metrics are now accurate for what is visible.

## Next Steps

1. Verify LED assignment algorithm distributes appropriately to all keys
2. Analyze quality metrics with correct coverage calculations
3. Optimize LED placement to improve symmetry and reduce overhang
