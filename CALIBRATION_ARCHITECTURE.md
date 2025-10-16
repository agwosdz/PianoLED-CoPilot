# LED Calibration System Architecture

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (UI Layer)                               │
│                                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐    │
│  │ Calibration UI  │  │ Test/Preview     │  │ Settings Panel         │    │
│  │                 │  │                  │  │                        │    │
│  │ • Global Offset │  │ • Play key       │  │ • Import/Export       │    │
│  │   Slider        │  │ • Observe LED    │  │ • Reset               │    │
│  │ • Per-Key List  │  │ • Adjust         │  │ • Profile Management  │    │
│  │ • Enable/Disable│  │                  │  │                        │    │
│  └────────┬────────┘  └──────────┬───────┘  └────────────┬───────────┘    │
│           │                       │                        │                 │
└───────────┼───────────────────────┼────────────────────────┼─────────────────┘
            │                       │                        │
     REST API Calls           WebSocket Events        REST API Calls
            │                       │                        │
┌───────────▼───────────────────────▼────────────────────────▼─────────────────┐
│                          BACKEND (API Layer)                                  │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                    calibration_bp (REST Endpoints)                     │  │
│  │                                                                         │  │
│  │  GET/PUT /global-offset         GET/PUT /key-offset/{note}            │  │
│  │  GET     /key-offsets           PUT     /key-offsets                  │  │
│  │  GET     /status                POST    /enable, /disable, /reset     │  │
│  │  GET/POST /export, /import                                            │  │
│  └────────────────────┬───────────────────────────────────────────────────┘  │
│                       │                                                       │
│                       │ Sets/Gets Settings                                    │
│                       ▼                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                      SettingsService                                   │  │
│  │                   (SQLite Persistence)                                 │  │
│  │                                                                         │  │
│  │  calibration:           led:                                           │  │
│  │  ├─ global_offset       ├─ mapping_mode                               │  │
│  │  ├─ key_offsets         ├─ leds_per_key                              │  │
│  │  ├─ enabled             └─ mapping_base_offset                        │  │
│  │  ├─ mode                                                               │  │
│  │  └─ last_calibration                                                   │  │
│  └────────────────────┬───────────────────────────────────────────────────┘  │
│                       │                                                       │
│                       │ Loads Settings                                        │
│                       ▼                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                   MidiEventProcessor                                   │  │
│  │                                                                         │  │
│  │  Fields:                                                                │  │
│  │  • global_offset: int                                                  │  │
│  │  • key_offsets: Dict[int, int]                                         │  │
│  │  • calibration_enabled: bool                                           │  │
│  │  • _precomputed_mapping: Dict[int, List[int]]                         │  │
│  │                                                                         │  │
│  │  Method: _map_note_to_leds(midi_note) -> List[int]                   │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │ 1. Get base mapping:                                             │ │  │
│  │  │    base_indices = precomputed_mapping[midi_note]                 │ │  │
│  │  │                                                                   │ │  │
│  │  │ 2. If calibration_enabled:                                       │ │  │
│  │  │    adjusted = []                                                 │ │  │
│  │  │    for led_idx in base_indices:                                  │ │  │
│  │  │        adj = led_idx + global_offset                             │ │  │
│  │  │        adj += key_offsets.get(midi_note, 0)                      │ │  │
│  │  │        adj = clamp(adj, 0, num_leds-1)                           │ │  │
│  │  │        adjusted.append(adj)                                       │ │  │
│  │  │    return adjusted                                                │ │  │
│  │  │                                                                   │ │  │
│  │  │ 3. Else: return base_indices                                      │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────┬───────────────────────────────────────────────────┘  │
│                       │                                                       │
│                       │ Sends adjusted LED indices                            │
│                       ▼                                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                     LEDController                                      │  │
│  │                                                                         │  │
│  │  turn_on_led(led_index, color)   # Receives adjusted indices          │  │
│  │  turn_off_led(led_index)         # No calibration needed              │  │
│  │  show()                          # Update physical LED strip           │  │
│  └────────────────────┬───────────────────────────────────────────────────┘  │
└────────────────────────┼──────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  Physical LED Strip            │
        │  WS2812B / WS2811 / etc        │
        │  (100+ individual LEDs)        │
        │                                │
        │  🔴 🔴 🟡 🟡 🟢 🟢 🔵 🔵 ⚫   │
        │  Lights aligned with keys      │
        └────────────────────────────────┘
```

## Data Flow: Setting Global Offset

```
User UI
  │
  │ "Set global offset to +5"
  ▼
PUT /api/calibration/global-offset
  │ {"global_offset": 5}
  ▼
calibration.py (REST handler)
  │ Validates: -100 ≤ 5 ≤ 100 ✓
  ▼
SettingsService.set_setting('calibration', 'global_offset', 5)
  │ SQLite UPDATE
  ▼
[broadcast] socketio.emit('global_offset_changed', {global_offset: 5})
  │
  ▼ Next MIDI event:
USBMIDIInputService.handle_message()
  │
  ▼
MidiEventProcessor.handle_message()
  │ (already loaded global_offset=5)
  ▼
_map_note_to_leds(60)  # Middle C
  │ base = 40
  │ adjusted = 40 + 5 = 45
  │ clamp(45, 0, 99) = 45
  ▼ [45]
LEDController.turn_on_led(45, color)
  │
  ▼ LED 45 lights up (shifted by 5)
```

## Data Flow: Setting Per-Key Offset

```
User UI
  │
  │ "Middle C is off by -2 LEDs"
  ▼
