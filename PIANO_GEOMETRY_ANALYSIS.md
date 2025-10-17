# Piano Geometry & LED Mapping Algorithm

## Physical Piano Geometry

### Key Spacing Foundation
- **Equal spacing at key base**: Each key occupies 1 unit of width at the base
- **Gap between keys**: 1mm (approximately 0.04 inches)
- **Key pattern**: Repeats every 7 white keys in an octave (A-B-C-D-E-F-G)
  
### Piano Key Layout (One Octave)
```
Standard octave pattern (repeating):
  [W] [B] [W] [B] [W]  [W] [B] [W] [B] [W] [B] [W]
   A   A#  B   C   C#   D   D#  E   F   F#  G   G#
   
W = White key (7 per octave)
B = Black key (5 per octave)
Total = 12 keys per octave (semitones)
```

### Standard Piano Sizes

| Size | Total Keys | Octaves | Start | End | White Keys | Black Keys | Total Octaves |
|------|-----------|---------|-------|-----|-----------|-----------|---------------|
| 25-key | 25 | 2.0 | C3 | C5 | 18 | 7 | 2.0 |
| 37-key | 37 | 3.0 | C2 | C5 | 27 | 10 | 3.0 |
| 49-key | 49 | 4.0 | C2 | C6 | 35 | 14 | 4.0 |
| 61-key | 61 | 5.0 | C2 | C7 | 44 | 17 | 5.0 |
| 76-key | 76 | 6.25 | E1 | G7 | 54 | 22 | 6.25 |
| 88-key | 88 | 7.25 | A0 | C8 | 52 | 36 | 7.25 |

**Formula for white keys in N keys**: 
- Full octaves have 7 white keys each
- For 88 keys (7.25 octaves = 7 full + 1 partial):
  - 7 full octaves × 7 = 49 white keys
  - Plus partial octave (A0, B0, C1) = 3 white keys
  - Total: 52 white keys

### Physical Width Calculation

For an **88-key piano**:
```
Total width at base = (number of white keys) + (gaps between keys)
                    = 52 keys × 1 unit + 51 gaps × 1mm

In normalized units (treating 1 key width = 1 unit):
Piano width = 52 units + 51mm
            = 52 + 0.051 units (if treating 1mm as 0.001 unit)
            ≈ 52 units (gap is negligible for mapping purposes)

For practical mapping, we consider:
Piano width ≈ Number of white keys ≈ 52 units for 88-key piano
```

### Key Position on Piano (0-indexed from left)
For white keys only:
```
88-key piano white key positions (in white-key indices):
Position 0 = A0
Position 1 = B0
Position 2 = C1
Position 3 = D1
...
Position 51 = C8 (last key)
```

## LED Strip Geometry

### LED Spacing
```
leds_per_meter values: [60, 72, 100, 120, 144, 160, 180, 200]

Distance between LEDs (mm):
60 LEDs/m   → 16.67 mm between LEDs
72 LEDs/m   → 13.89 mm between LEDs
100 LEDs/m  → 10.00 mm between LEDs
120 LEDs/m  → 8.33 mm between LEDs
144 LEDs/m  → 6.94 mm between LEDs
160 LEDs/m  → 6.25 mm between LEDs
180 LEDs/m  → 5.56 mm between LEDs
200 LEDs/m  → 5.00 mm between LEDs
```

### Total Strip Length
```
For N LEDs at D LEDs/meter:
Length (meters) = N / D
Length (mm)     = (N / D) × 1000
```

Example for 240 LEDs at 60 LEDs/m:
```
Length = 240 / 60 = 4 meters = 4000mm
```

## Smart Mapping Algorithm

### Problem Statement
**Given:**
- `leds_per_meter`: The density of the LED strip (e.g., 60, 72, 100, etc.)
- `start_led`: The physical LED index where the user placed the first LED of the piano
- `end_led`: The physical LED index where the user placed the last LED of the piano
- `piano_size`: The size of the piano (e.g., "88-key")

**Calculate:**
- `first_led` (mapping_base_offset): The logical starting point for LED-to-key mapping
- `led_count_usable`: The number of LEDs actually used for the piano
- `leds_per_key`: How many LEDs should light up per key (or per white key)
- Position correlation: How each physical LED position relates to piano key positions

### Algorithm Design

#### Step 1: Extract Piano Dimensions
```python
piano_specs = get_piano_specs(piano_size)
white_key_count = count_white_keys(piano_specs)
# For 88-key: white_key_count = 52
# For 61-key: white_key_count = 44
# etc.
```

