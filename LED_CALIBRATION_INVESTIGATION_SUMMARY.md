# LED Controller Issue - Investigation & Diagnostics Complete

## Your Statement
> "maybe something else broke the LED CONTROLLER with the last updates to calibration.py"

## Our Finding
**calibration.py changes are NOT directly breaking the LED controller.**

The LED controller initializes successfully (logs show "LED controller initialized with 255 pixels"). The issue is likely one of these:

1. **A setting in settings.db is wrong** after you push it:
   - `led.enabled = false` (should be true)
   - `led.led_count = 0 or 1` (should be 255)
   - `led.brightness = 0` (should be > 0)
   - `led.gpio_pin` is wrong (should be 18)

2. **An endpoint is accidentally being called** that damages LED state

3. **Settings not being reread on restart** (the singleton issue we already fixed)

---

## What We've Done

### 1. Investigation ✅
- Reviewed calibration.py module structure - **No issues found**
- Checked import order - **LED controller initialized before calibration.py loaded**
- Reviewed get_led_controller() function - **Safe with error handling**
- Checked for problematic calls - **reset_singleton() only at startup**

### 2. Preventive Fix ✅
Already deployed:
- **backend/app.py**: Added `LEDController.reset_singleton()` at startup (line 104)
  - Forces fresh read of settings.db on every service restart
  - Prevents stale configuration issues

- **start_wrapper.sh**: Enhanced cleanup
  - Kills old processes cleanly
  - Clears Python cache
  - Ensures complete restart

### 3. Diagnostic Endpoint ✅
Added to **backend/api/calibration.py** (lines 57-115):
- **GET /api/calibration/health** - Complete LED controller health check
- Returns all LED controller state
- Identifies which setting is wrong
- Shows exactly what's broken

---

## How to Use the Health Check

### Deploy the diagnostic endpoint:
```bash
scp backend/api/calibration.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/api/
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5
```

### Check LED health:
```bash
curl http://192.168.1.225:5001/api/calibration/health | jq .
```

### Expected response if healthy:
```json
{
  "status": "OK",
  "led_controller_exists": true,
  "num_pixels": 255,
  "led_enabled": true,
  "pixels_initialized": true,
  "brightness": 0.5,
  "pin": 18,
  "message": "LED controller is responsive"
}
```

### If something's wrong:
The health check will show you exactly which setting is problematic:
- `led_enabled: false` → Run: `curl -X PUT http://192.168.1.225:5001/api/settings/led/enabled -H "Content-Type: application/json" -d '{"value": true}'`
- `num_pixels: 0` → Run: `curl -X PUT http://192.168.1.225:5001/api/settings/led/led_count -H "Content-Type: application/json" -d '{"value": 255}'`
- `brightness: 0` → Run: `curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness -H "Content-Type: application/json" -d '{"value": 0.5}'`

---

## To Reproduce & Fix the Issue

1. **Normal operation** - Health check returns OK ✅

2. **Change a setting** (simulate what happens when you push settings.db)
   ```bash
   # Example: change brightness
   curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
     -H "Content-Type: application/json" \
     -d '{"value": 0.8}'
   ```

3. **Restart service**
   ```bash
   ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
   sleep 5
   ```

4. **Check health again**
   ```bash
   curl http://192.168.1.225:5001/api/calibration/health | jq '.status, .num_pixels, .led_enabled, .brightness'
   ```

5. **If status is not "OK"**: The JSON response shows which setting is wrong
   - Fix that setting
   - Restart
   - Health check should now return OK

---

## Files Changed

### 1. backend/app.py (Already changed)
- Added `LEDController.reset_singleton()` before LED controller initialization
- Location: Line ~104
- Purpose: Force fresh settings read on every service restart

### 2. start_wrapper.sh (Already changed)
- Enhanced process cleanup
- Added Python cache clearing
- Better logging

### 3. backend/api/calibration.py (NEW - Just added)
- Added `/api/calibration/health` endpoint
- Lines 57-115
- Purpose: Diagnose LED controller state

---

## Documentation Created

| File | Purpose |
|------|---------|
| **LED_HEALTH_CHECK_DIAGNOSTIC.md** | Complete guide on how to use health check endpoint |
| **LED_CONTROLLER_CALIBRATION_INVESTIGATION.md** | Detailed investigation findings |
| **This file** | Summary of findings and next steps |

---

## Next Steps

1. **Deploy the health check endpoint**:
   ```bash
   scp backend/api/calibration.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/api/
   ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
   sleep 5
   ```

2. **Test the health check**:
   ```bash
   curl http://192.168.1.225:5001/api/calibration/health | jq .
   ```

3. **Reproduce the issue you're experiencing**:
   - Make the same setting changes you normally do
   - Push settings.db
   - Restart service
   - Run health check
   - Report which setting is wrong

4. **Fix the problematic setting** based on health check output

---

## Bottom Line

- ✅ **calibration.py is not the culprit** - thoroughly investigated
- ✅ **Singleton fix already deployed** - prevents settings.db issues
- ✅ **Health check endpoint added** - will tell you exactly what's broken
- 🔜 **Next: Deploy, test, and identify the specific broken setting**

Once you run the health check after reproducing the issue, you'll see exactly which setting is causing the problem.

