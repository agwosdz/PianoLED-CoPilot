#!/bin/bash
# Fix GPIO settings database corruption on Pi Zero 2 W
# This script cleans up legacy camelCase keys and ensures correct GPIO pin and LED configuration

set -e

echo "=========================================="
echo "GPIO & LED Settings Database Repair"
echo "=========================================="

# Navigate to project directory
cd ~/PianoLED-CoPilot

# Backup the database first
echo "[1/5] Backing up settings database..."
cp backend/settings.db backend/settings.db.backup.$(date +%s)
echo "✓ Backup created"

# Check current state
echo ""
echo "[2/5] Current LED and GPIO settings state:"
sqlite3 backend/settings.db << EOF
.headers on
.mode column
SELECT category, key, value FROM settings 
WHERE category='led' AND (key LIKE '%gpio%' OR key LIKE '%pin%' OR key LIKE '%channel%' OR key='enabled') 
ORDER BY category, key;
EOF

# Clean up legacy camelCase keys
echo ""
echo "[3/5] Removing legacy camelCase keys..."
sqlite3 backend/settings.db << EOF
DELETE FROM settings WHERE category='led' AND key='gpioPin';
DELETE FROM settings WHERE category='gpio' AND key='gpioPin';
DELETE FROM settings WHERE category='gpio' AND key='dataPin';
DELETE FROM settings WHERE category='gpio' AND key='clockPin';
EOF
echo "✓ Legacy keys removed"

# Ensure correct GPIO pin value
echo ""
echo "[4/5] Setting GPIO and LED channel values (Pi Zero 2 W requirement)..."
sqlite3 backend/settings.db << EOF
UPDATE settings SET value='19' WHERE category='led' AND key='gpio_pin';
UPDATE settings SET value='1' WHERE category='led' AND key='led_channel';
UPDATE settings SET value='true' WHERE category='led' AND key='enabled';
EOF
echo "✓ GPIO pin set to 19"
echo "✓ LED channel set to 1 (required for GPIO 19)"
echo "✓ LED enabled set to true"

# Show final state
echo ""
echo "[5/5] Final LED and GPIO settings state:"
sqlite3 backend/settings.db << EOF
.headers on
.mode column
SELECT category, key, value FROM settings 
WHERE category='led' AND (key LIKE '%gpio%' OR key LIKE '%pin%' OR key LIKE '%channel%' OR key='enabled') 
ORDER BY category, key;
EOF

echo ""
echo "=========================================="
echo "✓ Database repair complete!"
echo "=========================================="
echo "Now restart the service:"
echo "  sudo systemctl restart piano-led-visualizer"
echo ""
