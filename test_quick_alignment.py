#!/usr/bin/env python3
"""
Quick alignment test - simpler version
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

print("Testing component alignment...")

# 1. Canonical function
print("\n1. Testing get_canonical_led_mapping()...")
try:
    from backend.services.settings_service import SettingsService
    from backend.config import get_canonical_led_mapping
    
    settings = SettingsService()
    result = get_canonical_led_mapping(settings)
    canonical_mapping = result.get('mapping', {})
    
    print(f"   [OK] Loaded canonical mapping with {len(canonical_mapping)} keys")
    if 0 in canonical_mapping and 87 in canonical_mapping:
        print(f"   Sample: Key 0 -> {canonical_mapping[0]}")
        print(f"   Sample: Key 87 -> {canonical_mapping[87]}")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# 2. USB MIDI processor
print("\n2. Testing USB MIDI processor...")
try:
    from backend.midi.midi_event_processor import MidiEventProcessor
    
    processor = MidiEventProcessor(
        led_controller=None,
        settings_service=settings,
    )
    processor.refresh_runtime_settings()
    processor_mapping = processor._precomputed_mapping
    
    # Convert to key indices for comparison
    processor_by_index = {}
    for note, leds in processor_mapping.items():
        if 21 <= note <= 108:
            processor_by_index[note - 21] = leds
    
    print(f"   [OK] Loaded USB MIDI mapping with {len(processor_by_index)} keys")
    if 0 in processor_by_index and 87 in processor_by_index:
        print(f"   Sample: Key 0 -> {processor_by_index[0]}")
        print(f"   Sample: Key 87 -> {processor_by_index[87]}")
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

# 3. Compare
print("\n3. Comparing mappings...")
if canonical_mapping == processor_by_index:
    print("   [OK] Canonical and USB MIDI processor mappings MATCH!")
    
    # Compare specific keys
    mismatches = 0
    for key in range(88):
        if canonical_mapping.get(key) != processor_by_index.get(key):
            mismatches += 1
    
    if mismatches == 0:
        print("   [SUCCESS] All 88 keys match perfectly!")
    else:
        print(f"   [WARNING] {mismatches} keys don't match")
else:
    print("   [ERROR] Mappings don't match!")
    for key in range(88):
        c = canonical_mapping.get(key)
        p = processor_by_index.get(key)
        if c != p:
            print(f"   Key {key}: canonical={c}, processor={p}")
            break
    sys.exit(1)

print("\n[SUCCESS] Backend components are aligned!")
