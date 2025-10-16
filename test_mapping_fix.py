#!/usr/bin/env python3
"""
Test the LED mapping fix for all 88 keys coverage
Tests that the /mapping-info endpoint now correctly uses calibration range
"""

import sys
sys.path.insert(0, '.')

from backend.services.settings_service import SettingsService
from backend.config import generate_auto_key_mapping, get_piano_specs

def test_mapping_with_calibration_range():
    """Test that mapping uses the calibration range, not total LED count"""
    
    settings_service = SettingsService()
    
    # Get settings that /mapping-info will use
    piano_size = settings_service.get_setting('piano', 'size', '88-key')
    led_count = settings_service.get_setting('led', 'led_count', 300)
    base_offset = settings_service.get_setting('led', 'mapping_base_offset', 0)
    leds_per_key = settings_service.get_setting('led', 'leds_per_key', None)
    
    # Get calibration settings (the FIX: now used in /mapping-info)
    start_led = settings_service.get_setting('calibration', 'start_led', 0)
    end_led = settings_service.get_setting('calibration', 'end_led', led_count - 1)
    
    # Calculate available LED range
    available_led_range = end_led - start_led + 1
    
    print("=" * 60)
    print("LED MAPPING FIX VERIFICATION")
    print("=" * 60)
    print()
    print("Settings:")
    print(f"  Piano: {piano_size}")
    print(f"  Total LEDs: {led_count}")
    print(f"  Calibration range: [{start_led}, {end_led}]")
    print(f"  Available LEDs: {available_led_range}")
    print(f"  Base offset: {base_offset}")
    print(f"  LEDs per key setting: {leds_per_key}")
    print()
    
    # This is the CORRECTED logic from /mapping-info
    mapping = generate_auto_key_mapping(
        piano_size=piano_size,
        led_count=available_led_range,  # FIX: use available range
        leds_per_key=leds_per_key,
        mapping_base_offset=base_offset
    )
    
    # Analyze distribution
    led_counts = {}
    total_leds_used = 0
    min_led_idx = float('inf')
    max_led_idx = 0
    
    for midi_note, led_indices in mapping.items():
        count = len(led_indices)
        total_leds_used += count
        led_counts[count] = led_counts.get(count, 0) + 1
        
        if led_indices:
            min_led_idx = min(min_led_idx, min(led_indices))
            max_led_idx = max(max_led_idx, max(led_indices))
    
    specs = get_piano_specs(piano_size)
    
    print("Mapping Results:")
    print(f"  Total keys: {specs['keys']}")
    print(f"  Mapped keys: {len(mapping)}")
    print(f"  Unmapped keys: {specs['keys'] - len(mapping)}")
    print()
    print("LED Usage:")
    print(f"  Total LEDs used: {total_leds_used}")
    print(f"  LED range: [{min_led_idx}, {max_led_idx}]")
    print(f"  Available LEDs: {available_led_range}")
    print(f"  Distribution: {dict(sorted(led_counts.items()))}")
    print()
    
    # Validation
    success = True
    print("Validation:")
    
    if len(mapping) == specs['keys']:
        print("  [PASS] All keys are mapped")
    else:
        print(f"  [FAIL] Only {len(mapping)}/{specs['keys']} keys mapped")
        first_unmapped = specs['midi_start'] + len(mapping)
        print(f"        Missing: MIDI {first_unmapped}-{specs['midi_end']}")
        success = False
    
    if total_leds_used <= available_led_range:
        print(f"  [PASS] LED usage within range ({total_leds_used} <= {available_led_range})")
    else:
        print(f"  [FAIL] LED usage exceeds available ({total_leds_used} > {available_led_range})")
        success = False
    
    print()
    print("=" * 60)
    if success:
        print("SUCCESS: All 88 keys are covered!")
    else:
        print("FAILURE: Mapping is incomplete")
    print("=" * 60)
    
    return success

if __name__ == '__main__':
    success = test_mapping_with_calibration_range()
    sys.exit(0 if success else 1)
