# Deployment Guide: LED Controller Singleton Fix

## Problem This Fixes
Every time you push `settings.db` to the Raspberry Pi, the LED controller stops working because the singleton pattern's `_initialized` flag prevents re-reading the new database.

## Changes Made

### 1. **`backend/app.py`** (Line ~90)
Added singleton reset before LED controller initialization:

```python
# CRITICAL FIX: Reset LEDController singleton to ensure fresh initialization
try:
    LEDController.reset_singleton()
    logger.info("LED Controller singleton reset - will initialize with current settings.db")
except Exception as e:
    logger.warning(f"Failed to reset LED controller singleton: {e}")
```

**Impact**: Forces the LED controller to re-read settings from the database on every service restart.

### 2. **`start_wrapper.sh`** (Complete rewrite)
Enhanced to:
- Kill old Python processes cleanly
- Clear Python cache (`__pycache__` and `.pyc` files)
- Use unbuffered output for better logging

**Impact**: Ensures complete process cleanup and forces Python to reimport all modules with fresh state.

## Deployment Steps

### Step 1: Push the Updated Files to Pi
```bash
# From your Windows/local machine
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/
scp start_wrapper.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/
ssh pi@192.168.1.225 "chmod +x /home/pi/PianoLED-CoPilot/start_wrapper.sh"
```

### Step 2: Restart the Service
```bash
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
```

### Step 3: Verify the Fix Works
```bash
# Check the logs for the reset message
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 50 | grep -E 'singleton reset|LED controller initialized|rpi_ws281x'"
```

Expected output should include:
```
LED Controller singleton reset - will initialize with current settings.db
rpi_ws281x library loaded successfully
LED controller initialized with 255 pixels on pin 18
```

### Step 4: Test LED Control After Pushing settings.db
```bash
# Make a test change to settings (e.g., change brightness)
ssh pi@192.168.1.225 "curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness -H 'Content-Type: application/json' -d '{\"value\": 0.7}'"

# Restart service with new settings
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"

# Verify LEDs light up and respond
curl http://192.168.1.225:5001/api/midi-input/status
```

## How It Works

### Before (Broken)
1. Service starts → LEDController initialized with settings.db
2. Set `_initialized = True`
3. Push new settings.db to Pi
4. Restart service → LEDController sees `_initialized = True` → **SKIPS INITIALIZATION**
5. LEDs use old configuration → **Doesn't work**

### After (Fixed)
1. Service starts → **`reset_singleton()` called first** (sets `_initialized = False`)
2. LEDController reads fresh settings.db
3. Set `_initialized = True`
4. Push new settings.db to Pi
5. Restart service → **`reset_singleton()` resets flag** → LEDController initializes with new settings
6. LEDs use new configuration → **Works correctly**

## Verification Checklist

- [ ] Files copied to Pi
- [ ] Service restarted
- [ ] Logs show "singleton reset" message
- [ ] Logs show "rpi_ws281x library loaded successfully" (not in simulation mode)
- [ ] Logs show "LED controller initialized" with correct pixel count
- [ ] LED controller responds to API calls
- [ ] Can change settings and restart service with new values taking effect

## Troubleshooting

### LEDs still don't work after restart
```bash
# Check if service is running
sudo systemctl status piano-led-visualizer

# Check full logs
sudo journalctl -u piano-led-visualizer -n 100

# Manually run the startup script to see errors
sudo /home/pi/PianoLED-CoPilot/start_wrapper.sh
```

### "LED Controller singleton reset" not appearing in logs
- Make sure you pushed the updated `app.py`
- Service may not have restarted cleanly
- Try: `sudo systemctl stop piano-led-visualizer && sleep 3 && sudo systemctl start piano-led-visualizer`

### LEDs still in simulation mode
- Check that `rpi_ws281x library loaded successfully` appears in logs
- If not, hardware libraries may not be installed
- Verify: `python3 -c "from rpi_ws281x import PixelStrip"`

## One-Line Quick Deploy
```bash
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/ && scp start_wrapper.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/ && ssh pi@192.168.1.225 "chmod +x /home/pi/PianoLED-CoPilot/start_wrapper.sh && sudo systemctl restart piano-led-visualizer"
```

Then verify:
```bash
ssh pi@192.168.1.225 "sleep 5 && sudo journalctl -u piano-led-visualizer -n 20 | grep -E 'singleton|initialized|library'"
```

## Impact Analysis

| Component | Impact | Risk |
|-----------|--------|------|
| app.py | Forces fresh LED config read | Very Low - just resets a flag |
| start_wrapper.sh | Cleans old processes | Very Low - standard practice |
| LED Controller | Now reinitializes on restart | Low - same code, just runs again |
| Settings | No changes | None |
| Database | No changes | None |

## Timeline
- **Push files**: ~30 seconds
- **Service restart**: ~5 seconds
- **LED initialization**: ~2 seconds
- **Total**: ~40 seconds downtime

## Rollback (if needed)
If this breaks something, revert with:
```bash
# Revert app.py to previous version (you have it in git)
cd /home/pi/PianoLED-CoPilot
git checkout backend/app.py start_wrapper.sh
sudo systemctl restart piano-led-visualizer
```

