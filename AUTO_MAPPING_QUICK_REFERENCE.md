# Auto Mapping Quick Reference Guide

## How Auto Mapping Works (Simple Version)

```
┌─────────────────────────────────────────┐
│ User Settings in Database               │
├─────────────────────────────────────────┤
│ piano_size = 88-key                     │
│ led_count = 300                         │
│ leds_per_key = null (auto-calculate)    │
└──────────────┬──────────────────────────┘
               │
        ┌──────▼──────┐
        │  Calculate  │
        │  300 ÷ 88   │
        │  = 3.4      │
        └──────┬──────┘
               │
    ┌──────────▼──────────────┐
    │ Distribution:           │
    │ 74 keys × 3 LEDs       │
    │ 14 keys × 2 LEDs       │
    │ Total: 300 LEDs        │
    └──────────┬──────────────┘
               │
    ┌──────────▼──────────────┐
    │ Create Mapping:         │
    │ Key 21 → LEDs [0,1,2]  │
    │ Key 22 → LEDs [3,4,5]  │
    │ ...                     │
    │ Key 108 → LEDs [...]   │
    └──────────┬──────────────┘
               │
    ┌──────────▼──────────────┐
    │ Apply Offsets:          │
    │ Global: +0              │
    │ Per-key: none           │
    └──────────┬──────────────┘
               │
    ┌──────────▼──────────────┐
    │ Final Mapping Ready     │
    │ for Frontend            │
    └────────────────────────┘
```

---

## Configuration Parameters

### Basic Parameters
```
Piano Size:           25, 37, 49, 61, 76, or 88 keys
LED Count:            Total LEDs available (e.g., 300)
Mapping Base Offset:  Skip first N LEDs (default: 0)
LEDs per Key:         Fixed allocation or auto-calculate
```

### Examples
```
Config A: 88 keys, 300 LEDs, auto-calculate
Result: 74 keys × 3 LEDs + 14 keys × 2 LEDs

Config B: 88 keys, 300 LEDs, 3 LEDs/key
Result: 88 keys × 3 LEDs = 264 used, 36 unused

Config C: 88 keys, 300 LEDs, base offset 50
Result: 74 keys × 3 LEDs + 14 keys × 2 LEDs (using LEDs 50-299)

Config D: 49 keys, 150 LEDs, auto-calculate
Result: 49 keys × 3 LEDs = 147 used, 3 unused
```

---

## Calibration Offsets

### Global Offset
Shifts ALL LEDs the same amount
```
Setting: global_offset = +5
Effect:  All LEDs move 5 positions forward

Example:
  Original:  Key 21 → [0, 1, 2]
  With +5:   Key 21 → [5, 6, 7]
```

### Per-Key Offset (Cascading)
Individual notes shift, affecting all subsequent notes
```
Setting: key_offsets = {48: +1, 50: +2}
Effect:  Offset accumulates for notes >= setting point

Example:
  Key 48 (C3):  offset +1
  Key 49 (C#3): offset +1 (cascaded)
  Key 50 (D3):  offset +1+2 = +3
  Key 51 (D#3): offset +3 (cascaded)
  Key 52 (E3):  offset +3 (cascaded)
```

---

## API Endpoints

### Get Mapping
```
GET /api/calibration/key-led-mapping

Response:
{
  "mapping": {
    "21": [0, 1, 2, 3],
    "22": [4, 5, 6, 7],
    ...
  },
  "piano_size": "88-key",
  "led_count": 300,
  "global_offset": 0,
  "key_offsets_count": 2
}
```

### Turn On LED (Single)
```
POST /api/calibration/led-on/6
Query: ?r=150&g=0&b=100 (optional, default white)

Response: { "message": "LED 6 turned on", ... }
```

### Turn On LEDs (Batch) 
```
POST /api/calibration/leds-on

Body:
{
  "leds": [
    {"index": 0, "r": 150, "g": 0, "b": 100},
    {"index": 1, "r": 0, "g": 100, "b": 150},
    ...
  ]
}

Response:
{
  "leds_turned_on": 15,
  "total_requested": 15,
  "errors": []
}
```

---

## Common Issues & Solutions

### Issue: Keys have different brightness
**Cause:** Uneven LED distribution (some keys 3 LEDs, some 2 LEDs)
**Solution:** Use LED count that divides evenly (264, 352, etc.)
**Example:** 264 LEDs ÷ 88 keys = 3 exactly

### Issue: Last keys don't light up
**Cause:** Not enough LEDs for all keys
**Solution:** Use fixed LEDs/key or increase LED count
**Example:** 100 LEDs with 2 LEDs/key = only 50 keys mapped

