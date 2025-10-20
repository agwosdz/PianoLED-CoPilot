# Play Page MIDI Input - API Reference

## Endpoints Connected

| Endpoint | Method | Purpose | Frontend Function |
|----------|--------|---------|-------------------|
| `/api/midi-input/devices` | GET | Get available MIDI devices | `loadMidiInputDevices()` |
| `/api/midi-input/start` | POST | Connect to MIDI device | `connectMidiInput()` |
| `/api/midi-input/stop` | POST | Disconnect from MIDI device | `disconnectMidiInput()` |
| `/api/midi-input/status` | GET | Check connection status | `checkMidiInputStatus()` |

## Request/Response Examples

### Load Devices
```bash
curl -X GET http://localhost:5001/api/midi-input/devices
```

### Connect to Device
```bash
curl -X POST http://localhost:5001/api/midi-input/start \
  -H "Content-Type: application/json" \
  -d '{"device_name": "USB Audio Device", "enable_usb": true, "enable_rtpmidi": false}'
```

### Disconnect
```bash
curl -X POST http://localhost:5001/api/midi-input/stop
```

### Check Status
```bash
curl -X GET http://localhost:5001/api/midi-input/status
```

## UI Components

- **MIDI Input Toggle**: ON/OFF switch to enable/disable MIDI listening
- **Device Dropdown**: Select which USB keyboard to use
- **Status Indicator**: Shows connected/not connected status
- **Refresh Button**: Reload list of available devices
- **Disconnect Button**: Manually disconnect from current device
- **Error Messages**: Show connection errors in red

## Polling Intervals

| Check | Interval | Purpose |
|-------|----------|---------|
| Playback Status | 100ms | Track play/pause/stop state |
| File List | 5000ms | Update available MIDI files |
| MIDI Status | 1000ms | Monitor connection state |

## Feature Status

✅ Get available MIDI devices  
✅ Connect to USB keyboard  
✅ See connection status  
✅ Disconnect from keyboard  
✅ Auto-detection of current device  
✅ Error handling & user feedback  
✅ Auto-connect on enable  

## Next Steps (Optional)

1. Test with actual USB keyboard
2. Verify MIDI notes are processed
3. Consider WebSocket optimization (replace polling)
4. Add MIDI event visualization
5. Implement MIDI note mapping/learning

