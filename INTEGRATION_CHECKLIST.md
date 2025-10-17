# Integration Points: Your piano.py with Current System

## Quick Reference

### What to Extract from piano.py

```python
# COPY THESE FUNCTIONS AS-IS OR WITH MINIMAL CHANGES:

1. calculate_all_key_geometries()
   - Returns exact 88-key geometry with cuts
   - Input: optionalwhite_key_width, black_key_width, white_key_gap
   - Output: List[Dict] with start/end/exposed positions

2. analyze_led_placement_on_top()
   - Detects LEDs overlapping each key
   - Input: key_geometry, led_spacing, led_width, led_offset, threshold
   - Output: List[Dict] with LED indices and positions

3. perform_symmetry_analysis()
   - Scores alignment quality
   - Input: key_geometry, led_analysis result
   - Output: {classification, details}

# ADAPT THESE:

4. run_full_strip_analysis() 
   → becomes analyze_full_mapping() for API endpoint
   - Iterate all keys and generate analysis
   - Return structured results instead of print statements
```

### What Your piano.py Constants Map To

```python
# Your Constant             → Our Setting
LED_DENSITY = 200          → led.leds_per_meter (already in DB)
LED_SPACING = 5.0mm        → calculated from leds_per_meter (5000/200)
DEFAULT_LED_PHYSICAL_WIDTH → calibration.led_physical_width (NEW)
DEFAULT_LED_STRIP_OFFSET   → calibration.led_strip_offset (NEW)
DEFAULT_LED_OVERHANG_THRESHOLD → calibration.led_overhang_threshold (NEW)

WHITE_KEY_WIDTH = 23.5     → piano.white_key_width (NEW)
BLACK_KEY_WIDTH = 13.7     → piano.black_key_width (NEW)
WHITE_KEY_GAP = 1.0        → piano.white_key_gap (NEW)
```

## Current System Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Backend Service Start                      │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────▼──────────┐
        │  Load Settings DB │
        │ (GPIO, LED count) │
        └────────┬──────────┘
                 │
        ┌────────▼─────────────────────┐
        │ config_led_mapping_advanced  │
        │ .generate_key_led_mapping()  │
        └────────┬─────────────────────┘
                 │
        ┌────────▼──────────────────┐
        │ Return key_led_mapping:   │
        │ {0: [4,5,6,7],           │
        │  1: [8,9,10],            │
        │  ...                     │
        │  87: [248,249]}          │
        └────────┬──────────────────┘
                 │
   API: /key-led-mapping (returns above)
```

## Proposed Addition: Physical Analysis Layer

```
┌──────────────────────────────────────────────────────────────┐
│           YOUR PHYSICAL ANALYSIS MODULE (NEW)                │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Input: key_led_mapping from current system             ││
│  │        Settings: LED width, offset, threshold          ││
│  └──────────────────┬──────────────────────────────────────┘│
│                     │                                        │
│  ┌──────────────────▼──────────────────────────────────────┐│
│  │ 1. Calculate exact key geometry                        ││
│  │    (your calculate_all_key_geometries)                 ││
│  └──────────────────┬──────────────────────────────────────┘│
│                     │                                        │
│  ┌──────────────────▼──────────────────────────────────────┐│
│  │ 2. For each key:                                        ││
│  │    - Get key geometry                                   ││
│  │    - Get assigned LEDs from current mapping            ││
│  │    - Analyze physical placement                        ││
│  │    - Calculate symmetry score                          ││
│  └──────────────────┬──────────────────────────────────────┘│
│                     │                                        │
│  ┌──────────────────▼──────────────────────────────────────┐│
│  │ Output: Enhanced mapping with quality metrics          ││
│  │ {                                                      ││
│  │   "mapping": current key_led_mapping,                 ││
│  │   "physical_analysis": {                              ││
│  │     0: {                                               ││
│  │       "leds": [4,5,6,7],                              ││
│  │       "symmetry": "Excellent",                         ││
│  │       "score": 0.95                                    ││
│  │     },                                                 ││
│  │     ...                                                ││
│  │   },                                                   ││
│  │   "quality_metrics": {                                 ││
│  │     "avg_symmetry": 0.92,                              ││
│  │     "problem_keys": [],                                ││
│  │     "overall_quality": "Excellent"                     ││
│  │   }                                                    ││
│  │ }                                                      ││
│  └──────────────────┬──────────────────────────────────────┘│
└─────────────────────┼──────────────────────────────────────┘
                      │
   New API: /physical-analysis (returns enhanced data)
   Enhanced API: /mapping-quality (includes physical data)
