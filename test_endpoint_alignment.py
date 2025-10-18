#!/usr/bin/env python3
"""
Test script to compare /key-led-mapping and /physical-analysis endpoints.
Calls both endpoints with same settings and compares the 'mapping' field.
"""

import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:5000"

def get_endpoints():
    """Call both endpoints and return their responses."""
    print("=" * 80)
    print("ENDPOINT ALIGNMENT TEST")
    print("=" * 80)
    
    # Call /key-led-mapping
    print("\n1. Calling /key-led-mapping...")
    try:
        response1 = requests.get(f"{BASE_URL}/api/calibration/key-led-mapping", timeout=5)
        data1 = response1.json()
        print(f"   Status: {response1.status_code}")
        print(f"   Response keys: {list(data1.keys())}")
        mapping1 = data1.get('mapping', {})
        print(f"   Mapping keys count: {len(mapping1)}")
        if mapping1:
            sample_key = list(mapping1.keys())[0]
            print(f"   Sample mapping[{sample_key}]: {mapping1[sample_key]}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return None, None
    
    # Call /physical-analysis
    print("\n2. Calling /physical-analysis...")
    try:
        response2 = requests.get(f"{BASE_URL}/api/calibration/physical-analysis", timeout=5)
        data2 = response2.json()
        print(f"   Status: {response2.status_code}")
        print(f"   Response keys: {list(data2.keys())}")
        mapping2 = data2.get('mapping', {})
        print(f"   Mapping keys count: {len(mapping2)}")
        if mapping2:
            sample_key = list(mapping2.keys())[0]
            print(f"   Sample mapping[{sample_key}]: {mapping2[sample_key]}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return data1, None
    
    return data1, data2


def compare_mappings(data1, data2):
    """Compare the 'mapping' field from both responses."""
    print("\n" + "=" * 80)
    print("MAPPING COMPARISON")
    print("=" * 80)
    
    mapping1 = data1.get('mapping', {})
    mapping2 = data2.get('mapping', {})
    
    print(f"\n/key-led-mapping:    {len(mapping1)} keys")
    print(f"/physical-analysis:  {len(mapping2)} keys")
    
    # Check if mappings are identical
    if mapping1 == mapping2:
        print("\n✓ Mappings are IDENTICAL!")
        return True
    
    print("\n✗ Mappings are DIFFERENT")
    
    # Find differences
    all_keys = set(mapping1.keys()) | set(mapping2.keys())
    differences = []
    
    for key in sorted(all_keys):
        val1 = mapping1.get(key)
        val2 = mapping2.get(key)
        if val1 != val2:
            differences.append((key, val1, val2))
    
    print(f"\nFound {len(differences)} different keys:")
    for key, val1, val2 in differences[:10]:  # Show first 10
        print(f"  Key {key}:")
        print(f"    /key-led-mapping:   {val1}")
        print(f"    /physical-analysis: {val2}")
    
    if len(differences) > 10:
        print(f"  ... and {len(differences) - 10} more differences")
    
    return False


def compare_responses(data1, data2):
    """Compare overall response structures."""
    print("\n" + "=" * 80)
    print("RESPONSE STRUCTURE COMPARISON")
    print("=" * 80)
    
    print("\n/key-led-mapping response fields:")
    for key, val in data1.items():
        if key != 'mapping':
            print(f"  {key}: {val}")
    
    print("\n/physical-analysis response fields:")
    for key, val in data2.items():
        if key not in ('mapping', 'per_key_analysis', 'quality_metrics', 'parameters_used'):
            print(f"  {key}: {val}")
    
    # Check key parameters
    print("\n" + "-" * 80)
    print("Key Parameters:")
    keys1 = {
        'piano_size': data1.get('piano_size'),
        'led_count': data1.get('led_count'),
        'start_led': data1.get('start_led'),
        'end_led': data1.get('end_led'),
        'distribution_mode': data1.get('distribution_mode'),
    }
    keys2 = {
        'piano_size': data2.get('mapping_info', {}).get('piano_size'),
        'led_count': data2.get('mapping_info', {}).get('total_keys'),  # This is different!
        'start_led': data2.get('mapping_info', {}).get('start_led'),
        'end_led': data2.get('mapping_info', {}).get('end_led'),
        'distribution_mode': None,  # physical-analysis doesn't return this
    }
    
    print("\n/key-led-mapping:")
    for k, v in keys1.items():
        print(f"  {k}: {v}")
    
    print("\n/physical-analysis:")
    for k, v in keys2.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    print("\nMake sure the backend is running on http://localhost:5000")
    print("(Run: python -m backend.app)")
    print()
    
    input("Press Enter to start test...")
    
    data1, data2 = get_endpoints()
    
    if data1 and data2:
        if compare_mappings(data1, data2):
            print("\n✓ SUCCESS: Endpoints are aligned!")
        else:
            print("\n✗ ISSUE: Endpoints return different mappings")
            compare_responses(data1, data2)
    else:
        print("\n✗ ERROR: Could not fetch one or both endpoints")
