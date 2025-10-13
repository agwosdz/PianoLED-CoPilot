#!/usr/bin/env python3
import sqlite3
import json
import sys

def cleanup_led_count():
    try:
        # Connect to the database
        conn = sqlite3.connect('/home/pi/Secret-Project/backend/settings.db')
        cursor = conn.cursor()
        
        print("=== LED Count Cleanup Script v2 ===")
        
        # First, let's see what we have
        cursor.execute("SELECT key, value, data_type FROM settings WHERE category = 'led' AND key IN ('led_count', 'ledCount', 'count')")
        before_results = cursor.fetchall()
        print(f"\nBEFORE cleanup - LED count entries:")
        for key, value, data_type in before_results:
            print(f"  {key}: {value} (type: {data_type})")
        
        # Delete the duplicate/conflicting entries
        print(f"\nDeleting duplicate entries...")
        
        # Delete 'ledCount' (frontend compatibility key that shouldn't be in DB)
        cursor.execute("DELETE FROM settings WHERE category = 'led' AND key = 'ledCount'")
        ledcount_deleted = cursor.rowcount
        print(f"  Deleted {ledcount_deleted} 'ledCount' entries")
        
        # Delete 'count' (old/duplicate key)
        cursor.execute("DELETE FROM settings WHERE category = 'led' AND key = 'count'")
        count_deleted = cursor.rowcount
        print(f"  Deleted {count_deleted} 'count' entries")
        
        # Now set the canonical led_count to 246 (the value the frontend was using)
        cursor.execute("""
            INSERT OR REPLACE INTO settings (category, key, value, data_type) 
            VALUES ('led', 'led_count', '246', 'number')
        """)
        print(f"  Set canonical 'led_count' to 246")
        
        # Commit the changes
        conn.commit()
        
        # Verify the cleanup
        cursor.execute("SELECT key, value, data_type FROM settings WHERE category = 'led' AND key IN ('led_count', 'ledCount', 'count')")
        after_results = cursor.fetchall()
        print(f"\nAFTER cleanup - LED count entries:")
        for key, value, data_type in after_results:
            print(f"  {key}: {value} (type: {data_type})")
        
        # Also check max_led_count for completeness
        cursor.execute("SELECT key, value FROM settings WHERE category = 'led' AND key = 'max_led_count'")
        max_result = cursor.fetchone()
        if max_result:
            print(f"  max_led_count: {max_result[1]}")
        
        conn.close()
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   - Deleted {ledcount_deleted + count_deleted} duplicate entries")
        print(f"   - Set canonical led_count to 246")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cleanup_led_count()