# GPIO Initialization Error: ws2811_init failed with code -11

## SOLUTION FOUND ✅

**The issue was GPIO 19 with Channel 0.** GPIO 19 on Raspberry Pi Zero 2 W requires Channel 1 (PWM1), not Channel 0.

**Fix Applied:**
- GPIO Pin: 19
- PWM Channel: 1
- Removed conflicting device tree overlay (`gpio-ir`)

This configuration now works correctly and LEDs are initializing successfully!

---

## Problem Statement

The LED controller was failing to initialize with this error:
```
Failed to initialize LED controller: ws2811_init failed with code -11 (Selected GPIO not possible)
```

Error code `-11` from rpi_ws281x means: **Selected GPIO not possible**

This typically indicates one of these issues:
1. **GPIO pin is already in use** by another service or hardware (device tree overlay conflict)
2. **Wrong PWM channel for the GPIO pin** (GPIO 19 needs channel 1, not 0)
3. **Permissions issue** (usually resolved by running as root/sudo)
4. **GPIO pin doesn't support PWM** (needed for WS2812B control)

## Root Cause Investigation

### Step 1: Check What GPIO Pin is Configured

On the Pi, SSH and check the current settings:

```bash
# SSH into Pi
ssh pi@192.168.1.225

# Check if service is running
sudo systemctl status piano-led-visualizer

# View the last 30 lines of logs to see what GPIO pin was attempted
sudo journalctl -u piano-led-visualizer -n 30 | grep -E "gpio_pin|pin [0-9]|GPIO"

# Alternative: check the settings database directly
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db "SELECT * FROM settings WHERE category='led' AND key='gpio_pin';"
```

### Step 2: Check Available GPIO Pins

```bash
# List GPIO pins that are already in use
cat /proc/device-tree/model
gpioinfo  # Shows GPIO availability (if installed)

# Alternative: check for common conflicts
ps aux | grep gpio
lsof /dev/mem 2>/dev/null | head -20
```

### Step 3: Verify rpi_ws281x Compatibility

```bash
# Check if rpi_ws281x is properly installed
python3 -c "from rpi_ws281x import PixelStrip; print('rpi_ws281x OK')"

# Test GPIO 18 specifically (most common for WS2812B)
python3 << 'EOF'
try:
    from rpi_ws281x import PixelStrip, Color
    # Test with GPIO 18
    strip = PixelStrip(1, 18, 800000, 10, False, 255, 0)
    strip.begin()
    strip.setPixelColor(0, Color(255, 0, 0))
    strip.show()
    print("GPIO 18 works!")
    strip.reset()
except Exception as e:
    print(f"GPIO 18 error: {e}")
EOF
```

## Solution: GPIO Pin Selection

### For Most Raspberry Pi Models (Raspberry Pi 4/5)

GPIO 18 is the **recommended pin** for WS2812B LED strips. It supports PWM and has good hardware support.

**However**, if GPIO 18 is not available, the following pins have PWM support:
- **GPIO 12** - PWM0 (Hardware PWM) ✅ Recommended alternative
- **GPIO 13** - PWM1 (Hardware PWM) ✅ Recommended alternative  
- **GPIO 18** - PWM0 (Hardware PWM) ✅ Most common
- **GPIO 19** - PWM1 (Hardware PWM) ✅ Most common

### Why Error -11 Occurs

The error occurs when:
1. GPIO 18 is in use by Bluetooth or other hardware
2. GPIO pin conflicts with another device tree overlay
3. Pin number is wrong in settings.db

## Fix Steps

### Option A: Fix via Web API (Recommended)

If the service is running enough to serve HTTP (even in LED-disabled mode):

```bash
# Get current GPIO setting
curl -X GET http://192.168.1.225:5001/api/settings/led

# Try changing to GPIO 12 or 13 instead
curl -X POST http://192.168.1.225:5001/api/settings/led \
  -H "Content-Type: application/json" \
  -d '{"gpio_pin": 12}'

# Or GPIO 13
curl -X POST http://192.168.1.225:5001/api/settings/led \
  -H "Content-Type: application/json" \
  -d '{"gpio_pin": 13}'

# Restart service
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# Check if it worked
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

### Option B: Fix via Database (Direct)

If API is not responding:

```bash
# SSH into Pi
ssh pi@192.168.1.225

# Stop the service
sudo systemctl stop piano-led-visualizer

# Backup settings first
cp /home/pi/PianoLED-CoPilot/backend/settings.db /home/pi/PianoLED-CoPilot/backend/settings.db.backup

