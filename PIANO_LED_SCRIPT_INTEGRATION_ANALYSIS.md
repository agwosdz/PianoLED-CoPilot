# Piano LED Mapping Script Integration Analysis

## Overview

Your `piano.py` script is an **advanced, geometry-based LED placement analyzer** that takes a fundamentally different approach than our current position-based system. It models the physical piano keyboard geometry and determines LED placement based on actual physical overlap.

## Current vs. Your Approach

### Current System (config_led_mapping_advanced.py)
- **Model**: Position-based allocation
- **Calculation**: Maps piano width (1273mm) to LED range (4-249)
- **Allocation**: Uses floor division to assign LED indices to key ranges
- **Result**: Simple mapping - each LED assigned to exactly one key
- **Validation**: Coverage %, overlap detection
- **Settings**: `start_led`, `end_led`, `led_count`, `leds_per_meter`

### Your System (piano.py)
- **Model**: Physical geometry-based
- **Calculation**: Exact white/black key dimensions with cuts + LED physical width
- **Allocation**: Detects which LEDs physically overlap each key within threshold
- **Result**: Complex mapping - per-key analysis with quality metrics
- **Validation**: Symmetry scoring, gap detection, neighbor interaction
- **Settings**: 7+ parameters including LED width, overhang, key dimensions

## Your Script's Capabilities

```
Key Features:
✓ Exact piano key geometry (white/black keys with cuts)
✓ Physical LED width consideration (3.5mm default)
✓ Overhang threshold (realistic placement tolerance)
✓ Symmetry classification (centered, symmetrical, asymmetrical)
✓ Gap detection (consecutive coverage analysis)
✓ Neighbor interaction analysis (LED sharing detection)
✓ Per-key quality scoring
✓ Configurable parameters for fine-tuning
```

## Integration Roadmap

### Phase 1: Hybrid Approach (Recommended) - **LOW RISK**

**Goal**: Keep current working system, enhance with physical geometry

```
1. Create new mapping engine: `config_led_mapping_physical.py`
   - Extract calculate_all_key_geometries() from your script
   - Use current system's LED allocation logic
   - Add symmetry_analysis for quality feedback
   - Keep backward compatible with current output format

2. Add new settings for physical parameters (optional):
   - piano.white_key_width: 23.5 (mm)
   - piano.black_key_width: 13.7 (mm)
   - piano.white_key_gap: 1.0 (mm)
   - led.physical_width: 3.5 (mm)
   - led.strip_offset: 1.75 (mm) - half of physical width
   - led.overhang_threshold: 1.5 (mm)

3. Enhance quality endpoint:
   - Add symmetry classification for each key
   - Return per-key alignment quality
   - Identify problem areas (gaps, high asymmetry)
```

### Phase 2: Full Integration (Higher Effort) - **MEDIUM RISK**

**Goal**: Replace allocation with physical-based detection

```
1. Rewrite no-overlap algorithm to use analyze_led_placement_on_top():
   - For each key, find LEDs that physically overlap
   - Respect overhang threshold
   - First-come-first-served assignment
   - May produce different (possibly better) results

2. Add with-overlap variant:
   - Allow all physical overlaps
   - Calculate % overlap per LED
   - Weight LED brightness by overlap %

3. New endpoint: /api/calibration/physical-analysis
   - Returns detailed per-key placement analysis
   - Symmetry scores
   - Gap warnings
   - Neighbor sharing info
```

### Phase 3: Advanced Features (Later) - **FUTURE**

```
1. UI visualization:
   - Show exact key geometry
   - Highlight LED placement
   - Overlay symmetry zones

2. Recommendations engine:
   - "LED 5 is off-center by 0.8mm, consider offset adjustment"
   - "Keys 15-20 have LED gaps"

3. Calibration wizard:
   - Guided physical measurement
   - Auto-adjust strip offset based on measurements
```

## Database Schema Changes Needed

### Add to `settings` table (Optional Advanced Settings)

