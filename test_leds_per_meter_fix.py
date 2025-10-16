#!/usr/bin/env python3
"""
Test script to verify leds_per_meter fix is working correctly.
Tests both the validator and the settings service.
"""

import sys
import os
sys.path.insert(0, '.')

from backend.services.settings_validator import SettingsValidator
from backend.services.settings_service import SettingsService

def test_validator():
    """Test that validator accepts leds_per_meter"""
    print("\n" + "="*60)
    print("TEST 1: Validator Schema")
    print("="*60)
    
    schema = SettingsValidator._get_category_schema('led')
    if 'leds_per_meter' not in schema:
        print("❌ FAIL: leds_per_meter not in schema")
        return False
    
    print("✅ leds_per_meter found in schema")
    print(f"   Schema: {schema['leds_per_meter']}")
    
    # Test validation of various values
    test_values = [60, 72, 100, 120, 144, 160, 180, 200]
    print(f"\n✅ Valid enum values: {test_values}")
    
    for value in test_values:
        test_payload = {'led': {'leds_per_meter': value}}
        normalized, errors = SettingsValidator.validate_and_normalize(test_payload)
        
        if errors:
            print(f"❌ FAIL for value {value}: {errors}")
            return False
        
        if normalized.get('led', {}).get('leds_per_meter') != value:
            print(f"❌ FAIL for value {value}: normalized to {normalized}")
            return False
        
        print(f"   ✓ {value} → validated and normalized correctly")
    
    # Test invalid value
    print("\n✅ Testing invalid value (150):")
    test_payload = {'led': {'leds_per_meter': 150}}
    normalized, errors = SettingsValidator.validate_and_normalize(test_payload)
    
    if errors:
        print(f"   ✓ Correctly rejected: {errors[0]}")
    else:
        print(f"   ❌ FAIL: Should have rejected 150, got: {normalized}")
        return False
    
    return True

def test_settings_service():
    """Test that settings service can save and retrieve leds_per_meter"""
    print("\n" + "="*60)
    print("TEST 2: Settings Service Persistence")
    print("="*60)
    
    # Create temp database for testing
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    try:
        service = SettingsService(db_path=test_db)
        
        # Test save and retrieve
        print(f"\n✅ Testing save/retrieve cycle:")
        
        test_value = 180
        result = service.update_settings({
            'led': {
                'leds_per_meter': test_value,
                'led_count': 255,
                'brightness': 0.8
            }
        })
        
        if not result:
            print(f"❌ FAIL: update_settings returned False")
            return False
        
        print(f"   ✓ Saved leds_per_meter={test_value}")
        
        # Retrieve and verify
        retrieved = service.get_setting('led', 'leds_per_meter')
        if retrieved != test_value:
            print(f"❌ FAIL: Retrieved {retrieved}, expected {test_value}")
            return False
        
        print(f"   ✓ Retrieved leds_per_meter={retrieved}")
        
        # Test get_all_settings
        all_settings = service.get_all_settings()
        if all_settings['led']['leds_per_meter'] != test_value:
            print(f"❌ FAIL: get_all_settings returned {all_settings['led']['leds_per_meter']}")
            return False
        
        print(f"   ✓ get_all_settings returns correct value")
        
        return True
        
    finally:
        os.remove(test_db)

def main():
    """Run all tests"""
    print("\n" + "🎹"*30)
    print("LED Density (leds_per_meter) Fix - Verification Tests")
    print("🎹"*30)
    
    tests = [
        ("Validator", test_validator),
        ("Settings Service", test_settings_service),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - leds_per_meter fix is working!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - please review the output above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
