#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')

from backend.services.settings_service import SettingsService
from backend.config import get_canonical_led_mapping, apply_calibration_offsets_to_mapping

settings_service = SettingsService()

print("DEBUG: Checking offset conversion and application\n")

# Check raw offsets
key_offsets_raw = settings_service.get_setting('calibration', 'key_offsets', {})
print(f"1. Raw key_offsets from settings: {key_offsets_raw}")

# Check conversion (MIDI to key index)
converted_offsets = {}
for midi_note_str, offset_value in key_offsets_raw.items():
    try:
        midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
        key_index = midi_note - 21
        if 0 <= key_index < 88:
            converted_offsets[key_index] = offset_value
            print(f"   MIDI {midi_note} -> key index {key_index}, offset {offset_value}")
    except (ValueError, TypeError):
        pass

print(f"\n2. Converted offsets: {converted_offsets}")

# Get the actual canonical mapping
result = get_canonical_led_mapping(settings_service)
print(f"\n3. Canonical mapping success: {result['success']}")
if result['success']:
    mapping = result['mapping']
    # Key index 9 is MIDI note 30
    key_9_leds = mapping.get(9, None)
    print(f"   Key index 9 (MIDI 30) LEDs: {key_9_leds}")
    
    # Compare with other keys
    print(f"\n   Sample of mapping (first 5 keys):")
    for k in sorted(list(mapping.keys())[:5]):
        print(f"     Key {k}: {mapping[k]}")
else:
    print(f"   Error: {result['error']}")
