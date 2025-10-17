# GPIO Permissions and Channel Configuration Fix

## Issue Summary

**Error:** `ws2811_init failed with code -11 (Selected GPIO not possible)`

**Root Causes Found:**
1. **Permissions Issue:** Service was running as pi user (UID 1000) instead of root
2. **Device Tree Conflict:** `gpio-ir` overlay was claiming GPIO 19
3. **Wrong PWM Channel:** GPIO 19 requires Channel 1 on Pi Zero 2 W, not Channel 0

## Solutions Applied

### 1. Service Permissions Fix ✅

**Problem:** Service was configured as `User=root` but actually running as `pi` user, which lacks `/dev/mem` access.

**Solution:** Restarted systemd service properly:
```bash
sudo systemctl daemon-reload
sudo systemctl restart piano-led-visualizer
```

**Result:** Service now runs as root with full GPIO access.

### 2. Boot Configuration Fix ✅

**Problem:** `/boot/firmware/config.txt` had conflicting device tree overlay:
```
dtoverlay=gpio-ir,gpio_pin=19
```

This IR receiver overlay was claiming GPIO 19.

**Solution:** Removed conflicting overlay:
```bash
sudo sed -i '/dtoverlay=gpio-ir/d; /dtparam=gpio_pin/d; /gpio_pull/d' /boot/firmware/config.txt
sudo reboot
```

**Result:** GPIO 19 now available for WS2812B LED control.

### 3. PWM Channel Fix ✅

**Problem:** GPIO 19 on Raspberry Pi Zero 2 W uses PWM Channel 1, but LED controller was defaulting to Channel 0.

**Solution:** Updated settings to use GPIO 19 with Channel 1:
```bash
sqlite3 backend/settings.db "UPDATE settings SET value='19' WHERE category='led' AND key='gpio_pin';"
sqlite3 backend/settings.db "INSERT OR REPLACE INTO settings (category, key, value, data_type) VALUES ('led', 'led_channel', '1', 'int');"
sudo systemctl restart piano-led-visualizer
```

**Result:** LEDs now initialize successfully!

## Verification

Health check now returns:
```json
{
  "led_controller_exists": true,
  "led_controller_type": "LEDController",
  "num_pixels": 255,
  "led_enabled": true,
  "pixels_initialized": true,
  "brightness": 0.8,
  "pin": 19,
  "status": "OK",
  "message": "LED controller is responsive"
}
```

Service logs show:
```
2025-10-17 12:49:52 - backend.led_controller - INFO - LED controller initialized with 255 pixels on pin 19 (freq=800000, dma=10, channel=1)
2025-10-17 12:49:52 - backend.app - INFO - 🎹 Triggering fancy startup animation...
2025-10-17 12:49:52 - backend.led_effects_manager - INFO - Starting fancy startup animation
```

## Key Learnings

1. **Permissions Matter:** Even with `User=root` in systemd, verify the process actually runs as root
2. **Device Tree Overlays:** Check boot config for conflicting overlays that claim GPIO pins
3. **GPIO Channel Pairing:** Different Pi models may require specific PWM channels for GPIO pins:
   - GPIO 18 → Channel 0 (PWM0)
   - GPIO 19 → Channel 1 (PWM1)
   - GPIO 12 → Channel 0 (PWM0)
   - GPIO 13 → Channel 1 (PWM1)

4. **Pi Zero 2 W Specifics:**
   - Uses BCM2835 GPIO module
   - Requires channel 1 for GPIO 19
   - Sensitive to device tree overlays

## Files Modified

1. **`/boot/firmware/config.txt`** - Removed `gpio-ir` overlay
2. **`backend/settings.db`** - Updated GPIO pin and channel settings
3. **`backend/app.py`** - Already had proper error handling
4. **Service restart** - Ensured root execution

## Next Steps

The LED system is now fully operational:
- ✅ LEDs initialize on boot
- ✅ 255 LEDs detected
- ✅ Startup animation plays
- ✅ Health check returns OK status
- ✅ Ready for MIDI input and visualization

All remaining work is front-end integration and feature development.
