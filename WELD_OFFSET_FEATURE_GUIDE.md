# LED Strip Weld Offset Feature Guide

## Overview

The **Weld Offset** feature allows you to account for density discontinuities at LED strip solder joints/welds. When two LED strips are soldered together, the physical spacing at the junction may deviate from the standard LED density, causing LED mapping misalignment in that region.

This feature compensates for these imperfections by applying calibrated offsets at weld locations.

---

## Problem Statement

### Why Welds Matter

When LED strips are soldered together from smaller sub-strips:
- The connection point introduces mechanical stress and heat
- Physical spacing may compress, expand, or shift slightly
- Standard LED density (e.g., 200 LEDs/meter) breaks down at the junction
- LEDs after the weld may be misaligned by 1-5mm from expected positions

### Example Scenario

```
Strip 1: LEDs 0-99 (standard 200 LEDs/meter spacing)
┌─────────────────────────────────────────────────────┐
│ LED 0    LED 20    LED 40    LED 60    LED 80 LED 99 │
└─────────────────────────────────────────────────────┘
                      [SOLDER JOINT]
┌─────────────────────────────────────────────────────┐
│ LED 100  LED 120   LED 140   LED 160   LED 180 LED 199
└─────────────────────────────────────────────────────┘
Strip 2: LEDs 100-199 (spacing offset by ~3mm at junction)
```

Without weld offset compensation, LEDs 100+ appear misaligned on the piano visualization.

---

## Solution: Weld Offsets

### How It Works

1. **Identify welds**: Determine which LED indices have solder joints
2. **Measure offset**: Quantify the spatial deviation in millimeters
3. **Configure offset**: Store the weld location and offset value
4. **Apply during mapping**: Weld offsets adjust LED positions after the junction

### Offset Calculation

Each weld's offset is automatically converted to LED indices:

```
LED offset = Weld offset (mm) / LED spacing (mm)
           = Offset (mm) / (1000 / LEDs per meter)
           = Offset (mm) / 3.5  [for 200 LEDs/meter]
```

**Example**: 3.5mm weld offset at 200 LEDs/meter = 1 LED index shift

---

## Configuration

### Settings Storage

Weld offsets are stored in SQLite under:
```
table: settings
category: calibration
key: led_weld_offsets
value: {"LED_INDEX": OFFSET_MM, ...}
```

**Example**:
```json
{
  "100": 3.5,      // Weld at LED 100, +3.5mm offset
  "200": -1.2,     // Weld at LED 200, -1.2mm offset
  "299": 2.0       // Weld at LED 299, +2.0mm offset
}
```

### Default Behavior

- **Default value**: `{}` (empty - no welds configured)
- **Range**: -10.0 to +10.0 mm per weld
- **Valid LED indices**: 0 to 999

---

## API Endpoints

All weld offset endpoints are under: `/api/calibration/weld/`

### 1. Get All Weld Offsets

**Endpoint**: `GET /api/calibration/weld/offsets`

**Description**: Retrieve all configured weld offsets

