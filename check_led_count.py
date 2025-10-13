#!/usr/bin/env python3
import sqlite3
import json

# Connect to the database
conn = sqlite3.connect('settings.db')
conn.row_factory = sqlite3.Row

# Query for LED count setting
cursor = conn.execute("SELECT * FROM settings WHERE category='led' AND key='led_count'")
rows = cursor.fetchall()

print("LED count settings:")
for row in rows:
    print(f"Category: {row['category']}, Key: {row['key']}, Value: {row['value']}, Data Type: {row['data_type']}")
    try:
        parsed_value = json.loads(row['value'])
        print(f"Parsed Value: {parsed_value} (type: {type(parsed_value)})")
    except:
        print(f"Raw Value: {row['value']}")

# Also check all LED settings
print("\nAll LED settings:")
cursor = conn.execute("SELECT * FROM settings WHERE category='led'")
rows = cursor.fetchall()

for row in rows:
    print(f"Key: {row['key']}, Value: {row['value']}")

conn.close()