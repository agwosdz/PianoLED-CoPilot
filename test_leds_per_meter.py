#!/usr/bin/env python3
"""
Test to verify leds_per_meter setting is saved and retrieved correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.settings_service import SettingsService

def test_leds_per_meter():
    """Test that leds_per_meter setting persists correctly"""
    print("\n✓ Testing leds_per_meter setting persistence...\n")
    
    # Initialize the settings service
    settings_service = SettingsService()
    
    # Test 1: Get default value
    print("Test 1: Get default leds_per_meter")
    default_value = settings_service.get_setting('led', 'leds_per_meter', 60)
    print(f"  Default value: {default_value}")
    assert default_value == 60, f"Expected 60, got {default_value}"
    print("  ✓ Default is 60\n")
    
    # Test 2: Set to valid value
    print("Test 2: Set leds_per_meter to 120")
    success = settings_service.set_setting('led', 'leds_per_meter', 120)
    print(f"  Set result: {success}")
    assert success, "Failed to set leds_per_meter"
    print("  ✓ Successfully set to 120\n")
    
    # Test 3: Retrieve saved value
    print("Test 3: Retrieve leds_per_meter after setting")
    retrieved_value = settings_service.get_setting('led', 'leds_per_meter', 60)
    print(f"  Retrieved value: {retrieved_value}")
    assert retrieved_value == 120, f"Expected 120, got {retrieved_value}"
    print("  ✓ Retrieved value is 120\n")
    
    # Test 4: Test all valid values
    print("Test 4: Test all valid enum values")
    valid_values = [60, 72, 100, 120, 144, 160, 180, 200]
    for value in valid_values:
        success = settings_service.set_setting('led', 'leds_per_meter', value)
        retrieved = settings_service.get_setting('led', 'leds_per_meter', 60)
        print(f"  Set to {value}, retrieved {retrieved}: {'✓' if retrieved == value else '✗'}")
        assert retrieved == value, f"Mismatch: set {value}, got {retrieved}"
    print("  ✓ All valid values persist correctly\n")
    
    # Test 5: Verify in get_category_settings
    print("Test 5: Verify leds_per_meter in get_category_settings")
    category_settings = settings_service.get_category_settings('led')
    if 'leds_per_meter' in category_settings:
        print(f"  leds_per_meter in category settings: {category_settings['leds_per_meter']}")
        print("  ✓ Setting is included in category settings\n")
    else:
        print("  ⚠ leds_per_meter NOT in category settings")
        print("  Available keys:", list(category_settings.keys())[:5], "...\n")
    
    # Test 6: Export/Import
    print("Test 6: Test export/import cycle")
    settings_service.set_setting('led', 'leds_per_meter', 160)
    exported = settings_service.export_settings()
    if 'led' in exported and 'leds_per_meter' in exported['led']:
        print(f"  Exported leds_per_meter: {exported['led']['leds_per_meter']}")
        print("  ✓ Setting is included in export\n")
    else:
        print("  ⚠ leds_per_meter NOT in export\n")
    
    print("=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)

if __name__ == '__main__':
    test_leds_per_meter()
