#!/usr/bin/env python3
import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('settings.db')

# Delete duplicate LED count entries, keeping only led_count
cursor = conn.execute("DELETE FROM settings WHERE category='led' AND key IN ('ledCount', 'count') AND key != 'led_count'")
print(f'Deleted {cursor.rowcount} duplicate LED count entries')

# Update the canonical led_count to 246 to match the expected default
cursor = conn.execute("UPDATE settings SET value='246' WHERE category='led' AND key='led_count'")
print(f'Updated {cursor.rowcount} led_count entries')

conn.commit()

# Verify the cleanup
cursor = conn.execute("SELECT key, value FROM settings WHERE category='led' AND key LIKE '%count%'")
rows = cursor.fetchall()
print("\nRemaining LED count entries:")
for row in rows:
    print(f"Key: {row[0]}, Value: {row[1]}")

conn.close()
print('Database cleanup completed')