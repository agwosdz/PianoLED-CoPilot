# LED Calibration Usage Guide

## Quick Start

### Enable Calibration
```bash
curl -X POST http://localhost:5001/api/calibration/enable
```

### Set Global Offset
If your LED strip is longer than the piano, use global offset to shift all LEDs:
```bash
curl -X PUT http://localhost:5001/api/calibration/global-offset \
  -H "Content-Type: application/json" \
  -d '{"global_offset": 5}'
```

### Adjust Individual Keys
Fine-tune specific keys that might be misaligned:
```bash
# Adjust Middle C (MIDI note 60) forward by 2 LEDs
curl -X PUT http://localhost:5001/api/calibration/key-offset/60 \
  -H "Content-Type: application/json" \
  -d '{"offset": 2}'

# Adjust A0 (lowest key, MIDI note 21) backward by 1 LED
curl -X PUT http://localhost:5001/api/calibration/key-offset/21 \
  -H "Content-Type: application/json" \
  -d '{"offset": -1}'
```

### Disable Calibration
```bash
curl -X POST http://localhost:5001/api/calibration/disable
```

## API Reference

### Status Endpoints

#### Get Calibration Status
```
GET /api/calibration/status
```
Returns current calibration configuration:
```json
{
  "enabled": true,
  "mode": "manual",
  "global_offset": 3,
  "key_offsets": {
    "60": 2,
    "21": -1
  },
  "last_calibration": "2025-10-16T14:30:00.123456",
  "mapping_base_offset": 0,
  "leds_per_key": 3
}
```

### Global Offset Endpoints

#### Get Global Offset
```
GET /api/calibration/global-offset
```

#### Set Global Offset
```
PUT /api/calibration/global-offset
Content-Type: application/json

{
  "global_offset": 5
}
```
- Valid range: -100 to +100
- Applies uniformly to all LEDs

### Per-Key Offset Endpoints

#### Get Single Key Offset
```
GET /api/calibration/key-offset/{midi_note}
```
Example: `GET /api/calibration/key-offset/60` (Middle C)

#### Set Single Key Offset
```
PUT /api/calibration/key-offset/{midi_note}
Content-Type: application/json

{
  "offset": 2
}
```
- Valid range: -100 to +100 per key
- MIDI notes: 0-127
- Example: `PUT /api/calibration/key-offset/60` (Middle C)

#### Get All Key Offsets
```
GET /api/calibration/key-offsets
```
Returns:
```json
{
  "key_offsets": {
    "60": 2,
    "21": -1,
    "108": 1
  }
}
```

#### Batch Set Key Offsets
```
PUT /api/calibration/key-offsets
Content-Type: application/json

{
  "key_offsets": {
    "60": 2,
    "21": -1,
    "108": 1
  }
}
```

### Control Endpoints

#### Enable Calibration
```
POST /api/calibration/enable
```
Enables calibration mode and sets mode to 'manual'.

#### Disable Calibration
```
POST /api/calibration/disable
```
Disables all calibration offset application.

#### Reset Calibration
```
POST /api/calibration/reset
```
Resets all offsets to defaults:
- global_offset → 0
- key_offsets → {}
- calibration_enabled → false

### Import/Export Endpoints

#### Export Calibration
```
GET /api/calibration/export
```
Returns complete calibration data:
```json
{
  "enabled": true,
  "mode": "manual",
  "global_offset": 3,
  "key_offsets": {
    "60": 2,
    "21": -1
  },
  "last_calibration": "2025-10-16T14:30:00.123456",
  "timestamp": "2025-10-16T14:35:12.654321"
}
```

#### Import Calibration
```
POST /api/calibration/import
Content-Type: application/json

{
  "global_offset": 3,
  "key_offsets": {
    "60": 2,
    "21": -1,
    "108": 1
  }
}
```

## Calibration Workflow

### Step 1: Enable Calibration Mode
```bash
curl -X POST http://localhost:5001/api/calibration/enable
```

### Step 2: Set Global Offset (if needed)
Test whether all LEDs are offset uniformly from the piano keys:
```bash
# Try small offset first (e.g., +2)
curl -X PUT http://localhost:5001/api/calibration/global-offset \
  -H "Content-Type: application/json" \
  -d '{"global_offset": 2}'
```
Play each key and observe if all LEDs shift by the same amount. Adjust until the LED strip aligns with the first key position.

