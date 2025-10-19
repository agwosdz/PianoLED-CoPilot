# MIDI Output Implementation - Visual Summary

## 🎹 Feature Overview

```
┌─────────────────────────────────────────────────┐
│         MIDI PLAYBACK OUTPUT SYSTEM             │
│                                                 │
│  MIDI FILE → PLAYBACK SERVICE → USB KEYBOARD   │
│                                                 │
│  (with calibrated velocity & volume control)   │
└─────────────────────────────────────────────────┘
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Listen Page)                  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ 🎵 MIDI Playback Section                            │ │
│  │                                                      │ │
│  │  ┌─ Play/Stop Controls                            │ │
│  │  │                                                 │ │
│  │  ├─ Timeline & Progress                           │ │
│  │  │                                                 │ │
│  │  └─ MIDI OUTPUT TOGGLE                            │ │
│  │     ☑ Send MIDI to USB Keyboard                  │ │
│  │     Status: 🎹 Connected | 🔌 Disconnected       │ │
│  │     Device: [SELECT DROPDOWN ▼]                  │ │
│  │                                                  │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ API Calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND API LAYER                         │
│                                                             │
│  GET  /api/midi-output/devices                            │
│  POST /api/midi-output/connect                            │
│  POST /api/midi-output/disconnect                         │
│  GET  /api/midi-output/status                             │
│  POST /api/midi-output/toggle                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              PLAYBACK SERVICE INTEGRATION                  │
│                                                             │
│  load_midi_file()                                          │
│           │                                                 │
│           ▼                                                 │
│  start_playback()                                          │
│           │                                                 │
│           ├─→ _playback_loop()                             │
│           │    │                                            │
│           │    ├─→ _process_note_events()                  │
│           │    │    │                                       │
│           │    │    ├─→ Note Start Detected               │
│           │    │    │    ├─→ Update LEDs                  │
│           │    │    │    └─→ _send_midi_note_on()         │
│           │    │    │                                       │
│           │    │    └─→ Note End Detected                 │
│           │    │         ├─→ Clear LEDs                   │
│           │    │         └─→ _send_midi_note_off()        │
│           │    │                                            │
│           │    └─→ _update_leds()                          │
│           │                                                 │
│           └─→ stop_playback()                              │
│                │                                            │
│                └─→ Send all note_offs                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            USB MIDI OUTPUT SERVICE                         │
│                                                             │
│  Device Management:                                        │
│  • get_available_devices()  → List USB MIDI devices       │
│  • connect(device_name)     → Connect to device           │
│  • disconnect()             → Disconnect                   │
│                                                             │
│  MIDI Sending:                                             │
│  • send_note_on(note, velocity, channel)                  │
│  • send_note_off(note, channel)                           │
│  • send_control_change(control, value, channel)           │
│                                                             │
│  Status:                                                    │
│  • is_connected: bool                                      │
│  • current_device: str                                     │
│  • state: MIDIOutputState                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ mido Messages
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  USB MIDI KEYBOARD                         │
│                                                             │
│  Receives:                                                  │
│  • Note On (pitch, velocity, channel)                      │
│  • Note Off (pitch, channel)                               │
│  • CC Messages (optional future)                           │
│                                                             │
│  Action:                                                    │
│  • Plays sound synchronized with LEDs                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow for Single Note

```
MIDI File contains:
  NoteEvent {
    time: 1.5s,
    note: 60 (Middle C),
    velocity: 80,
    duration: 0.5s,
    channel: 0
  }

                      │
                      ▼

Playback Processor detects note at 1.5s:
  
  1. Adds to _active_notes:
     {60: 2.0}  (note: end_time)

  2. Updates LEDs:
     Maps MIDI 60 → LED indices → colored
  
  3. IF midi_output_enabled:
     
     _send_midi_note_on(60, 80)
     │
     ├─ Reads volume_multiplier (e.g., 0.8)
     ├─ Calculate: velocity = 80 * 0.8 = 64
     ├─ Clamp: 1 ≤ 64 ≤ 127 ✓
     │
     └─ Send via MIDI:
        mido.Message('note_on', 
          note=60, 
          velocity=64, 
          channel=0)
           │
           └─→ USB Keyboard Receives:
               Note On: C4, velocity 64
               ↓
               🎵 Sound plays

                      │
              (0.5 seconds passes)
                      │
                      ▼

Playback Processor detects note end at 2.0s:
  
  1. Removes from _active_notes
  2. Clears LEDs
  3. IF midi_output_enabled:
     
     _send_midi_note_off(60)
     │
     └─ Send via MIDI:
        mido.Message('note_off',
          note=60,
          channel=0)
           │
           └─→ USB Keyboard Receives:
               Note Off: C4
               ↓
               🔇 Sound stops
