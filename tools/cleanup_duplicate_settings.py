#!/usr/bin/env python3
"""
Clean up duplicate settings with different naming conventions in the database.
This script consolidates settings like led_count/ledCount, auto_save/autoSave, etc.
"""

import sqlite3
import json
import logging
from pathlib import Path
from logging_config import setup_logging, get_logger

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

# Database path
DB_PATH = "/home/pi/Secret-Project/backend/settings.db"

# Mapping of duplicate keys to their canonical form
DUPLICATE_MAPPINGS = {
    # LED settings
    'led': {
        'ledCount': 'led_count',
        'ledOrientation': 'led_orientation', 
        'ledType': 'led_type',
        'gpioPin': 'gpio_pin',
        'colorScheme': 'color_scheme',
        'gammaCorrection': 'gamma_correction',
        'count': 'led_count',  # Another variant
        'strip_type': 'led_strip_type',  # Consolidate to led_strip_type
    },
    # System settings
    'system': {
        'autoSave': 'auto_save',
        'debugMode': 'debug',
    },
    # Audio settings
    'audio': {
        'inputDevice': 'input_device',
        'sampleRate': 'sample_rate',
        'bufferSize': 'buffer_size',
    },
    # Hardware settings
    'hardware': {
        'autoDetectMidi': 'auto_detect_midi',
        'autoDetectGpio': 'auto_detect_gpio', 
        'autoDetectLed': 'auto_detect_led',
        'rtpmidiEnabled': 'rtpmidi_enabled',
        'rtpmidiPort': 'rtpmidi_port',
        'midiDeviceId': 'midi_device_id',
    },
    # Piano settings
    'piano': {
        'velocitySensitivity': 'velocity_sensitivity',
    },
    # GPIO settings
    'gpio': {
        'debounceTime': 'debounce_time',
        'dmaChannel': 'dma_channel',
    },
    # UI settings
    'ui': {
        'showTooltips': 'show_tooltips',
        'showKeyboard': 'show_keyboard',
        'keyboardSize': 'keyboard_size',
        'showPedals': 'show_pedals',
        'showMetronome': 'show_metronome',
        'showProgress': 'show_progress',
        'autoHideControls': 'auto_hide_controls',
    },
    # Upload settings
    'upload': {
        'maxFileSize': 'max_file_size',
        'allowedTypes': 'allowed_types',
        'autoProcess': 'auto_process',
        'lastUploadedFile': 'last_uploaded_file',
    },
    # Help settings
    'help': {
        'showHints': 'show_hints',
        'showOnboarding': 'show_onboarding',
        'tourCompleted': 'tour_completed',
        'completedTours': 'completed_tours',
        'skippedTours': 'skipped_tours',
    },
    # History settings
    'history': {
        'maxHistorySize': 'max_history_size',
        'autosaveInterval': 'autosave_interval',
        'persistHistory': 'persist_history',
    },
    # A11y settings
    'a11y': {
        'highContrast': 'high_contrast',
        'largeText': 'large_text',
        'reduceMotion': 'reduce_motion',
        'screenReader': 'screen_reader',
    },
    # User settings
    'user': {
        'userName': 'user_name',
        'userEmail': 'user_email',
        'lastLogin': 'last_login',
    }
}

def connect_to_db():
    """Connect to the settings database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None

def get_all_settings(conn):
    """Get all settings from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT category, key, value FROM settings ORDER BY category, key")
    return cursor.fetchall()

def backup_settings(conn):
    """Create a backup of current settings."""
    settings = get_all_settings(conn)
    backup_data = {}
    
    for row in settings:
        category = row['category']
        key = row['key']
        value = row['value']
        
        if category not in backup_data:
            backup_data[category] = {}
        
        # Try to parse JSON values
        try:
            parsed_value = json.loads(value)
            backup_data[category][key] = parsed_value
        except (json.JSONDecodeError, TypeError):
            backup_data[category][key] = value
    
    backup_file = "/home/pi/Secret-Project/backend/settings_backup_before_duplicate_cleanup.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"Backup saved to: {backup_file}")
    return backup_data

def find_duplicates(settings_data):
    """Find duplicate settings that need to be consolidated."""
    duplicates_found = {}
    
    for category, mappings in DUPLICATE_MAPPINGS.items():
        if category in settings_data:
            category_duplicates = {}
            
            for old_key, canonical_key in mappings.items():
                if old_key in settings_data[category] and canonical_key in settings_data[category]:
                    # Both versions exist - this is a duplicate
                    category_duplicates[old_key] = {
                        'canonical': canonical_key,
                        'old_value': settings_data[category][old_key],
                        'canonical_value': settings_data[category][canonical_key]
                    }
                elif old_key in settings_data[category]:
                    # Only old version exists - needs renaming
                    category_duplicates[old_key] = {
                        'canonical': canonical_key,
                        'old_value': settings_data[category][old_key],
                        'canonical_value': None,
                        'needs_rename': True
                    }
            
            if category_duplicates:
                duplicates_found[category] = category_duplicates
    
    return duplicates_found

