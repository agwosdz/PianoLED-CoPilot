import sqlite3

# Connect to the database on the Pi
conn = sqlite3.connect('settings.db')
cursor = conn.cursor()

# Get GPIO settings
cursor.execute("SELECT category, key, value FROM settings WHERE category = 'gpio' LIMIT 20")
gpio_settings = cursor.fetchall()

print('GPIO settings:')
for s in gpio_settings:
    print(f'  {s[0]}.{s[1]} = {s[2]}')

# Check for any settings that might be misclassified
cursor.execute("SELECT category, key, value FROM settings WHERE key LIKE '%gpio%' OR key LIKE '%pin%' LIMIT 20")
pin_settings = cursor.fetchall()

print('\nSettings with gpio/pin in key name:')
for s in pin_settings:
    print(f'  {s[0]}.{s[1]} = {s[2]}')

conn.close()