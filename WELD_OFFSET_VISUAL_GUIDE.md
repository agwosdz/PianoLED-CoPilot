# LED Weld Offset - Visual Reference Guide

## Problem Visualization

### Without Weld Compensation

```
Expected Piano Layout:
Key A0  A#0  B0  C1  C#1  D1  D#1  ...  C8
LED  0   3    6   9   12   15   18   ... 254

Actual LED Strip (with welds):
Strip 1: LEDs 0-99     [Perfect alignment]
         [SOLDER JOINT] ← +3.5mm shift
Strip 2: LEDs 100-199  [Shifted forward by 3.5mm!]
         [SOLDER JOINT] ← -1.0mm shift
Strip 3: LEDs 200-254  [Shifted backward by 1.0mm!]

Result on Piano:
┌────────────────────────────────────────┐
│ Keys A0-C4: ✓ Correct alignment        │
│ Keys C#4-C7: ✗ Off by ~3mm             │ ← Welds not compensated
│ Keys C#7-C8: ✗ Off by ~4mm            │
└────────────────────────────────────────┘
```

### With Weld Compensation

```
Configure Welds:
  LED 100: +3.5mm → +1 LED index
  LED 200: -1.0mm → 0 LED index (rounds to 0)

After Compensation:
┌────────────────────────────────────────┐
│ Keys A0-C4: ✓ Correct                  │
│ Keys C#4-C7: ✓ Correct (+ weld 1 LED) │ ← Fixed!
│ Keys C#7-C8: ✓ Correct                │
└────────────────────────────────────────┘
```

---

## Offset Measurement Guide

### Visual Check

```
Use a ruler against the LED strip at solder joint:

Perfect alignment:     ⬤⬤⬤⬤⬤
                       0 1 2 3 4

Forward shift (+):     ⬤⬤⬤⬤⬤    ← Gap here
                      0 1 2 3 4   → Measure gap
Result: +2.5mm offset

Backward shift (-):    ⬤⬤⬤⬤⬤
                        0 1 2 3 4 ← Overlap here
Result: -1.0mm offset   → Measure overlap
```

---

## Offset Value Reference Table

| Measurement | Offset Value | LED Index Shift | Use Case |
|-------------|--------------|-----------------|----------|
| None | 0 | 0 | No weld needed |
| +1mm forward | +1.0 | 0 | Minimal shift |
| +2mm forward | +2.0 | 1 | Typical weld |
| +3.5mm forward | +3.5 | 1 | Common |
| +5mm forward | +5.0 | 1 | Significant shift |
| -1mm backward | -1.0 | 0 | Minimal |
| -2mm backward | -2.0 | -1 | Typical |
| -3.5mm backward | -3.5 | -1 | Common |

---

## API Flow Diagram

### Creating a Weld

```
┌─ User ─────────────────────────┐
│ curl POST /offset/100          │
│   offset_mm: 3.5               │
└────────────┬────────────────────┘
             │ HTTP POST
             ▼
┌─ API Endpoint ─────────────────┐
│ set_weld_offset(100)           │
│ Validate input                 │
│ Check range: -10 to +10        │
└────────────┬────────────────────┘
             │ Validation OK
             ▼
┌─ Settings Service ─────────────┐
│ set_setting(                   │
│   'calibration',               │
│   'led_weld_offsets',          │
│   {'100': 3.5}                 │
│ )                              │
└────────────┬────────────────────┘
             │ Write
             ▼
┌─ SQLite Database ──────────────┐
│ INSERT settings (              │
│   category: 'calibration',     │
│   key: 'led_weld_offsets',     │
│   value: '{"100": 3.5}'        │
│ )                              │
└────────────┬────────────────────┘
             │ Persisted
             ▼
┌─ WebSocket ────────────────────┐
│ emit('weld_offset_updated', {  │
│   event_type: 'weld_created'   │
│ })                             │
└────────────┬────────────────────┘
             │ Broadcast
             ▼
┌─ Response to User ─────────────┐
│ 201 Created                    │
│ {success: true, ...}           │
└────────────────────────────────┘
```

