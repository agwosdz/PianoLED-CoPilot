#!/usr/bin/env python3
"""
Test script to verify optimal LED-to-key mapping using calibration range
"""
import sys
sys.path.insert(0, '.')

from backend.config import generate_auto_key_mapping

# Test case: 88-key piano with 255 total LEDs, calibration range [4-249] = 246 usable
# With current approach using mapping_base_offset=4 and led_count=246
print("=" * 70)
print("TEST: 88-key Piano with 246 usable LEDs (range 4-249)")
print("=" * 70)

# Method 1: Pass available range size with offset
mapping = generate_auto_key_mapping(
    piano_size="88-key",
    led_count=246,  # Available usable LEDs
    mapping_base_offset=4,  # Start at LED 4
    distribution_mode="proportional"
)

print(f"\nGenerated mapping for 88 keys:")
print(f"  Total keys mapped: {len(mapping)}")

if mapping:
    min_key = min(mapping.keys())
    max_key = max(mapping.keys())
    
    # Show first 5 keys
    print(f"\nFirst 5 keys (A0-E0):")
    for midi_note in range(21, 26):  # A0=21, ..., E0=25
        if midi_note in mapping:
            leds = mapping[midi_note]
            print(f"  MIDI {midi_note}: LEDs {leds}")
    
    # Show middle keys
    print(f"\nMiddle keys (A4):")
    for midi_note in range(69, 72):  # Around A4=69
        if midi_note in mapping:
            leds = mapping[midi_note]
            print(f"  MIDI {midi_note}: LEDs {leds}")
    
    # Show last 5 keys
    print(f"\nLast 5 keys (E8-C8):")
    for midi_note in range(104, 109):  # Around E8=104, ..., C8=108
        if midi_note in mapping:
            leds = mapping[midi_note]
            print(f"  MIDI {midi_note}: LEDs {leds}")
    
    # Calculate actual LED usage
    all_leds_used = set()
    for leds in mapping.values():
        if isinstance(leds, list):
            all_leds_used.update(leds)
    
    min_led = min(all_leds_used) if all_leds_used else None
    max_led = max(all_leds_used) if all_leds_used else None
    
    print(f"\nLED Range Usage:")
    print(f"  Minimum LED index: {min_led}")
    print(f"  Maximum LED index: {max_led}")
    print(f"  Total unique LEDs used: {len(all_leds_used)}")
    print(f"  Expected range: [4, 249]")
    
    # Verify no waste
    expected_total = 246
    if len(all_leds_used) == expected_total:
        print(f"  ✅ Perfect mapping - all 246 LEDs used!")
    else:
        print(f"  ⚠️  {expected_total - len(all_leds_used)} LEDs wasted")
else:
    print("ERROR: Mapping is empty!")

print("\n" + "=" * 70)
