# MIDI Output - Quick Reference

## Feature Summary
**Send MIDI note events to USB keyboards during MIDI playback with optional toggle on Listen page.**

## User Controls

### Listen Page Toggle
- **Checkbox**: "Send MIDI to USB Keyboard"
- **Status Indicator**: Shows connection state (🎹 Connected / 🔌 Disconnected)
- **Device Selector**: Dropdown to choose USB keyboard device
- **Auto-Connect**: First available device selected if none specified

## Backend Architecture

### Core Services
1. **USBMIDIOutputService** - Device management and MIDI sending
2. **PlaybackService** - Integrates MIDI output into playback loop
3. **SettingsService** - Persists MIDI output settings

### Key Methods
```python
# Connect to device
midi_output_service.connect("Device Name")

# Send MIDI
midi_output_service.send_note_on(note=60, velocity=100, channel=0)
midi_output_service.send_note_off(note=60, channel=0)

# Check status
midi_output_service.get_status()
```

### Settings Keys
```python
settings_service.get_setting('hardware', 'midi_output_enabled')  # bool
settings_service.get_setting('hardware', 'midi_output_device')   # str
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/midi-output/devices` | List available output devices |
| POST | `/api/midi-output/connect` | Connect to device |
| POST | `/api/midi-output/disconnect` | Disconnect from device |
| GET | `/api/midi-output/status` | Get connection status |
| POST | `/api/midi-output/toggle` | Enable/disable MIDI output |

## Velocity Handling

**Formula**: `adjusted_velocity = clamp(velocity * volume_multiplier, 1, 127)`

- Volume multiplier from playback settings (default: 1.0)
- Minimum velocity: 1 (prevents silent notes)
- Maximum velocity: 127 (MIDI spec)

## Flow Diagram

```
Playback File Load
      ↓
Note Event Processing
      ↓
Note Start Detected (within 20ms tolerance)
      ↓
├─→ Add to active_notes
├─→ Update LEDs
└─→ IF midi_output_enabled:
    └─→ _send_midi_note_on()
        └─→ Apply volume multiplier
        └─→ Send to USB keyboard
      ↓
Note Duration Expires
      ↓
├─→ Remove from active_notes
├─→ Update LEDs
└─→ IF midi_output_enabled:
    └─→ _send_midi_note_off()
        └─→ Send to USB keyboard
```

## Configuration

### Enable MIDI Output
```json
POST /api/midi-output/toggle
{
  "enabled": true,
  "device_name": "CASIO USB-MIDI"
}
```

### Response
```json
{
  "status": "success",
  "midi_output_enabled": true,
  "midi_output_device": "CASIO USB-MIDI"
}
```

## Troubleshooting

### No Devices Shown
- Check USB keyboard is connected and recognized by OS
- Run device detection: `GET /api/midi-output/devices`
- Verify mido/python-rtmidi installed: `pip list | grep mido`

### Connection Failed
- Ensure device name matches exactly
- Try auto-select (don't specify device_name)
- Check device isn't busy (no MIDI input active)

### MIDI Not Reaching Keyboard
- Verify toggle is ON (checkbox checked)
- Check device shows "Connected" status
- Monitor playback - verify file is playing
- Check volume multiplier isn't 0

### Hanging Notes
- Stop playback (■ button) to send all note_offs
- Reload page to reset connection
- Manually send note_off via API if needed

## File Locations

| Component | File |
|-----------|------|
| MIDI Output Service | `backend/usb_midi_output_service.py` |
| Playback Integration | `backend/playback_service.py` |
| API Endpoints | `backend/app.py` (search: MIDI OUTPUT ENDPOINTS) |
| Frontend UI | `frontend/src/routes/listen/+page.svelte` |
| Settings Schema | `backend/services/settings_service.py` |

## Code Examples

### Frontend - Toggle MIDI Output
```javascript
await fetch('/api/midi-output/toggle', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    enabled: true,
    device_name: "CASIO USB-MIDI"
  })
});
```

### Backend - Check Device List
```python
devices = midi_output_service.get_available_devices()
for device in devices:
    print(f"{device.name}: {device.status}")
```

### Backend - Send Note with Multiplier
```python
velocity = 100
adjusted = max(1, min(127, int(velocity * volume_multiplier)))
midi_output_service.send_note_on(note=60, velocity=adjusted)
```

## Testing Checklist

- [ ] MIDI output disabled by default
- [ ] Toggle enables MIDI output
- [ ] Device dropdown populates correctly
- [ ] Connection status updates on device select
- [ ] Playback sends MIDI note_on
- [ ] Playback sends MIDI note_off
- [ ] Volume multiplier affects velocity
- [ ] Stop playback sends all note_offs
- [ ] Settings persist on reload
- [ ] Works with multiple USB devices

## Performance Notes

- MIDI sends are non-blocking (threadsafe)
- No impact on LED visualization performance
- Device enumeration is cached
- Settings loaded on playback service init

## Status: ✅ READY FOR TESTING
