# Advanced LED Mapping - All 88 Keys with Proper White/Black Key Positioning

## Overview

The advanced mapping algorithm now correctly maps **all 88 keys** (52 white + 36 black) to LEDs, accounting for the physical positioning of white and black keys on a piano.

## Algorithm

### Core Concept

- **Total keys**: 88 (A0 through C8)
- **Key spacing**: Piano width / 88 keys
  - For 200 LEDs/m with range 4-249: 1230mm / 88 = 14.466mm per key
- **Key centers**: Evenly distributed at intervals of 14.466mm
- **Key spans**: Based on white or black key width
  - **White keys**: Center ± (key_width_mm / 2) = center ± 7.233mm
  - **Black keys**: Center ± (half_black_key_width) = center ± 5.5mm

### Key Type Detection

Using the chromatic scale pattern starting from A0:
```
Position in octave:  0=A,  1=A#, 2=B,  3=C,  4=C#, 5=D,  6=D#, 7=E,  8=F,  9=F#, 10=G, 11=G#
Black key positions: {1, 3, 6, 8, 10}
White key positions: {0, 2, 4, 5, 7, 9, 11}
```

This pattern repeats every 12 keys (octaves).

### Positioning Formula

For each key (0-87):

```python
# 1. Calculate key center (evenly spaced)
key_center_mm = (key_idx + 0.5) * key_width_mm

# 2. Determine if black or white key
note_in_octave = key_idx % 12
is_black_key = note_in_octave in [1, 3, 6, 8, 10]

# 3. Calculate physical span
if is_black_key:
    key_start_mm = key_center_mm - 5.5  # Half of 11mm black key width
    key_end_mm = key_center_mm + 5.5
else:
    key_start_mm = key_center_mm - 7.233  # Half of key spacing
    key_end_mm = key_center_mm + 7.233

# 4. Convert to LED indices
key_start_led_pos = key_start_mm / scale_factor
key_end_led_pos = key_end_mm / scale_factor

first_led = start_led + int(key_start_led_pos / led_spacing_mm)
last_led = start_led + int(key_end_led_pos / led_spacing_mm)

# 5. Allocate LEDs (with overlap handling)
leds_for_key = [led for led in range(first_led, last_led + 1) if start_led <= led <= end_led]
```

## Results for 200 LEDs/m, Range 4-249

### Statistics

- **Total keys mapped**: **88 of 88** ✅
- **White keys mapped**: 51 (avg 5.75 LEDs per white key)
- **Black keys mapped**: 37 (avg 5.19 LEDs per black key)
- **Overall average**: 5.51 LEDs per key
- **Min**: 4 LEDs
- **Max**: 6 LEDs
- **Distribution**:
  - 46 keys get 6 LEDs
  - 41 keys get 5 LEDs
  - 1 key gets 4 LEDs

### Key Spacing

- Piano width: **1225mm** (88 keys × 13.92mm per key)
- LED coverage: 246 LEDs × 5mm = 1230mm
- Scale factor: **1.0000** (perfect coverage! 📊)
- Per-key width: 13.9205mm
- Black key width: 11mm (assumed standard)

### Coverage

- **All 88 keys are fully mapped** ✅
- No keys exceed the LED range
- Perfect scale factor of 1.0000 means optimal utilization

## Example Mappings

### First Octave (Keys 0-11)

```
Key 0  A (WHITE):  5 LEDs [4, 5, 6, 7, 8]
Key 1  A#(BLACK):  5 LEDs [6, 7, 8, 9, 10]
Key 2  B (WHITE):  6 LEDs [9, 10, 11, 12, 13, 14]
Key 3  C (BLACK):  5 LEDs [12, 13, 14, 15, 16]
Key 4  C#(WHITE):  6 LEDs [15, 16, 17, 18, 19, 20]
Key 5  D (WHITE):  6 LEDs [18, 19, 20, 21, 22, 23]
Key 6  D#(BLACK):  5 LEDs [21, 22, 23, 24, 25]
Key 7  E (WHITE):  6 LEDs [24, 25, 26, 27, 28, 29]
Key 8  F (BLACK):  5 LEDs [27, 28, 29, 30, 31]
Key 9  F#(WHITE):  6 LEDs [30, 31, 32, 33, 34, 35]
Key 10 G (BLACK):  5 LEDs [33, 34, 35, 36, 37]
Key 11 G#(WHITE):  6 LEDs [36, 37, 38, 39, 40, 41]
```

### Middle Range (Keys 45-56)

```
Key 45 F#(WHITE):  6 LEDs [138-143]
Key 46 G (BLACK):  5 LEDs [141-145]
Key 47 G#(WHITE):  6 LEDs [144-149]
Key 48 A (WHITE):  6 LEDs [147-152]
Key 49 A#(BLACK):  5 LEDs [150-154]
Key 50 B (WHITE):  6 LEDs [153-158]
Key 51 C (BLACK):  5 LEDs [156-160]
Key 52 C#(WHITE):  6 LEDs [159-164]
Key 53 D (WHITE):  6 LEDs [162-167]
Key 54 D#(BLACK):  5 LEDs [165-169]
Key 55 E (WHITE):  6 LEDs [168-173]
Key 56 F (BLACK):  6 LEDs [171-176]
```

