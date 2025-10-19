# MIDI Playback Output Implementation - Complete

## Overview
Successfully implemented optional MIDI output to USB keyboards during MIDI playback, with full integration of calibrated mapping adjustments (velocity, volume multiplier). The feature is controlled via a toggle on the Listen page.

## Architecture

### Backend Components

#### 1. **USBMIDIOutputService** (`backend/usb_midi_output_service.py`)
- **New Service**: Mirrors USBMIDIInputService design pattern
- **Functions**:
  - `connect(device_name)`: Connect to MIDI output device
  - `disconnect()`: Disconnect from current device
  - `send_note_on(note, velocity, channel)`: Send note_on with clamped values
  - `send_note_off(note, channel)`: Send note_off message
  - `send_control_change(control, value, channel)`: Send CC messages
  - `get_available_devices()`: List all MIDI output devices
  - `get_status()`: Return connection status

**Key Features**:
- Thread-safe with `_lock` for concurrent access
- Graceful fallback when mido not available
- Device auto-selection if none specified
- WebSocket broadcasting of status changes

#### 2. **PlaybackService Enhancements** (`backend/playback_service.py`)
- **New Parameters**:
  - `midi_output_service`: USBMIDIOutputService instance
  - `_midi_output_enabled`: Toggle state
  - `_midi_notes_sent`: Track active MIDI notes

- **New Methods**:
  - `_load_midi_output_settings()`: Load config from SettingsService
  - `_send_midi_note_on(note, velocity)`: Send note with volume multiplier applied
  - `_send_midi_note_off(note)`: Send note_off to USB keyboard
  - Updated `_process_note_events()`: Sends MIDI when notes start/stop
  - Updated `stop_playback()`: Sends note_off for all active notes

- **Integration**:
  - Volume multiplier applied to MIDI velocity
  - Velocity clamped to valid MIDI range (0-127)
  - Integrates with existing playback loop without breaking changes

#### 3. **Settings Schema** (`backend/services/settings_service.py`)
Added to `hardware` category:
```python
'midi_output_enabled': {
    'type': 'boolean',
    'default': False,
    'description': 'Enable MIDI output to connected devices during playback'
},
'midi_output_device': {
    'type': 'string',
    'default': '',
    'description': 'Selected MIDI output device name'
}
```

#### 4. **API Endpoints** (`backend/app.py`)
New routes under `/api/midi-output/`:

```
GET  /api/midi-output/devices       - List available output devices
POST /api/midi-output/connect       - Connect to device
POST /api/midi-output/disconnect    - Disconnect from device
GET  /api/midi-output/status        - Get current status
POST /api/midi-output/toggle        - Enable/disable + set device
```

**Response Format**:
```json
{
  "status": "success",
  "devices": [
    {
      "name": "Device Name",
      "id": 0,
      "status": "available|connected",
      "is_current": true
    }
  ],
  "current_device": "Device Name",
  "is_connected": true
}
```

#### 5. **App Initialization** (`backend/app.py`)
- Creates `midi_output_service` instance
- Passes to `playback_service` during initialization
- Registers MIDI output endpoints

### Frontend Components

#### **Listen Page UI** (`frontend/src/routes/listen/+page.svelte`)

**New State Variables**:
```typescript
let midiOutputEnabled = false;
let midiOutputDevices: Array<...> = [];
let selectedMidiOutputDevice: string | null = null;
let midiOutputConnected = false;
let loadingMidiDevices = false;
let midiOutputError = '';
```

**New Functions**:
- `loadMidiOutputDevices()`: Fetch available devices
- `toggleMidiOutput(enabled, device)`: Enable/disable + set device
- `connectMidiOutput(device)`: Connect to specific device

**UI Component**:
- Checkbox to enable/disable MIDI output
- Status indicator (🎹 Connected / 🔌 Disconnected)
- Dropdown to select output device
- Error message display

**Styling**:
- Integrated into playback card
- Consistent with existing design language
- Responsive on mobile
- Visual feedback for connected state

## Data Flow

```
MIDI Playback File
    ↓
NoteEvent (time, note, velocity, duration)
    ↓
_process_note_events() detects note start/stop
    ↓
_send_midi_note_on(note, velocity):
  - Apply volume multiplier to velocity
  - Clamp to 0-127 range
  - Send via midi_output_service
    ↓
USBMIDIOutputService.send_note_on()
    ↓
mido.Message('note_on', note=note, velocity=adjusted_velocity, channel=0)
    ↓
USB Keyboard receives MIDI event
    ↓
Keyboard plays sound synchronized with LEDs
```