#### Step 2: Calculate Physical LED Range
```python
physical_led_range = end_led - start_led + 1
# Example: end_led=119, start_led=0 → range=120 LEDs

# Optional: Calculate physical distance if we have piano width
# (This is the NEW insight - we can validate LED density against piano geometry)
```

#### Step 3: Calculate LED-to-Distance Mapping
```python
# Distance between consecutive LEDs (in mm)
led_spacing_mm = 1000 / leds_per_meter
# e.g., 60 LEDs/m → 16.67 mm between LEDs

# Total distance covered by the LED range (in mm)
total_distance_mm = (physical_led_range - 1) * led_spacing_mm
# Example: 120 LEDs at 60/m → 119 × 16.67 = 1984.3 mm ≈ 1.98 meters

# Total distance covered by white keys (assuming ~23.5mm per white key)
# This is a standard piano measurement (middle C white key width ≈ 23.5mm)
white_key_width_mm = 23.5  # Standard piano key width
piano_width_mm = white_key_count * white_key_width_mm + (white_key_count - 1) * 1  # +1mm gaps
# e.g., 52 keys × 23.5mm + 51 × 1mm = 1222mm + 51mm = 1273mm ≈ 1.27 meters
```

#### Step 4: Calculate LEDs per White Key
```python
# Method A: Proportional Distribution
leds_per_white_key = physical_led_range / white_key_count
# Example: 120 LEDs / 52 white keys ≈ 2.31 LEDs/key
# Meaning: ~2-3 LEDs per white key, with some keys getting one extra

# Method B: Distance-Based Mapping (More Accurate)
# Each white key covers a certain distance on the piano
distance_per_white_key = piano_width_mm / white_key_count
# Example: 1273mm / 52 keys ≈ 24.5mm per key

# Each LED covers a certain distance on the strip
distance_per_led = 1000 / leds_per_meter
# Example: 1000 / 60 = 16.67mm per LED span (or 10mm for center-to-center spacing)

# LEDs per key = distance_per_white_key / distance_per_led
leds_per_white_key = distance_per_white_key / distance_per_led
# Example: 24.5mm / 16.67mm ≈ 1.47 LEDs/key → round to 1-2 LEDs/key
```

#### Step 5: Calculate LED-to-Key Correspondence
```python
# For each white key, calculate which LED(s) should light up
# Based on physical position alignment

for white_key_index in range(white_key_count):
    # Physical position of this white key on the piano (in mm from start)
    key_position_mm = white_key_index * distance_per_white_key
    
    # Which LED(s) correspond to this position?
    # Map piano position to LED index
    led_index_start = start_led + (key_position_mm / distance_per_led)
    led_index_end = led_index_start + leds_per_white_key
    
    # Round to actual LED indices
    led_indices = list(range(
        int(ceil(led_index_start)),
        int(ceil(led_index_end))
    ))
    
    # Map this LED range to the MIDI note corresponding to this white key
    midi_note = white_key_to_midi_note(piano_specs, white_key_index)
    
    mapping[midi_note] = led_indices
```

#### Step 6: Handle All Keys (White + Black)
```python
# The white-key mapping gives us the backbone
# For chromatic (all 88 keys), we need to also map black keys

# Black keys fall between white keys
# They can be mapped to:
# Option A: Average of adjacent white key LEDs
# Option B: Single LED closest to their position
# Option C: Share LEDs with adjacent white key
```

### Output Structure
```python
result = {
    "first_led": start_led,  # Logical offset (= start_led from calibration)
    "led_count_usable": physical_led_range,  # end_led - start_led + 1
    "leds_per_key": calculated_leds_per_key,
    "mapping": {
        # MIDI note → LED indices
        21: [0, 1],      # A0 → LEDs 0-1
        22: [1, 2],      # A#0 → LEDs 1-2 (shares with A0)
        23: [2, 3],      # B0 → LEDs 2-3
        ...
    },
    "metadata": {
        "piano_size": piano_size,
        "white_key_count": 52,
        "total_keys": 88,
        "leds_per_meter": leds_per_meter,
        "led_spacing_mm": 16.67,
        "piano_width_mm": 1273,
        "piano_width_m": 1.273,
        "led_coverage_mm": 1984,
        "led_coverage_m": 1.984,
        "coverage_ratio": 1.984 / 1.273,  # How many times LED span covers piano width
        "leds_per_white_key": 2.31,
        "utilization": "good" | "oversaturated" | "undersaturated"
    },
    "validation": {
        "range_valid": True,
        "sufficient_leds": True,
        "warnings": [],
        "suggestions": []
    }
}
```

## Implementation Roadmap