---

## LED Mapping Calculation Example

### Scenario

```
Key: Middle C (MIDI 60)
Base mapping: LEDs [64, 65, 66]
Key offset: +2
Welds: LED 60: +1.0mm, LED 65: +2.0mm

Conversion:
  LED 60: +1.0mm / 3.5mm = 0 LEDs
  LED 65: +2.0mm / 3.5mm = 1 LED
```

### Calculation

```
Process LED 64:
  Base: 64
  + Key offset: +2 → 66
  + Weld compensation: 0 LEDs (no welds < 66)
  = 66
  ✓ Final: 66

Process LED 65:
  Base: 65
  + Key offset: +2 → 67
  + Weld compensation: 0 LEDs (weld at 65 not < 67)
  = 67
  ✓ Final: 67

Process LED 66:
  Base: 66
  + Key offset: +2 → 68
  + Weld compensation: 0 LEDs (weld at 65 < 68, but 1 + 1 = 1)
  = 68 + 1 = 69
  ✓ Final: 69

Result: [66, 67, 69] instead of [66, 67, 68]
```

---

## Cascading Welds Example

### Setup

```
LEDs: 0-254
Welds:
  LED 100: +2.0mm → 1 LED
  LED 150: +3.0mm → 1 LED
  LED 200: +1.0mm → 0 LEDs
  LED 250: +2.0mm → 1 LED
```

### Processing Different LEDs

```
Processing LED 75 (before any welds):
  Welds < 75: NONE
  Total compensation: 0
  Final: 75 + 0 = 75 ✓

Processing LED 125 (after weld 100):
  Welds < 125: LED 100 ✓
  Total compensation: 1
  Final: 125 + 1 = 126 ✓

Processing LED 175 (after welds 100, 150):
  Welds < 175: LED 100 ✓, LED 150 ✓
  Total compensation: 1 + 1 = 2
  Final: 175 + 2 = 177 ✓

Processing LED 225 (after welds 100, 150, 200):
  Welds < 225: LED 100 ✓, LED 150 ✓, LED 200 ✓
  Total compensation: 1 + 1 + 0 = 2
  Final: 225 + 2 = 227 ✓

Processing LED 254 (after all welds):
  Welds < 254: ALL
  Total compensation: 1 + 1 + 0 + 1 = 3
  Final: 254 + 3 = 257 (clamped to 254) ✓
```

---

## Bulk Operation Modes

### Replace Mode (default)

```
Current state:
  {"100": 2.5, "200": -1.0}

Bulk request (append: false):
  {"100": 3.5, "300": 1.0}

Result: {"100": 3.5, "300": 1.0}
         ↑ Updated        ↑ New
         (200 removed)
```

### Append Mode

```
Current state:
  {"100": 2.5, "200": -1.0}

Bulk request (append: true):
  {"100": 3.5, "300": 1.0}

Result: {"100": 3.5, "200": -1.0, "300": 1.0}
         ↑ Updated    ↑ Kept      ↑ New
```

---

## Response Status Codes Flowchart

```
POST /offset/<led>
    │
    ├─ Invalid LED index
    │  ├─ Negative → 400
    │  └─ Wrong type → 400
    │
    ├─ Invalid offset
    │  ├─ Out of range (-10, +10) → 400
    │  ├─ Wrong type → 400
    │  └─ Missing field → 400
    │
    ├─ Database error → 500
    │
    ├─ offset_mm == 0
    │  ├─ Weld exists → 200 Removed
    │  └─ Weld missing → 404 Not Found
    │
    ├─ offset_mm != 0
    │  ├─ New weld → 201 Created
    │  └─ Existing → 200 Updated
    │
    └─ Success → Response with data
```

---

## Command Cheat Sheet

### Single Weld Operations

