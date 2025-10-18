# LED Strip Weld Offset - Quick Start Guide

## TL;DR

When LED strips are soldered together, the connection point may have slight misalignment. Use **weld offsets** to compensate for these ~1-5mm deviations.

---

## 5-Minute Setup

### 1. Identify Your Welds
Count LED strip segments and find solder joints:
```
Strip 1: LEDs 0-99
Strip 2: LEDs 100-199  ← Weld here at LED 100
Strip 3: LEDs 200-254
```

### 2. Measure Offset
Check if LEDs after weld are shifted forward (+) or backward (-):
- **Forward 3.5mm** → offset: `+3.5`
- **Backward 1mm** → offset: `-1.0`
- **Perfect** → offset: `0` (or don't configure)

### 3. Apply Offset
```bash
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5}'
```

### 4. Test
Play keys on the piano - LEDs should now align properly!

---

## Common Scenarios

### Scenario 1: Single Weld
**Strip**: 255 LEDs soldered at position 100

```bash
# Add weld
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 2.0}'

# Verify
curl http://localhost:5001/api/calibration/weld/offsets
```

### Scenario 2: Multiple Welds
**Strip**: Three 100-LED segments joined at 100 and 200

```bash
# Configure both welds at once
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 2.5,
      "200": -1.0
    }
  }'
```

### Scenario 3: Adjusting Existing Weld
**Current**: Weld at 100 with +3.5mm offset  
**Want**: Change to +2.0mm

```bash
curl -X PUT http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 2.0}'
```

### Scenario 4: Remove Weld
**Current**: Weld at 150 configured  
**Want**: Delete it

```bash
# Option 1: Set offset to 0
curl -X POST http://localhost:5001/api/calibration/weld/offset/150 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 0}'

# Option 2: DELETE endpoint
curl -X DELETE http://localhost:5001/api/calibration/weld/offset/150
```

---

## Offset Values Quick Reference

| Observation | Offset Value | Action |
|---|---|---|
| LEDs look shifted forward | `+2.5` | Positive offset |
| LEDs look shifted backward | `-1.5` | Negative offset |
| LEDs look perfect | Don't add | No weld config needed |
| Not sure | Validate first | Use POST `/validate` |

---

## Validation Before Applying

```bash
# Test your config before saving
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.2
    }
  }'
```

Response shows:
- ✅ Valid/Invalid
- ⚠️ Any errors or warnings
- 📊 Statistics (count, ranges, etc.)

---

## API Reference (Quick)

### Get All Welds
```bash
curl http://localhost:5001/api/calibration/weld/offsets
```

### Get One Weld
```bash
curl http://localhost:5001/api/calibration/weld/offset/100
```

### Create/Update Weld
```bash
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5}'
```

### Delete Weld
```bash
curl -X DELETE http://localhost:5001/api/calibration/weld/offset/100
```

### Bulk Set
```bash
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{"weld_offsets": {"100": 2.5, "200": -1.0}}'
```

### Clear All
```bash
curl -X DELETE http://localhost:5001/api/calibration/weld/offsets
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| LED alignment unchanged | Ensure weld LED index is correct; check `/offsets` to verify |
| "Offset out of range" error | Use -10.0 to +10.0 mm only; split larger offsets |
| Welds not applied to USB MIDI | Welds apply automatically; check that distribution_mode is correct |
| Want to undo | DELETE the weld and recalibrate from scratch |

---

## Offset Limits

- **Range**: -10.0 to +10.0 mm (typical weld deviations)
- **Typical value**: ±2-3 mm
- **Too large**: Indicates mechanical misalignment (check hardware) or incorrect LED index

---

## Files Changed

- ✅ `backend/services/settings_service.py` - Settings schema
- ✅ `backend/config.py` - LED mapping logic
- ✅ `backend/api/calibration_weld_offsets.py` - REST endpoints (NEW)
- ✅ `backend/app.py` - Blueprint registration

---

## Next Steps

1. **Test on hardware**: Apply weld offset and verify LED alignment
2. **Fine-tune**: Adjust offset values until perfect
3. **Document**: Note weld locations for future reference
4. **Export**: Backup settings for recovery
5. **Automate**: Consider frontend UI for weld management

---

## For More Details

See: `WELD_OFFSET_FEATURE_GUIDE.md` for comprehensive documentation

---

## Examples with cURL

### Complete Workflow

```bash
# 1. Check current welds
echo "=== Current welds ==="
curl http://localhost:5001/api/calibration/weld/offsets | jq

# 2. Validate new config
echo "=== Validating new welds ==="
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.0
    }
  }' | jq

# 3. Apply welds
echo "=== Applying welds ==="
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.0
    }
  }' | jq

# 4. Verify
echo "=== Verification ==="
curl http://localhost:5001/api/calibration/weld/offsets | jq

# 5. Test first key
echo "=== Testing key mapping ==="
curl http://localhost:5001/api/calibration/key-led-mapping | jq '.mapping."21"'
```

---

## Success Checklist

- [ ] Identified weld locations (LED indices)
- [ ] Measured offset values (mm)
- [ ] Validated configuration with POST `/validate`
- [ ] Applied welds with PUT `/offsets/bulk`
- [ ] Verified welds saved: GET `/offsets`
- [ ] Tested LED alignment on piano keys
- [ ] Adjusted offsets if needed
- [ ] All LEDs aligned correctly ✅

You're done!
