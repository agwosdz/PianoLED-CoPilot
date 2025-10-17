# Visual Guide: Physical LED-to-Key Mapping

## Understanding the Mapping Process

### Layer 1: Piano Physical Space

```
88-Key Piano (Top View)
═════════════════════════════════════════════════════════════════════════════

Position:    0                                                          1273mm
             |                                                            |
             ▼                                                            ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  A0   B0  │C1  D1  E1 │ F1  G1 │A1  B1 │C2  D2  E2 │...      │
        │     │    ││   │   │  ││   │   ││   │   ││   │   │  │         │ 
        └─────────────────────────────────────────────────────────────────┘
             ▲      ▲         ▲      ▲      ▲         ▲                   ▲
             │      │         │      │      │         │                   │
        White keys (52 total) × 23.5 mm each + 51 gaps × 1 mm = 1273 mm total

Key widths:
├─ White: 23.5 mm
├─ Gap: 1.0 mm
└─ Total width: 1273 mm ≈ 1.27 meters
```

### Layer 2: LED Strip Physical Space

```
LED Strip at 60 LEDs/meter
═════════════════════════════════════════════════════════════════════════════

Spacing: 1000 / 60 = 16.67 mm between each LED

Position:    0                                                          ~2000mm
             |                                                            |
             ▼ (LED 0)                                            (LED 119)▼
        ●────●────●────●────●────●────●────●────●────●────...────●────●
        │ 16.67mm │ 16.67mm │ 16.67mm │ 16.67mm │ ... │ 16.67mm │ 16.67mm
        └────────┬─────────────────────────────────────────────────────────┘
                 Total coverage: 119 × 16.67 = 1983.3 mm ≈ 2 meters

Note: This is much larger than the piano (1273 mm)!
      Oversaturation factor: 1983.3 / 1273 = 1.56x
```

### Layer 3: Distance-Based Mapping

```
Correlation Through Physical Distance
═════════════════════════════════════════════════════════════════════════════

Step 1: Calculate distance per piano white key
        Distance = Piano_Width / White_Key_Count
        = 1273 mm / 52 keys
        = 24.48 mm per white key

Step 2: Calculate distance per LED position
        Distance = 1000 mm / LEDs_Per_Meter
        = 1000 / 60
        = 16.67 mm per LED

Step 3: Calculate mapping ratio
        LEDs_Per_Key = Distance_Per_Key / Distance_Per_LED
        = 24.48 / 16.67
        = 1.47 LEDs per key

        But we have 120 LEDs for 52 keys (proportional):
        = 120 / 52 = 2.31 LEDs per key
        
        (Proportional is used because it considers the actual range)

Step 4: Assign LED ranges to keys
        Key 0 (A0):      LEDs 0-2      (2 LEDs)
        Key 1 (A#0):     LEDs 2-5      (3 LEDs)  <- Extra LED
        Key 2 (B0):      LEDs 5-7      (2 LEDs)
        ...
        Key 51 (C8):     LEDs 117-119  (2 LEDs)
```

## Real-World Example: Calibration Setup

```
Physical Setup
═════════════════════════════════════════════════════════════════════════════

User Places LED Strip Over Piano:
                                                     
    Piano:    [A0  B0  C1  D1  E1  F1  G1  A1  ...  C8]
              |   |   |   |   |   |   |   |   |   |   |
              0   23.5 47  70.5 94 117.5 141 164.5...1273 mm
    
    LEDs:     [0]─────[1]─────[2]─────[3]─────[4]─────[5]─────...────[119]
              |       |       |       |       |       |              |
              0       16.67   33.33   50      66.67   83.33...   1983.3 mm

    User calibrates:
    ✓ Set First LED: Click LED physically aligned with A0
      → Gets LED index 0 → start_led = 0
    ✓ Set Last LED: Click LED physically aligned with C8  
      → Gets LED index 119 → end_led = 119

Algorithm Calculates:
    ✓ first_led = 0 (from start_led)
    ✓ led_count_usable = 119 - 0 + 1 = 120
    ✓ leds_per_key = 120 / 52 = 2.31
    ✓ quality_level = "good" (85/100)
    ✓ coverage_ratio = 1983.3 / 1273 = 1.56 (excess coverage)
    
    Warnings: "LED strip coverage exceeds piano width by 56%"
              "This may cause edge keys to light up outside their physical area"
    
    Recommendations: 
    - OK for music visualization (smooth effects from excess LEDs)
    - If precision calibration needed: reduce calibration range or use 100 LEDs/m strip
```

