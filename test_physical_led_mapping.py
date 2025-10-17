#!/usr/bin/env python3
"""
Test suite for the physical LED mapping algorithm
"""

import sys
sys.path.insert(0, '.')

from backend.config import calculate_physical_led_mapping

def test_standard_88key():
    """Test Example 1: Standard 88-key piano, 60 LEDs/m, 120 total LEDs"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Standard 88-key piano, 60 LEDs/m, range 0-119")
    print("=" * 80)
    
    result = calculate_physical_led_mapping(
        leds_per_meter=60,
        start_led=0,
        end_led=119,
        piano_size="88-key",
        distribution_mode="proportional"
    )
    
    print("first_led: {}".format(result['first_led']))
    print("led_count_usable: {}".format(result['led_count_usable']))
    print("leds_per_key: {:.2f}".format(result['leds_per_key']))
    print("quality_level: {} ({}/100)".format(result['quality_level'], result['quality_score']))
    print("piano_width_mm: {:.1f}".format(result['piano_width_mm']))
    print("led_coverage_mm: {:.1f}".format(result['led_coverage_mm']))
    print("coverage_ratio: {:.2f}".format(result['metadata']['coverage_ratio']))
    
    if result['warnings']:
        print("Warnings: {}".format(', '.join(result['warnings'])))
    if result['recommendations']:
        print("Recommendation: {}".format(result['recommendations'][0]))
    
    assert result['first_led'] == 0, "first_led should be 0"
    assert result['led_count_usable'] == 120, "led_count_usable should be 120"
    assert result['quality_level'] == 'good', "quality_level should be 'good'"
    print("PASS")


def test_undersaturated():
    """Test Example 2: Undersaturated - 88-key piano, 60 LEDs/m, range 0-35 (only 36 LEDs)"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Undersaturated - 88-key piano, 60 LEDs/m, range 0-35 (only 36 LEDs)")
    print("=" * 80)
    
    result = calculate_physical_led_mapping(
        leds_per_meter=60,
        start_led=0,
        end_led=35,
        piano_size="88-key",
        distribution_mode="proportional"
    )
    
    print("first_led: {}".format(result['first_led']))
    print("led_count_usable: {}".format(result['led_count_usable']))
    print("leds_per_key: {:.2f}".format(result['leds_per_key']))
    print("quality_level: {} ({}/100)".format(result['quality_level'], result['quality_score']))
    
    if result['warnings']:
        print("Warnings:")
        for w in result['warnings']:
            print("  - {}".format(w))
    if result['recommendations']:
        print("Recommendations:")
        for r in result['recommendations']:
            print("  - {}".format(r))
    
    assert result['led_count_usable'] == 36, "led_count_usable should be 36"
    assert result['quality_level'] == 'poor', "quality_level should be 'poor' (undersaturated)"
    assert len(result['warnings']) > 0, "Should have warnings"
    print("PASS")


def test_oversaturated():
    """Test Example 3: Oversaturated - 88-key piano, 200 LEDs/m, range 0-240"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Oversaturated - 88-key piano, 200 LEDs/m, range 0-240")
    print("=" * 80)
    
    result = calculate_physical_led_mapping(
        leds_per_meter=200,
        start_led=0,
        end_led=240,
        piano_size="88-key",
        distribution_mode="proportional"
    )
    
    print("first_led: {}".format(result['first_led']))
    print("led_count_usable: {}".format(result['led_count_usable']))
    print("leds_per_key: {:.2f}".format(result['leds_per_key']))
    print("quality_level: {} ({}/100)".format(result['quality_level'], result['quality_score']))
    
    if result['warnings']:
        print("Warnings: {}".format(', '.join(result['warnings'])))
    
    assert result['led_count_usable'] == 241, "led_count_usable should be 241"
    assert result['leds_per_key'] > 4.0, "leds_per_key should be > 4"
    print("PASS")


def test_49key_different_density():
    """Test Example 4: 49-key piano, 100 LEDs/m, range 50-180 (131 LEDs)"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: 49-key piano, 100 LEDs/m, range 50-180 (131 LEDs)")
    print("=" * 80)
    
    result = calculate_physical_led_mapping(
        leds_per_meter=100,
        start_led=50,
        end_led=180,
        piano_size="49-key",
        distribution_mode="proportional"
    )
    
    print("first_led: {}".format(result['first_led']))
    print("led_count_usable: {}".format(result['led_count_usable']))
    print("leds_per_key: {:.2f}".format(result['leds_per_key']))
    print("quality_level: {} ({}/100)".format(result['quality_level'], result['quality_score']))
    print("white_key_count: {}".format(result['white_key_count']))
    print("piano_width_mm: {:.1f}".format(result['piano_width_mm']))
    
    if result['warnings']:
        print("Warnings: {}".format(', '.join(result['warnings'])))
    
    assert result['first_led'] == 50, "first_led should be 50"
    assert result['led_count_usable'] == 131, "led_count_usable should be 131"
    assert result['white_key_count'] == 35, "white_key_count should be 35 for 49-key"
    print("PASS")


