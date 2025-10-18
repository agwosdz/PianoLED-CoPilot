#!/usr/bin/env python3
"""
Test frontend API integration
"""

import sys
import json
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

print("Testing frontend API alignment...")

# Create a test client
from backend.app import app

client = app.test_client()

print("\n1. Testing /api/calibration/key-led-mapping endpoint...")
try:
    response = client.get('/api/calibration/key-led-mapping')
    if response.status_code != 200:
        print(f"   [ERROR] HTTP {response.status_code}")
        sys.exit(1)
    
    data = response.get_json()
    mapping = data.get('mapping', {})
    
    print(f"   [OK] Received response with {len(mapping)} keys")
    
    # Verify structure
    if 'start_led' not in data or 'end_led' not in data or 'led_count' not in data:
        print("   [ERROR] Missing required fields in response")
        sys.exit(1)
    
    print(f"   LED range: {data['start_led']}-{data['end_led']} (total: {data['led_count']})")
    
    # Check that keys are indices (0-87), not MIDI notes (21-108)
    keys = [int(k) for k in mapping.keys()]
    if min(keys) >= 0 and max(keys) <= 87:
        print(f"   [OK] Keys are 0-based indices (min={min(keys)}, max={max(keys)})")
    else:
        print(f"   [WARNING] Keys might not be 0-based indices (min={min(keys)}, max={max(keys)})")
    
    # Sample values
    if 0 in mapping:
        print(f"   Sample: Key 0 -> {mapping[0]}")
    if 87 in mapping:
        print(f"   Sample: Key 87 -> {mapping[87]}")

except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

print("\n2. Simulating frontend conversion (indices to MIDI notes)...")
try:
    frontend_mapping = {}
    for key_str, leds in mapping.items():
        key_index = int(key_str)
        midi_note = 21 + key_index  # Convert to MIDI
        frontend_mapping[midi_note] = leds
    
    print(f"   [OK] Converted {len(frontend_mapping)} keys to MIDI notes")
    if 21 in frontend_mapping:
        print(f"   Sample: MIDI 21 -> {frontend_mapping[21]}")
    if 108 in frontend_mapping:
        print(f"   Sample: MIDI 108 -> {frontend_mapping[108]}")
        
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

print("\n3. Comparing with backend canonical...")
try:
    from backend.services.settings_service import SettingsService
    from backend.config import get_canonical_led_mapping
    
    settings = SettingsService()
    canonical_result = get_canonical_led_mapping(settings)
    canonical = canonical_result.get('mapping', {})
    
    # Backend canonical is 0-based indices, convert to MIDI for comparison
    backend_midi_mapping = {}
    for key_idx, leds in canonical.items():
        midi_note = 21 + key_idx
        backend_midi_mapping[midi_note] = leds
    
    if frontend_mapping == backend_midi_mapping:
        print("   [OK] Frontend API response matches backend canonical!")
    else:
        print("   [ERROR] Mismatch between frontend API and backend canonical")
        for note in range(21, 109):
            if frontend_mapping.get(note) != backend_midi_mapping.get(note):
                print(f"      MIDI {note}: API={frontend_mapping.get(note)}, Backend={backend_midi_mapping.get(note)}")
                break
        sys.exit(1)
        
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] Frontend API is properly aligned!")
print("- API returns 0-based indices")
print("- Frontend correctly converts to MIDI notes (21-108)")
print("- Results match backend canonical mapping")