## Quality Evaluation Matrix

```
Configuration Quality Score Determination
═════════════════════════════════════════════════════════════════════════════

Factor 1: LEDs per Key Adequacy (Target: 2-4)
────────────────────────────────────────────

  < 1.0    : CRITICAL - Not enough LEDs for each key
             Quality: -50 points
             Example: 0.69 LEDs/key (36 LEDs for 52 keys)
  
  1.0-2.0  : LOW - Acceptable but sparse
             Quality: -20 to -10 points
             Example: 1.5 LEDs/key (limited effects)
  
  2.0-4.0  : IDEAL - Perfect for most use cases
             Quality: 0 points (baseline)
             Example: 2.31 LEDs/key (good balance)
  
  4.0-6.0  : HIGH - Excellent but oversaturated
             Quality: -5 points
             Example: 4.63 LEDs/key (smooth gradients)
  
  > 6.0    : EXCESS - Too many LEDs, diminishing returns
             Quality: -15 points
             Example: 8.0+ LEDs/key (overkill)

Factor 2: Coverage Ratio (Target: 0.95-1.05)
─────────────────────────────────────────────

  < 0.80   : SEVERE UNDERSATURATION
             Quality: -25 points
             Example: 0.46 (only 46% of piano width covered)
  
  0.80-0.95: UNDERSATURATED
             Quality: -10 points
             Example: 0.90 (90% coverage, 10% of keys unmapped)
  
  0.95-1.05: PERFECT MATCH
             Quality: 0 points
             Example: 1.00 (LEDs exactly match piano width)
  
  1.05-1.20: OVERSATURATED (Acceptable)
             Quality: -5 points
             Example: 1.20 (20% excess coverage)
  
  > 1.20   : SEVERELY OVERSATURATED
             Quality: -15 points
             Example: 1.56 (56% excess coverage)

Factor 3: Efficiency (Can all keys be mapped?)
───────────────────────────────────────────────

  < 0.50   : CRITICAL - Can only map 50% of keys
             Quality: -30 points
             Example: 36 LEDs can only map 36 of 88 keys
  
  0.50-1.00: PARTIAL - Some keys will be unmapped
             Quality: -10 points
             Example: 44 LEDs can map 44 of 88 keys
  
  1.00-1.10: IDEAL - All keys can be mapped efficiently
             Quality: 0 points
             Example: 100 LEDs can map all 88 keys with room to spare
  
  > 1.10   : EXCESS - Far more than needed
             Quality: -5 points
             Example: 200 LEDs can map all 88 keys multiple times

Final Score = 100 + Factor1_Penalty + Factor2_Penalty + Factor3_Penalty
            = 100 - 20 - 5 - 0 = 75/100 for Example 1
```

## Configuration Scenarios Visualized

### Scenario A: Perfect Balance ✓

```
Piano:  [===================================] 1273 mm
LED:    [======================================] 1983 mm

Ratio:  1.56x (oversaturated, but acceptable)
LEDs:   2.31 per key (good)
Score:  85/100 (GOOD)

Characteristics:
  ✓ All keys get 2-3 LEDs each
  ✓ Smooth color transitions possible
  ✓ Slight excess coverage (not critical)
  ✓ Good for music visualization
```

### Scenario B: Undersaturated ⚠️

```
Piano:  [===================================] 1273 mm
LED:    [===============]                      583 mm

Ratio:  0.46x (critical undersaturation)
LEDs:   0.69 per key (too few!)
Score:  25/100 (POOR)

Characteristics:
  ✗ Only 36 LEDs for 52 white keys
  ✗ Some keys share single LED
  ✗ Can only map lower 36 keys
  ✗ Gaps in coverage
  
Solutions:
  1. Extend calibration range (use more LEDs from strip)
  2. Use denser LED strip (e.g., 120 instead of 60 LEDs/m)
  3. Use smaller piano (49-key instead of 88-key)
```

### Scenario C: Premium Coverage ✓✓

