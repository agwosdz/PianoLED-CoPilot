# Quick Reference: Piano LED Script Integration

## TL;DR

Your `piano.py` is **excellent** and could be integrated in 3 ways:

| Phase | What | Time | Risk | Benefit |
|-------|------|------|------|---------|
| **1** | Add geometry + symmetry feedback layer | 1-2d | Low | See mapping quality scores per key |
| **2** | Replace algorithm with physical-based | 1-2w | Med | Better accuracy (possibly) |
| **3** | UI visualization + recommendations | 3-5w | Low | Excellent UX for tuning |

**Recommendation**: Start Phase 1 → Test → Decide on Phase 2

---

## Phase 1: Extract & Add to Feedback (Recommended)

### What Gets Added
```
New file: backend/config_led_mapping_physical.py
New endpoint: GET /api/calibration/physical-analysis
New settings: piano geometry, LED physical properties
Enhanced endpoint: /mapping-quality includes symmetry data
```

### Example Response
```json
{
  "mapping": {0: [4,5,6,7], 1: [8,9,10], ...},
  "physical_analysis": {
    "0": {
      "symmetry": "Excellent Center Alignment",
      "symmetry_score": 0.95,
      "alignment_notes": "Perfect centering on key"
    },
    "1": {...},
    ...
  },
  "quality_metrics": {
    "avg_symmetry": 0.92,
    "overall_quality": "Excellent"
  }
}
```

### Settings to Add (Optional, Advanced Tab)
- Piano: white_key_width (23.5mm), black_key_width (13.7mm), white_key_gap (1.0mm)
- LED Physical: width (3.5mm), offset (1.75mm), threshold (1.5mm)

### Code Changes
```python
# New file: backend/config_led_mapping_physical.py
- Copy calculate_all_key_geometries() from piano.py
- Copy analyze_led_placement_on_top() from piano.py  
- Copy perform_symmetry_analysis() from piano.py
- Add: generate_physical_mapping_analysis() integration function

# Modify: backend/api/calibration.py
+ Add endpoint: GET /physical-analysis
~ Enhance: /mapping-quality with physical_analysis data

# Modify: backend/schemas/settings_schema.py
+ Add category: 'piano' with keys
+ Add category: 'calibration' with keys

# Modify: backend/services/settings_service.py
~ Update defaults to include new settings
```

### Risk Level: **LOW**
- ✅ Doesn't change current mapping
- ✅ Backward compatible
- ✅ Can be disabled via feature flag
- ✅ Isolated module

### Time: **1-2 days**
- Extract functions: 2-3 hours
- Integrate into API: 2-3 hours
- Add settings: 1 hour
- Testing: 2-3 hours
- Documentation: 1 hour

---

## Phase 2: Replace Algorithm (Later)

### What Changes
```
Replace: config_led_mapping_advanced.py allocation logic
With: Physical-based LED detection from piano.py
Result: Potentially better accuracy
```

### Risk Level: **MEDIUM**
- ⚠️ Changes mapping algorithm
- ⚠️ Needs extensive testing
- ⚠️ Could produce different results (possibly better/worse)
- ✅ Can be feature-flagged for A/B testing

### Time: **1-2 weeks**
- Implement physical allocation: 3-4 days
- Testing: 3-4 days  
- Validation: 2-3 days
- Documentation: 1 day

---

## Phase 3: UI & Recommendations (Future)

### What Gets Added
```
Frontend visualization of LED placement
Per-key alignment quality display  
Recommendation engine: "Adjust offset by +2mm"
Manual calibration tuning interface
```

### Risk Level: **LOW** (after Phase 1-2)
- ✅ Frontend only
- ✅ Uses data from Phase 1-2
- ✅ No backend logic changes

### Time: **3-5 weeks**
- UI components: 2-3 weeks
- Integration: 1 week
- Polish: 1 week

---

## Parameters Your Script Uses vs What We Have

