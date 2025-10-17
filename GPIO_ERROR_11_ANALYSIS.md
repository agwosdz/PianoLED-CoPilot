# GPIO Pin -11 Error Analysis & Resolution

## What Happened

The service started and the singleton reset worked correctly! However, when the LEDController tried to initialize the actual hardware using `rpi_ws281x`, it got error code `-11: "Selected GPIO not possible"`.

This means **the GPIO pin configured in settings.db is not available on your Raspberry Pi**.

## Root Cause

The LED controller is trying to use a GPIO pin that:
1. Is already in use by another service (Bluetooth, UART, etc.)
2. Is not supported by your Pi model
3. Has a hardware conflict

## The Fix

We need to find which GPIO pin **is** available and update settings.db to use it.

### Immediate Action

**SSH into your Pi and run this to find available GPIO pins:**

```bash
ssh pi@192.168.1.225

cd /home/pi/PianoLED-CoPilot

# Run the diagnostic script (shows which GPIO pins work)
sudo bash scripts/diagnose-gpio.sh
```

The script will output something like:
```
📌 Testing GPIO pins for compatibility...

  ✓ GPIO 12: Available
  ✓ GPIO 13: Available
  ✗ GPIO 18: Not possible (conflict/unavailable)
  ✗ GPIO 19: Not possible (conflict/unavailable)
```

### Once You Know a Working GPIO Pin

For example, if GPIO 12 is available:

```bash
# Stop service
sudo systemctl stop piano-led-visualizer

# Update settings to use GPIO 12
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"

# Restart service
sudo systemctl start piano-led-visualizer
sleep 5

# Verify it worked
curl http://localhost:5001/api/calibration/health | jq .
```

The health response should show `"status": "OK"` and `"pin": 12`

## Why This Happens

On Raspberry Pi:
- GPIO 18 is commonly used for SPI or Bluetooth in some configurations
- GPIO 19 might be reserved for other hardware
- GPIO 12 and 13 have dedicated PWM hardware and usually work best

The good news: Most Pi models have multiple PWM-capable GPIO pins available!

## Priority Order to Try

1. **GPIO 12** ← Try this first (usually available, dedicated PWM)
2. **GPIO 13** ← Try this second (usually available, dedicated PWM)
3. **GPIO 19** ← Try this third
4. **GPIO 21** ← Try this fourth
5. **GPIO 26** ← Last resort

## Verification

Once you change the GPIO pin, verify it works by:

```bash
# Check the health endpoint
curl http://localhost:5001/api/calibration/health | jq .

# If it returns "status": "OK", the LEDs are ready to use!

# Test LED control
curl -X POST http://localhost:5001/api/calibration/test-led \
  -H "Content-Type: application/json" \
  -d '{"index": 0, "color": [255, 0, 0], "duration_ms": 1000}'
```

Look at your LED strip - the first LED should blink red for 1 second.

## What Changed from Previous Session

The singleton reset is working correctly - it's allowing fresh settings.db reads. However, the GPIO pin in your settings.db appears to be unavailable on your specific Pi hardware.

This is likely because:
1. A previous configuration assumed a different Pi model
2. Your specific Pi has that GPIO pin reserved
3. Another service is using that pin

## Files Updated

- `backend/app.py` - Singleton reset (still there, works correctly)
- `start_wrapper.sh` - Enhanced startup (still there)
- `backend/api/calibration.py` - Health check endpoint (still there)

## Next Steps

1. **Run diagnostic script** to identify available GPIO pins
2. **Update settings.db** with a working GPIO pin
3. **Restart service** and verify with health endpoint
4. **Test LED control** to confirm working

See: `GPIO_ERROR_11_QUICK_FIX.md` for the 3-step fix
See: `GPIO_INITIALIZATION_ERROR_FIX.md` for detailed troubleshooting

This is the final piece of the puzzle - once GPIO is working, everything else is ready!