```

## Database Schema Changes

### Current Settings (Existing)
```sql
-- Already in settings table:
led.leds_per_meter = 200
led.led_count = 255
led.enabled = true
led.gpio_pin = 19
led.led_channel = 1
-- etc.
```

### New Settings to Add
```sql
-- Piano geometry
INSERT INTO settings (category, key, value, data_type) VALUES
('piano', 'white_key_width', '23.5', 'number'),
('piano', 'black_key_width', '13.7', 'number'),
('piano', 'white_key_gap', '1.0', 'number');

-- LED physical properties
INSERT INTO settings (category, key, value, data_type) VALUES
('calibration', 'use_physical_geometry', 'true', 'boolean'),
('calibration', 'led_physical_width', '3.5', 'number'),
('calibration', 'led_strip_offset', '1.75', 'number'),
('calibration', 'led_overhang_threshold', '1.5', 'number'),
('calibration', 'symmetry_tolerance', '0.8', 'number');
```

## Code Integration Checklist

### File: backend/config_led_mapping_physical.py (NEW)
```
☐ Copy piano.py functions:
  ☐ KEY_MAP = [...]  (or calculate from 88 keys)
  ☐ WHITE_KEY_CUTS = {...}
  ☐ CUT_VALUES = {...}
  ☐ calculate_all_key_geometries()
  ☐ analyze_led_placement_on_top()
  ☐ perform_symmetry_analysis()

☐ Create new integration function:
  ☐ generate_physical_mapping_analysis(key_led_mapping, settings)
     Returns enhanced mapping with quality scores

☐ No breaking changes - add functions, don't modify anything
```

### File: backend/schemas/settings_schema.py
```
☐ Add 'piano' category with properties:
  ☐ white_key_width
  ☐ black_key_width
  ☐ white_key_gap

☐ Add 'calibration' category with properties:
  ☐ use_physical_geometry
  ☐ led_physical_width
  ☐ led_strip_offset
  ☐ led_overhang_threshold
  ☐ symmetry_tolerance
```

### File: backend/services/settings_service.py
```
☐ Update _get_default_settings_schema() to include new defaults
☐ Ensure auto-initialization on first run
```

### File: backend/api/calibration.py
```
☐ Add new endpoint: GET /physical-analysis
  ☐ Get current key_led_mapping
  ☐ Get settings for piano geometry
  ☐ Call generate_physical_mapping_analysis()
  ☐ Return JSON response

☐ Enhance endpoint: GET /mapping-quality
  ☐ Optionally include physical_analysis data
  ☐ Add 'use_physical_geometry' check
```

### File: backend/app.py
```
☐ On startup: call ensure_all_settings_initialized()
  ☐ Populates new settings with defaults if missing
