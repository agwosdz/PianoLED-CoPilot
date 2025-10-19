# MIDI Playback Audit - USB Keyboard Event Sending

## Summary
**The playback service is currently NOT sending MIDI events to the USB keyboard (or any external MIDI output device).**

## Current Architecture

### PlaybackService (`backend/playback_service.py`)
- **Purpose**: Coordinates MIDI playback with LED visualization
- **Scope**: Read-only from MIDI files, LED output only
- **What it does**:
  - Loads and parses MIDI files via `MIDIParser`
  - Processes note events with timing
  - Sends note events to LED controller only (via `_update_leds()`)
  - Tracks active notes internally

### Key Finding: No MIDI Output
The playback service has no capability to send MIDI events to:
- USB keyboard devices
- External synthesizers
- MIDI output ports
- Any other MIDI device

### Evidence
1. **No MIDI Output Imports**: 
   - No `mido.open_output()` calls
   - No MIDI output device enumeration
   - No MIDI message sending code

2. **Note Event Processing**:
   ```python
   def _process_note_events(self):
       """Process note events at current time"""
       current_time = self._current_time
       
       # Find notes that should start now
       for event in self._note_events:
           if abs(event.time - current_time) < 0.02:
               if event.note not in self._active_notes:
                   self._active_notes[event.note] = current_time + event.duration
                   logger.debug(f"Note ON: {event.note} at {current_time:.2f}s")
       
       # Remove notes that should end
       # ... (only removes from internal tracking)
   ```
   - Only logs note events
   - Updates internal `_active_notes` dict
   - Does not send MIDI messages anywhere

3. **LED Updates Only**:
   ```python
   def _update_leds(self):
       """Update LED display based on active notes"""
       if not self._led_controller:
           return
       
       # Prepare LED data for batch update
       led_data = {}
       
       # Map active notes to LEDs using multi-LED mapping
       for note in self._active_notes.keys():
           led_indices = self._map_note_to_leds(note)
           color = self._get_note_color(note)
           # ... updates LED controller only
   ```

## Current MIDI Flow

```
USB Keyboard Input
    ↓
USBMIDIInputService (receives note events)
    ↓
MIDIInputManager (unifies USB and rtpMIDI)
    ↓
WebSocket Events (browser)
    ↓
LED Controller (visualization)

MIDI File Playback
    ↓
PlaybackService (loads MIDI)
    ↓
LED Controller (visualization)
    ↓
❌ No MIDI Output to USB Keyboard
```

## What's Available in System
- **mido** (v1.3.2) - MIDI library with input/output support
- **python-rtmidi** (v1.5.8) - Cross-platform MIDI support
- **MIDI Input**: Fully implemented for USB and rtpMIDI
- **MIDI Output**: Not implemented

## Next Steps if Needed
To enable USB keyboard MIDI output from playback, you would need:

1. **Create MIDI Output Service**:
   - Similar to `USBMIDIInputService`
   - Use `mido.open_output()` to enumerate output devices
   - Send `note_on` and `note_off` messages during playback

2. **Extend PlaybackService**:
   - Accept optional MIDI output device name
   - Send messages when notes start/stop
   - Example:
     ```python
     def _process_note_events(self):
         for event in self._note_events:
             if event.time matches current_time:
                 self._midi_output.send(mido.Message('note_on', note=event.note, velocity=event.velocity))
         for note in notes_to_end:
             self._midi_output.send(mido.Message('note_off', note=note))
     ```

3. **Add API Endpoints**:
   - Select MIDI output device
   - Enable/disable MIDI output during playback

## Files Involved
- `backend/playback_service.py` - Main playback logic (no MIDI output)
- `backend/app.py` - API endpoints for playback
- `backend/usb_midi_service.py` - USB MIDI input only
- `backend/midi_input_manager.py` - Unified MIDI input manager
- `backend/requirements.txt` - Has `mido` and `python-rtmidi` available

## Recommendation
The current design is intentional - playback is visualization-focused. If loopback functionality (playback → USB keyboard) is desired, it would require:
- Explicit design decision
- New service module for MIDI output
- Configuration to select output device
- API endpoints to manage output settings