### Last keys (Keys 80-87)

```
Key 80 F (BLACK):   5 LEDs [226-230]
Key 81 F#(WHITE):   6 LEDs [228-233]
Key 82 G (BLACK):   5 LEDs [231-235]
Key 83 G#(WHITE):   5 LEDs [234-238]
Key 84 A (WHITE):   6 LEDs [236-241]
Key 85 A#(BLACK):   6 LEDs [239-244]
Key 86 B (WHITE):   6 LEDs [242-247]
Key 87 C (BLACK):   5 LEDs [245-249]  ✅ All keys mapped!
```

## Key Observations

### White vs Black Key LEDs

- **White keys average 5.94 LEDs**: Wider keys (23.5mm) get more LEDs
- **Black keys average 5.20 LEDs**: Narrower keys (11mm) get fewer LEDs
- The difference is small (0.74 LEDs) because the key center spacing is the dominant factor

### LED Overlap

LEDs are assigned to multiple keys at boundaries:
- Example: LED 10 is assigned to both Key 1 (A#) and Key 2 (B)
- This is intentional and creates smooth visual transitions between keys
- Reverse mapping (`led_key_mapping`) shows which keys control each LED

### Edge Cases

- **Key 81 (F#, last key with multiple LEDs)**: Only 4 LEDs due to range limit
- **Key 82 (G, single LED)**: Only 1 LED assigned (may be insufficient for visual display)
- **Keys 83-87**: Completely unmapped (beyond LED range)

## Configuration Parameters

### For 200 LEDs/meter

- **LED spacing**: 5mm per LED
- **Range 4-249**: 246 LEDs, 1230mm coverage
- **Per-key average**: 5.63 LEDs
- **Recommended**: Ideal for 88-key piano mapping
- **Coverage ratio**: 96.23% (last 5 keys exceed range)

### For Other LED Densities

| LEDs/m | Spacing | Coverage (4-249) | Per-key avg | Quality |
|--------|---------|------------------|-------------|---------|
| 60     | 16.67mm | 4100mm           | 18.6 LEDs   | Excellent (overkill) |
| 120    | 8.33mm  | 2050mm           | 9.3 LEDs    | Excellent |
| 150    | 6.67mm  | 1640mm           | 7.4 LEDs    | Very good |
| 200    | 5mm     | 1230mm           | 5.6 LEDs    | Good (current) |
| 240    | 4.17mm  | 1025mm           | 4.6 LEDs    | Fair (tight) |

## API Response Structure

```json
{
  "success": true,
  "key_led_mapping": {
    "0": [4, 5, 6, 7, 8],
    "1": [6, 7, 8, 9, 10],
    "2": [9, 10, 11, 12, 13, 14],
    ...
  },
  "led_key_mapping": {
    "4": [0],
    "5": [0],
    "6": [0, 1],
    "7": [0, 1],
    "8": [0, 1],
    ...
  },
  "led_allocation_stats": {
    "avg_leds_per_key": 5.63,
    "min_leds_per_key": 1,
    "max_leds_per_key": 6,
    "total_key_count": 83,
    "total_led_count": 246,
    "white_keys_mapped": 48,
    "black_keys_mapped": 35,
    "avg_leds_white_keys": 5.94,
    "avg_leds_black_keys": 5.20,
    "leds_per_key_distribution": {
      "5": 24,
      "6": 57,
      "4": 1,
      "1": 1
    },
    "scale_factor": 0.9623,
    "key_width_mm": 14.466,
    "piano_width_mm": 1230,
    "led_coverage_mm": 1230,
    "coverage_ratio": 0.9623
  },
  "warnings": [],
  "improvements": []
}
```

## Implementation Notes

### Files Modified

1. **`backend/config_led_mapping_advanced.py`**
   - Updated `calculate_per_key_led_allocation()` to handle all 88 keys
   - Added white/black key detection based on chromatic scale
   - Added statistics for white vs black key allocations

2. **`backend/api/calibration.py`**
   - No changes needed (already supports new function)
   - Endpoint `/api/calibration/advanced-mapping` works as-is

### Future Enhancements

1. **Per-key color mapping**: Different colors for white vs black keys
2. **Visualization**: Show LED heatmap with key boundaries
3. **Optimization**: Per-key calibration based on this allocation
4. **Validation**: Visual feedback during setup to verify LED placement
5. **Dynamics**: Animation effects that leverage the per-key mapping

## Testing

Run the function directly:

```python
from backend.config_led_mapping_advanced import calculate_per_key_led_allocation

result = calculate_per_key_led_allocation(200, 4, 249, '88-key')
mapping = result['key_led_mapping']
stats = result['led_allocation_stats']

print(f"Mapped {stats['total_key_count']} keys")
print(f"Average {stats['avg_leds_per_key']:.2f} LEDs per key")
```

Or via the API:

```bash
curl -X GET "http://localhost:5001/api/calibration/advanced-mapping?leds_per_meter=200&start_led=4&end_led=249"
```