## Key Features

### 1. **Calibrated Velocity Handling**
```python
adjusted_velocity = max(1, int(velocity * self._volume_multiplier))
adjusted_velocity = min(127, adjusted_velocity)
```
- Respects playback volume multiplier setting
- Minimum velocity of 1 (prevents silent notes)
- Clamped to MIDI valid range

### 2. **Active Note Tracking**
- `_midi_notes_sent` dict tracks which notes have been sent
- Ensures note_off only sent for notes that had note_on
- Prevents orphaned notes

### 3. **Clean Shutdown**
- `stop_playback()` sends note_off for all active notes
- Prevents hanging notes if playback interrupted
- Clears tracking dictionaries

### 4. **Optional Architecture**
- Import guarded with try/except
- Gracefully degrades if mido not available
- Works with or without USB device connected

## Settings Integration

### Enable/Disable MIDI Output
```python
settings_service.set_setting('hardware', 'midi_output_enabled', True/False)
playback_service._load_midi_output_settings()
```

### Select Device
```python
settings_service.set_setting('hardware', 'midi_output_device', 'Device Name')
```

### Persistence
Settings saved to SQLite database and restored on app restart

## Testing Considerations

### Unit Tests Should Cover
1. MIDI output service device enumeration
2. Note on/off message sending
3. Velocity clamping and multiplier application
4. Active note tracking
5. Clean shutdown with note_off

### Integration Tests Should Verify
1. Playback with MIDI output enabled
2. Volume multiplier affects velocity correctly
3. Device connection/disconnection
4. Settings persistence
5. Frontend toggle updates backend correctly

### Manual Testing
1. Connect USB MIDI keyboard to system
2. Enable MIDI output toggle on Listen page
3. Select USB keyboard from dropdown
4. Play MIDI file - keyboard should receive note events
5. Verify volume multiplier affects velocity
6. Test stop playback sends all note_offs

## Backward Compatibility

✅ **Fully Backward Compatible**
- MIDI output disabled by default (`False`)
- Optional parameter in PlaybackService (`midi_output_service=None`)
- Existing code paths unchanged
- No breaking changes to PlaybackService API

## Performance Impact

**Minimal**:
- Adds one MIDI send per note start/stop during playback
- No LED visualization impact
- Thread-safe design prevents blocking
- mido handles async MIDI sending

## Known Limitations

1. **Single MIDI Output Channel**: Currently sends on channel 0 only
   - Could extend to support per-note channel mapping

2. **No Pitch Bend/CC Support**: Currently note_on/note_off only
   - Could add volume CC (CC7), modulation (CC1), etc.

3. **No MIDI Timing Clock**: Playback timing is software-based
   - Keyboard follows playback, not vice versa

4. **Device Auto-Selection**: Picks first available device if not specified
   - User should explicitly select if multiple devices present

## Future Enhancements

1. **Per-Note Channel Assignment**: Route different octaves/ranges to different channels
2. **Velocity Curve Calibration**: Allow remapping velocity ranges
3. **MIDI CC Support**: Send volume/modulation/expression CCs
4. **Channel Separation**: Route melody to channel 0, accompaniment to channel 1, etc.
5. **Loopback Feedback**: Monitor USB keyboard input to trigger LED visualization

## Files Modified

### Backend
- `backend/usb_midi_output_service.py` - **NEW**
- `backend/playback_service.py` - Enhanced with MIDI output
- `backend/services/settings_service.py` - Added MIDI output settings
- `backend/app.py` - Initialize service + add endpoints

### Frontend
- `frontend/src/routes/listen/+page.svelte` - Added UI toggle and device selector

## Deployment Notes

1. **Mido Requirement**: Already in `requirements.txt` (v1.3.2)
2. **Python-rtmidi**: Already in `requirements.txt` (v1.5.8)
3. **No Database Migration**: New settings have defaults
4. **Frontend Build**: No new dependencies
5. **API Stable**: New endpoints don't conflict with existing routes

## Quick Start

### For Users
1. Open Listen page
2. Enable "Send MIDI to USB Keyboard" toggle
3. Select USB keyboard from dropdown
4. Play MIDI file - keyboard will receive MIDI events

### For Developers
1. Check `usb_midi_output_service.py` for service implementation
2. Review MIDI send logic in `playback_service.py._send_midi_note_on()`
3. Test with `pytest backend/tests/` for unit tests
4. Verify endpoints with `curl /api/midi-output/devices`

## Status: ✅ COMPLETE AND READY FOR TESTING