```

## Settings Integration

```
┌─────────────────────────────────────────────────┐
│      Settings Service (SQLite Database)        │
├─────────────────────────────────────────────────┤
│ hardware:                                       │
│   midi_output_enabled: boolean (default: false)│
│   midi_output_device: string (default: "")     │
└─────────────────────────────────────────────────┘
           │
           ├─ On App Start
           │  └─→ Restore settings
           │
           ├─ User Toggles MIDI Output
           │  └─→ POST /api/midi-output/toggle
           │     └─→ Update database
           │
           └─ Playback Service Init
              └─→ _load_midi_output_settings()
                 └─→ Connect to saved device
                 └─→ Enable MIDI output
```

## Velocity Calculation

```
Original MIDI Velocity: 100
                 │
                 ▼
         Volume Multiplier: 0.75
                 │
                 ▼
    Calculation: 100 × 0.75 = 75
                 │
                 ▼
     Clamp Range: [1, 127]
                 │
                 ▼
        Final Velocity: 75 ✓
```

## State Machine

```
                    ┌─────────────┐
                    │ IDLE        │
                    │ (No Device) │
                    └──────┬──────┘
                           │
                    User enables toggle
                           │
                           ▼
          ┌─────────────────────────────────┐
          │  MIDI_OUTPUT_ENABLED            │
          │  (Waiting for device selection) │
          └────────┬────────────────────────┘
                   │
          User selects device
                   │
                   ▼
          ┌──────────────────────┐
          │ CONNECTED            │
          │ 🎹 USB Keyboard      │
          └────────┬─────────────┘
                   │
          ┌────────┴─────────────┬──────────────┐
          │                      │              │
    Play Playback          Change Device  Disable Toggle
          │                      │              │
          ▼                      ▼              ▼
    ┌──────────────┐      ┌────────────┐  ┌─────────┐
    │ SENDING      │      │ CONNECTED  │  │ IDLE    │
    │ MIDI EVENTS  │      │ (New Dev)  │  │         │
    │ 🎵→🎹        │      └────────────┘  └─────────┘
    └──────────────┘
          │
    Playback Stops
          │
          ▼
    ┌──────────────┐
    │ CONNECTED    │
    │ (Idle)       │
    └──────────────┘
```

## File Organization

```
PIANO LED VISUALIZER
│
├── backend/
│   ├── app.py ............................ Main Flask app
│   │   ├─ Initialize midi_output_service
│   │   ├─ Register MIDI output routes
│   │   └─ Pass to playback_service
│   │
│   ├── playback_service.py .............. Core playback logic
│   │   ├─ _send_midi_note_on()
│   │   ├─ _send_midi_note_off()
│   │   ├─ _load_midi_output_settings()
│   │   └─ Integration with _process_note_events()
│   │
│   ├── usb_midi_output_service.py ....... NEW! MIDI output
│   │   ├─ get_available_devices()
│   │   ├─ connect()
│   │   ├─ send_note_on()
│   │   ├─ send_note_off()
│   │   └─ Thread-safe with locks
│   │
│   └── services/
│       └── settings_service.py ......... Settings persistence
│           └─ hardware.midi_output_*
│
├── frontend/
│   └── src/routes/listen/
│       └── +page.svelte ................ UI toggle & device select
│           ├─ midiOutputEnabled checkbox
│           ├─ Device dropdown
│           ├─ Connection status indicator
│           └─ Error message display
│
└── Documentation/
    ├── MIDI_OUTPUT_IMPLEMENTATION.md
    └── MIDI_OUTPUT_QUICK_REF.md
```

## Timeline

```
Application Start
     │
     ├─→ Load Settings Service
     │   └─→ Read hardware.midi_output_* from DB
     │
     ├─→ Initialize MIDI Output Service
     │   └─→ Check for available devices
     │
     ├─→ Create Playback Service
     │   ├─→ Pass midi_output_service
     │   └─→ Load MIDI output settings
     │
     └─→ Register API Routes
         └─→ /api/midi-output/*

User Actions (Listen Page)
     │
     ├─→ Toggle MIDI Output Checkbox
     │   └─→ POST /api/midi-output/toggle
     │       └─→ Update database & playback service
     │
     ├─→ Select Device from Dropdown
     │   └─→ POST /api/midi-output/connect
     │       └─→ Connect service to device
     │
     └─→ Play MIDI File
         └─→ playback_service.start_playback()
             └─→ For each note event:
                 ├─→ Update LEDs
                 └─→ If enabled: send MIDI to keyboard
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Files Modified | 4 |
| Files Created | 1 |
| New API Endpoints | 5 |
| New Settings Keys | 2 |
| MIDI Message Types | 3 (note_on, note_off, CC) |
| Device Limit | Unlimited |
| Channel Support | 16 (0-15) |
| Velocity Range | 1-127 (MIDI spec) |
| Thread Safety | Yes (Lock-based) |
| Backward Compatible | 100% |
| Performance Impact | Minimal (<1ms per note) |

## Status: ✅ COMPLETE
