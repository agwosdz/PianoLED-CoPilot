# LED Controller Re-Enable Fix - October 17, 2025

## Problem

LEDs stopped working after deploying the no-overlap LED distribution mode fix. Health check showed:
- `led_enabled: false` ❌
- `pixels_initialized: false` ❌
- `status: DEGRADED` ⚠️

## Root Cause

The `led.enabled` setting in the database was set to `false`. When the service restarted after deploying the new backend code, it read this setting and initialized in **simulation mode** (LEDs disabled) instead of actual hardware control mode.

**Database Query Results:**
```sql
SELECT key, value FROM settings WHERE category='led' AND key='enabled';
-- Result: enabled|false
```

## Solution

Updated the LED enabled setting back to `true` in the database:

```bash
sqlite3 /home/pi/PianoLED-CoPilot/backend/settings.db \
  "UPDATE settings SET value='true' WHERE category='led' AND key='enabled';"
```

Then restarted the service:
```bash
sudo systemctl restart piano-led-visualizer
```

## Results After Fix

Health check now shows:
```json
{
  "brightness": 0.8,
  "led_enabled": true,         ✅
  "pixels_initialized": true,  ✅
  "status": "OK",              ✅
  "message": "LED controller is responsive"
}
```

## Why This Happened

The `led.enabled` setting is persisted in SQLite. When code changes are deployed and the service restarts, it reads from the database. If this setting was previously disabled (possibly during testing or troubleshooting), it remains disabled unless explicitly re-enabled.

## Prevention for Future Deployments

**Before restarting the service after deployment:**

1. **Verify LED settings are correct:**
   ```bash
   sqlite3 /home/pi/PianoLED-CoPilot/backend/settings.db \
     "SELECT key, value FROM settings WHERE category='led';"
   ```

2. **Ensure these critical settings:**
   - `led.enabled = true`
   - `led.gpio_pin = 19` (for Pi Zero 2 W)
   - `led_channel = 1` (for Pi Zero 2 W)

3. **Or reset to defaults** if unsure:
   ```bash
   # Delete and rebuild settings
   rm /home/pi/PianoLED-CoPilot/backend/settings.db
   sudo systemctl restart piano-led-visualizer
   ```

## Current Working Configuration

**Hardware:** Raspberry Pi Zero 2 W
- GPIO: 19
- Channel: 1 (PWM1)
- LED Count: 255 pixels
- LEDs per Meter: 200
- Enabled: ✅ true

**Mapping Modes:**
- Piano Based (with overlap): 5-6 LEDs/key, 243 shared LEDs
- Piano Based (no overlap): 2-3 LEDs/key, 0 shared LEDs ✅

**Status:** ✅ Full operational

## Service Log Reference

When service starts correctly, you should see:
```
LED controller initialized with 255 pixels on pin 19 (freq=800000, dma=10, channel=1)
LEDEffectsManager initialized with calibration range: [4, 249]
LED controller and effects manager initialized successfully with 255 LEDs
🎹 Triggering fancy startup animation...
```

If you see instead:
```
LEDs are disabled in settings - running in simulation mode
```

Then check and fix the `led.enabled` setting as shown in the "Solution" section.
