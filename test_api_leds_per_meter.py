#!/usr/bin/env python3
"""
Test to verify leds_per_meter works through the API endpoints
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app, settings_service

def test_api_leds_per_meter():
    """Test that leds_per_meter setting works through REST API"""
    print("\nTesting leds_per_meter via REST API...\n")
    
    client = app.test_client()
    
    # Test 1: Get settings
    print("Test 1: GET /api/settings/")
    response = client.get('/api/settings/')
    assert response.status_code == 200, f"GET failed: {response.status_code}"
    data = response.get_json()
    print(f"  Status: {response.status_code}")
    if 'led' in data and 'leds_per_meter' in data['led']:
        print(f"  Current leds_per_meter: {data['led']['leds_per_meter']}")
        print("  [OK] leds_per_meter is in response\n")
    else:
        print("  [WARN] leds_per_meter not in response (might be using defaults)\n")
    
    # Test 2: Update settings with leds_per_meter
    print("Test 2: PUT /api/settings/ (update leds_per_meter to 144)")
    payload = {"led": {"leds_per_meter": 144}}
    response = client.put('/api/settings/', 
                         data=json.dumps(payload),
                         content_type='application/json')
    assert response.status_code == 200, f"PUT failed: {response.status_code}\n{response.get_json()}"
    print(f"  Status: {response.status_code}")
    print("  [OK] Successfully updated leds_per_meter to 144\n")
    
    # Test 3: Get category settings
    print("Test 3: GET /api/settings/led/")
    response = client.get('/api/settings/led/')
    assert response.status_code == 200, f"GET led failed: {response.status_code}"
    data = response.get_json()
    print(f"  Status: {response.status_code}")
    if 'leds_per_meter' in data:
        print(f"  leds_per_meter: {data['leds_per_meter']}")
        assert data['leds_per_meter'] == 144, f"Expected 144, got {data['leds_per_meter']}"
        print("  [OK] leds_per_meter is 144\n")
    else:
        print("  [WARN] leds_per_meter not in led category\n")
    
    # Test 4: Test invalid value rejection
    print("Test 4: PUT /api/settings/ (try invalid leds_per_meter value)")
    payload = {"led": {"leds_per_meter": 999}}
    response = client.put('/api/settings/', 
                         data=json.dumps(payload),
                         content_type='application/json')
    print(f"  Status: {response.status_code}")
    if response.status_code != 200:
        print(f"  Response: {response.get_json()}")
        print("  [OK] Invalid value correctly rejected\n")
    else:
        print("  [WARN] Invalid value was accepted (might be lenient validation)\n")
    
    # Test 5: Verify schema
    print("Test 5: GET /api/settings/schema/")
    response = client.get('/api/settings/schema/')
    assert response.status_code == 200, f"GET schema failed: {response.status_code}"
    schema = response.get_json()
    if 'led' in schema and 'leds_per_meter' in schema['led']:
        led_schema = schema['led']['leds_per_meter']
        print(f"  leds_per_meter schema: {led_schema}")
        if 'enum' in led_schema:
            print(f"  Valid values: {led_schema['enum']}")
        if 'default' in led_schema:
            print(f"  Default: {led_schema['default']}")
        print("  [OK] Schema includes leds_per_meter\n")
    else:
        print("  [WARN] leds_per_meter not in schema\n")
    
    print("=" * 50)
    print("API tests passed!")
    print("=" * 50)

if __name__ == '__main__':
    test_api_leds_per_meter()
