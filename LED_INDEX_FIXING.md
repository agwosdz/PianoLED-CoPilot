# LED Index Fixing - Phase 1

## Problem Identified

The LED placement calculation was using **absolute physical LED indices** to calculate spacing, which is incorrect. The issue:

1. **Before:** LEDs were indexed as their actual strip position (e.g., LED 4-249 for 246 LEDs)
2. **Formula used:** `led_center = strip_start + (led_idx * spacing) + offset`
3. **Problem:** This creates incorrect spacing because LED 4 would be at `4 * 5mm = 20mm`, not at the first position

## Correct Approach

LEDs should use **relative indices** (0 to range_size-1) for the spacing formula:

1. **Now:** LEDs in usable range (start_led to end_led) are indexed 0 to range_size-1
2. **Formula now:** `led_center = strip_start + (relative_idx * spacing) + offset`
3. **Result:** LED 0 is at `0 * 5mm = 0mm`, LED 1 is at `1 * 5mm = 5mm`, etc.

## Additional Fix

The `led_strip_offset` was hardcoded to `1.75mm`, but it should default to:
```
led_strip_offset = led_physical_width / 2
```

This ensures the offset is always at the center of the LED, which is the proper physical reference point.

## Changes Made

### `LEDPlacementCalculator.__init__()`

**Before:**
```python
led_strip_offset: float = 1.75,  # mm (half width, offset from start)
self.led_strip_offset = led_strip_offset
```

**After:**
```python
led_strip_offset: Optional[float] = None,  # mm (defaults to led_physical_width / 2)
self.led_strip_offset = led_strip_offset if led_strip_offset is not None else (led_physical_width / 2)
```

### `LEDPlacementCalculator.calculate_led_placements()`

**Before:**
```python
def calculate_led_placements(
    self,
    led_count: int,
    strip_start_mm: float = 0.0,
) -> Dict[int, LEDPlacement]:
    placements = {}
    for led_idx in range(led_count):  # WRONG: absolute indices
        led_center = strip_start_mm + (led_idx * self.led_spacing_mm) + self.led_strip_offset
        # ... creates placement at led_idx key
```

**After:**
```python
def calculate_led_placements(
    self,
    led_count: int,
    strip_start_mm: float = 0.0,
    start_led: int = 0,
    end_led: Optional[int] = None,
) -> Dict[int, LEDPlacement]:
    if end_led is None:
        end_led = led_count - 1
    
    placements = {}
    for relative_idx in range(start_led, end_led + 1):  # CORRECT: relative indices
        led_center = strip_start_mm + (relative_idx * self.led_spacing_mm) + self.led_strip_offset
        placements[relative_idx] = LEDPlacement(
            led_index=relative_idx,  # key uses relative index
            ...
        )
```

### `PhysicalMappingAnalyzer.analyze_mapping()`

Now passes the correct parameters:
```python
led_placements = self.led_placement.calculate_led_placements(
    led_count=led_count,
    strip_start_mm=0.0,
    start_led=start_led,
    end_led=end_led,
)
```

## Next Phase

Once verified working:
1. We can add the offset back to indices to get actual LED numbers: `actual_led = relative_idx + start_led`
2. This two-step process ensures clean separation of concerns
3. Easier to debug and verify correctness

## Test Approach

The physical-analysis endpoint should show:
- LED indices starting from 0 (not from 4 or start_led)
- Correct spacing based on relative position
- Proper physical placement relative to keys

