#!/usr/bin/env python3
"""
Test script to verify MIDI processor uses the exact mapping including key offset -57 for MIDI 30
"""

import sys
import json
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')

from backend.services.settings_service import SettingsService
from backend.midi.midi_event_processor import MidiEventProcessor
from backend.config import get_canonical_led_mapping

# Initialize settings service
settings_service = SettingsService()

print("=" * 60)
print("MIDI PROCESSOR MAPPING VERIFICATION")
print("=" * 60)

# 1. Verify settings have the key offset
print("\n1. Checking settings...")
key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
midi_30_offset = key_offsets.get('30', None)
print(f"   Key offset for MIDI 30: {midi_30_offset}")
assert midi_30_offset == -57, f"Expected -57, got {midi_30_offset}"
print("   ✓ Settings correct")

# 2. Check canonical mapping includes the offset
print("\n2. Checking canonical LED mapping...")
canonical_result = get_canonical_led_mapping(settings_service)
assert canonical_result['success'], f"Canonical mapping failed: {canonical_result['error']}"
canonical_mapping = canonical_result['mapping']
midi_30_key_index = 30 - 21  # MIDI 30 -> key index 9
midi_30_leds = canonical_mapping.get(midi_30_key_index, [])
print(f"   Canonical mapping key index {midi_30_key_index} (MIDI 30) -> LEDs: {midi_30_leds}")
assert 30 in midi_30_leds, f"Expected LED 30 in {midi_30_leds}"
print(f"   ✓ LED 30 is in mapping")

# 3. Check MIDI processor's precomputed mapping
print("\n3. Checking MIDI processor precomputed mapping...")
processor = MidiEventProcessor(
    led_controller=None,
    settings_service=settings_service
)
midi_30_processor_leds = processor._precomputed_mapping.get(30, [])
print(f"   Processor precomputed MIDI 30 -> LEDs: {midi_30_processor_leds}")
assert 30 in midi_30_processor_leds, f"Expected LED 30 in {midi_30_processor_leds}"
print(f"   ✓ LED 30 is in processor mapping")

# 4. Check via the public map_note_to_leds method
print("\n4. Checking MIDI processor public method...")
public_leds = processor.map_note_to_leds(30)
print(f"   Processor.map_note_to_leds(30) -> LEDs: {public_leds}")
assert 30 in public_leds, f"Expected LED 30 in {public_leds}"
print(f"   ✓ LED 30 is in public method result")

print("\n" + "=" * 60)
print("✅ ALL VERIFICATION CHECKS PASSED!")
print("=" * 60)
print("\nConfirmed:")
print("  ✓ Settings has key offset -57 for MIDI 30")
print("  ✓ Canonical mapping includes LED 30 for MIDI 30")
print("  ✓ MIDI processor precomputed mapping has LED 30")
print("  ✓ MIDI processor public method returns LED 30")
print("\nThe MIDI processor IS using the exact mapping with the new offset!")
