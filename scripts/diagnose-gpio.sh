#!/bin/bash

# GPIO Diagnostic Script for Piano LED Visualizer
# Helps identify GPIO pin issues on Raspberry Pi

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            GPIO DIAGNOSTIC SCRIPT FOR PIANO LED                ║"
echo "║              Error: ws2811_init failed with -11                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "⚠️  WARNING: This script should be run as root for full diagnostics"
  echo "   Run with: sudo bash $0"
  echo ""
fi

# Function to print section headers
print_section() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📊 $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Detect Pi Model
print_section "RASPBERRY PI MODEL"
if [ -f /proc/device-tree/model ]; then
  MODEL=$(cat /proc/device-tree/model)
  echo "✓ Model: $MODEL"
else
  echo "? Model: Unknown (could not read /proc/device-tree/model)"
fi

# Check if settings database exists
print_section "CURRENT SETTINGS CONFIGURATION"
if [ -d "/home/pi/PianoLED-CoPilot" ]; then
  cd /home/pi/PianoLED-CoPilot
  
  if [ -f "backend/settings.db" ]; then
    echo "✓ Found settings.db"
    echo ""
    echo "Current LED Settings:"
    sqlite3 backend/settings.db "SELECT '  ' || key || ': ' || value FROM settings WHERE category='led' ORDER BY key;" 2>/dev/null || {
      echo "  ERROR: Could not query settings database"
    }
  else
    echo "✗ settings.db not found at backend/settings.db"
    echo "  Expected location: /home/pi/PianoLED-CoPilot/backend/settings.db"
  fi
else
  echo "✗ PianoLED-CoPilot not found at /home/pi"
fi

# Check GPIO availability
print_section "GPIO PIN AVAILABILITY"
if command -v gpioinfo &> /dev/null; then
  echo "✓ Using gpioinfo to check GPIO:"
  gpioinfo 2>/dev/null | grep -E "GPIO[0-9]+.*\(" | head -20 || echo "  Could not retrieve GPIO info"
else
  echo "ℹ gpioinfo not available (gpiod package not installed)"
  echo "  GPIO status cannot be determined automatically"
fi

# Check for processes using GPIO
print_section "PROCESSES POTENTIALLY USING GPIO"
echo "Checking for processes that might conflict with GPIO..."
echo ""

FOUND_CONFLICT=0

# Check for pigpio daemon
if pgrep -x pigpiod > /dev/null; then
  echo "⚠️  pigpiod daemon is running (PID: $(pgrep -x pigpiod))"
  FOUND_CONFLICT=1
fi

# Check for other hardware services
if pgrep -x bluetoothd > /dev/null; then
  echo "ℹ Bluetooth daemon running - may use GPIO 18 if enabled"
fi

# Check for GPIO-related processes
RESULT=$(ps aux | grep -i gpio | grep -v grep | grep -v "piano-led" || true)
if [ -n "$RESULT" ]; then
  echo "ℹ GPIO-related processes found:"
  echo "$RESULT" | while read line; do
    echo "  $line"
  done
fi

if [ $FOUND_CONFLICT -eq 0 ]; then
  echo "✓ No major GPIO conflicts detected"
fi

# Check for rpi_ws281x installation
print_section "rpi_ws281x LIBRARY STATUS"
python3 << 'PYEOF'
import sys

try:
    from rpi_ws281x import PixelStrip, Color
    print("✓ rpi_ws281x library is installed")
except ImportError:
    print("✗ rpi_ws281x library NOT found")
    print("  Run: pip install rpi-ws281x")
    sys.exit(1)

# Try to detect which GPIO pins work
print("\n📌 Testing GPIO pins for compatibility...\n")

test_pins = [12, 13, 18, 19, 21, 26]
working_pins = []

for pin in test_pins:
    try:
        # Just try to create the strip object - don't call begin()
        strip = PixelStrip(1, pin, 800000, 10, False, 255, 0)
        working_pins.append(pin)
        print(f"  ✓ GPIO {pin}: Available")
    except Exception as e:
        error_msg = str(e).lower()
        if "gpio not possible" in error_msg or "code -11" in error_msg:
            print(f"  ✗ GPIO {pin}: Not possible (conflict/unavailable)")
        else:
            print(f"  ✗ GPIO {pin}: Error - {e}")

if working_pins:
    print(f"\n✓ Working GPIO pins: {', '.join(map(str, working_pins))}")
else:
    print("\n✗ No GPIO pins appear to be working")
    print("  This might indicate a deeper permissions or hardware issue")

PYEOF

# Check service status
print_section "SERVICE STATUS"
if systemctl is-active --quiet piano-led-visualizer; then
  echo "✓ piano-led-visualizer service is RUNNING"
  echo ""
  echo "Last 10 lines of service logs:"
  journalctl -u piano-led-visualizer -n 10 | sed 's/^/  /'
else
  echo "⚠️  piano-led-visualizer service is NOT RUNNING"
  echo ""
  echo "Last 10 lines of service logs:"
  journalctl -u piano-led-visualizer -n 10 | sed 's/^/  /'
fi

# Check API connectivity
print_section "API CONNECTIVITY"
if curl -s http://localhost:5001/api/calibration/health > /dev/null 2>&1; then
  echo "✓ API is responding on http://localhost:5001"
  echo ""
  echo "Health check response:"
  curl -s http://localhost:5001/api/calibration/health | python3 -m json.tool 2>/dev/null | sed 's/^/  /' || curl -s http://localhost:5001/api/calibration/health | sed 's/^/  /'
else
  echo "✗ API not responding on http://localhost:5001"
fi

# Device tree overlay status
print_section "DEVICE TREE STATUS"
if [ -f /proc/device-tree/pin_setup ]; then
  echo "Device tree pin setup:"
  cat /proc/device-tree/pin_setup
fi

OVERLAYS=$(ls /proc/device-tree/overlays 2>/dev/null || echo "none")
echo "Active device tree overlays:"
for overlay in $OVERLAYS; do
  echo "  - $(basename $overlay)"
done

# Summary and recommendations
print_section "DIAGNOSTIC SUMMARY & RECOMMENDATIONS"
echo ""
echo "✅ If everything shows green above:"
echo "   Your GPIO setup should be working. Issue may be elsewhere."
echo ""
echo "❌ If you see 'GPIO N: Not possible':"
echo "   That GPIO pin is unavailable. Try one of the working pins instead."
echo ""
echo "⚠️  To fix GPIO configuration:"
echo ""
echo "   1. Note which GPIO pins show as 'Working' above"
echo ""
echo "   2. Update settings database with working pin:"
echo "      sqlite3 backend/settings.db \"UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';\""
echo "      (Replace 12 with your working GPIO pin)"
echo ""
echo "   3. Restart the service:"
echo "      sudo systemctl restart piano-led-visualizer"
echo ""
echo "   4. Check health endpoint:"
echo "      curl http://localhost:5001/api/calibration/health | jq ."
echo ""
echo "For more details, see: GPIO_INITIALIZATION_ERROR_FIX.md"
echo ""
