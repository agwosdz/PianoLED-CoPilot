#!/usr/bin/env python3
"""
Comprehensive cleanup script to remove all duplicate settings keys from the database.
This script identifies and removes camelCase duplicates, keeping only snake_case versions.
"""

import sqlite3
import json
import sys
import os

# Database path
DB_PATH = '/home/pi/Secret-Project/backend/settings.db'

def connect_db():
    """Connect to the settings database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

def get_all_settings(conn):
    """Get all settings from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    return cursor.fetchall()

def identify_duplicates():
    """Identify duplicate key patterns (camelCase vs snake_case)."""
    # Define known duplicate patterns: camelCase -> snake_case
    duplicate_patterns = {
        # LED settings
        'ledCount': 'led_count',
        'ledOrientation': 'led_orientation', 
        'ledType': 'led_type',
        'gammaCorrection': 'gamma_correction',
        'gpioPin': 'gpio_pin',
        'maxLedCount': 'max_led_count',
        'maxPowerWatts': 'max_power_watts',
        'maxTemperatureCelsius': 'max_temperature_celsius',
        'performanceMode': 'performance_mode',
        'powerLimitingEnabled': 'power_limiting_enabled',
        'powerSupplyCurrent': 'power_supply_current',
        'powerSupplyVoltage': 'power_supply_voltage',
        'reverseOrder': 'reverse_order',
        'stripType': 'strip_type',
        'thermalProtectionEnabled': 'thermal_protection_enabled',
        'updateRate': 'update_rate',
        'whiteBalance': 'white_balance',
        'ditherEnabled': 'dither_enabled',
        'ledStripType': 'led_strip_type',
        
        # Audio settings
        'bufferSize': 'buffer_size',
        'sampleRate': 'sample_rate',
        'deviceName': 'device_name',
        'inputDevice': 'input_device',
        'outputDevice': 'output_device',
        
        # System settings
        'autoSave': 'auto_save',
        'debugMode': 'debug',
        'logLevel': 'log_level',
        'performanceMode': 'performance_mode',
        'backupSettings': 'backup_settings',
        
        # GPIO settings
        'debounceTime': 'debounce_time',
        'pullUpResistor': 'pull_up_resistor',
        
        # UI settings
        'animationSpeed': 'animation_speed',
        'reducedMotion': 'reduced_motion',
        'showTooltips': 'show_tooltips',
        'tooltipDelay': 'tooltip_delay',
        
        # Upload settings
        'autoUpload': 'auto_upload',
        'confirmBeforeReset': 'confirm_before_reset',
        'enableValidationPreview': 'enable_validation_preview',
        'lastUploadedFile': 'last_uploaded_file',
        'rememberLastDirectory': 'remember_last_directory',
        'showFilePreview': 'show_file_preview',
        
        # User settings
        'favoriteSchemes': 'favorite_schemes',
        'lastUsedDevice': 'last_used_device',
        'navigationCollapsed': 'navigation_collapsed',
        'recentConfigs': 'recent_configs',
        
        # Piano settings
        'velocitySensitivity': 'velocity_sensitivity',
        
        # Other potential duplicates
        'count': 'led_count',  # Special case for count -> led_count
    }
    
    return duplicate_patterns

def cleanup_duplicates():
    """Clean up all duplicate settings keys."""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Get current settings
        print("Fetching current settings...")
        settings = get_all_settings(conn)
        print(f"Found {len(settings)} total settings")
        
        # Get duplicate patterns
        duplicate_patterns = identify_duplicates()
        
        deleted_count = 0
        updated_count = 0
        
        # Process each duplicate pattern
        for camel_case, snake_case in duplicate_patterns.items():
            # Check if both keys exist
            cursor.execute("SELECT value FROM settings WHERE key = ?", (camel_case,))
            camel_result = cursor.fetchone()
            
            cursor.execute("SELECT value FROM settings WHERE key = ?", (snake_case,))
            snake_result = cursor.fetchone()
            
            if camel_result and snake_result:
                # Both exist - keep snake_case, delete camelCase
                print(f"Found duplicate: {camel_case} and {snake_case}")
                print(f"  {camel_case}: {camel_result[0]}")
                print(f"  {snake_case}: {snake_result[0]}")
                
                # Delete the camelCase version
                cursor.execute("DELETE FROM settings WHERE key = ?", (camel_case,))
                deleted_count += 1
                print(f"  Deleted {camel_case}")
                
            elif camel_result and not snake_result:
                # Only camelCase exists - rename it to snake_case
                print(f"Renaming {camel_case} to {snake_case}")
                cursor.execute("UPDATE settings SET key = ? WHERE key = ?", (snake_case, camel_case))
                updated_count += 1
                print(f"  Renamed {camel_case} -> {snake_case}")
        
        # Special case: ensure led_count is set to a consistent value
        cursor.execute("SELECT value FROM settings WHERE key = 'led_count'")
        led_count_result = cursor.fetchone()
        if led_count_result:
            # Set led_count to 246 (the value we want to keep)
            cursor.execute("UPDATE settings SET value = ? WHERE key = 'led_count'", ('246',))
            updated_count += 1
            print(f"Updated led_count to 246")
        
        # Commit changes
        conn.commit()
        
        print(f"\nCleanup completed:")
        print(f"  Deleted {deleted_count} duplicate keys")
        print(f"  Updated {updated_count} keys")
        
        # Verify final state
        print("\nFinal LED-related settings:")
        cursor.execute("SELECT key, value FROM settings WHERE key LIKE '%led%' OR key LIKE '%count%' ORDER BY key")
        led_settings = cursor.fetchall()
        for key, value in led_settings:
            print(f"  {key}: {value}")
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting comprehensive settings cleanup...")
    cleanup_duplicates()
    print("Cleanup completed successfully!")