def consolidate_duplicates(conn, duplicates):
    """Consolidate duplicate settings in the database."""
    cursor = conn.cursor()
    changes_made = 0
    
    for category, category_duplicates in duplicates.items():
        logger.info(f"Processing duplicates in category '{category}':")
        
        for old_key, duplicate_info in category_duplicates.items():
            canonical_key = duplicate_info['canonical']
            old_value = duplicate_info['old_value']
            canonical_value = duplicate_info.get('canonical_value')
            needs_rename = duplicate_info.get('needs_rename', False)
            
            if needs_rename:
                # Rename the old key to canonical key
                logger.info(f"  Renaming '{old_key}' to '{canonical_key}' with value: {old_value}")
                
                # Update the key name
                cursor.execute(
                    "UPDATE settings SET key = ? WHERE category = ? AND key = ?",
                    (canonical_key, category, old_key)
                )
                changes_made += 1
                
            else:
                # Both exist - keep canonical, remove old
                logger.info(f"  Removing duplicate '{old_key}' (keeping '{canonical_key}')")
                logger.info(f"    Old value: {old_value}")
                logger.info(f"    Canonical value: {canonical_value}")
                
                # Remove the old duplicate
                cursor.execute(
                    "DELETE FROM settings WHERE category = ? AND key = ?",
                    (category, old_key)
                )
                changes_made += 1
    
    if changes_made > 0:
        conn.commit()
        logger.info(f"Successfully consolidated {changes_made} duplicate settings")
    else:
        logger.info("No duplicate settings found to consolidate")
    
    return changes_made

def verify_cleanup(conn):
    """Verify that the cleanup was successful."""
    logger.info("=== VERIFICATION ===")
    
    # Get updated settings
    settings = get_all_settings(conn)
    settings_by_category = {}
    
    for row in settings:
        category = row['category']
        key = row['key']
        
        if category not in settings_by_category:
            settings_by_category[category] = []
        settings_by_category[category].append(key)
    
    # Check for remaining duplicates
    remaining_duplicates = 0
    for category, mappings in DUPLICATE_MAPPINGS.items():
        if category in settings_by_category:
            category_keys = settings_by_category[category]
            
            for old_key, canonical_key in mappings.items():
                if old_key in category_keys and canonical_key in category_keys:
                    logger.warning(f"  Still has duplicates: {category}.{old_key} and {category}.{canonical_key}")
                    remaining_duplicates += 1
                elif old_key in category_keys:
                    logger.warning(f"  Still has old key: {category}.{old_key} (should be {canonical_key})")
                    remaining_duplicates += 1
    
    if remaining_duplicates == 0:
        logger.info("✓ No duplicate settings found - cleanup successful!")
    else:
        logger.warning(f"⚠ Found {remaining_duplicates} remaining duplicate issues")
    
    # Show final category counts
    logger.info("Final settings count by category:")
    for category in sorted(settings_by_category.keys()):
        count = len(settings_by_category[category])
        logger.info(f"  {category}: {count} settings")

def main():
    """Main function to clean up duplicate settings."""
    logger.info("Starting duplicate settings cleanup...")
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        logger.error("Failed to connect to database")
        return
    
    try:
        # Create backup
        logger.info("Creating backup of current settings...")
        settings_data = backup_settings(conn)
        
        # Find duplicates
        logger.info("Analyzing settings for duplicates...")
        duplicates = find_duplicates(settings_data)
        
        if not duplicates:
            logger.info("No duplicates found - database is already clean!")
            return
        
        # Show what will be changed
        logger.info("=== DUPLICATES FOUND ===")
        total_duplicates = 0
        for category, category_duplicates in duplicates.items():
            logger.info(f"Category '{category}':")
            for old_key, duplicate_info in category_duplicates.items():
                canonical_key = duplicate_info['canonical']
                if duplicate_info.get('needs_rename'):
                    logger.info(f"  Will rename: {old_key} → {canonical_key}")
                else:
                    logger.info(f"  Will remove duplicate: {old_key} (keeping {canonical_key})")
                total_duplicates += 1
        
        logger.info(f"Total duplicates to fix: {total_duplicates}")
        
        # Consolidate duplicates
        logger.info("=== CONSOLIDATING DUPLICATES ===")
        changes_made = consolidate_duplicates(conn, duplicates)
        
        # Verify cleanup
        verify_cleanup(conn)
        
        logger.info("Duplicate settings cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()