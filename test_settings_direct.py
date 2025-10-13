#!/usr/bin/env python3
"""
Test script to debug settings service issues
"""
import sys
import os
sys.path.append('/home/pi/Secret-Project/backend')

from services.settings_service import SettingsService
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_settings():
    """Test settings service directly"""
    try:
        # Initialize settings service
        service = SettingsService()
        
        print("Testing LED brightness update...")
        result = service.set_setting('led', 'brightness', 0.75)
        print(f"Brightness result: {result}")
        
        print("Testing LED count update...")
        result = service.set_setting('led', 'led_count', 100)
        print(f"LED count result: {result}")
        
        print("Testing system debug update...")
        result = service.set_setting('system', 'debug', True)
        print(f"System debug result: {result}")
        
        # Check current values
        print("\nCurrent LED settings:")
        led_settings = service.get_category_settings('led')
        print(f"LED Count: {led_settings.get('led_count')}")
        print(f"Brightness: {led_settings.get('brightness')}")
        
        print("\nCurrent system settings:")
        system_settings = service.get_category_settings('system')
        print(f"Debug: {system_settings.get('debug')}")
        
    except Exception as e:
        logger.error(f"Error testing settings: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_settings()