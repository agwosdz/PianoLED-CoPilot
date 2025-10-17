# Smart Physical LED Mapping Algorithm - Implementation Summary

## Overview

We've implemented a **physically-grounded, distance-based LED mapping algorithm** that intelligently calculates LED-to-key mappings based on:

1. **LED strip density** (leds_per_meter)
2. **Calibration points** (start_led, end_led from user setup)
3. **Piano geometry** (white key positions and spacing)
4. **Physical distance correlations** between LED positions and key positions

## Key Insight

Instead of treating LEDs and keys as abstract indices, we map them through **physical distance**:

```
Piano Physical Space (in mm)
├─ White key width: 23.5 mm each
├─ Gap between keys: 1.0 mm each
└─ Total piano width (88-key): 1273 mm

LED Strip Physical Space (in mm)
├─ LED spacing depends on density (60-200 LEDs/meter)
├─ Example at 60 LEDs/m: 16.67 mm between LEDs
└─ Range coverage: (end_led - start_led) * spacing

Mapping:
Each physical LED position → correlates to → piano key position via distance
```

## Algorithm Components

### 1. Piano Geometry Data (config.py)

Pre-calculated constants for each piano size:

```python
WHITE_KEY_COUNTS = {
    "25-key": 18,
    "37-key": 27,
    "49-key": 35,
    "61-key": 44,
    "76-key": 54,
    "88-key": 52,
}

PIANO_WIDTHS_MM = {
    "88-key": 52 * 23.5 + 51 * 1.0 = 1273 mm,
    ...
}
```

### 2. Core Algorithm: `calculate_physical_led_mapping()`

**Function signature:**
```python
def calculate_physical_led_mapping(
    leds_per_meter: int,
    start_led: int,
    end_led: int,
    piano_size: str,
    distribution_mode: str = "proportional"
) -> Dict[str, Any]
```

**Input Parameters:**
- `leds_per_meter`: LED strip density (60, 72, 100, 120, 144, 160, 180, 200)
- `start_led`: Physical LED index where piano calibration starts
- `end_led`: Physical LED index where piano calibration ends
- `piano_size`: Piano size ("88-key", "49-key", etc.)
- `distribution_mode`: How to allocate LEDs ("proportional", "fixed", "custom")

**Output:**
```python
{
    "first_led": 0,                    # Logical offset = start_led
    "led_count_usable": 120,           # end_led - start_led + 1
    "leds_per_key": 2.31,              # Average LEDs per white key
    "leds_per_key_int": 2,             # Integer version for fixed mode
    "white_key_count": 52,             # Number of white keys
    "piano_width_mm": 1273.0,          # Physical piano width
    "led_spacing_mm": 16.67,           # Distance between LEDs
    "led_coverage_mm": 1983.3,         # Total distance covered by LED range
    "quality_score": 85,               # 0-100 quality rating
    "quality_level": "good",           # "poor", "ok", "good", "excellent"
    "warnings": [...],                 # Issues with this configuration
    "recommendations": [...],          # Suggestions for improvement
    "metadata": {                       # Detailed metrics
        "coverage_ratio": 1.56,        # led_coverage / piano_width
        "piano_width_m": 1.273,        # Piano width in meters
        "led_coverage_m": 1.983,       # LED coverage in meters
        ...
    }
}
```

### 3. Quality Scoring: `_calculate_led_mapping_quality()`

Evaluates the configuration on three factors (each 0-100, summed):

| Factor | Ideal Range | Score Impact |
|--------|------------|--------------|
| **LEDs per key** | 2-4 | -50 if <1, -20 if <2, +0 if 2-4, -5 if 4-6, -15 if >6 |
| **Coverage ratio** | 0.95-1.05 | -25 if <0.8, -10 if <0.95, +0 if 0.95-1.05, -5 if 1.05-1.2, -15 if >1.2 |
| **Efficiency** | 1.0-1.1 | -30 if <0.5, -10 if <1.0, +0 if 1.0-1.1, -5 if >1.1 |

## Test Results

### Example 1: Standard Configuration ✓
```
88-key piano, 60 LEDs/m, range 0-119 (120 LEDs)
Result: 2.31 LEDs/key, quality = GOOD (85/100)
Piano width: 1273 mm
LED coverage: 1983 mm (1.56x piano width)
```

**Analysis:**
- Excellent: More than enough LEDs per key
- Expected warning: Oversaturated (56% excess coverage)
- Use case: Smooth transitions, good visual effects

### Example 2: Undersaturated ⚠️
```
88-key piano, 60 LEDs/m, range 0-35 (36 LEDs)
Result: 0.69 LEDs/key, quality = POOR (25/100)
Piano width: 1273 mm
LED coverage: 583 mm (0.46x piano width)
Warnings: Only 36 LEDs for 52 white keys!
```

**Issues detected:**
- Only 0.69 LEDs per white key (should be ≥1)
- Covers only 46% of piano width
- Can only map ~36 keys instead of 52

**Recommendations:**
1. Use more LEDs from strip (extend range)
2. Use denser LED strip (higher leds_per_meter)
3. Use smaller piano size (fewer keys)

### Example 3: Dense LED Strip ✓
```
88-key piano, 200 LEDs/m, range 0-240 (241 LEDs)
Result: 4.63 LEDs/key, quality = GOOD (75/100)
```

**Characteristics:**
- 4.63 LEDs per key (excellent coverage)
- Premium effects possible (smooth gradients, fine control)

