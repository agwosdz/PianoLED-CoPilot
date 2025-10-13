#!/usr/bin/env python3
"""
Fix settings database structure by properly grouping individual settings under their correct categories.
This script addresses the validation errors caused by individual setting keys being treated as categories.
"""

import sqlite3
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "/home/pi/Secret-Project/backend/settings.db"

# Mapping of individual setting keys to their proper categories
SETTING_CATEGORY_MAP = {
    # GPIO settings
    'gpio_pin': 'gpio',
    'gpio_power_pin': 'gpio', 
    'gpio_ground_pin': 'gpio',
    'gpio_pull_up': 'gpio',
    'gpio_pull_down': 'gpio',
    
    # LED settings
    'led_frequency': 'led',
    'led_dma': 'led',
    'led_channel': 'led',
    'led_invert': 'led',
    
    # Hardware settings
    'auto_detect_hardware': 'hardware',
    'hardware_test_enabled': 'hardware',
    'validate_gpio_pins': 'hardware',
    
    # System settings
    'signal_level': 'system',
    'pwm_range': 'system',
    'spi_speed': 'system',
}

def connect_db():
    """Connect to the settings database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def get_all_settings(conn):
    """Retrieve all settings from the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT category, key, value FROM settings ORDER BY category, key")
    return cursor.fetchall()

def backup_database(conn):
    """Create a backup of current settings."""
    logger.info("Creating backup of current settings...")
    settings = get_all_settings(conn)
    
    backup_data = []
    for setting in settings:
        backup_data.append({
            'category': setting['category'],
            'key': setting['key'],
            'value': setting['value']
        })
    
    backup_file = Path(DB_PATH).parent / "settings_backup_before_restructure.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"Backup saved to: {backup_file}")
    return backup_file

def find_orphaned_settings(conn):
    """Find settings that need to be moved to proper categories."""
    cursor = conn.cursor()
    
    orphaned_settings = []
    for setting_key, target_category in SETTING_CATEGORY_MAP.items():
        # Check if this setting exists as a category (which is wrong)
        cursor.execute("SELECT category, key, value FROM settings WHERE category = ?", (setting_key,))
        results = cursor.fetchall()
        
        if results:
            logger.info(f"Found orphaned settings under category '{setting_key}': {len(results)} settings")
            for result in results:
                orphaned_settings.append({
                    'old_category': result['category'],
                    'old_key': result['key'],
                    'new_category': target_category,
                    'new_key': setting_key,  # The category becomes the key
                    'value': result['value']
                })
    
    return orphaned_settings

def restructure_settings(conn, orphaned_settings):
    """Restructure the orphaned settings into proper categories."""
    cursor = conn.cursor()
    
    logger.info(f"Restructuring {len(orphaned_settings)} orphaned settings...")
    
    for setting in orphaned_settings:
        old_category = setting['old_category']
        old_key = setting['old_key']
        new_category = setting['new_category']
        new_key = setting['new_key']
        value = setting['value']
        
        logger.info(f"Moving {old_category}.{old_key} -> {new_category}.{new_key}")
        
        # Insert the setting in the correct category
        cursor.execute("""
            INSERT OR REPLACE INTO settings (category, key, value, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        """, (new_category, new_key, value))
        
        # Delete the old orphaned setting
        cursor.execute("DELETE FROM settings WHERE category = ? AND key = ?", (old_category, old_key))
    
    conn.commit()
    logger.info("Settings restructuring completed")

def verify_restructure(conn):
    """Verify that the restructuring was successful."""
    logger.info("Verifying restructure...")
    
    # Check that orphaned categories are gone
    cursor = conn.cursor()
    remaining_orphans = []
    
    for setting_key in SETTING_CATEGORY_MAP.keys():
        cursor.execute("SELECT COUNT(*) as count FROM settings WHERE category = ?", (setting_key,))
        count = cursor.fetchone()['count']
        if count > 0:
            remaining_orphans.append(f"{setting_key}: {count} settings")
    
    if remaining_orphans:
        logger.warning(f"Still have orphaned settings: {remaining_orphans}")
        return False
    else:
        logger.info("No orphaned settings remain - restructure successful!")
        return True

def show_current_structure(conn):
    """Display the current database structure."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM settings ORDER BY category")
    categories = [row['category'] for row in cursor.fetchall()]
    
    logger.info("Current database categories:")
    for category in categories:
        cursor.execute("SELECT COUNT(*) as count FROM settings WHERE category = ?", (category,))
        count = cursor.fetchone()['count']
        logger.info(f"  {category}: {count} settings")

def main():
    """Main function to fix the settings structure."""
    logger.info("Starting settings database restructure...")
    
    try:
        # Connect to database
        conn = connect_db()
        
        # Show current structure
        logger.info("=== BEFORE RESTRUCTURE ===")
        show_current_structure(conn)
        
        # Create backup
        backup_file = backup_database(conn)
        
        # Find orphaned settings
        orphaned_settings = find_orphaned_settings(conn)
        
        if not orphaned_settings:
            logger.info("No orphaned settings found - database structure is already correct!")
            return
        
        logger.info(f"Found {len(orphaned_settings)} orphaned settings to restructure")
        
        # Restructure settings
        restructure_settings(conn, orphaned_settings)
        
        # Verify the restructure
        success = verify_restructure(conn)
        
        # Show final structure
        logger.info("=== AFTER RESTRUCTURE ===")
        show_current_structure(conn)
        
        if success:
            logger.info("Settings database restructure completed successfully!")
            logger.info(f"Backup available at: {backup_file}")
        else:
            logger.error("Restructure completed but verification failed!")
            
    except Exception as e:
        logger.error(f"Error during restructure: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()