### Parameters YOU Use
```python
LED_DENSITY = 200                    # LEDs per meter
LED_SPACING = 1000/LED_DENSITY       # 5mm per LED
DEFAULT_LED_PHYSICAL_WIDTH = 3.5     # mm
DEFAULT_LED_STRIP_OFFSET = 1.75      # mm (half width)
DEFAULT_LED_OVERHANG_THRESHOLD = 1.5 # mm

WHITE_KEY_WIDTH = 23.5               # mm
BLACK_KEY_WIDTH = 13.7               # mm
WHITE_KEY_GAP = 1.0                  # mm
```

### Parameters We Have (✓ Already in settings.db)
```
✓ led.leds_per_meter = 200
✓ led.led_count = 255
✓ led.enabled = true
✓ led.gpio_pin = 19
✓ led.led_channel = 1
✓ calibration.start_led = 4
✓ calibration.end_led = 249
```

### Parameters We Need to Add (Optional)
```
~ piano.white_key_width = 23.5           (NEW)
~ piano.black_key_width = 13.7           (NEW)
~ piano.white_key_gap = 1.0              (NEW)
~ calibration.led_physical_width = 3.5   (NEW)
~ calibration.led_strip_offset = 1.75    (NEW)
~ calibration.led_overhang_threshold = 1.5 (NEW)
```

---

## Decision Matrix

**Choose Phase 1 if:**
- ✓ Want to see mapping quality feedback
- ✓ Want user-accessible parameters
- ✓ Want low-risk improvement
- ✓ Want foundation for Phase 2

**Choose Phase 2 if:**
- ✓ Phase 1 validation looks good
- ✓ Current algorithm not working well
- ✓ Physical accuracy matters more than speed
- ✓ Ready to test thoroughly

**Skip Integration if:**
- ✗ Current system working great
- ✗ No need for detailed quality feedback
- ✗ Time constraints
- ✗ Want to keep piano.py as standalone tool

---

## Implementation Priority If Phase 1 Approved

**Day 1:**
1. Create backend/config_led_mapping_physical.py
2. Extract functions from piano.py
3. Add integration function
4. Write unit tests

**Day 2:**
1. Add settings schema + defaults
2. Create new API endpoint
3. Integration testing
4. Documentation

---

## What Happens After Integration

### Phase 1 (Feedback Layer)
- Users can see per-key symmetry scores
- Can adjust physical parameters via API
- Better visibility into mapping quality
- No change to actual LED control

### Phase 2 (New Algorithm - Future)
- Possibly better accuracy
- Physical overlap detection replaces simple math
- More intelligent LED assignment
- Needs validation first

### Phase 3 (UX - Future)
- Frontend shows visual representation
- User can calibrate interactively
- Recommendations guide tuning
- Much better user experience

---

## API Summary (Phase 1)

### New Endpoint
```
GET /api/calibration/physical-analysis
  → Returns all 88 keys with symmetry scores and placement quality
  → ~5s first call (5ms per key + overhead)
  → Cached after calculation
```

### Enhanced Endpoint
```
GET /api/calibration/mapping-quality (existing)
  → Now includes: physical_analysis data
  → Backward compatible
  → Optional physical analysis section
```

### New Settings Categories
```
GET /api/settings/piano
  → white_key_width, black_key_width, white_key_gap

GET /api/settings/calibration
  → led_physical_width, led_strip_offset, led_overhang_threshold
  → use_physical_geometry (enable/disable)
```

---

## Questions to Answer Before Starting

1. **Phase preference?** (1, 2, both eventually, or skip)
2. **User-adjustable parameters?** (Expose all 6 new settings to users?)
3. **Performance ok?** (5-6s for physical analysis acceptable?)
4. **When needed?** (Immediately, after current work, or future?)

---

## Documents to Read

1. **`INTEGRATION_SUMMARY.md`** - Executive summary
2. **`PIANO_LED_SCRIPT_INTEGRATION_ANALYSIS.md`** - Detailed comparison
3. **`PHASE1_IMPLEMENTATION_PLAN.md`** - Step-by-step
4. **`INTEGRATION_CHECKLIST.md`** - Code changes checklist

---

**Your script is sophisticated and well-designed. Integration would be valuable!** 🎯
