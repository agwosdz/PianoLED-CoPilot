# GPIO Error -11 Quick Fix

## The Problem
```
Failed to initialize LED controller: ws2811_init failed with code -11 (Selected GPIO not possible)
```

Error -11 = GPIO pin is not available or in use

## Quick Fix (3 Steps)

### Step 1: SSH into Pi
```bash
ssh pi@192.168.1.225
```

### Step 2: Stop Service & Try GPIO 12
```bash
sudo systemctl stop piano-led-visualizer

cd /home/pi/PianoLED-CoPilot

# Update settings to use GPIO 12 instead
sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"

# Verify the change
sqlite3 backend/settings.db "SELECT value FROM settings WHERE category='led' AND key='gpio_pin';"
```

Expected output: `12`

### Step 3: Restart & Verify
```bash
sudo systemctl start piano-led-visualizer
sleep 5

# Check if it worked
curl http://localhost:5001/api/calibration/health | jq .
```

**Expected response when working:**
```json
{
  "status": "OK",
  "led_controller_exists": true,
  "led_enabled": true,
  "num_pixels": 255,
  "pin": 12,
  "pixels_initialized": true,
  "brightness": 0.3
}
```

## If GPIO 12 Doesn't Work

Try GPIO 13:
```bash
sudo systemctl stop piano-led-visualizer
sqlite3 backend/settings.db "UPDATE settings SET value='13' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
curl http://localhost:5001/api/calibration/health | jq .
```

## If GPIO 13 Doesn't Work

Try GPIO 19:
```bash
sudo systemctl stop piano-led-visualizer
sqlite3 backend/settings.db "UPDATE settings SET value='19' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
curl http://localhost:5001/api/calibration/health | jq .
```

## Full Diagnostics

For detailed GPIO diagnostics, run the diagnostic script:

```bash
ssh pi@192.168.1.225
cd /home/pi/PianoLED-CoPilot
sudo bash scripts/diagnose-gpio.sh
```

This will show:
- Your Pi model
- Current GPIO settings
- Which GPIO pins are available
- Any process conflicts
- Service status
- API health

## Success Indicators

✅ Health endpoint shows `"status": "OK"`
✅ `"led_controller_exists": true`
✅ `"pin"` matches your configured GPIO pin
✅ `"pixels_initialized": true`

## More Help

See: `GPIO_INITIALIZATION_ERROR_FIX.md` for detailed troubleshooting
