#!/usr/bin/env python3
"""Debug canonical mapping generation"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from backend.services.settings_service import SettingsService
from backend.config import get_canonical_led_mapping

settings_service = SettingsService()

# Get some key settings
print("Settings:")
print(f"  start_led: {settings_service.get_setting('calibration', 'start_led', 4)}")
print(f"  end_led: {settings_service.get_setting('calibration', 'end_led', 249)}")
print(f"  led_count: {settings_service.get_setting('led', 'led_count', 255)}")

# Get canonical mapping
result = get_canonical_led_mapping(settings_service)
print(f"\nCanonical mapping result: {result['success']}")

if result['success']:
    mapping = result['mapping']
    
    # Check a few keys
    print("\nSample from canonical mapping:")
    for key_index in [0, 20, 40, 60, 80, 87]:
        leds = mapping.get(key_index)
        if leds:
            print(f"  Key {key_index:2d} (MIDI {key_index+21:3d}): {leds}")
        else:
            print(f"  Key {key_index:2d} (MIDI {key_index+21:3d}): NOT MAPPED")
    
    # Check LED ranges
    all_leds = set()
    for leds_list in mapping.values():
        all_leds.update(leds_list)
    
    if all_leds:
        print(f"\nLED range in canonical mapping:")
        print(f"  Min LED: {min(all_leds)}")
        print(f"  Max LED: {max(all_leds)}")
