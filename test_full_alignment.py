#!/usr/bin/env python3
"""
Comprehensive end-to-end alignment test:
- Backend endpoints
- USB MIDI processor  
- Frontend API responses
All should return identical LED mappings for the same settings
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_backend_alignment():
    """Test backend alignment"""
    from backend.app import app
    from backend.services.settings_service import SettingsService
    from backend.config import get_canonical_led_mapping
    from backend.midi.midi_event_processor import MidiEventProcessor
    
    client = app.test_client()
    settings = SettingsService()
    
    print("=" * 80)
    print("END-TO-END ALIGNMENT TEST")
    print("=" * 80)
    
    # 1. Test /key-led-mapping endpoint
    print("\n1. Testing /api/calibration/key-led-mapping endpoint...")
    response1 = client.get('/api/calibration/key-led-mapping')
    data1 = response1.get_json()
    mapping1 = data1.get('mapping', {})
    print(f"   Status: {response1.status_code}")
    print(f"   Keys in mapping: {len(mapping1)}")
    print(f"   Distribution mode: {data1.get('distribution_mode')}")
    print(f"   Sample key 0: {mapping1.get(0)}")
    print(f"   Sample key 87: {mapping1.get(87)}")
    
    # 2. Test /physical-analysis endpoint
    print("\n2. Testing /api/calibration/physical-analysis endpoint...")
    response2 = client.get('/api/calibration/physical-analysis')
    data2 = response2.get_json()
    mapping2 = data2.get('mapping', {})
    print(f"   Status: {response2.status_code}")
    print(f"   Keys in mapping: {len(mapping2)}")
    print(f"   Sample key 0: {mapping2.get(0)}")
    print(f"   Sample key 87: {mapping2.get(87)}")
    
    # 3. Test canonical mapping function
    print("\n3. Testing get_canonical_led_mapping() function...")
    canonical_result = get_canonical_led_mapping(settings)
    mapping3 = canonical_result.get('mapping', {})
    print(f"   Success: {canonical_result.get('success')}")
    print(f"   Keys in mapping: {len(mapping3)}")
    print(f"   Sample key 0: {mapping3.get(0)}")
    print(f"   Sample key 87: {mapping3.get(87)}")
    
    # 4. Test USB MIDI processor
    print("\n4. Testing USB MIDI processor...")
    processor = MidiEventProcessor(
        led_controller=None,
        settings_service=settings,
    )
    processor.refresh_runtime_settings()
    processor_mapping = processor._precomputed_mapping
    print(f"   Total MIDI notes mapped: {len(processor_mapping)}")
    # Convert from MIDI notes back to key indices for comparison
    processor_by_index = {note - 21: leds for note, leds in processor_mapping.items() if 21 <= note <= 108}
    print(f"   Keys in mapping: {len(processor_by_index)}")
    print(f"   Sample key 0: {processor_by_index.get(0)}")
    print(f"   Sample key 87: {processor_by_index.get(87)}")
    
    # 5. Compare all three
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    
    # Compare endpoints
    print("\n1. Endpoint comparison (/key-led-mapping vs /physical-analysis):")
    if mapping1 == mapping2:
        print("   [OK] Endpoints return IDENTICAL mappings")
    else:
        print("   [DIFF] Endpoints return DIFFERENT mappings")
        # Find first difference
        for key in sorted(set(mapping1.keys()) | set(mapping2.keys())):
            if mapping1.get(key) != mapping2.get(key):
                print(f"      First diff at key {key}: {mapping1.get(key)} vs {mapping2.get(key)}")
                break
    
    # Compare endpoints with canonical
    print("\n2. Endpoint vs Canonical comparison:")
    if mapping1 == mapping3:
        print("   [OK] Endpoint matches canonical mapping")
    else:
        print("   [DIFF] Endpoint differs from canonical mapping")
        for key in sorted(set(mapping1.keys()) | set(mapping3.keys())):
            if mapping1.get(key) != mapping3.get(key):
                print(f"      First diff at key {key}: {mapping1.get(key)} vs {mapping3.get(key)}")
                break
    
    # Compare canonical with USB MIDI
    print("\n3. Canonical vs USB MIDI processor comparison:")
    if mapping3 == processor_by_index:
        print("   [OK] USB MIDI processor matches canonical mapping")
    else:
        print("   [DIFF] USB MIDI processor differs from canonical")
        for key in sorted(set(mapping3.keys()) | set(processor_by_index.keys())):
            if mapping3.get(key) != processor_by_index.get(key):
                print(f"      First diff at key {key}: {mapping3.get(key)} vs {processor_by_index.get(key)}")
                break
    
    # Overall result
    print("\n" + "=" * 80)
    print("OVERALL RESULT")
    print("=" * 80)
    
    all_match = (mapping1 == mapping2 == mapping3 == processor_by_index)
    if all_match:
        print("\n[SUCCESS] All components are perfectly aligned!")
        print("- /key-led-mapping endpoint")
        print("- /physical-analysis endpoint")
        print("- Canonical mapping function")
        print("- USB MIDI processor")
        print("\nAll return identical LED mappings. System is ready for deployment!")
        return True
    else:
        print("\n[ERROR] Components are NOT aligned")
        print("Please review the differences above.")
        return False

if __name__ == "__main__":
    success = test_backend_alignment()
    sys.exit(0 if success else 1)