```

## API Responses After Integration

### GET /api/calibration/physical-analysis
```json
{
  "timestamp": "2025-10-17T14:05:00",
  "mapping": {
    "0": [4, 5, 6, 7],
    "1": [8, 9, 10],
    ...
  },
  "physical_analysis": {
    "0": {
      "key_name": "A0",
      "type": "White",
      "exposed_start_mm": 0.0,
      "exposed_end_mm": 23.5,
      "assigned_leds": [4, 5, 6, 7],
      "symmetry_classification": "Excellent Center Alignment",
      "symmetry_score": 0.95,
      "placement_quality": "Optimal",
      "center_alignment_mm": 0.2,
      "left_edge_mm": 1.5,
      "right_edge_mm": 1.3
    },
    "1": {...},
    ...
    "87": {...}
  },
  "quality_metrics": {
    "total_keys": 88,
    "keys_analyzed": 88,
    "avg_symmetry_score": 0.92,
    "keys_excellent": 52,
    "keys_good": 28,
    "keys_fair": 8,
    "keys_poor": 0,
    "detected_gaps": [],
    "high_asymmetry_keys": [15, 42],
    "overall_quality": "Excellent",
    "overall_score": 0.91
  }
}
```

### GET /api/calibration/mapping-quality (Enhanced)
```json
{
  "allow_led_sharing": false,
  "distribution_mode": "Piano Based (no overlap)",
  "key_count": 88,
  "led_coverage_percent": 100,
  "avg_leds_per_key": 2.8,
  "total_leds_assigned": 246,
  
  "physical_analysis_enabled": true,
  "physical_analysis": {
    "avg_symmetry": 0.92,
    "quality_classification": "Excellent",
    "problem_keys": []
  }
}
```

## Testing Checklist

### Unit Tests
```
☐ test_calculate_all_key_geometries()
  ☐ Verify key 0 at correct position
  ☐ Verify key 87 at correct position
  ☐ Verify white key widths
  ☐ Verify black key positions

☐ test_analyze_led_placement_on_top()
  ☐ Test various LED positions
  ☐ Test threshold edge cases
  ☐ Test gap detection

☐ test_perform_symmetry_analysis()
  ☐ Test perfect center alignment
  ☐ Test symmetrical edge placement
  ☐ Test asymmetrical cases
```

### Integration Tests
```
☐ test_physical_analysis_endpoint()
  ☐ Call /physical-analysis
  ☐ Verify response format
  ☐ Verify all keys analyzed
  ☐ Verify scores between 0-1

☐ test_settings_persistence()
  ☐ Verify settings in DB
  ☐ Get via API
  ☐ Update via API
  ☐ Verify changes reflected

☐ test_backward_compatibility()
  ☐ Old endpoints still work
  ☐ No breaking changes
  ☐ Current mapping unchanged
```

### Manual Testing
```
☐ Start service
✓ Check logs for settings initialization
✓ Call /api/calibration/physical-analysis
✓ Verify response has all keys
✓ Check symmetry scores make sense
✓ Update a setting via API
✓ Re-call endpoint, verify change reflected
✓ Test with different LED spacings
```

## Success Criteria

✅ All 88 keys have physical analysis
✅ Symmetry scores between 0 and 1
✅ API returns within 1 second
✅ Settings persist correctly
✅ No breaking changes to existing endpoints
✅ Current mapping unchanged
✅ Gap detection works
✅ Quality scores make sense

## Deployment Checklist

```
Pre-Deployment:
☐ All tests passing
☐ Settings schema valid
☐ Database migration ready
☐ API responses match spec

Deployment:
☐ Backup database
☐ Deploy new code
☐ Run settings initialization
☐ Verify API endpoints
☐ Check logs for errors
☐ Test via curl/Postman

Post-Deployment:
☐ Monitor service logs
☐ Verify physical-analysis works
☐ Check performance impact
☐ Confirm mapping unchanged
```

## Performance Notes

- **Key geometry calculation**: ~5ms (cached, called once per settings change)
- **LED placement analysis**: ~50ms (per key, ~4.4s for all 88)
- **Symmetry analysis**: ~1ms per key, negligible
- **Total API response**: ~5-6 seconds first call, cached after

**Optimization options** (Phase 2):
- Cache key geometries (already at startup)
- Cache LED analysis results
- Lazy-load per-key details
- Return summary endpoint for quick checks
