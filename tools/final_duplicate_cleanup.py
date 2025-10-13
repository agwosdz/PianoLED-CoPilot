#!/usr/bin/env python3
"""
Final cleanup of ALL duplicate settings in the database.
This script removes all camelCase variants and keeps only snake_case versions.
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
    
    backup_file = "/home/pi/Secret-Project/backend/settings_backup_final_cleanup.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"Backup saved to: {backup_file}")
    return backup_data

def camel_to_snake(name):
    """Convert camelCase to snake_case."""
    import re
    # Insert an underscore before any uppercase letter that follows a lowercase letter
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Insert an underscore before any uppercase letter that follows a lowercase letter or digit
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def find_all_duplicates(settings_data):
    """Find all duplicate settings (camelCase vs snake_case)."""
    duplicates_to_remove = []
    
    for category, settings in settings_data.items():
        logger.info(f"Checking category '{category}' for duplicates...")
        
        # Create a mapping of snake_case versions to original keys
        snake_case_map = {}
        for key in settings.keys():
            snake_version = camel_to_snake(key)
            if snake_version != key:  # This is a camelCase key
                if snake_version not in snake_case_map:
                    snake_case_map[snake_version] = []
                snake_case_map[snake_version].append(key)
        
        # Find duplicates
        for snake_key, camel_keys in snake_case_map.items():
            if snake_key in settings:  # snake_case version exists
                # Remove all camelCase versions
                for camel_key in camel_keys:
                    logger.info(f"  Will remove duplicate: {category}.{camel_key} (keeping {category}.{snake_key})")
                    duplicates_to_remove.append((category, camel_key))
            elif len(camel_keys) > 1:  # Multiple camelCase versions, no snake_case
                # Keep the first one, remove the rest
                keep_key = camel_keys[0]
                for camel_key in camel_keys[1:]:
                    logger.info(f"  Will remove duplicate: {category}.{camel_key} (keeping {category}.{keep_key})")
                    duplicates_to_remove.append((category, camel_key))
    
    return duplicates_to_remove

def remove_duplicates(conn, duplicates_to_remove):
    """Remove duplicate settings from the database."""
    cursor = conn.cursor()
    changes_made = 0
    
    for category, key in duplicates_to_remove:
        logger.info(f"Removing duplicate: {category}.{key}")
        cursor.execute(
            "DELETE FROM settings WHERE category = ? AND key = ?",
            (category, key)
        )
        changes_made += 1
    
    if changes_made > 0:
        conn.commit()
        logger.info(f"Successfully removed {changes_made} duplicate settings")
    else:
        logger.info("No duplicate settings found to remove")
    
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
    for category, keys in settings_by_category.items():
        # Create snake_case mapping
        snake_case_map = {}
        for key in keys:
            snake_version = camel_to_snake(key)
            if snake_version in snake_case_map:
                logger.warning(f"  Still has duplicates: {category}.{snake_case_map[snake_version]} and {category}.{key}")
                remaining_duplicates += 1
            else:
                snake_case_map[snake_version] = key
    
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
    """Main function to clean up all duplicate settings."""
    logger.info("Starting final duplicate settings cleanup...")
    
    # Connect to database
    conn = connect_to_db()
    if not conn:
        logger.error("Failed to connect to database")
        return
    
    try:
        # Create backup
        logger.info("Creating backup of current settings...")
        settings_data = backup_settings(conn)
        
        # Find all duplicates
        logger.info("Analyzing settings for all duplicates...")
        duplicates_to_remove = find_all_duplicates(settings_data)
        
        if not duplicates_to_remove:
            logger.info("No duplicates found - database is already clean!")
            return
        
        logger.info(f"Total duplicates to remove: {len(duplicates_to_remove)}")
        
        # Remove duplicates
        logger.info("=== REMOVING DUPLICATES ===")
        changes_made = remove_duplicates(conn, duplicates_to_remove)
        
        # Verify cleanup
        verify_cleanup(conn)
        
        logger.info("Final duplicate settings cleanup completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()