### Example 4: Different Piano Size ✓
```
49-key piano, 100 LEDs/m, range 50-180 (131 LEDs)
Result: 3.74 LEDs/key, quality = GOOD (85/100)
Piano width: 856.5 mm
LED coverage: 1300 mm (1.52x piano width)
```

## Integration with Existing Code

### 1. Update Calibration API (calibration.py)

When user sets `start_led` or `end_led`:

```python
@calibration_bp.route('/start-led', methods=['PUT'])
def set_start_led():
    # ... existing validation ...
    
    # NEW: Calculate optimal mapping
    result = calculate_physical_led_mapping(
        leds_per_meter=settings_service.get_setting('led', 'leds_per_meter', 60),
        start_led=start_led,
        end_led=settings_service.get_setting('calibration', 'end_led', 245),
        piano_size=settings_service.get_setting('piano', 'size', '88-key')
    )
    
    # Emit metadata to frontend
    socketio.emit('mapping_calculated', {
        'first_led': result['first_led'],
        'led_count_usable': result['led_count_usable'],
        'leds_per_key': result['leds_per_key'],
        'quality_level': result['quality_level'],
        'warnings': result['warnings'],
        'recommendations': result['recommendations']
    })
```

### 2. Auto-Mapping Integration

Pass calculated values to `generate_auto_key_mapping()`:

```python
result = calculate_physical_led_mapping(...)

mapping = generate_auto_key_mapping(
    piano_size=piano_size,
    led_count=result['led_count_usable'],
    mapping_base_offset=result['first_led'],
    distribution_mode=distribution_mode
)
```

### 3. UI Feedback

Display results to user:

```
LED Mapping Summary
─────────────────────
Piano: 88-key (52 white keys, 1273 mm width)
LED Strip: 60 LEDs/meter (16.67 mm spacing)
Calibration: LEDs 0-119 (120 total, 1983 mm coverage)

Results:
✓ 2.31 LEDs per white key (good!)
✓ Quality: GOOD (85/100)
⚠ Note: 56% excess LED coverage (1.56x piano width)

Recommendations:
1. Adjust calibration to better match piano width
2. Or use a less dense LED strip (e.g., 100 LEDs/m instead of 60)
```

## Physical Geometry Explained

### Piano Measurements

**Standard acoustic piano:**
- White key width: 23.5 mm
- Black key width: 13.5 mm
- Gap between keys: 1 mm

**88-key piano layout:**
```
White keys per octave: 7 (A, B, C, D, E, F, G)
88-key span: 7.25 octaves = 7×7 + 3 = 52 white keys

Total width:
52 white keys × 23.5 mm = 1222 mm
51 gaps × 1.0 mm = 51 mm
Total = 1273 mm ≈ 1.27 meters
```

### LED Strip Measurements

**Distance between LEDs:**
- 60 LEDs/m → 1000/60 = 16.67 mm
- 100 LEDs/m → 10.00 mm
- 200 LEDs/m → 5.00 mm

**Physical Distance Covered:**
For N LEDs at D LEDs/meter:
- Spacing = 1000/D mm
- Total distance = (N-1) × spacing

Example: 120 LEDs at 60 LEDs/m
- Spacing: 16.67 mm
- Distance: 119 × 16.67 = 1983.3 mm ≈ 2 meters

## Quality Metrics Interpretation

### Quality Score (0-100)

- **90-100: EXCELLENT** - Perfect for high-quality visualization
- **70-90: GOOD** - Suitable for most applications
- **50-70: OK** - Acceptable but suboptimal
- **0-50: POOR** - Requires reconfiguration

### Coverage Ratio

```
Coverage Ratio = LED_Coverage_Distance / Piano_Width

< 0.9:   Undersaturated (not enough LEDs)
0.9-1.1: Ideal (LEDs match piano width)
> 1.1:   Oversaturated (excess LEDs)
```

## Validation & Error Handling

The algorithm validates:

1. ✓ LED density is one of supported values
2. ✓ start_led and end_led are valid indices
3. ✓ end_led >= start_led (no reversed ranges)
4. ✓ Piano size is recognized
5. ✓ All calculations produce non-negative results

Returns errors in `result['error']` field with explanations.

## Future Enhancements

1. **Black Key Mapping**: Special handling for black keys between white keys
2. **Key-Specific Offsets**: Per-key calibration adjustments
3. **Physical Width Input**: Accept user-measured piano width for validation
4. **Density Recommendations**: Suggest optimal LED density for given piano size
5. **Multi-Strip Support**: Handle multiple LED strips for larger pianos
6. **Temperature-Based Compensation**: Account for thermal effects on LED spacing

## Testing

Comprehensive test suite in `test_physical_led_mapping.py`:

```bash
python test_physical_led_mapping.py
```

Tests cover:
- Standard configurations
- Undersaturated scenarios (warnings)
- Oversaturated scenarios (warning)
- Different piano sizes
- Physical geometry verification
- Edge cases and error handling

All tests passing ✓

## Summary

This algorithm provides:

✅ **Physical grounding**: Maps through actual distances, not abstract indices  
✅ **Intelligent validation**: Detects misconfigurations and offers solutions  
✅ **Quality scoring**: Helps users understand their configuration  
✅ **Backward compatible**: Works with existing settings schema  
✅ **Extensible**: Easy to add more piano sizes or LED densities  
✅ **Well-tested**: Comprehensive test suite with real-world examples  

The result is a **smart, transparent, user-friendly system** for mapping LEDs to piano keys that respects the physical reality of both the piano and the LED strip.
