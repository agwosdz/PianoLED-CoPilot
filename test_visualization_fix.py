#!/usr/bin/env python3
"""
Quick test to verify LED visualization respects distribution modes
"""

import sys
sys.path.insert(0, '/h/Development/Copilot/PianoLED-CoPilot')

from backend.services.settings_service import SettingsService
from backend.config_led_mapping_advanced import calculate_per_key_led_allocation

def test_distribution_modes():
    """Test that different distribution modes produce different LED allocations"""
    
    print("=" * 80)
    print("Testing LED Visualization Distribution Mode Fix")
    print("=" * 80)
    
    # Initialize settings service
    settings_service = SettingsService()
    
    # Test parameters
    leds_per_meter = 200
    start_led = 4
    end_led = 249
    piano_size = '88-key'
    
    print(f"\nTest Configuration:")
    print(f"  LEDs per meter: {leds_per_meter}")
    print(f"  LED range: {start_led}-{end_led}")
    print(f"  Piano size: {piano_size}")
    
    # Test Mode 1: With overlap (allow_led_sharing=True)
    print("\n" + "-" * 80)
    print("MODE 1: Piano Based (with overlap)")
    print("-" * 80)
    
    result_with_overlap = calculate_per_key_led_allocation(
        leds_per_meter=leds_per_meter,
        start_led=start_led,
        end_led=end_led,
        piano_size=piano_size,
        allow_led_sharing=True
    )
    
    if result_with_overlap.get('success'):
        stats = result_with_overlap.get('led_allocation_stats', {})
        print(f"✅ Mapping generated successfully")
        print(f"   Total keys: {stats.get('total_key_count', 0)}")
        print(f"   Total LEDs used: {stats.get('total_led_count', 0)}")
        print(f"   Avg LEDs/key: {stats.get('avg_leds_per_key', 0):.2f}")
        print(f"   Distribution: {stats.get('leds_per_key_distribution', {})}")
        
        mode1_led_count = stats.get('total_led_count', 0)
    else:
        print(f"❌ Mapping generation failed")
        return False
    
    # Test Mode 2: Without overlap (allow_led_sharing=False)
    print("\n" + "-" * 80)
    print("MODE 2: Piano Based (no overlap)")
    print("-" * 80)
    
    result_no_overlap = calculate_per_key_led_allocation(
        leds_per_meter=leds_per_meter,
        start_led=start_led,
        end_led=end_led,
        piano_size=piano_size,
        allow_led_sharing=False
    )
    
    if result_no_overlap.get('success'):
        stats = result_no_overlap.get('led_allocation_stats', {})
        print(f"✅ Mapping generated successfully")
        print(f"   Total keys: {stats.get('total_key_count', 0)}")
        print(f"   Total LEDs used: {stats.get('total_led_count', 0)}")
        print(f"   Avg LEDs/key: {stats.get('avg_leds_per_key', 0):.2f}")
        print(f"   Distribution: {stats.get('leds_per_key_distribution', {})}")
        
        mode2_led_count = stats.get('total_led_count', 0)
    else:
        print(f"❌ Mapping generation failed")
        return False
    
    # Verify the modes are different
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    allocation1 = result_with_overlap.get('led_allocation_data', {})
    allocation2 = result_no_overlap.get('led_allocation_data', {})
    
    # Check a few keys to see the difference
    print("\nLED allocation comparison for first 4 keys:")
    print(f"{'Key':<10} {'Mode 1 (overlap)':<20} {'Mode 2 (no overlap)':<20}")
    print("-" * 50)
    
    for midi_note in range(21, 25):  # First 4 keys (A0-C#1)
        leds1 = allocation1.get(midi_note, [])
        leds2 = allocation2.get(midi_note, [])
        key_name = ['A0', 'A#0', 'B0', 'C1'][midi_note - 21]
        print(f"{key_name:<10} {str(leds1):<20} {str(leds2):<20}")
    
    # Check if mappings are different
    if allocation1 != allocation2:
        print("\n✅ PASS: Distribution modes produce DIFFERENT LED allocations")
        print(f"   Mode 1 total allocations: {sum(len(v) for v in allocation1.values())}")
        print(f"   Mode 2 total allocations: {sum(len(v) for v in allocation2.values())}")
        return True
    else:
        print("\n❌ FAIL: Distribution modes produce IDENTICAL LED allocations")
        print("   This indicates the fix is not working correctly")
        return False

if __name__ == '__main__':
    success = test_distribution_modes()
    sys.exit(0 if success else 1)
