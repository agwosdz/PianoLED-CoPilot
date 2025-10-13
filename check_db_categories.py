import sqlite3

# Connect to the database on the Pi
conn = sqlite3.connect('settings.db')
cursor = conn.cursor()

# Get all categories
cursor.execute('SELECT DISTINCT category FROM settings ORDER BY category')
categories = cursor.fetchall()

print('Categories in database:')
for cat in categories:
    print(f'  {cat[0]}')

print('\nSample settings for problematic categories:')
cursor.execute("SELECT category, key, value FROM settings WHERE category IN ('gpio_pin', 'gpio_power_pin', 'signal_level', 'led_frequency') LIMIT 10")
samples = cursor.fetchall()
for sample in samples:
    print(f'  {sample[0]}.{sample[1]} = {sample[2]}')

conn.close()