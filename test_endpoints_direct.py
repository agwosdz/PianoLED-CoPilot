#!/usr/bin/env python3
"""
Test the /key-led-mapping and /physical-analysis endpoints directly by importing the app.
This avoids networking issues and directly tests the endpoint logic.
"""

import sys
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def test_endpoints():
    """Test both endpoints and compare their responses"""
    from backend.app import app
    
    # Create a test client
    client = app.test_client()
    
    print("=" * 80)
    print("ENDPOINT ALIGNMENT TEST")
    print("=" * 80)
    
    # Test /key-led-mapping
    print("\n1. Testing /api/calibration/key-led-mapping...")
    try:
        response1 = client.get('/api/calibration/key-led-mapping')
        data1 = response1.get_json()
        print(f"   Status: {response1.status_code}")
        if response1.status_code == 200:
            print(f"   Response keys: {list(data1.keys())}")
            mapping1 = data1.get('mapping', {})
            print(f"   Mapping type: {type(mapping1)}")
            print(f"   Mapping keys count: {len(mapping1)}")
            if mapping1:
                sample_key = list(mapping1.keys())[0]
                sample_val = mapping1[sample_key]
                print(f"   Sample mapping[{sample_key}]: {sample_val}")
            print(f"   distribution_mode: {data1.get('distribution_mode')}")
        else:
            print(f"   ERROR: {data1}")
    except Exception as e:
        print(f"   ERROR: {e}")
        data1 = None
    
    # Test /physical-analysis
    print("\n2. Testing /api/calibration/physical-analysis...")
    try:
        response2 = client.get('/api/calibration/physical-analysis')
        data2 = response2.get_json()
        print(f"   Status: {response2.status_code}")
        if response2.status_code == 200:
            print(f"   Response keys: {list(data2.keys())}")
            mapping2 = data2.get('mapping', {})
            print(f"   Mapping type: {type(mapping2)}")
            print(f"   Mapping keys count: {len(mapping2)}")
            if mapping2:
                sample_key = list(mapping2.keys())[0]
                sample_val = mapping2[sample_key]
                print(f"   Sample mapping[{sample_key}]: {sample_val}")
        else:
            print(f"   ERROR: {data2}")
    except Exception as e:
        print(f"   ERROR: {e}")
        data2 = None
    
    # Compare if both succeeded
    if data1 and data2:
        print("\n" + "=" * 80)
        print("MAPPING COMPARISON")
        print("=" * 80)
        
        mapping1 = data1.get('mapping', {})
        mapping2 = data2.get('mapping', {})
        
        if mapping1 == mapping2:
            print("\n[OK] MAPPINGS ARE IDENTICAL!")
            return True
        else:
            print("\n[DIFF] MAPPINGS ARE DIFFERENT")
            
            # Find differences
            all_keys = sorted(set(mapping1.keys()) | set(mapping2.keys()))
            differences = []
            
            for key in all_keys:
                val1 = mapping1.get(key)
                val2 = mapping2.get(key)
                if val1 != val2:
                    differences.append((key, val1, val2))
            
            print(f"\nFound {len(differences)} different keys:")
            for key, val1, val2 in differences[:20]:  # Show first 20
                print(f"  Key {key}:")
                print(f"    /key-led-mapping:   {val1}")
                print(f"    /physical-analysis: {val2}")
            
            if len(differences) > 20:
                print(f"  ... and {len(differences) - 20} more differences")
            
            # Also show first few keys from each mapping for comparison
            print("\nFirst 5 keys from each mapping:")
            for i in range(min(5, len(all_keys))):
                key = all_keys[i]
                print(f"  Key {key}: {mapping1.get(key)} vs {mapping2.get(key)}")
            
            return False
    else:
        print("\n[ERROR] Could not fetch both endpoints")
        return False

if __name__ == "__main__":
    test_endpoints()