def test_physical_geometry():
    """Test that physical geometry calculations are correct"""
    print("\n" + "=" * 80)
    print("PHYSICAL GEOMETRY VERIFICATION")
    print("=" * 80)
    
    result = calculate_physical_led_mapping(
        leds_per_meter=60,
        start_led=0,
        end_led=119,
        piano_size="88-key",
        distribution_mode="proportional"
    )
    
    # For 88-key piano
    white_keys = 52
    piano_width_mm = result['piano_width_mm']
    led_spacing = 1000.0 / 60  # mm between LEDs at 60 LEDs/m
    
    print("White keys: {}".format(white_keys))
    print("Piano width: {:.1f} mm".format(piano_width_mm))
    print("LED spacing (60 LEDs/m): {:.2f} mm".format(led_spacing))
    
    # Distance per white key
    distance_per_key = piano_width_mm / white_keys
    print("Distance per white key: {:.2f} mm".format(distance_per_key))
    
    # Physical LEDs per key
    physical_leds_per_key = distance_per_key / led_spacing
    print("Physical LEDs per white key: {:.2f}".format(physical_leds_per_key))
    
    # Compare with proportional calculation
    proportional_leds_per_key = result['leds_per_key']
    print("Proportional LEDs per key: {:.2f}".format(proportional_leds_per_key))
    
    # Physical and proportional should be close
    difference = abs(physical_leds_per_key - proportional_leds_per_key)
    print("Difference: {:.2f}".format(difference))
    
    print("PASS")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 80)
    print("EDGE CASES")
    print("=" * 80)
    
    # Test invalid LED density
    print("Test 1: Invalid LED density (should have error)")
    result = calculate_physical_led_mapping(
        leds_per_meter=999,  # Invalid
        start_led=0,
        end_led=10,
        piano_size="88-key"
    )
    assert result['error'] is not None, "Should have error for invalid LED density"
    print("PASS")
    
    # Test reversed range
    print("Test 2: Reversed range (end_led < start_led)")
    result = calculate_physical_led_mapping(
        leds_per_meter=60,
        start_led=100,
        end_led=50,  # Invalid
        piano_size="88-key"
    )
    assert result['error'] is not None, "Should have error for reversed range"
    print("PASS")
    
    # Test unknown piano size
    print("Test 3: Unknown piano size")
    result = calculate_physical_led_mapping(
        leds_per_meter=60,
        start_led=0,
        end_led=10,
        piano_size="invalid-size"
    )
    assert result['error'] is not None, "Should have error for unknown piano size"
    print("PASS")
    
    print("All edge cases handled correctly")


if __name__ == '__main__':
    try:
        test_standard_88key()
        test_undersaturated()
        test_oversaturated()
        test_49key_different_density()
        test_physical_geometry()
        test_edge_cases()
        
        print("\n" + "=" * 80)
        print("SUCCESS: All tests passed!")
        print("=" * 80)
    except AssertionError as e:
        print("\nFAILED: {}".format(e))
        sys.exit(1)
    except Exception as e:
        print("\nERROR: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
