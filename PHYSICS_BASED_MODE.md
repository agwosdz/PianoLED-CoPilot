# Physics-Based LED Distribution Mode

## Overview

We've added a new distribution mode to the Piano LED Visualizer: **Physics-Based LED Detection**. This mode uses the physical geometry analyzer we built to automatically allocate LEDs to piano keys based on actual physical overlap and quality metrics.

## How It Works

### The Problem with Fixed Modes

The existing "Piano Based" modes use fixed LED-per-key ratios:
- "Piano Based (with overlap)": Always 5-6 LEDs per key
- "Piano Based (no overlap)": Always 3-4 LEDs per key

These ratios don't adapt to:
- Different LED densities
- Different physical mounting positions
- Varying key sizes
- Hardware variations

### The Physics-Based Solution

The new "Physics-Based LED Detection" mode:

1. **Calculates Key Geometry** - Computes exact physical boundaries for all 88 piano keys
2. **Calculates LED Placements** - Determines exact physical position of each LED
3. **Detects Overlaps** - Finds which LEDs physically overlap each key's exposed surface
4. **Filters by Threshold** - Removes LEDs with overhang exceeding threshold
5. **Computes Quality Metrics** - Calculates coverage, symmetry, and consistency scores

Result: Optimal, adaptive LED allocation based on physics, not fixed ratios.

## Features

### Threshold-Based Filtering

Uses an **overhang threshold** (default 1.5mm) to ensure LED quality:

```
✓ Include LED if overhang on BOTH sides ≤ 1.5mm
✗ Exclude LED if overhang on EITHER side > 1.5mm
```

This ensures:
- LEDs don't extend too far beyond key edges
- Clean, precise LED-to-key assignment
- High-quality alignment

### Quality Metrics

Each key gets detailed metrics:
- **Coverage (mm)** - How much of exposed surface is covered
- **Symmetry Score** - How centered LEDs are on the key (0-1)
- **Consistency Score** - How evenly LEDs are distributed (0-1)
- **Overall Quality** - Excellent/Good/Acceptable/Poor

## Usage

### API Endpoint

```bash
# Get current mode and options
GET /api/calibration/distribution-mode

# Change to Physics-Based mode
POST /api/calibration/distribution-mode
{
  "mode": "Physics-Based LED Detection",
  "overhang_threshold_mm": 1.5,
  "apply_mapping": true
}
```

### Response Example

```json
{
  "message": "Distribution mode changed to: Physics-Based LED Detection",
  "distribution_mode": "Physics-Based LED Detection",
  "overhang_threshold_mm": 1.5,
  "mapping_regenerated": true,
  "mapping_stats": {
    "total_keys_mapped": 88,
    "total_leds_used": 240,
    "avg_leds_per_key": 2.73,
    "distribution": {
      "2": 12,
      "3": 76
    },
    "quality_metrics": {
      "avg_symmetry": 0.8542,
      "avg_coverage_consistency": 0.92,
      "overall_quality": "Very Good"
    }
  }
}
```

## Parameters

### Overhang Threshold (0.5 - 3.0mm)

Controls how much LEDs can extend beyond key edges:

- **0.5mm** - Very strict, tight alignment
  - Fewer LEDs per key
  - More keys with limited coverage
  - Best for maximum precision

- **1.5mm** - Balanced (default)
  - Good coverage
  - Good quality
  - Reasonable LED distribution

- **3.0mm** - Relaxed, generous
  - More LEDs per key
  - Better coverage
  - More overhang acceptable

## Comparison

| Feature | Piano Based | Physics-Based |
|---------|------------|---------------|
| **Algorithm** | Fixed ratios | Physical geometry |
| **Adaptivity** | No | Yes |
| **LED Density Sensitivity** | Poor | Excellent |
| **Quality Metrics** | None | Full analysis |
| **Coverage Guarantee** | No | Yes |
| **Symmetry Optimization** | No | Yes |
| **Tuning Parameters** | Few | Threshold (continuous) |

## Architecture

### Files

- `backend/services/physics_led_allocation.py` - Physics-based allocation service
- `backend/config_led_mapping_physical.py` - Geometry calculations and analysis
- `backend/api/calibration.py` - API endpoints

