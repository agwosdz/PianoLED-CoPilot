#!/usr/bin/env python3
"""
Final cleanup script to remove ALL duplicate camelCase keys from settings database
This script will systematically remove all camelCase variants and keep only snake_case versions
"""

import sqlite3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = '/home/pi/Secret-Project/backend/settings.db'

# Define all known duplicate key mappings (camelCase -> snake_case)
DUPLICATE_MAPPINGS = {
    # Audio settings
    'inputDevice': 'input_device',
    'latencyMs': 'latency',
    'sampleRate': 'sample_rate',
    'bufferSize': 'buffer_size',
    
    # LED settings
    'ledCount': 'led_count',
    'animationSpeed': 'animation_speed',
    'colorScheme': 'color_scheme',
    'gammaCorrection': 'gamma_correction',
    'gpioPin': 'gpio_pin',
    'ledOrientation': 'led_orientation',
    'ledType': 'led_type',
    
    # System settings
    'autoSave': 'auto_save',
    'debugMode': 'debug',
    'logLevel': 'log_level',
    'performanceMode': 'performance_mode',
    
    # User settings
    'favoriteSchemes': 'favorite_schemes',
    'recentConfigs': 'recent_configs',
    'lastUsedDevice': 'last_used_device',
    'navigationCollapsed': 'navigation_collapsed',
    
    # Upload settings
    'autoUpload': 'auto_upload',
    'rememberLastDirectory': 'remember_last_directory',
    'showFilePreview': 'show_file_preview',
    'confirmBeforeReset': 'confirm_before_reset',
    'lastUploadedFile': 'last_uploaded_file',
    
    # UI settings
    'reducedMotion': 'reduced_motion',
    'showTooltips': 'show_tooltips',
    'tooltipDelay': 'tooltip_delay',
    'animationSpeed': 'animation_speed'  # Note: this appears in both LED and UI
}

def cleanup_duplicate_settings():
    """Remove all duplicate camelCase settings keys from the database"""
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        logger.info("Starting comprehensive duplicate settings cleanup...")
        
        # Get all current settings
        cursor.execute('SELECT category, key, value FROM settings')
        all_settings = cursor.fetchall()
        
        logger.info(f"Found {len(all_settings)} total settings in database")
        
        deleted_count = 0
        updated_count = 0
        
        # Process each setting
        for setting in all_settings:
            category = setting['category']
            key = setting['key']
            value = setting['value']
            
            # Check if this is a camelCase key that should be removed
            if key in DUPLICATE_MAPPINGS:
                snake_case_key = DUPLICATE_MAPPINGS[key]
                
                # Check if the snake_case version already exists
                cursor.execute(
                    'SELECT value FROM settings WHERE category = ? AND key = ?',
                    (category, snake_case_key)
                )
                snake_case_exists = cursor.fetchone()
                
                if snake_case_exists:
                    # Snake case version exists, delete the camelCase version
                    cursor.execute(
                        'DELETE FROM settings WHERE category = ? AND key = ?',
                        (category, key)
                    )
                    deleted_count += 1
                    logger.info(f"Deleted duplicate: {category}.{key} (snake_case version exists)")
                else:
                    # Snake case version doesn't exist, rename camelCase to snake_case
                    cursor.execute(
                        'UPDATE settings SET key = ? WHERE category = ? AND key = ?',
                        (snake_case_key, category, key)
                    )
                    updated_count += 1
                    logger.info(f"Renamed: {category}.{key} -> {category}.{snake_case_key}")
        
        # Special handling for LED count - ensure it's set to 246
        cursor.execute(
            'SELECT value FROM settings WHERE category = ? AND key = ?',
            ('led', 'led_count')
        )
        led_count_setting = cursor.fetchone()
        
        if led_count_setting:
            current_value = json.loads(led_count_setting['value'])
            if current_value != 246:
                cursor.execute(
                    'UPDATE settings SET value = ? WHERE category = ? AND key = ?',
                    (json.dumps(246), 'led', 'led_count')
                )
                logger.info(f"Updated led_count from {current_value} to 246")
                updated_count += 1
        
        # Commit changes
        conn.commit()
        
        # Verify cleanup by checking for remaining duplicates
        logger.info("Verifying cleanup...")
        cursor.execute('SELECT category, key FROM settings')
        remaining_settings = cursor.fetchall()
        
        remaining_duplicates = []
        for setting in remaining_settings:
            if setting['key'] in DUPLICATE_MAPPINGS:
                remaining_duplicates.append(f"{setting['category']}.{setting['key']}")
        
        if remaining_duplicates:
            logger.warning(f"Still found {len(remaining_duplicates)} duplicate keys: {remaining_duplicates}")
        else:
            logger.info("✅ All duplicate keys successfully removed!")
        
        # Show final LED settings
        cursor.execute('SELECT key, value FROM settings WHERE category = ? AND key LIKE ?', ('led', '%count%'))
        led_counts = cursor.fetchall()
        logger.info("Final LED count settings:")
        for setting in led_counts:
            logger.info(f"  {setting['key']}: {json.loads(setting['value'])}")
        
        logger.info(f"Cleanup completed: {deleted_count} keys deleted, {updated_count} keys updated")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    success = cleanup_duplicate_settings()
    if success:
        print("✅ Duplicate settings cleanup completed successfully!")
    else:
        print("❌ Cleanup failed - check logs for details")