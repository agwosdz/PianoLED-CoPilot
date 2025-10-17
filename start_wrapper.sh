#!/bin/bash
# Clean start wrapper for Piano LED Visualizer
# This ensures:
# 1. Old Python processes are fully terminated
# 2. Python cache (__pycache__) is cleared
# 3. Fresh initialization from current settings.db

echo "Starting Piano LED Visualizer..."

# Kill any existing Python processes for this app (with timeout)
echo "Cleaning up old processes..."
pkill -f "python.*app.py" || true
pkill -f "python.*start.py" || true
sleep 2

# Clear Python bytecode cache to force reimport
echo "Clearing Python cache..."
cd /home/pi/PianoLED-CoPilot
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Activate virtual environment and start
cd /home/pi/PianoLED-CoPilot/backend
source venv/bin/activate

# Log startup
echo "$(date '+%Y-%m-%d %H:%M:%S') - Piano LED Visualizer starting..." >> /tmp/piano-led-startup.log

# Run with explicit unbuffered output to ensure logs appear immediately
exec python3 -u start.py