PUT /api/calibration/key-offset/60
  │ {"offset": -2}
  ▼
calibration.py (REST handler)
  │ Validates: MIDI note 60 ✓, offset -2 in [-100, 100] ✓
  ▼
Get current key_offsets: {60: -2}
  │ (or merge with existing)
  ▼
SettingsService.set_setting('calibration', 'key_offsets', {60: -2})
  │ SQLite UPDATE
  ▼
[broadcast] socketio.emit('key_offset_changed', {midi_note: 60, offset: -2})
  │
  ▼ Next MIDI 60 event:
MidiEventProcessor._map_note_to_leds(60)
  │ base = 40
  │ global = global_offset (e.g., 5)
  │ adjusted = 40 + 5 + (-2) = 43
  │ clamp(43, 0, 99) = 43
  ▼ [43]
LEDController.turn_on_led(43, color)
  │
  ▼ LED 43 lights up
```

## Settings Hierarchy

```
SQLite Database
  │
  └─ settings table
     │
     ├─ category: 'calibration'
     │  ├─ key: 'global_offset'     value: 5          type: 'number'
     │  ├─ key: 'key_offsets'       value: {...}      type: 'object'
     │  ├─ key: 'calibration_enabled' value: true     type: 'boolean'
     │  ├─ key: 'calibration_mode'  value: 'manual'   type: 'string'
     │  └─ key: 'last_calibration'  value: '2025...'  type: 'string'
     │
     └─ category: 'led'
        ├─ key: 'mapping_mode'      value: 'auto'     type: 'string'
        ├─ key: 'leds_per_key'      value: 3          type: 'number'
        └─ key: 'mapping_base_offset' value: 0        type: 'number'
```

## Offset Application Order

For each MIDI note during runtime:

```
┌─ MIDI Note (0-127)
│
├─ Validate in range [min_midi_note, max_midi_note]
│
├─ Get base mapping from _precomputed_mapping[note]
│  (generated at startup via generate_auto_key_mapping)
│
├─ IF calibration_enabled == False
│  └─ RETURN base mapping unchanged
│
├─ ELSE (calibration enabled)
│  │
│  ├─ FOR EACH led_index IN base mapping
│  │  │
│  │  ├─ step1 = led_index + global_offset
│  │  │  "Add global shift"
│  │  │
│  │  ├─ step2 = step1 + key_offsets.get(midi_note, 0)
│  │  │  "Add per-key adjustment if available"
│  │  │
│  │  ├─ step3 = clamp(step2, 0, num_leds - 1)
│  │  │  "Ensure within valid range"
│  │  │
│  │  └─ adjusted.append(step3)
│  │
│  └─ RETURN adjusted list
│
└─ Send LED indices to LEDController
   (physical LEDs light up)
```

## State Transitions

```
                    ┌─────────────┐
                    │   DISABLED  │
                    │ offsets=0   │
                    └──────┬──────┘
                           │
                      [enable]
                           │
                           ▼
                    ┌─────────────┐
                    │   ENABLED   │
                    │ offsets in  │
                    │   effect    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    [global]         [key_offset]       [import]
    [offset]         [changed]          [backup]
    [changed]             │                 │
         │                │                 │
    ┌─────────────────────────────────────┐ │
    │  ADJUST MODE                        │ │
    │ • Refine global_offset              │ │
    │ • Fine-tune key_offsets             │ │
    │ • Test individual keys              │ │
    └─────────────────────────────────────┘ │
                                            │
                                      [reset]
                                       [all]
                                        │
                                        ▼
                               Back to DISABLED
```

## API Endpoint Hierarchy

```
/api/calibration
│
├─ /status               [GET]      Current state
├─ /enable               [POST]     Turn on calibration
├─ /disable              [POST]     Turn off calibration
├─ /reset                [POST]     Reset to defaults
│
├─ /global-offset        [GET/PUT]  Manage global shift
│
├─ /key-offset
│  ├─ /{midi_note}       [GET/PUT]  Individual key offset
│  └─ s                  [GET/PUT]  Batch key offsets
│
└─ /export               [GET]      Download calibration JSON
   /import               [POST]     Upload calibration JSON
```

## WebSocket Event Timeline

```
Timeline:
T0:  User enables calibration
     └─ Event: calibration_enabled

T1:  User adjusts global offset to +5
     └─ Event: global_offset_changed {offset: 5}

T2:  User adjusts Middle C offset to -2
     └─ Event: key_offset_changed {midi_note: 60, offset: -2}

T3:  User adjusts multiple keys
     └─ Event: key_offsets_changed {key_offsets: {...}}

T4:  User clicks reset
     └─ Event: calibration_reset {enabled: false, offsets: {}}
```

## Integration Points Summary

| Component | Integration | Purpose |
|-----------|-------------|---------|
| **SettingsService** | Stores all calibration data | Persistence |
| **MidiEventProcessor** | Loads & applies offsets | Runtime logic |
| **USBMIDIInputService** | Uses adjusted indices | MIDI routing |
| **calibration_bp** | REST interface | User control |
| **WebSocket** | Broadcasting events | Real-time UI sync |
| **LEDController** | Receives indices | Physical output |

This system is:
- ✅ Modular (independent calibration module)
- ✅ Persistent (settings stored in DB)
- ✅ Real-time (WebSocket updates)
- ✅ Extensible (ready for assisted calibration)
- ✅ Testable (unit tests included)
