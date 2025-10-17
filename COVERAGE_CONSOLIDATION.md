# LED Coverage Analysis Consolidation

## Changes Summary

**Consolidated three separate functions into one comprehensive function using threshold logic.**

### Removed Functions
1. `find_overlapping_leds()` - Found LEDs by overlap amount
2. `calculate_overhang()` - Calculated left/right overhang separately
3. `calculate_coverage_amount()` - Calculated coverage separately

### New Function: `analyze_led_coverage()`

**Single function that does everything:**

```python
def analyze_led_coverage(
    self,
    key_geometry: KeyGeometry,
    led_indices: List[int],
    led_placements: Dict[int, LEDPlacement],
    overhang_threshold_mm: float = 1.5,
) -> Dict[str, Any]
```

**Logic:**
Uses simplified threshold-based filtering:
- Include LED if: `led.start_mm <= exposed_start + threshold_mm` **AND** `led.end_mm >= exposed_end - threshold_mm`
- This ensures only LEDs that meet overhang requirements on BOTH sides are included
- No LED can extend beyond the threshold on either side

**Returns Dictionary with:**
- `filtered_leds`: List of LED indices meeting threshold criteria
- `coverage_amount_mm`: Total coverage on exposed surface
- `overhang_left_mm`: LED extension beyond left exposed edge
- `overhang_right_mm`: LED extension beyond right exposed edge

### Updated `analyze_mapping()` Method

**Before:**
```python
# Three separate calls
left_overhang, right_overhang = self.led_placement.calculate_overhang(...)
coverage_amount = self.led_placement.calculate_coverage_amount(...)
# Plus separate filtering elsewhere
```

**After:**
```python
# One comprehensive call
coverage_result = self.led_placement.analyze_led_coverage(
    key_geom, rel_led_indices, led_placements, 
    overhang_threshold_mm=self.overhang_threshold_mm
)

filtered_led_indices = coverage_result["filtered_leds"]
coverage_amount = coverage_result["coverage_amount_mm"]
left_overhang = coverage_result["overhang_left_mm"]
right_overhang = coverage_result["overhang_right_mm"]
```

### Output Impact

**LED indices are now filtered:**
- Only LEDs meeting the threshold criteria appear in output
- Prevents poor-quality LED assignments from being included
- Makes mapping quality metrics more accurate

### Benefits

1. **Simplified Logic** - One function, one threshold check
2. **Clearer Intent** - Single unified API
3. **Performance** - Single pass through LED placements
4. **Consistency** - Same filtering logic for all metrics
5. **Maintainability** - Less code to maintain and debug

## Threshold Behavior

Example with 1.5mm threshold:
- Key exposed range: 20.0-40.0mm
- LED must satisfy:
  - `led.start <= 20.0 + 1.5 = 21.5mm` (not too far left)
  - `led.end >= 40.0 - 1.5 = 38.5mm` (not too far right)
- This ensures meaningful coverage on both ends of the key

## Files Modified

- `backend/config_led_mapping_physical.py`
  - Removed 3 functions (lines 346-443 in old version)
  - Added 1 comprehensive function (lines 346-422 in new version)
  - Updated `analyze_mapping()` to use new function
  - Updated LED detail collection to use filtered indices
