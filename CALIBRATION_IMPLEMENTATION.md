# LED Calibration Implementation Summary

## Overview
Implemented comprehensive LED-to-key calibration logic to ensure LEDs align perfectly with piano keys and support fine-tuning adjustments for hardware imperfections and drift.

## Components Implemented

### 1. Settings Schema (`backend/services/settings_service.py`)
Added new `calibration` category with settings:
- **`global_offset`** (number, -100 to 100): Shifts all LEDs uniformly to account for LED strip starting position
- **`key_offsets`** (object): Per-key offset adjustments `{midi_note: offset_value}`
- **`calibration_enabled`** (boolean): Enable/disable calibration offsets
- **`calibration_mode`** (string): 'none', 'assisted', or 'manual'
- **`last_calibration`** (string): ISO timestamp of last calibration

Also added to `led` category:
- **`mapping_mode`**: 'auto', 'manual', 'proportional'
- **`leds_per_key`**: Number of LEDs per key (1-10)
- **`mapping_base_offset`**: Base offset for the entire mapping

### 2. MIDI Mapping Logic (`backend/midi/midi_event_processor.py`)
Enhanced `MidiEventProcessor` with:
- **Calibration fields** loaded on initialization:
  - `global_offset`: Global shift for all LEDs
  - `key_offsets`: Dictionary of per-note offsets
  - `calibration_enabled`: Enable/disable flag

- **Updated `_map_note_to_leds()`** method:
  - Applies global offset to all mapped LED indices
  - Applies per-key offsets when available
  - Clamps results to valid LED range [0, num_leds)
  - Example: Note 60 → LED 40 + global_offset(+5) + key_offset(+2) = LED 47

### 3. Configuration Helpers (`backend/config.py`)
Added `apply_calibration_offsets_to_mapping()` function:
- Takes a base key-to-LED mapping
- Applies global and per-key offsets
- Useful for preview/testing without runtime changes

### 4. REST API Endpoints (`backend/api/calibration.py`)
Complete RESTful API for calibration management:

#### Status & Control
- `GET /api/calibration/status` - Get current calibration state
- `POST /api/calibration/enable` - Enable calibration mode
- `POST /api/calibration/disable` - Disable calibration mode

#### Global Offset
- `GET /api/calibration/global-offset` - Get global offset
- `PUT /api/calibration/global-offset` - Set global offset

#### Per-Key Offsets
- `GET /api/calibration/key-offset/<midi_note>` - Get offset for specific key
- `PUT /api/calibration/key-offset/<midi_note>` - Set offset for specific key
- `GET /api/calibration/key-offsets` - Get all key offsets
- `PUT /api/calibration/key-offsets` - Batch update multiple key offsets

#### Calibration Management
- `POST /api/calibration/reset` - Reset all offsets to defaults
- `GET /api/calibration/export` - Export calibration as JSON
- `POST /api/calibration/import` - Import calibration from JSON

### 5. WebSocket Events
Emitted when calibration changes:
- `calibration_enabled` - Calibration mode turned on
- `calibration_disabled` - Calibration mode turned off
- `global_offset_changed` - Global offset updated
- `key_offset_changed` - Single key offset updated
- `key_offsets_changed` - Multiple key offsets updated
- `calibration_reset` - All offsets reset to defaults

## Usage Patterns

### Basic Global Offset
```python
# Shift all LEDs by 5 positions (e.g., LED strip longer than piano)
PUT /api/calibration/global-offset
{"global_offset": 5}
```

### Per-Key Fine Tuning
```python
# Adjust Middle C (MIDI 60) forward by 2 LEDs
PUT /api/calibration/key-offset/60
{"offset": 2}

# Adjust A0 (MIDI 21) backward by 1 LED
PUT /api/calibration/key-offset/21
{"offset": -1}
```

### Batch Import
```python
POST /api/calibration/import
{
  "global_offset": 3,
  "key_offsets": {
    "21": 1,
    "60": -2,
    "108": 1
  }
}
```

## Technical Details

### Offset Application Flow
1. MIDI note (e.g., 60) received
2. Look up base LED mapping in precomputed_mapping
3. If calibration enabled:
   - Add global_offset to each LED index
   - Add key_offset for this specific MIDI note if available
   - Clamp result to [0, num_leds)
4. Return adjusted LED indices

### Validation
- Global offset: -100 to +100 range
- Per-key offset: -100 to +100 range per key
- MIDI notes: 0-127 (validated per request)
- Offsets stored as integers (no fractional LEDs)

### Persistence
- All calibration settings stored in SQLite via SettingsService
- Timestamp recorded on each calibration update
- Export/import support for backup and configuration sharing

## Integration Points

1. **SettingsService**: Persists calibration data
2. **MidiEventProcessor**: Applies offsets during runtime
3. **REST API**: User interface for calibration
4. **WebSocket**: Real-time UI updates
5. **LED Controller**: Receives calibrated LED indices

## Backward Compatibility
- Calibration is disabled by default
- All offsets default to 0
- Existing mappings work unchanged when calibration disabled
- No breaking changes to existing APIs

## Future Enhancements
- **Assisted Calibration**: Auto-detect misalignment with guided LED testing
- **Calibration Profiles**: Save multiple calibration presets
- **Drift Compensation**: Progressive offset adjustment based on position in strip
- **Prediction Models**: ML-based offset calculation from sample readings