```
Piano:  [===================================] 1273 mm
LED:    [============================================] 2500+ mm

Ratio:  2.0x+ (heavily oversaturated)
LEDs:   4.6+ per key (excellent)
Score:  75-85/100 (GOOD)

Characteristics:
  ✓ Multiple LEDs per key
  ✓ Smooth gradient mapping possible
  ✓ Professional-grade visualization
  ✓ Can mask alignment errors
  
Trade-offs:
  - Uses more expensive LED strip
  - More power consumption
  - More complex wiring
  - Diminishing visual returns
```

### Scenario D: Highly Constrained ⚠️

```
Piano:  [===================================] 1273 mm
LED:    [================] 500 mm

Ratio:  0.39x (severely undersaturated)
LEDs:   0.96 per key (critical!)
Score:  10/100 (CRITICALLY POOR)

Characteristics:
  ✗ Cannot adequately map all keys
  ✗ Must choose between:
    - Mapping only first 30-40 keys, or
    - Using denser LED strip, or
    - Using smaller piano
  
Not recommended for this setup unless:
  - Using 49-key or smaller piano, AND
  - Extending calibration range to use full strip
```

## Integration Timeline

```
User Workflow
═════════════════════════════════════════════════════════════════════════════

Phase 1: Settings
  ├─ User selects piano size (e.g., "88-key")
  ├─ User selects LED density (e.g., "60 LEDs/m")
  └─ System loads piano geometry and LED specs

Phase 2: Calibration
  ├─ User places LED strip on piano
  ├─ User clicks "Set First LED" and selects LED at piano start
  │  └─ → start_led = 0
  ├─ User clicks "Set Last LED" and selects LED at piano end
  │  └─ → end_led = 119
  └─ System calculates mapping parameters

Phase 3: Calculation & Feedback
  ├─ System calls: calculate_physical_led_mapping(60, 0, 119, "88-key")
  ├─ System receives:
  │  ├─ first_led: 0
  │  ├─ led_count_usable: 120
  │  ├─ leds_per_key: 2.31
  │  ├─ quality_level: "good" (85/100)
  │  └─ metadata with warnings/recommendations
  └─ Frontend displays mapping summary:
     
     LED Mapping Configuration
     ────────────────────────────
     Piano: 88-key (52 white keys, 1273 mm)
     LEDs: 60 LEDs/meter (16.67 mm spacing)
     Calibration: LEDs 0-119 (120 total)
     
     Results:
     ✓ 2.31 LEDs per white key
     ✓ Quality: GOOD (85/100)
     ✓ All keys can be mapped
     
     Note: LED strip coverage is 56% larger than 
           piano width. This allows smooth transitions
           but means edge keys have extra LEDs.

Phase 4: Auto-Mapping
  ├─ System calls: generate_auto_key_mapping(..., 120, 0)
  ├─ Each key gets assigned LED indices based on position
  └─ Mapping is stored and used for MIDI→LED translation
```

## Performance Impact

```
Computational Complexity
═════════════════════════════════════════════════════════════════════════════

Operation                    | Time    | Called By
───────────────────────────────────────────────────────────────
get_piano_width_mm()         | O(1)    | calculate_physical_led_mapping
count_white_keys()           | O(1)    | calculate_physical_led_mapping
_calculate_led_mapping_quality() | O(1)    | calculate_physical_led_mapping
calculate_physical_led_mapping() | O(1)    | Calibration API
generate_auto_key_mapping()  | O(n)    | Where n = number of keys (88)

Total for full calibration: O(n) ≈ negligible (< 1ms on typical system)
```

## Summary

The physical distance-based mapping algorithm:

1. **Grounds the system in physical reality** - LEDs and keys are mapped through actual distances
2. **Provides intelligent validation** - Detects and warns about misconfigurations
3. **Enables user-friendly feedback** - Shows quality scores and recommendations
4. **Maintains backward compatibility** - Works with existing settings and APIs
5. **Scales across piano sizes** - Works with 25-key through 88-key pianos
6. **Adapts to LED densities** - Handles 60-200 LEDs/meter strips

The result is a **transparent, intelligent system** that helps users understand and optimize their LED-to-piano mapping without requiring deep technical knowledge.