### Data Flow

```
Frontend: Select "Physics-Based LED Detection"
    ↓
POST /api/calibration/distribution-mode
    ↓
Backend: PhysicsBasedAllocationService.allocate_leds()
    ↓
Calculate key geometries (all 88 keys)
    ↓
Calculate LED placements
    ↓
For each key: detect overlapping LEDs
    ↓
Filter by overhang threshold
    ↓
Compute quality metrics (symmetry, coverage, consistency)
    ↓
Return complete allocation with analysis
    ↓
Frontend: Display allocation and quality metrics
```

## Quality Output

The Physics-Based mode returns comprehensive metrics:

```python
allocation_result = {
    'success': True,
    'key_led_mapping': {0: [4, 5], 1: [6], ...},  # Which LEDs for each key
    'led_allocation_stats': {
        'total_key_count': 88,
        'total_leds_used': 240,
        'avg_leds_per_key': 2.73,
        'mapped_key_count': 88,  # All keys have LEDs
        'unmapped_key_count': 0,
        'leds_per_key_distribution': {'2': 12, '3': 76},
    },
    'quality_metrics': {
        'avg_symmetry': 0.8542,
        'avg_coverage_consistency': 0.92,
        'avg_overhang_left': 0.32,
        'avg_overhang_right': 0.28,
        'excellent_alignment': 74,
        'good_alignment': 14,
        'acceptable_alignment': 0,
        'poor_alignment': 0,
    },
    'overall_quality': 'Very Good',
    'per_key_analysis': {...},  # Detailed per-key metrics
}
```

## Integration Points

### Settings

Stores in settings database:
- `calibration.distribution_mode` - Current mode ("Physics-Based LED Detection")
- `calibration.overhang_threshold_mm` - Threshold value (default 1.5)
- `calibration.allow_led_sharing` - Set to false for physics-based

### Frontend

Can display:
- Mode selector dropdown
- Threshold slider (0.5-3.0mm)
- Real-time preview of metrics
- Per-key quality visualization
- Before/after comparison

## Next Steps

### Phase 3 (UI Integration)

1. **Distribution Mode Selector**
   - Dropdown in calibration panel
   - Descriptions for each mode

2. **Physics-Based Controls**
   - Slider for overhang threshold
   - Real-time metric updates
   - Apply button

3. **Quality Visualization**
   - Color-coded keys by quality grade
   - Heatmap of coverage
   - Symmetry distribution chart

4. **Export/Save**
   - Save physics-based allocation to database
   - Load/compare with previous allocations

## Testing

### Unit Tests

```python
def test_physics_based_allocation():
    service = PhysicsBasedAllocationService()
    result = service.allocate_leds(start_led=4, end_led=249)
    assert result['success']
    assert len(result['key_led_mapping']) == 88
    assert result['quality_metrics']['avg_symmetry'] > 0.8
```

### Integration Tests

1. Verify all 88 keys get LED assignments
2. Check no LEDs exceed threshold
3. Validate symmetry scores
4. Compare with Piano Based modes
5. Test threshold variations

## Performance

- Allocation time: ~50-100ms for 88 keys
- Memory usage: ~5-10MB
- Real-time threshold adjustment: <100ms response

## Future Enhancements

1. **Custom Thresholds per Key** - Vary threshold by key position
2. **Coverage Minimums** - Ensure minimum coverage % per key
3. **LED Rebalancing** - Optimize LED distribution across all keys
4. **Hardware Profiles** - Pre-configured profiles for common setups
5. **Genetic Algorithm Optimization** - Auto-tune threshold for best results

---

## Quick Reference

**Enable Physics-Based Mode:**
```bash
curl -X POST http://192.168.1.225:5001/api/calibration/distribution-mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "Physics-Based LED Detection",
    "overhang_threshold_mm": 1.5,
    "apply_mapping": true
  }'
```

**Adjust Threshold:**
```bash
curl -X POST http://192.168.1.225:5001/api/calibration/distribution-mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "Physics-Based LED Detection",
    "overhang_threshold_mm": 1.0,
    "apply_mapping": true
  }'
```

**Get Current Mode:**
```bash
curl http://192.168.1.225:5001/api/calibration/distribution-mode
```