### Phase 1: Helper Functions (config.py)
1. `count_white_keys_in_range(start_note, end_note)` → calculates white keys for any piano size
2. `get_white_key_positions(piano_size)` → returns list of white key indices and their MIDI notes
3. `calculate_piano_width_mm(white_key_count)` → standard formula: 52 keys = 1273mm
4. `get_white_key_to_midi_mapping(piano_size)` → maps white key indices to MIDI notes

### Phase 2: Core Algorithm (config.py)
1. `calculate_led_mapping_parameters(leds_per_meter, start_led, end_led, piano_size, distribution_mode)` → the main algorithm
   - Takes calibration inputs
   - Returns first_led, led_count_usable, leds_per_key, and full mapping
   
2. `generate_physical_position_mapping(...)` → maps LED positions to key positions accurately

### Phase 3: Integration
1. Update calibration API endpoints to use new algorithm
2. Add metadata return to help users understand the mapping
3. Add validation warnings for unusual configurations

## Example Walkthroughs

### Example 1: Standard 88-Key, 60 LEDs/m, 120 Total LEDs
```
Input:
  - leds_per_meter: 60
  - start_led: 0
  - end_led: 119
  - piano_size: "88-key"

Calculations:
  - White keys: 52
  - Physical range: 120 LEDs
  - LED spacing: 16.67mm
  - Piano width: 1273mm (approx)
  - Distance per white key: 1273 / 52 = 24.5mm
  - LEDs per white key: 24.5 / 16.67 = 1.47 → 1-2 LEDs/key

Output:
  - first_led: 0
  - led_count_usable: 120
  - leds_per_key: 1-2
  - Quality: GOOD (reasonable coverage)
```

### Example 2: Undersaturated (Too Few LEDs)
```
Input:
  - leds_per_meter: 60
  - start_led: 0
  - end_led: 35
  - piano_size: "88-key"

Calculations:
  - Physical range: 36 LEDs
  - LED spacing: 16.67mm
  - Distance per white key: 24.5mm
  - LEDs per white key: 24.5 / 16.67 = 1.47
  - But only 36 LEDs for 52 white keys = 0.69 LEDs/key

Warning: "Only 36 LEDs for 52 white keys. Consider:
  - Reducing piano size (use only 36 keys)
  - Increasing LED density (use 100+ LEDs/m strip)
  - Extending the calibration range (use more LEDs from strip)"
```

### Example 3: Oversaturated (Too Many LEDs)
```
Input:
  - leds_per_meter: 200
  - start_led: 0
  - end_led: 240
  - piano_size: "88-key"

Calculations:
  - Physical range: 241 LEDs
  - LED spacing: 5mm
  - Distance per white key: 24.5mm
  - LEDs per white key: 24.5 / 5 = 4.9 LEDs/key

Info: "Excellent coverage: ~5 LEDs per white key.
  This allows very smooth transitions and detailed effects."
```

## Physical Constants

```python
# Standard piano measurements (from acoustic piano specs)
WHITE_KEY_WIDTH_MM = 23.5      # Standard white key width
BLACK_KEY_WIDTH_MM = 13.5      # Standard black key width
KEY_GAP_MM = 1.0               # Gap between keys at base

# Derived constants
WHITE_KEYS_PER_OCTAVE = 7
BLACK_KEYS_PER_OCTAVE = 5
TOTAL_KEYS_PER_OCTAVE = 12     # Semitones

# White key count by piano size (pre-calculated for efficiency)
WHITE_KEY_COUNTS = {
    "25-key": 18,
    "37-key": 27,
    "49-key": 35,
    "61-key": 44,
    "76-key": 54,
    "88-key": 52,
}

# Total piano width (mm) by size (accounting for key widths and gaps)
PIANO_WIDTHS_MM = {
    "25-key": 18 * 23.5 + 17 * 1.0,   # 423 + 17 = 440mm
    "37-key": 27 * 23.5 + 36 * 1.0,   # 634.5 + 36 = 670.5mm
    "49-key": 35 * 23.5 + 48 * 1.0,   # 822.5 + 48 = 870.5mm
    "61-key": 44 * 23.5 + 60 * 1.0,   # 1034 + 60 = 1094mm
    "76-key": 54 * 23.5 + 75 * 1.0,   # 1269 + 75 = 1344mm
    "88-key": 52 * 23.5 + 87 * 1.0,   # 1222 + 87 = 1309mm (standard: 1273mm)
}
```

---

## Next Steps

1. Implement helper functions for piano geometry
2. Create the main algorithm function
3. Add comprehensive validation and error handling
4. Create unit tests with the examples above
5. Integrate into calibration API
6. Update UI to display mapping metadata
