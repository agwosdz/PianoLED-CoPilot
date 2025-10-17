# GPIO Error Resolution - Oct 17, 2025

## Issue Summary

Service successfully starts and all systems initialize correctly, but LED controller fails with:
```
Failed to initialize LED controller: ws2811_init failed with code -11 (Selected GPIO not possible)
```

**Error -11 means:** The GPIO pin configured in settings.db is not available on this Raspberry Pi.

## Root Cause

The GPIO pin in your settings.db (likely GPIO 18 or 19) is unavailable because:
- It's in use by another service (Bluetooth, UART, etc.)
- It's not supported on your specific Pi model
- It has a hardware conflict

## Solution: 3-Step Quick Fix

### Step 1: Identify Working GPIO Pins
```bash
ssh pi@192.168.1.225
cd /home/pi/PianoLED-CoPilot
sudo bash scripts/diagnose-gpio.sh
```

This will show which GPIO pins are available. Look for pins marked with ✓.

### Step 2: Update settings.db with Working Pin

If the diagnostic shows GPIO 12 is available:
```bash
sudo systemctl stop piano-led-visualizer
sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
```

### Step 3: Verify Success
```bash
curl http://localhost:5001/api/calibration/health | jq .
```

Expected response:
```json
{
  "status": "OK",
  "led_controller_exists": true,
  "led_enabled": true,
  "pin": 12
}
```

## GPIO Pins to Try (In Order)

1. **GPIO 12** ← Usually works first
2. **GPIO 13** ← Usually works second
3. **GPIO 19** ← Try if 12/13 don't work
4. **GPIO 21** ← Last resort

## Recommended Reading Order

1. **Quick Fix**: `GPIO_ERROR_11_QUICK_FIX.md` (3 steps)
2. **Analysis**: `GPIO_ERROR_11_ANALYSIS.md` (explanation)
3. **Detailed Guide**: `GPIO_INITIALIZATION_ERROR_FIX.md` (comprehensive)

## System Status

✅ **Fixed:**
- LED Controller singleton pattern (can reread settings.db)
- Health check endpoint (diagnoses LED state)
- start_wrapper.sh (clean process management)
- Calibration.py (verified not the culprit)

🔧 **Current Issue:**
- GPIO pin not available (fix: use diagnostic script, change pin)

✅ **Once GPIO is Fixed:**
- Everything else is ready to go!
- LED mapping algorithm working
- Distribution modes working
- API endpoints ready
- Frontend calibration complete

## Why This Happened

The GPIO pin configuration was probably set up for a different Raspberry Pi model or before other services were added. Your specific Pi model has different GPIO pin availability.

Good news: Most Pi models have at least 2-3 working PWM-capable GPIO pins. The diagnostic script will find them automatically!

## Next Actions

1. **SSH into Pi and run diagnostic script**
2. **Note which GPIO pins are available**
3. **Update settings.db with available pin**
4. **Restart service and verify with health endpoint**
5. **Test LED control to confirm working**

## Files Created/Updated Today

### Documentation
- `GPIO_ERROR_11_QUICK_FIX.md` - 3-step fix guide
- `GPIO_ERROR_11_ANALYSIS.md` - Problem explanation
- `GPIO_INITIALIZATION_ERROR_FIX.md` - Comprehensive troubleshooting

### Scripts
- `scripts/diagnose-gpio.sh` - Automatic GPIO pin diagnostics

### Code (Previously Updated)
- `backend/app.py` - Singleton reset (working)
- `backend/api/calibration.py` - Health check endpoint (working)
- `start_wrapper.sh` - Enhanced startup (working)

## Questions Answered

**Q: Why is the service running in LED-disabled mode?**
A: The LED controller failed to initialize due to GPIO unavailability, so the API falls back to simulation mode. Once GPIO is fixed, LEDs will initialize on next restart.

**Q: Why didn't the health check endpoint help?**
A: The health check endpoint IS working - it's telling us the LED controller exists but can't initialize the hardware. That's exactly the diagnostic we needed.

**Q: Did calibration.py break the LEDs?**
A: No. calibration.py was investigated thoroughly and cleared. The issue is the GPIO pin configuration.

**Q: Is the singleton reset working?**
A: Yes! The logs show it's being called correctly. Once GPIO is fixed, settings.db changes will be read properly on service restart.

## Success Criteria

Once you complete the fix:

✅ Health endpoint returns `"status": "OK"`
✅ `"pixels_initialized": true`
✅ `"led_enabled": true`
✅ LED test endpoint blinks LED 0
✅ LED service responds to API commands

All of these indicate the GPIO fix was successful!

## Support

If GPIO 12, 13, and 19 all fail:

1. Run full diagnostics: `sudo bash scripts/diagnose-gpio.sh`
2. Check for conflicting services: `ps aux | grep -i gpio`
3. Review device tree: `dtc -I fs /proc/device-tree | grep gpio`
4. Try GPIO 21, 26, or 14

---

**Status**: GPIO error identified and resolution documented
**Estimate**: 5 minutes to implement fix
**Expected Outcome**: LEDs fully operational
**Blockers**: None - diagnostic tools and fix procedure ready
