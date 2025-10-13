#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/home/pi/Secret-Project/backend/settings.db')
cursor = conn.cursor()

cursor.execute("SELECT key, value FROM settings WHERE key LIKE '%count%' OR key LIKE '%Count%' ORDER BY key")
results = cursor.fetchall()

print("Count-related keys in database:")
for key, value in results:
    print(f"  {key}: {value}")

conn.close()