```bash
# Add/update
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5}'

# Get
curl http://localhost:5001/api/calibration/weld/offset/100

# Delete
curl -X DELETE http://localhost:5001/api/calibration/weld/offset/100

# Get all
curl http://localhost:5001/api/calibration/weld/offsets
```

### Bulk Operations

```bash
# Replace all
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{"weld_offsets": {"100": 3.5, "200": -1.0}}'

# Append
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {"300": 2.0},
    "append": true
  }'

# Clear all
curl -X DELETE http://localhost:5001/api/calibration/weld/offsets

# Validate
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{"weld_offsets": {"100": 3.5}}'
```

---

## Troubleshooting Flowchart

```
LEDs after weld look misaligned
    │
    ├─ Weld configured?
    │  ├─ NO → Add weld with offset value
    │  └─ YES → Go to next check
    │
    ├─ Correct LED index?
    │  ├─ NO → Update LED index
    │  └─ YES → Go to next check
    │
    ├─ Correct offset value?
    │  ├─ NO → Adjust offset (re-measure)
    │  └─ YES → Go to next check
    │
    ├─ Mapping regenerated?
    │  ├─ NO → Trigger regeneration (change setting)
    │  └─ YES → Go to next check
    │
    ├─ Multiple welds?
    │  ├─ YES → Verify all weld offsets correct
    │  └─ NO → Problem isolated
    │
    └─ Still misaligned? → Check calibration.start_led/end_led
```

---

## LED Index vs MIDI Note

### Conversion Formula

```
MIDI Note = LED Index + 21
LED Index = MIDI Note - 21

Examples:
  A0 (MIDI 21) → LED index 0
  C4 (MIDI 60) → LED index 39
  C8 (MIDI 108) → LED index 87
```

### In Weld Config

```
API stores weld LED indices:
  {"100": 3.5, "200": -1.0}
       ↑
    Physical LED index (not MIDI)

Same indices used in /key-led-mapping response:
  {
    "21": [4, 5, 6, 7],     ← A0 → indices 0-3 (LED 4-7 after calibration)
    "60": [64, 65, 66],     ← C4 → indices 39-41 (LED 64-66 + offsets)
    "108": [248, 249]       ← C8 → indices 87-88 (LED 248-249 + offsets)
  }
```

---

## Performance Metrics

```
Operation              Typical Time    Resources
───────────────────────────────────────────────────
Create weld            0.1ms          SQLite write
Update weld            0.1ms          SQLite update
Delete weld            0.1ms          SQLite delete
Get single weld        0.5ms          SQLite select
Get all welds (10)     1ms            SQLite select
Get all welds (100)    5ms            SQLite select
Validate 50 welds      2ms            Parse + validate
Regenerate mapping     ~10ms          Includes all offsets
                       (no slowdown)

Storage per weld:      ~50 bytes
100 welds total:       ~5KB
```

---

## Quick Fixes

### Offset too large
**Error**: "Offset 15mm out of range"  
**Fix**: Split into multiple welds or check measurement units

### Weld not applied
**Check**: `GET /offsets` returns your weld?  
**Fix**: Verify LED index is correct, trigger mapping regeneration

### Offset converts to 0
**Info**: Small offsets (<1.75mm) round to 0 LEDs  
**Fix**: Use larger offsets or accept no LED shift

### Still misaligned after weld
**Check**: Multiple welds configured?  
**Fix**: List all with `GET /offsets`, verify cascading calculation

---

## Summary Table

| Task | Endpoint | Method |
|------|----------|--------|
| List all welds | `/offsets` | GET |
| Get one weld | `/offset/{led}` | GET |
| Add weld | `/offset/{led}` | POST |
| Update weld | `/offset/{led}` | PUT |
| Remove weld | `/offset/{led}` | DELETE |
| Bulk configure | `/offsets/bulk` | PUT |
| Clear all | `/offsets` | DELETE |
| Validate | `/validate` | POST |

---

This visual guide provides quick reference for understanding, configuring, and troubleshooting LED weld offsets!