### Step 3: Fine-Tune Individual Keys
If some keys are still misaligned after global offset, adjust them individually:
```bash
# Adjust A0 (first key)
curl -X PUT http://localhost:5001/api/calibration/key-offset/21 \
  -H "Content-Type: application/json" \
  -d '{"offset": -1}'

# Adjust Middle C
curl -X PUT http://localhost:5001/api/calibration/key-offset/60 \
  -H "Content-Type: application/json" \
  -d '{"offset": 1}'

# Adjust C8 (last key)
curl -X PUT http://localhost:5001/api/calibration/key-offset/108 \
  -H "Content-Type: application/json" \
  -d '{"offset": 0}'
```

### Step 4: Save Configuration
Export calibration for backup:
```bash
curl http://localhost:5001/api/calibration/export > calibration.json
```

### Step 5: Verify
Play a full octave and verify all keys light up the correct LEDs.

## WebSocket Events

Listen for real-time calibration updates:

### Enable/Disable Events
```javascript
socket.on('calibration_enabled', (data) => {
  console.log('Calibration enabled:', data.enabled);
});

socket.on('calibration_disabled', (data) => {
  console.log('Calibration disabled:', data.enabled);
});
```

### Offset Change Events
```javascript
socket.on('global_offset_changed', (data) => {
  console.log('Global offset:', data.global_offset);
});

socket.on('key_offset_changed', (data) => {
  console.log(`MIDI ${data.midi_note} offset: ${data.offset}`);
});

socket.on('key_offsets_changed', (data) => {
  console.log('Updated offsets:', data.key_offsets);
});
```

### Reset Event
```javascript
socket.on('calibration_reset', (data) => {
  console.log('Calibration reset:', data);
});
```

## MIDI Note Reference

Common MIDI notes for testing:
- **A0** (21): Lowest piano key
- **C2** (36): Often first key on smaller keyboards
- **C3** (48): 1 octave below middle C
- **C4** (60): Middle C
- **A4** (69): Concert A (tuning reference)
- **C8** (108): Highest piano key

## Troubleshooting

### LEDs shift but not uniformly
→ Use global offset first to align the overall strip position

### Some keys are off but others are correct
→ Use per-key offsets to adjust individual keys after global offset

### Offsets keep reverting
→ Check that calibration_enabled is true via `/api/calibration/status`

### Can't set very large offsets
→ Global and per-key offsets are limited to ±100 to prevent extreme misalignments
→ If strip needs larger shift, adjust `mapping_base_offset` in LED settings instead

### Not seeing WebSocket events
→ Verify you're connected to WebSocket at `/socket.io/`
→ Check browser console for connection errors

## Advanced Usage

### Assisted Calibration (Future)
When implemented, use:
```bash
curl -X POST http://localhost:5001/api/calibration/assist
```
This will guide you through an automatic detection process.

### Calibration Profiles (Future)
Save multiple calibration sets:
```bash
# Save current as "profile1"
curl -X POST http://localhost:5001/api/calibration/profiles/profile1

# Load "profile1"
curl -X POST http://localhost:5001/api/calibration/profiles/profile1/load
```

### Progressive Drift Compensation (Future)
For strips that drift over their length:
```json
{
  "drift_enabled": true,
  "drift_model": "linear",
  "drift_amount": 0.5
}
```

## API Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid offset, MIDI note, etc.) |
| 404 | Not found (setting or profile doesn't exist) |
| 500 | Server error |

## Example: Complete Calibration Script

```bash
#!/bin/bash

API="http://localhost:5001/api/calibration"

# Enable calibration
echo "Enabling calibration..."
curl -X POST $API/enable

# Set global offset
echo "Setting global offset to 3..."
curl -X PUT $API/global-offset \
  -H "Content-Type: application/json" \
  -d '{"global_offset": 3}'

# Adjust first few keys
echo "Adjusting key offsets..."
for note in 21 24 27 30; do
  curl -X PUT $API/key-offset/$note \
    -H "Content-Type: application/json" \
    -d "{\"offset\": 1}"
done

# Verify
echo "Current status:"
curl $API/status | jq

# Export
echo "Exporting calibration..."
curl $API/export > calibration.json

echo "Calibration complete!"
```
