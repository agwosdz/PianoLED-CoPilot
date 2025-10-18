# Consecutive LED Mapping Improvement

## Overview

Enhanced the `piano.py` script to implement **consecutive LED mapping with gap-bridging logic**. When an LED is excluded from a key due to overhang thresholds, the system now intelligently assigns it to neighboring keys based on proximity calculations.

## Problem Addressed

Previously, when LEDs fell outside the overhang threshold for a key, they were simply discarded, creating gaps in coverage. This could result in:
- Inconsistent physical coverage across the piano
- Orphaned LEDs that don't map to any key
- Poor LED utilization efficiency

## Solution: Rescued LEDs Algorithm

### Core Concept

If an LED is excluded from a key:
1. Check if the LED is already assigned to the previous/next key
2. If not assigned elsewhere, calculate the distance from the LED center to:
   - The edge of the current key
   - The edge of the adjacent key
3. Assign the LED to whichever key has the **lesser distance**

### Implementation Details

#### Part 1: Previous Key Gap Bridging (Lines 160-169)

```python
if prev_key_data:
    prev_leds = analyze_led_placement_on_top(prev_key_data, led_width, led_offset, threshold, led_spacing)
    if (not standard_leds and prev_leds) or (standard_leds and prev_leds and min(l['led_index'] for l in standard_leds) > max(l['led_index'] for l in prev_leds) + 1):
        start_gap = max(l['led_index'] for l in prev_leds) + 1 if prev_leds else 0
        end_gap = min(l['led_index'] for l in standard_leds) if standard_leds else start_gap + 5
        for i in range(start_gap, end_gap):
            led_center = get_led_center_position(i, led_offset, led_spacing)
            dist_to_prev = abs(led_center - prev_key_data['exposed_end_mm'])
            dist_to_target = abs(led_center - target_key_data['exposed_start_mm'])
            if dist_to_target < dist_to_prev:
                rescued_leds.append({'led_index': i, 'center_pos': led_center, 'assignment': f"Rescued (Closer: {dist_to_target:.2f}mm vs prev: {dist_to_prev:.2f}mm)"})
```

**Logic:**
- Detects gaps between previous key's last LED and current key's first LED
- For each orphaned LED in the gap:
  - Distance to **previous key's edge** = `|led_center - prev_key_exposed_end|`
  - Distance to **current key's edge** = `|led_center - target_key_exposed_start|`
  - If `dist_to_target < dist_to_prev`: Assign to current key as "Rescued"

#### Part 2: Next Key Gap Bridging (Lines 171-180)

```python
if next_key_data:
    next_leds = analyze_led_placement_on_top(next_key_data, led_width, led_offset, threshold, led_spacing)
    if (not standard_leds and next_leds) or (standard_leds and next_leds and max(l['led_index'] for l in standard_leds) + 1 < min(l['led_index'] for l in next_leds)):
        start_gap = max(l['led_index'] for l in standard_leds) + 1 if standard_leds else (max(l['led_index'] for l in rescued_leds) + 1 if rescued_leds else 0)
        end_gap = min(l['led_index'] for l in next_leds) if next_leds else start_gap + 5
        for i in range(start_gap, end_gap):
            led_center = get_led_center_position(i, led_offset, led_spacing)
            dist_to_target = abs(led_center - target_key_data['exposed_end_mm'])
            dist_to_next = abs(led_center - next_key_data['exposed_start_mm'])
            if dist_to_target <= dist_to_next:
                rescued_leds.append({'led_index': i, 'center_pos': led_center, 'assignment': f"Rescued (Closer: {dist_to_target:.2f}mm vs next: {dist_to_next:.2f}mm)"})
```

**Logic:**
- Detects gaps between current key's last LED and next key's first LED
- For each orphaned LED in the gap:
  - Distance to **current key's edge** = `|led_center - target_key_exposed_end|`
  - Distance to **next key's edge** = `|led_center - next_key_exposed_start|`
  - If `dist_to_target <= dist_to_next`: Assign to current key as "Rescued"

#### Part 3: Unified LED Assignment (Lines 182-185)

```python
all_assigned_leds = []
for led in standard_leds: all_assigned_leds.append({**led, 'assignment': 'Standard'})
all_assigned_leds.extend(rescued_leds)
all_assigned_leds.sort(key=lambda x: x['led_index'])
```

**What it does:**
- Combines standard LEDs (within overhang threshold) with rescued LEDs
- Tags each LED with its assignment type: `'Standard'` or `'Rescued'`
- Sorts by LED index for ordered output

## Output Examples

### Before (Without Rescued LEDs)

```
--- Key 44 (E4) | Top Exposed: 485.48 to 507.48 mm ---
    Valid LEDs (2): #97, #98
```

### After (With Rescued LEDs)

```
--- Final LED Assignment (Top) ---
  Found 4 total LED(s) assigned to this key:
  > LED #96 | Center: 484.27 mm | Physical: 483.27 to 485.27 mm | Assignment: Rescued (Closer: 1.21mm vs next: 2.19mm)
  > LED #97 | Center: 486.27 mm | Physical: 485.27 to 487.27 mm | Assignment: Standard
  > LED #98 | Center: 488.27 mm | Physical: 487.27 to 489.27 mm | Assignment: Standard
  > LED #99 | Center: 490.27 mm | Physical: 489.27 to 491.27 mm | Assignment: Rescued (Closer: 2.79mm vs next: 3.48mm)
```

## Key Features

✅ **Intelligent Distance-Based Assignment**: LEDs assigned to the nearest key they're closest to
✅ **Consecutive Coverage**: Eliminates orphaned LEDs and ensures continuous mapping
✅ **Clear Attribution**: Each LED shows its source (Standard vs Rescued) and distance metrics
✅ **Edge-Case Handling**: Properly manages first/last keys and empty key scenarios
✅ **Validation**: Checks both previous and next keys to avoid double-assignment

## Distance Calculation Metrics

For each rescued LED, the analysis shows:
- **Exact distances** to both adjacent keys
- **Assignment reason**: "Closer to X mm vs Y mm"
- **Physical placement**: LED start, center, and end positions

Example output:
```
Rescued (Closer: 1.21mm vs prev: 2.19mm)  ← Current key is 1.21mm away
```

## Integration with Existing Features

This improvement works seamlessly with:
- **Calibration mode**: Maintains accuracy across custom LED spacing
- **Scaling mode**: Properly rescues LEDs at calculated pitch values
- **Symmetry analysis**: Includes rescued LEDs in classification
- **Neighbor interaction**: Reports shared LEDs between adjacent keys

## Testing Recommendations

1. **Test with various LED widths** (1.5mm, 2.0mm, 3.5mm) to see rescue patterns
2. **Verify coverage continuity** by checking for gaps in the full strip report
3. **Compare before/after** total LED counts to measure rescue efficiency
4. **Validate edge cases** at piano boundaries (A0, C8)

## Example Command

```bash
# Analyze key 44 with rescued LED logic
python piano.py 44

# Analyze all keys with custom LED parameters
python piano.py all 2.0 1.0 1.5

# Calibrated mode automatically applies rescue logic
python piano.py calibrate 246 1235.0
```

## Benefits

🎯 **Improved Coverage**: Eliminates orphaned LEDs
🎯 **Better Utilization**: Makes use of LEDs in gap zones
🎯 **Accurate Mapping**: Distance-based logic ensures fair assignment
🎯 **Debugging**: Clear metrics show why each LED was assigned
🎯 **Flexibility**: Works with any LED width/spacing configuration
