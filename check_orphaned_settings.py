import sqlite3

# Connect to the database on the Pi
conn = sqlite3.connect('settings.db')
cursor = conn.cursor()

# Get all settings
cursor.execute("SELECT category, key, value FROM settings ORDER BY category, key")
all_settings = cursor.fetchall()

# Valid categories based on the schema
valid_categories = ['piano', 'gpio', 'led', 'audio', 'hardware', 'system', 'user', 'ui', 'upload', 'a11y', 'help', 'history']

print('All settings by category:')
current_category = None
for s in all_settings:
    if s[0] != current_category:
        current_category = s[0]
        print(f'\n{current_category}:')
    print(f'  {s[1]} = {s[2]}')

print('\n\nPotentially problematic settings (categories not in schema):')
for s in all_settings:
    if s[0] not in valid_categories:
        print(f'  {s[0]}.{s[1]} = {s[2]}')

conn.close()