**Response** (200 OK):
```json
{
  "success": true,
  "weld_offsets": {
    "100": 3.5,
    "200": -1.2,
    "299": 2.0
  },
  "total_welds": 3,
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

### 2. Get Single Weld Offset

**Endpoint**: `GET /api/calibration/weld/offset/<led_index>`

**Parameters**:
- `led_index` (path): LED index to check

**Response** (200 OK):
```json
{
  "success": true,
  "led_index": 100,
  "offset_mm": 3.5,
  "has_weld": true,
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

**Response** (200 OK - no weld):
```json
{
  "success": true,
  "led_index": 50,
  "offset_mm": null,
  "has_weld": false,
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

### 3. Create/Update Weld Offset

**Endpoint**: `POST /api/calibration/weld/offset/<led_index>`  
**Alias**: `PUT /api/calibration/weld/offset/<led_index>`

**Parameters**:
- `led_index` (path): LED index where weld occurs

**Request Body**:
```json
{
  "offset_mm": 3.5,
  "description": "Main strip junction (solder joint)"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "led_index": 100,
  "offset_mm": 3.5,
  "action": "created",
  "message": "Weld offset at LED 100 created: 3.5mm",
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

**Response** (200 OK - updated):
```json
{
  "success": true,
  "led_index": 100,
  "offset_mm": 2.0,
  "action": "updated",
  "message": "Weld offset at LED 100 updated: 2.0mm",
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

### 4. Delete Weld Offset

**Endpoint**: `DELETE /api/calibration/weld/offset/<led_index>`

**Parameters**:
- `led_index` (path): LED index where weld should be removed

**Response** (200 OK):
```json
{
  "success": true,
  "led_index": 100,
  "deleted_offset_mm": 3.5,
  "message": "Weld offset at LED 100 deleted",
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

**Response** (404 Not Found):
```json
{
  "error": "Weld not found",
  "message": "No weld offset exists at LED 100"
}
```

---

### 5. Bulk Set Weld Offsets

**Endpoint**: `PUT /api/calibration/weld/offsets/bulk`

**Description**: Create/update multiple weld offsets at once

**Request Body**:
```json
{
  "weld_offsets": {
    "100": 3.5,
    "200": -1.2,
    "299": 2.0
  },
  "append": false
}
```

**Parameters**:
- `weld_offsets` (object, required): Dictionary of LED indices to offsets
- `append` (boolean, optional, default: false):
  - `true`: Merge with existing offsets (update only)
  - `false`: Replace entire configuration

**Response** (200 OK):
```json
{
  "success": true,
  "total_welds": 3,
  "created": 2,
  "updated": 1,
  "removed": 0,
  "weld_offsets": {
    "100": 3.5,
    "200": -1.2,
    "299": 2.0
  },
  "validation_errors": null,
  "message": "Bulk update complete: 2 created, 1 updated, 0 removed",
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

### 6. Clear All Weld Offsets

**Endpoint**: `DELETE /api/calibration/weld/offsets`

**Description**: Remove all weld configurations

**Response** (200 OK):
```json
{
  "success": true,
  "previous_count": 3,
  "message": "All 3 weld offset configurations cleared",
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

### 7. Validate Weld Configuration

**Endpoint**: `POST /api/calibration/weld/validate`

**Description**: Validate a proposed weld configuration without saving

**Request Body**:
```json
{
  "weld_offsets": {
    "100": 3.5,
    "200": -1.2,
    "299": 15.0
  }
}
```

**Response** (200 OK):
```json
{
  "valid": false,
  "errors": [
    "LED 299: Offset 15.0mm out of range [-10, +10]"
  ],
  "warnings": [],
  "affected_leds": [100, 200],
  "coverage": {
    "first_led": 100,
    "last_led": 200
  },
  "statistics": {
    "total_welds": 2,
    "positive_offset_count": 1,
    "negative_offset_count": 1,
    "zero_offset_count": 0,
    "max_positive_offset_mm": 3.5,
    "max_negative_offset_mm": -1.2,
    "avg_offset_magnitude_mm": 2.35
  },
  "timestamp": "2025-10-18T14:30:00.000000"
}
```

---

## Usage Examples

### Example 1: Single Weld at LED 100

```bash
# Create weld offset
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5, "description": "Main strip junction"}'

# Verify
curl http://localhost:5001/api/calibration/weld/offset/100
```

### Example 2: Multiple Welds (Bulk)

```bash
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.2,
      "299": 2.0
    },
    "append": false
  }'
```

### Example 3: Find and Fix Misaligned Weld

```bash
# Validate proposed offset before applying
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{"weld_offsets": {"150": 2.5}}'

# If valid, apply it
curl -X POST http://localhost:5001/api/calibration/weld/offset/150 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 2.5}'
```

### Example 4: Update Existing Weld

```bash
# Adjust offset from 3.5mm to 2.0mm
curl -X PUT http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 2.0}'
```

### Example 5: Remove Weld

```bash
# Method 1: Set offset to 0
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 0}'

# Method 2: Delete endpoint
curl -X DELETE http://localhost:5001/api/calibration/weld/offset/100
```

---

## How LED Mapping Uses Weld Offsets

### Processing Order

When calculating final LED positions for each key:

1. **Start with base mapping** (from physics-based or piano-based allocation)
2. **Apply key offsets** (per-key calibration adjustments)
3. **Apply weld offsets** (for all welds at indices <= current LED)

### Calculation Example

```
Base LED for key: 150
Key offset: +2
Weld at LED 100: +3.5mm → ~1 LED
Weld at LED 149: +1.0mm → ~0 LED
Weld at LED 150: +2.0mm → ~0 LED (doesn't apply, must be < current)

Final LED = 150 + 2 (key) + 1 (weld at 100) + 0 (weld at 149) = 153
```

### Cascading Welds

Multiple welds **cascade**: each weld at an index < current LED adds its offset.

```
Current LED: 200
Welds:
  - LED 100: +2.0mm → 0 LEDs ✓ (100 < 200)
  - LED 150: +3.0mm → 1 LED ✓ (150 < 200)
  - LED 199: +1.0mm → 0 LEDs ✓ (199 < 200)
  - LED 200: +2.0mm → N/A (200 not < 200)

Total weld compensation: 0 + 1 + 0 = 1 LED index
Adjusted LED = 200 + 1 = 201
```

---

## Calibration Workflow with Welds

### Step 1: Identify Welds

Visually inspect your LED strip:
- Count total LEDs
- Locate solder joints
- Note the LED index at each junction

```
Strip 1: 100 LEDs (0-99)
Strip 2: 100 LEDs (100-199)
Strip 3: 55 LEDs (200-254)
Solder joints at: LED 100, LED 200
```

### Step 2: Measure Offset

For each weld:
1. Place a ruler or caliper at the weld location
2. Measure deviation from expected position
3. Positive offset = LEDs shifted forward
4. Negative offset = LEDs shifted backward

```
Weld at LED 100: 3.5mm forward → offset: +3.5
Weld at LED 200: -1.0mm backward → offset: -1.0
```

### Step 3: Configure Welds

Use the API or frontend to set weld offsets:

```bash
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.0
    }
  }'
```

### Step 4: Test and Adjust

1. Play keys across the piano
2. Check LED alignment visually
3. If still misaligned, adjust offset values
4. Repeat until satisfied

### Step 5: Validate

Use the validation endpoint to ensure configuration is sound:

```bash
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{"weld_offsets": {"100": 3.5, "200": -1.0}}'
```

---

## Troubleshooting

### Issue: LED mapping doesn't update after adding weld

**Solution**: 
- Welds only affect NEW LED mappings generated after they're added
- If you have an existing mapping, trigger a regeneration:
  - Change `distribution_mode` and change it back, OR
  - Update `start_led` or `end_led` slightly and revert

### Issue: Offset value rejected (out of range)

**Solution**:
- Valid range: -10.0 to +10.0 mm
- If weld offset is > 10mm, split into two LEDs or use global offset instead
- Check if measurement is in correct units (mm, not inches)

### Issue: Some LEDs correct, others still wrong

**Solution**:
- Multiple welds may be present - add offsets for all of them
- Use `GET /api/calibration/weld/offsets` to list all configured welds
- Check if welds are located at the right LED indices

### Issue: Welds appear to shift all LEDs uniformly

**Solution**:
- This may indicate a **global offset** issue instead
- Use `calibration.start_led` and `end_led` to adjust entire strip position
- Weld offsets only affect LEDs AFTER the weld point

### Issue: WebSocket event not received

**Solution**:
- Welds emit `weld_offset_updated` events
- Ensure WebSocket connection is active
- Check browser console for connection errors
- Falls back to REST polling if WebSocket unavailable

---

## Performance Considerations

### Offset Calculation Impact

Weld offset processing:
- **Negligible** if < 10 welds (< 1ms per mapping recalculation)
- **Minimal** even with 50+ welds (< 5ms)
- No impact on real-time LED updates (precomputed)

### Storage

- Each weld stores: LED index (integer) + offset (float)
- Example 100 welds: ~2KB in SQLite
- No performance impact on database

---

## Best Practices

1. **Measure twice, configure once**: Verify weld positions before setting offsets
2. **Start with small offsets**: Begin with ±1.0mm and adjust incrementally
3. **Document your welds**: Add descriptions in comments for future reference
4. **Test systematically**: Check keys at weld boundaries first (e.g., around LED 100)
5. **Export your config**: Save weld offsets as backup
6. **Validate before applying**: Use POST /validate to catch errors early
7. **Use cascading offsets**: Multiple small welds better than one large offset

---

## Advanced: Converting Physical Measurements to Offsets

If you have physical measurements (pixels, mm, inches):

### From LED Count
```
LED offset = Number of LED shifts
Weld offset (mm) = LED offset × (1000 / leds_per_meter)
                 = LED offset × 5.0  [for 200 LEDs/meter]
```

### From Pixels (screen measurement)
```
If strip is visible on screen:
  Pixel offset ÷ pixels_per_mm = mm offset
  Pixel offset ÷ (DPI ÷ 25.4) = mm offset
```

### From Micrometers
```
Micrometer reading ÷ 1000 = mm offset
```

---

## Related Features

- **Key Offsets**: Per-key calibration (`/api/calibration/key-offset/`)
- **LED Range**: Global strip range (`start_led`, `end_led`)
- **Distribution Modes**: Physics-based or piano-based allocation
- **Physical Analysis**: Detailed geometry analysis (`/api/calibration/physical-analysis`)

---

## FAQ

**Q: Can I have multiple welds at the same LED?**  
A: No, each LED index can have at most one weld offset. Multiple values would override each other.

**Q: What if my strip has 1000 LEDs - can welds go beyond 255?**  
A: Yes, weld offsets support LED indices from 0 to 999.

**Q: Do welds affect MIDI event processing?**  
A: Yes, welds are automatically considered in the canonical LED mapping used by USB MIDI and rtpMIDI processors.

**Q: Can I export/import weld configurations?**  
A: Yes, use bulk endpoints or database export. WebSocket events also track all changes.

**Q: What's the relationship between welds and `leds_per_meter`?**  
A: Weld offset (mm) is converted to LED indices using the current `leds_per_meter` setting. Changing density requires recalibrating welds.

---

## Summary

The Weld Offset feature provides:
- ✅ Precise compensation for LED strip solder joints
- ✅ Per-weld or bulk configuration
- ✅ Automatic cascading application
- ✅ Validation and error checking
- ✅ Real-time WebSocket updates
- ✅ Integration with key offsets and global range

Use welds to achieve pixel-perfect LED-to-key alignment even with imperfect solder joints!