### Issue: Offsets seem to affect more keys than expected
**Cause:** Cascading offset behavior
**Solution:** This is normal - offset cascades to all subsequent keys
**Details:** If you set offset at C3, it affects C3, C#3, D3, etc.

### Issue: Some LEDs not being used
**Cause:** Fixed LEDs/key doesn't divide evenly
**Solution:** This is expected - some LEDs may be reserved
**Details:** 88 keys × 3 LEDs/key = 264 LEDs, leaving 36 unused

---

## Piano Sizes Reference

```
25-key:  C3 to C5   (MIDI 48-72)    - Entry level
37-key:  C2 to C5   (MIDI 36-72)    - Common home piano
49-key:  C2 to C6   (MIDI 36-84)    - Keyboard
61-key:  C2 to C7   (MIDI 36-96)    - Full keyboard
76-key:  E1 to G7   (MIDI 28-103)   - Professional
88-key:  A0 to C8   (MIDI 21-108)   - Full size piano
```

---

## Troubleshooting Checklist

- [ ] Is LED count reasonable for piano size?
  - Minimum: 1 LED/key
  - Recommended: 2-3 LEDs/key
  - Ideal: Divides evenly (no remainder)

- [ ] Is base offset too high?
  - Base offset + keys × leds_per_key ≤ LED count
  - Example: offset 50 + 88 keys × 3 = 314, need ≥ 314 LEDs

- [ ] Are offsets causing confusion?
  - Check if cascading behavior is expected
  - Individual offsets stack across notes

- [ ] Are some keys unmapped?
  - With fixed leds_per_key, this is expected
  - Calculate: available_leds ÷ leds_per_key = max_keys
  - If less than piano's key count, some keys unmapped

---

## Settings to Adjust

### For Even Distribution
```json
{
  "piano": {
    "size": "88-key"
  },
  "led": {
    "led_count": 264,  // 88 × 3, divides evenly
    "leds_per_key": null,  // auto-calculate
    "mapping_base_offset": 0
  }
}
```

### For Maximum Coverage
```json
{
  "led": {
    "led_count": 300,
    "leds_per_key": null,  // auto-calculate, gets 2-3 per key
    "mapping_base_offset": 0
  }
}
```

### For Fixed Allocation
```json
{
  "led": {
    "led_count": 300,
    "leds_per_key": 3,  // exactly 3 per key, 36 unused
    "mapping_base_offset": 0
  }
}
```

### For Reserved LED Section
```json
{
  "led": {
    "led_count": 300,
    "leds_per_key": null,
    "mapping_base_offset": 50  // Use LEDs 50-299
  }
}
```

---

## Performance Notes

- **Mapping Generation:** ~1ms for 88 keys
- **Offset Application:** ~1ms for 88 keys
- **API Response Time:** ~50-100ms total
- **LED Update:** ~1ms for batch of 300 LEDs

Single-key lighting now uses batch endpoint:
- Before: 3 sequential API calls (150ms)
- After: 1 batch API call (50ms)
- **Improvement:** 3x faster

---

## Future Improvements (Not Yet Implemented)

- [ ] Distribution mode configuration (even, spread, end)
- [ ] Offset mode configuration (cascading, independent)
- [ ] Validation endpoint (before applying config)
- [ ] Mapping info endpoint (statistics, warnings)
- [ ] Better logging and warnings
- [ ] More comprehensive tests

---

## Testing the Mapping

### Via API
```bash
# Get current mapping
curl http://localhost:5000/api/calibration/key-led-mapping

# Turn on a batch of LEDs
curl -X POST http://localhost:5000/api/calibration/leds-on \
  -H "Content-Type: application/json" \
  -d '{
    "leds": [
      {"index": 0, "r": 255, "g": 0, "b": 0},
      {"index": 1, "r": 0, "g": 255, "b": 0},
      {"index": 2, "r": 0, "g": 0, "b": 255}
    ]
  }'
```

### Via Frontend
1. Navigate to Settings → Calibration
2. Click on a piano key to see its LED mapping
3. Check browser console for LED debug logs
4. Click "Show Layout" to see all mapped LEDs

---

## Important Notes

1. **Cascading offsets are cumulative:** Multiple offsets stack
2. **LED indices are logical:** Physical reversal happens in LEDController
3. **Bounds are enforced:** Offsets can't exceed LED count
4. **Distribution is deterministic:** Same config = same mapping
5. **Settings are persistent:** Changes saved to database

