# LED Controller Diagnostic Guide

## Quick Diagnosis

Use these commands to identify what's broken with the LED controller:

### Step 1: Deploy the Health Check Endpoint
This adds a new `/api/calibration/health` endpoint to check LED controller status.

Files changed:
- `backend/api/calibration.py` - Added health check endpoint (lines 57-115)

Deploy:
```bash
scp backend/api/calibration.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/api/
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5
```

### Step 2: Check LED Controller Health After Restart

```bash
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

**Expected healthy response:**
```json
{
  "timestamp": "2025-10-17T12:10:00.123456",
  "led_controller_exists": true,
  "led_controller_type": "LEDController",
  "status": "OK",
  "num_pixels": 255,
  "led_enabled": true,
  "pixels_initialized": true,
  "brightness": 0.3,
  "pin": 18,
  "message": "LED controller is responsive"
}
```

### Step 3: Interpret the Results

#### If `status` is "OK"
✅ LED controller is fine! The issue must be elsewhere.
- Try: `curl -X POST http://192.168.1.225:5001/api/calibration/test-led/50`
- Should light up LED 50 for 3 seconds

#### If `status` is "ERROR" or "DEGRADED"
❌ LED controller is broken. Check the specific fields:

| Field | Expected | Problem If |
|-------|----------|-----------|
| `led_controller_exists` | true | false → LED controller not initialized |
| `num_pixels` | 255 | 0 or null → Wrong LED count in settings |
| `led_enabled` | true | false → LED disabled in settings |
| `pixels_initialized` | true | false → rpi_ws281x not loaded (hardware issue) |
| `brightness` | > 0 | 0 → Brightness set to 0 |

### Step 4: Identify the Root Cause

If health check shows error, check logs:

```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 100 | grep -E 'LED|led|ERROR|error'"
```

Look for:
- `LEDController initialization failed` → Hardware not available
- `num_pixels is invalid` → Settings.db has bad LED count
- `led_enabled is False` → LED disabled in settings
- `rpi_ws281x library not available` → Missing hardware libraries

### Step 5: Common Fixes

#### Fix 1: LED count wrong in settings.db
```bash
# Check current LED count
curl http://192.168.1.225:5001/api/settings/led/led_count

# If wrong, set it back to 255
curl -X PUT http://192.168.1.225:5001/api/settings/led/led_count \
  -H "Content-Type: application/json" \
  -d '{"value": 255}'

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# Test again
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

#### Fix 2: LED disabled in settings
```bash
# Check if LED enabled
curl http://192.168.1.225:5001/api/settings/led/enabled

# If false, enable it
curl -X PUT http://192.168.1.225:5001/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": true}'

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# Test again
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

#### Fix 3: Brightness set to 0
```bash
# Check brightness
curl http://192.168.1.225:5001/api/settings/led/brightness

# If 0, set it to reasonable value
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.5}'

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# Test again
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

#### Fix 4: Hardware not loaded
If `pixels_initialized` is false AND `led_enabled` is true:
- Hardware libraries may be missing
- Try: `ssh pi@192.168.1.225 "python3 -c \"from rpi_ws281x import PixelStrip; print('OK')\""`
- If error, you need to install rpi_ws281x on the Pi

### Step 6: Reproduce the Issue

Once health checks pass, try to reproduce the issue:

```bash
# 1. Check everything works
curl http://192.168.1.225:5001/api/calibration/health | jq .status

# 2. Change a setting
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.7}'

# 3. Push new settings.db and restart
# (Your normal deployment process)
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# 4. Check health again
curl http://192.168.1.225:5001/api/calibration/health | jq .status

# Should still be "OK"
```

If it's NOT "OK" after this:
- LEDs are broken by a setting change
- Check what setting was changed
- It's likely one of these: `led_count`, `led_enabled`, `brightness`, `gpio_pin`, `led_type`

### Step 7: Report the Issue

If health check fails after a specific setting change, report:
1. The health check response (full JSON)
2. What setting was changed and to what value
3. The logs from after the restart: `sudo journalctl -u piano-led-visualizer -n 50`

### Health Check Response Fields Explained

```json
{
  "timestamp": "ISO 8601 timestamp of when health check was run",
  "led_controller_exists": "true/false - is LED controller instance created",
  "led_controller_type": "Type name of LED controller class",
  "status": "OK / DEGRADED / ERROR",
  "num_pixels": "Number of LEDs configured (should be 255)",
  "led_enabled": "true/false - is LED control enabled in settings",
  "pixels_initialized": "true/false - is hardware initialized (rpi_ws281x ready)",
  "brightness": "Brightness level (0.0-1.0, should be > 0)",
  "pin": "GPIO pin number (should be 18)",
  "led_state_length": "Length of internal LED state array",
  "message": "Human readable status message"
}
```

### Batch Testing Script

Save as `test_leds.sh`:

```bash
#!/bin/bash

echo "🔍 LED Controller Diagnostic"
echo "================================"
echo ""

echo "1. Checking health..."
HEALTH=$(curl -s http://192.168.1.225:5001/api/calibration/health | jq .)
STATUS=$(echo "$HEALTH" | jq -r '.status')
echo "Status: $STATUS"
echo ""

echo "2. Checking settings..."
LED_ENABLED=$(curl -s http://192.168.1.225:5001/api/settings/led/enabled | jq .)
LED_COUNT=$(curl -s http://192.168.1.225:5001/api/settings/led/led_count | jq .)
BRIGHTNESS=$(curl -s http://192.168.1.225:5001/api/settings/led/brightness | jq .)

echo "LED Enabled: $LED_ENABLED"
echo "LED Count: $LED_COUNT"
echo "Brightness: $BRIGHTNESS"
echo ""

echo "3. Testing LED control..."
curl -s -X POST http://192.168.1.225:5001/api/calibration/test-led/100 > /dev/null
echo "Sent test LED command (should blink LED 100 for 3 seconds)"
echo ""

echo "4. Full health status:"
echo "$HEALTH" | jq .
```

Run with:
```bash
bash test_leds.sh
```

## Summary

1. Deploy the health check endpoint
2. Run the health check after restart
3. If status is "ERROR" or "DEGRADED", check which setting is wrong
4. Fix the setting and restart
5. Verify with health check again
6. Report any persistent issues with the health check output

