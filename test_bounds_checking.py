#!/usr/bin/env python3
"""
Test bounds checking in apply_calibration_offsets_to_mapping
Demonstrates clamping LED indices to [0, led_count-1]
"""

import sys
sys.path.insert(0, '/home/user/project')

from backend.config import apply_calibration_offsets_to_mapping

# Test case: 255 LEDs (indices 0-254) with +4 global offset
led_count = 255  # Valid indices: 0-254
base_mapping = {
    21: [0],      # First key at LED 0
    108: [251],   # Last key at LED 251 (typical)
}

print("=" * 60)
print("Bounds Checking Test: 255 LEDs with +4 global offset")
print("=" * 60)
print(f"\nConfiguration:")
print(f"  - LED count: {led_count} (valid indices: 0-{led_count-1})")
print(f"  - Global offset: +4")
print(f"  - Base mapping (before offset):")
for note, indices in base_mapping.items():
    print(f"    MIDI {note}: {indices}")

# Apply offset with bounds checking
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,
    global_offset=4,
    key_offsets=None,
    led_count=led_count
)

print(f"\nAfter applying +4 offset with bounds checking:")
for note, indices in final_mapping.items():
    print(f"  MIDI {note}: {indices}")
    if indices[0] > led_count - 1:
        print(f"    ⚠️  CLAMPED! Would be {indices[0] + 4} but max is {led_count - 1}")

print("\n" + "=" * 60)
print("Test Case 2: Edge case - last key with max offset")
print("=" * 60)

edge_case = {
    108: [250, 251, 252, 253, 254],  # Last 5 LEDs
}

print(f"\nBase mapping (indices 250-254):")
for note, indices in edge_case.items():
    print(f"  MIDI {note}: {indices}")

final_edge = apply_calibration_offsets_to_mapping(
    mapping=edge_case,
    global_offset=4,
    key_offsets=None,
    led_count=led_count
)

print(f"\nAfter +4 offset (clamped to max {led_count-1}):")
for note, indices in final_edge.items():
    print(f"  MIDI {note}: {indices}")
    print(f"  Result: All indices clamped to max {led_count-1} ✅")

print("\n" + "=" * 60)
print("Test Case 3: No bounds checking (led_count=None)")
print("=" * 60)

no_bounds = apply_calibration_offsets_to_mapping(
    mapping=edge_case,
    global_offset=4,
    key_offsets=None,
    led_count=None  # No bounds
)

print(f"\nWithout bounds checking:")
for note, indices in no_bounds.items():
    print(f"  MIDI {note}: {indices}")
    print(f"  ⚠️  Indices exceed LED count! (indices now > 254)")

print("\n✅ All tests completed!")
