# Physics-Based Mode - Quick Reference

## Three Distribution Modes

### 1️⃣ Piano Based (with overlap)
- Fixed 5-6 LEDs per key
- LEDs shared at boundaries
- Smooth transitions
- Less per-key control

### 2️⃣ Piano Based (no overlap)  
- Fixed 3-4 LEDs per key
- No LED sharing
- Individual key control
- Limited transitions

### 3️⃣ Physics-Based LED Detection ⭐ NEW
- Adaptive, based on geometry
- Threshold-driven (0.5-3.0mm)
- Full quality metrics
- Best accuracy

---

## API: Switch Modes

```bash
# Physics-Based (strict threshold)
POST /api/calibration/distribution-mode
{
  "mode": "Physics-Based LED Detection",
  "overhang_threshold_mm": 1.0,
  "apply_mapping": true
}

# Physics-Based (relaxed threshold)
POST /api/calibration/distribution-mode
{
  "mode": "Physics-Based LED Detection",
  "overhang_threshold_mm": 2.0,
  "apply_mapping": true
}

# Back to Piano-Based
POST /api/calibration/distribution-mode
{
  "mode": "Piano Based (with overlap)",
  "apply_mapping": true
}
```

---

## Threshold Settings

| Threshold | LEDs/Key | Use Case |
|-----------|----------|----------|
| **0.5mm** | 2-3 | Very precise, minimal overhang |
| **1.0mm** | 2-3 | Strict quality control |
| **1.5mm** | 2-3 | Balanced (default) |
| **2.0mm** | 3-4 | More coverage, some overhang |
| **3.0mm** | 3-4 | Maximum coverage |

---

## Quality Metrics Explained

**Symmetry Score** (0-1)
- How centered LEDs are on key
- 1.0 = perfectly centered
- < 0.7 = off-center

**Coverage Amount** (mm)
- How much of exposed surface is covered
- Higher is better
- Target: 70-90% of key width

**Consistency Score** (0-1)
- How evenly LEDs are distributed
- 1.0 = perfectly even gaps
- < 0.7 = uneven distribution

**Overall Quality**
- Excellent (0.95-1.0 avg)
- Very Good (0.85-0.95 avg)
- Good (0.75-0.85 avg)
- Acceptable (0.65-0.75 avg)

---

## When to Use Each Mode

### Use Piano Based (with overlap) if:
- ✅ You want 5-6 LEDs per key
- ✅ You want smooth transitions
- ✅ You're using 200 LEDs/meter density
- ✅ Standard 88-key piano setup

### Use Piano Based (no overlap) if:
- ✅ You want fewer LEDs per key
- ✅ You want individual key control
- ✅ You prefer no LED sharing
- ✅ You have plenty of brightness per LED

### Use Physics-Based if:
- ✅ You want optimal alignment
- ✅ You have custom LED strip
- ✅ You want quality metrics
- ✅ You want adaptive allocation
- ✅ You're experimenting/tuning

---

## Key Differences

```
Piano Based:
  Algorithm: Fixed ratios
  LEDs/key: Always 5-6 or 3-4
  Tuning: Swap modes
  Metrics: None
  Result: Predictable

Physics-Based:
  Algorithm: Geometry-based
  LEDs/key: Adaptive (varies by key)
  Tuning: Threshold slider
  Metrics: Coverage, symmetry, quality
  Result: Optimized
```

---

## Implementation Files

- `backend/services/physics_led_allocation.py` - Service class
- `backend/config_led_mapping_physical.py` - Geometry engine
- `backend/api/calibration.py` - API endpoint

---

## Example Response

```json
{
  "distribution_mode": "Physics-Based LED Detection",
  "mapping_stats": {
    "total_keys_mapped": 88,
    "total_leds_used": 240,
    "avg_leds_per_key": 2.73
  },
  "quality_metrics": {
    "avg_symmetry": 0.85,
    "avg_coverage_consistency": 0.92,
    "overall_quality": "Very Good"
  }
}
```

---

## Next: UI Integration (Phase 3)

Frontend will add:
- ✅ Mode selector dropdown
- ✅ Threshold slider (0.5-3.0mm)
- ✅ Quality metrics display
- ✅ Per-key visualization
- ✅ Real-time preview

---

**Status:** ✅ Backend complete, ready for UI integration
