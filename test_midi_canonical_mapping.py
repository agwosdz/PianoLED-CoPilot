#!/usr/bin/env python3
"""
Test that USB MIDI processor uses canonical LED mapping from settings.
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_midi_processor_canonical_mapping():
    """Test MIDI processor uses canonical mapping"""
    from backend.services.settings_service import SettingsService
    from backend.midi.midi_event_processor import MidiEventProcessor
    
    print("=" * 80)
    print("USB MIDI PROCESSOR CANONICAL MAPPING TEST")
    print("=" * 80)
    
    settings_service = SettingsService()
    
    # Create MIDI processor with settings service
    processor = MidiEventProcessor(
        led_controller=None,
        settings_service=settings_service,
    )
    
    # Trigger refresh to load mapping
    processor.refresh_runtime_settings()
    
    print(f"\nProcessor settings:")
    print(f"  Piano size: {processor.piano_size}")
    print(f"  MIDI range: {processor.min_midi_note}-{processor.max_midi_note}")
    print(f"  LED count: {processor.num_leds}")
    print(f"  Precomputed mapping keys: {len(processor._precomputed_mapping)}")
    print(f"  Distribution mode: {getattr(processor, 'mapping_mode', 'N/A')}")
    
    # Get the mapping
    mapping = processor._precomputed_mapping
    
    if not mapping:
        print("\n[ERROR] No mapping generated!")
        return False
    
    print(f"\nMapping analysis:")
    print(f"  Total mapped MIDI notes: {len(mapping)}")
    
    # Check a few notes
    test_notes = [21, 42, 64, 108]  # A0, E2, E4, C8
    print(f"\n  Sample mappings:")
    for note in test_notes:
        if note in mapping:
            leds = mapping[note]
            print(f"    MIDI {note:3d}: {leds}")
        else:
            print(f"    MIDI {note:3d}: NOT MAPPED")
    
    # Compare with canonical mapping
    from backend.config import get_canonical_led_mapping
    canonical = get_canonical_led_mapping(settings_service)
    
    print(f"\nCanonical mapping validation:")
    if canonical.get('success'):
        canonical_map = canonical.get('mapping', {})
        print(f"  Canonical mapping has {len(canonical_map)} keys")
        
        # Convert canonical (0-87) to MIDI (21-108) for comparison
        canonical_midi = {}
        for key_idx, leds in canonical_map.items():
            canonical_midi[key_idx + 21] = leds
        
        # Compare samples
        matches = 0
        mismatches = 0
        for note in test_notes:
            if note - 21 in canonical_map:
                canonical_leds = canonical_midi.get(note)
                processor_leds = mapping.get(note)
                if canonical_leds == processor_leds:
                    matches += 1
                    print(f"  [OK] Note {note}: MATCH ({processor_leds})")
                else:
                    mismatches += 1
                    print(f"  [DIFF] Note {note}: MISMATCH")
                    print(f"      Canonical:  {canonical_leds}")
                    print(f"      Processor:  {processor_leds}")
        
        print(f"\n  Comparison: {matches} matches, {mismatches} mismatches")
        return mismatches == 0
    else:
        print(f"  [ERROR] Canonical mapping failed: {canonical.get('error')}")
        return False

if __name__ == "__main__":
    success = test_midi_processor_canonical_mapping()
    sys.exit(0 if success else 1)