# Update GPIO pin in database
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db << 'EOF'
-- Try GPIO 12 first (common alternative)
UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';

-- Verify the change
SELECT category, key, value FROM settings WHERE category='led' ORDER BY key;
EOF

# Restart service
sudo systemctl start piano-led-visualizer
sleep 5

# Check logs
sudo journalctl -u piano-led-visualizer -n 20 | tail -10
```

### Option C: If GPIO 12 Also Fails

Try GPIO 13 or GPIO 19:

```bash
ssh pi@192.168.1.225

sudo systemctl stop piano-led-visualizer

cd /home/pi/PianoLED-CoPilot

# Try GPIO 13
sqlite3 backend/settings.db "UPDATE settings SET value='13' WHERE category='led' AND key='gpio_pin';"

# Or GPIO 19
# sqlite3 backend/settings.db "UPDATE settings SET value='19' WHERE category='led' AND key='gpio_pin';"

sudo systemctl start piano-led-visualizer
sleep 5

sudo journalctl -u piano-led-visualizer -n 20 | tail -10
```

## Verification

After changing GPIO pin, verify it works:

```bash
# Check health endpoint
curl http://192.168.1.225:5001/api/calibration/health | jq .

# Expected response when working:
{
  "led_controller_exists": true,
  "led_controller_type": "LEDController",
  "num_pixels": 255,
  "led_enabled": true,
  "pixels_initialized": true,
  "brightness": 0.3,
  "pin": 12,              # Should match GPIO pin you set
  "status": "OK",
  "message": "LED controller is responsive"
}

# Test LED control
curl -X POST http://192.168.1.225:5001/api/calibration/test-led \
  -H "Content-Type: application/json" \
  -d '{"index": 0, "color": [255, 0, 0], "duration_ms": 1000}'

# LED at index 0 should blink red for 1 second
```

## Troubleshooting

### Still Getting Error -11?

```bash
# Check what other processes might be using GPIO
ps aux | grep -i gpio
ps aux | grep -i raspi
ps aux | grep -i pigpio

# Check kernel messages for GPIO errors
dmesg | grep -i gpio | tail -20

# Check device tree overlays
dtc -I fs /proc/device-tree > /tmp/devicetree.txt 2>/dev/null
grep -i gpio /tmp/devicetree.txt | head -20
```

### GPIO Pin Still Fails?

Try **GPIO 14** (UART TX - less commonly used):

```bash
ssh pi@192.168.1.225
sudo systemctl stop piano-led-visualizer
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db "UPDATE settings SET value='14' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

## Hardware Setup Verification

Once GPIO is working, verify physical connections:

```bash
# SSH into Pi
ssh pi@192.168.1.225

# Run test to verify LED strip responds
python3 << 'EOF'
import time
from rpi_ws281x import PixelStrip, Color

# Use the GPIO pin you found working (e.g., 12)
GPIO_PIN = 12
NUM_LEDS = 255

strip = PixelStrip(NUM_LEDS, GPIO_PIN, 800000, 10, False, 255, 0)
strip.begin()

# Test 1: Red
for i in range(NUM_LEDS):
    strip.setPixelColor(i, Color(255, 0, 0))
strip.show()
print("LEDs should be RED")
time.sleep(2)

# Test 2: Green
for i in range(NUM_LEDS):
    strip.setPixelColor(i, Color(0, 255, 0))
strip.show()
print("LEDs should be GREEN")
time.sleep(2)

# Test 3: Blue
for i in range(NUM_LEDS):
    strip.setPixelColor(i, Color(0, 0, 255))
strip.show()
print("LEDs should be BLUE")
time.sleep(2)

# Off
for i in range(NUM_LEDS):
    strip.setPixelColor(i, Color(0, 0, 0))
strip.show()
print("LEDs should be OFF")
EOF
```

## Common GPIO Pin Mapping

| Raspberry Pi Model | Recommended GPIO | Alternative 1 | Alternative 2 |
|---|---|---|---|
| Pi 4/5 | 18 | 12 | 13 |
| Pi 3/3B+ | 18 | 12 | 13 |
| Pi Zero/Zero W | 18 | 12 | 13 |
| Pi Zero 2 W | 18 | 12 | 13 |

## Summary

1. **Identify problem**: Check what GPIO pin is currently set
2. **Test alternatives**: Try GPIO 12, 13, or 19
3. **Verify fix**: Use `/api/calibration/health` endpoint
4. **Validate hardware**: Use test script to verify LED strip responds

The error `-11` is usually fixed by switching to a GPIO pin that's not in use (GPU 12 or 13 are good alternatives if GPIO 18 is taken).