```sql
-- Piano geometry parameters
INSERT INTO settings (category, key, value, data_type) VALUES
('piano', 'white_key_width', '23.5', 'number'),
('piano', 'black_key_width', '13.7', 'number'),
('piano', 'white_key_gap', '1.0', 'number');

-- LED physical parameters
INSERT INTO settings (category, key, value, data_type) VALUES
('led', 'physical_width', '3.5', 'number'),
('led', 'strip_offset', '1.75', 'number'),
('led', 'overhang_threshold', '1.5', 'number');

-- Mapping quality metrics
INSERT INTO settings (category, key, value, data_type) VALUES
('calibration', 'use_physical_geometry', 'true', 'boolean'),
('calibration', 'symmetry_tolerance', '0.8', 'number');
```

### Update settings_schema.py

```python
'piano': {
    'type': 'object',
    'properties': {
        'white_key_width': {'type': 'number', 'minimum': 20, 'maximum': 30},
        'black_key_width': {'type': 'number', 'minimum': 10, 'maximum': 20},
        'white_key_gap': {'type': 'number', 'minimum': 0.5, 'maximum': 2.0},
    }
},

'led': {
    'type': 'object',
    'properties': {
        # ... existing ...
        'physical_width': {'type': 'number', 'minimum': 2, 'maximum': 6},
        'strip_offset': {'type': 'number', 'minimum': 0.5, 'maximum': 5},
        'overhang_threshold': {'type': 'number', 'minimum': 0.5, 'maximum': 3},
    }
},

'calibration': {
    'type': 'object',
    'properties': {
        'use_physical_geometry': {'type': 'boolean'},
        'symmetry_tolerance': {'type': 'number', 'minimum': 0.1, 'maximum': 2},
    }
}
```

## Code Integration Points

### Current System Architecture
```
backend/config_led_mapping_advanced.py
├── generate_key_led_mapping()
│   ├── calculate_piano_geometry (SIMPLE - just width/88)
│   ├── allocate_leds_with_sharing (with-overlap mode)
│   └── allocate_leds_no_sharing (no-overlap mode)
└── calculate_mapping_statistics()

backend/api/calibration.py
├── /key-led-mapping (GET) - returns mapping
├── /mapping-quality (GET) - returns quality metrics
└── /regenerate-mapping (POST) - regenerates mapping
```

### Proposed Addition
```
backend/config_led_mapping_physical.py (NEW)
├── calculate_all_key_geometries()
│   └── Exact white/black key positions with cuts
├── analyze_led_placement_on_top()
│   └── Physical overlap detection
├── perform_symmetry_analysis()
│   └── Quality scoring
└── generate_physical_key_led_mapping()
    └── Integration point with current system

backend/api/calibration.py (ENHANCED)
├── /physical-analysis (GET) - new endpoint
├── /mapping-quality (ENHANCED) - add symmetry data
└── /api/settings/piano (GET/PUT) - new category
```

## Effort Estimates

| Phase | Tasks | Effort | Risk | Benefit |
|-------|-------|--------|------|---------|
| **Phase 1** | Extract geometry + add quality metrics | 4-6 hours | Low | 15% improvement in feedback |
| **Phase 2** | Replace allocation algorithm | 8-12 hours | Medium | 30-50% better precision |
| **Phase 3** | UI + recommendations | 20+ hours | Medium | Excellent UX |

## Recommendation

**Start with Phase 1 (Hybrid Approach)**:

1. ✅ Low risk - current system stays operational
2. ✅ Immediate benefit - better quality feedback
3. ✅ Foundation for Phase 2
4. ✅ Optional parameters - can be exposed later

**Timeline**: 1-2 day implementation, thoroughly tested

**Benefits**:
- Your advanced geometry model available
- Per-key symmetry scores
- Gap detection and warnings
- Foundation for future physical-based allocation
- User-adjustable parameters for fine-tuning

## Next Steps

Would you like me to:
1. **Create Phase 1 implementation** - Extract your key geometry into our system
2. **Add settings schema** - Define the new advanced parameters
3. **Create new API endpoint** - `/physical-analysis` with symmetry data
4. **Both** - Do all of the above

Your script is excellent - this integration would significantly improve mapping accuracy! 🎯
