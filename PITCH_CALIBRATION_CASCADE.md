# Pitch Calibration Cascade - Single-Pass Architecture

## Overview
Implemented a **single-pass pitch calibration cascade** that properly handles the LED coverage adjustment scenario:

1. **Generate initial mapping** → detect coverage gap
2. **Calculate pitch adjustment** based on gap  
3. **Regenerate mapping once** with adjusted pitch
4. Return optimized allocation

This ensures the final mapping is built with the **correct pitch spacing** from the start.

## Flow

```
START
  ↓
┌─────────────────────────────────────────┐
│ STEP 1: Generate Initial Mapping        │
│ • Calculate LED placements (current pitch)
│ • Find overlapping LEDs for each key    │
│ • Apply overhang filtering              │
│ • Extend last key to end_led            │
│ • Record: max_led_assigned              │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│ STEP 2: Calculate Pitch Adjustment      │
│ • Detect coverage gap:                  │
│   gap = end_led - max_led_assigned      │
│ • Call auto_calibrate_pitch() with:     │
│   - theoretical_pitch                   │
│   - piano dimensions                    │
│   - start_led, actual_end_led           │
│ • Returns: calibrated_pitch, was_adjusted
└─────────────────────────────────────────┘
  ↓
  │  was_adjusted?
  ├─ YES ──────────────────────────────────┐
  │                                        │
  │  ┌─────────────────────────────────┐  │
  │  │ STEP 3: Regenerate with        │  │
  │  │ Adjusted Pitch                 │  │
  │  │ • Update analyzer pitch        │  │
  │  │ • Call _generate_mapping()     │  │
  │  │   again with new pitch         │  │
  │  │ • New LEDs = better coverage   │  │
  │  └─────────────────────────────────┘  │
  │                                        │
  ├─ NO ───────────────────────────────────┐
  │                                        │
  │  Use initial_mapping as-is            │
  │                                        │
  └─────────────────────────────────────────┘
         ↓
  ┌─────────────────────────────────────┐
  │ Analyze final mapping               │
  │ Calculate quality metrics           │
  │ Return complete result              │
  └─────────────────────────────────────┘
         ↓
       DONE
```

## Key Components

### `allocate_leds()` Method
The main entry point that orchestrates the cascade:

```python
# STEP 1: Generate initial mapping
initial_mapping, initial_max_led = self._generate_mapping(
    key_geometries, start_led, end_led
)

# STEP 2: Detect gap and calculate pitch adjustment
coverage_gap = end_led - initial_max_led
calibrated_pitch, was_adjusted, pitch_info = auto_calibrate_pitch(...)

# STEP 3: Regenerate if needed
if was_adjusted:
    self.analyzer.led_placement.led_spacing_mm = calibrated_pitch
    final_mapping, final_max_led = self._generate_mapping(
        key_geometries, start_led, end_led
    )
else:
    final_mapping = initial_mapping
```

### `_generate_mapping()` Helper Method
Encapsulates the complete mapping generation logic:

1. Calculate LED placements with **current pitch**
2. Build initial mapping by finding overlapping LEDs
3. Apply overhang filtering
4. Extend last key to full LED range
5. Return mapping and max_led_assigned

**Returns**: `(final_mapping, max_led_assigned)`

This makes the method reusable for both initial and regenerated passes.

## Pitch Adjustment Trigger

The pitch gets adjusted when:

```
Detected Coverage < Desired Coverage
            ↓
     Pitch Adjustment Calculated
            ↓
  Pitch Spacing Decreased (wider LEDs)
            ↓
   More LEDs Cover Piano Width
            ↓
     New Mapping Generated
            ↓
   Full Range Utilization Achieved
```

## Example Scenario

**Initial state**:
- LED density: 200 LEDs/meter
- LED spacing: 5mm
- Piano width: 1200mm
- Desired LEDs: 4-245 (242 LEDs)

**After initial mapping**:
- Max LED assigned: 242
- Coverage: 239 LEDs used
- Gap detected: 242 - 239 = 3 LEDs

**Pitch calculation**:
- Actual coverage: 239 LEDs
- Needed: 242 LEDs to span 1200mm
- Adjustment: Reduce pitch from 5mm to 4.95mm
- Result: `was_adjusted = True`

**After regeneration with new pitch**:
- Tighter LED spacing (4.95mm)
- More LEDs now overlap keys
- Max LED assigned: 245 (full range!)
- Mapping completely optimized

## Performance

✓ **Single pass for no-adjustment case**: O(n) complexity
✓ **Two passes for adjusted case**: One to detect, one to optimize
✓ **No redundant calculations**: Each pass uses current pitch
✓ **Caching-friendly**: Pitch updated once in analyzer

## Logging

Three levels of visibility:

```
INFO: STEP 1: Generating initial mapping to calculate coverage...
INFO: STEP 2: Analyzing coverage gap and calculating pitch adjustment...
INFO: Coverage gap: max_led=242, end_led=245, gap=3
INFO: Pitch adjusted: 5.0000mm → 4.9500mm (coverage adjustment)
INFO: STEP 3: Regenerating mapping with adjusted pitch...
INFO: New mapping coverage: max_led=245
DEBUG: Extended key 87 to reach end_led 245
```

## Files Modified

- **backend/services/physics_led_allocation.py**
  - Refactored `allocate_leds()` to implement cascade
  - Added `_generate_mapping()` helper method
  - Added comprehensive logging at each step

## Benefits

1. **Correct pitch used throughout**: Final mapping uses calibrated pitch
2. **No redundant work**: Single generation per pitch setting
3. **Transparent logic**: Three clear steps with logging
4. **Maintainable**: _generate_mapping() is reusable helper
5. **Debuggable**: Each step can be traced independently
6. **Optimal coverage**: Regeneration ensures full range utilization when adjusted

The cascade ensures the system finds and applies the optimal pitch adjustment, resulting in a mapping that utilizes the **full provided LED range** with the **best possible pitch spacing**.
