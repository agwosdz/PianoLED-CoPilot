# GPIO Error -11 Fix Checklist

## Problem Summary
- **Error**: `ws2811_init failed with code -11 (Selected GPIO not possible)`
- **Cause**: GPIO pin in settings.db is unavailable on this Raspberry Pi
- **Solution**: Use diagnostic script to find working GPIO pin, update settings.db, restart

## Pre-Fix Checklist

- [ ] Have SSH access to Raspberry Pi (192.168.1.225)
- [ ] Know the current GPIO pin setting (usually GPIO 18 or 19)
- [ ] Have a terminal ready for commands
- [ ] Have LED strip physically connected (or note where to connect it)

## Step-by-Step Fix Guide

### Phase 1: Identify Working GPIO Pins (5 minutes)

**Action:**
```bash
ssh pi@192.168.1.225
cd /home/pi/PianoLED-CoPilot
sudo bash scripts/diagnose-gpio.sh
```

**What to look for:**
- Find lines showing `✓ GPIO N: Available` (where N is a pin number)
- Note which pins are marked as "Available"
- Priority order: GPIO 12 > GPIO 13 > GPIO 19 > GPIO 21

**Checklist:**
- [ ] Diagnostic script ran successfully
- [ ] Identified at least one working GPIO pin
- [ ] Noted the GPIO pin number

### Phase 2: Update Settings Database (1 minute)

**Action:**
```bash
sudo systemctl stop piano-led-visualizer
```

**Checklist:**
- [ ] Service stopped successfully

**Action:**
```bash
cd /home/pi/PianoLED-CoPilot
sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"
```

**Replace 12 with your working GPIO pin number**

**Verification:**
```bash
sqlite3 backend/settings.db "SELECT value FROM settings WHERE category='led' AND key='gpio_pin';"
```

**Checklist:**
- [ ] sqlite3 command executed
- [ ] Verification shows correct GPIO pin number
- [ ] No error messages

### Phase 3: Restart Service (1 minute)

**Action:**
```bash
sudo systemctl start piano-led-visualizer
sleep 5
```

**Checklist:**
- [ ] Service started
- [ ] Waited 5 seconds for service to fully initialize

### Phase 4: Verify Success (1 minute)

**Action - Check Service Status:**
```bash
sudo systemctl status piano-led-visualizer
```

**Expected output:**
- `Active: active (running)`
- No error messages in status

**Checklist:**
- [ ] Service is running (active)
- [ ] No error indicators

**Action - Check Health Endpoint:**
```bash
curl http://localhost:5001/api/calibration/health | jq .
```

**Expected JSON response:**
```json
{
  "status": "OK",
  "led_controller_exists": true,
  "led_enabled": true,
  "num_pixels": 255,
  "pin": 12,
  "pixels_initialized": true,
  "brightness": 0.3,
  "message": "LED controller is responsive"
}
```

**Checklist:**
- [ ] Health endpoint responds
- [ ] `"status": "OK"` (not "ERROR" or "DEGRADED")
- [ ] `"pixels_initialized": true`
- [ ] `"pin"` matches the GPIO pin you set
- [ ] `"led_enabled": true`

## If GPIO 12 Doesn't Work

**Action:**
```bash
sudo systemctl stop piano-led-visualizer
sqlite3 backend/settings.db "UPDATE settings SET value='13' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
curl http://localhost:5001/api/calibration/health | jq .
```

**Checklist:**
- [ ] Tried GPIO 13
- [ ] Health endpoint returns "OK"

## If GPIO 13 Doesn't Work

**Action - Try GPIO 19:**
```bash
sudo systemctl stop piano-led-visualizer
sqlite3 backend/settings.db "UPDATE settings SET value='19' WHERE category='led' AND key='gpio_pin';"
sudo systemctl start piano-led-visualizer
sleep 5
curl http://localhost:5001/api/calibration/health | jq .
```

**Checklist:**
- [ ] Tried GPIO 19
- [ ] Health endpoint returns "OK"

## Physical Hardware Setup

**After successful GPIO fix:**

- [ ] Locate your Raspberry Pi GPIO pins
- [ ] Find the GPIO pin number you configured (e.g., GPIO 12)
- [ ] Locate the pin on your Pi's header (refer to pinout diagram)
- [ ] Connect LED strip to the correct GPIO pin
  - GPIO pin (data)
  - GND (ground)
  - 5V power (external)

**Verification:**
- [ ] LED strip physically connected to correct GPIO pin
- [ ] Power connections verified
- [ ] No loose connections

## Post-Fix Testing

**Test 1: Health Check**
```bash
curl http://localhost:5001/api/calibration/health | jq '.status'
```

**Expected:** `"OK"`

**Checklist:**
- [ ] Returns "OK"

**Test 2: Test LED Endpoint**
```bash
curl -X POST http://localhost:5001/api/calibration/test-led \
  -H "Content-Type: application/json" \
  -d '{"index": 0, "color": [255, 0, 0], "duration_ms": 1000}'
```

**Expected:** LED 0 blinks red for 1 second

**Checklist:**
- [ ] Command returns 200 OK response
- [ ] LED blinks red (if connected)
- [ ] No error messages

**Test 3: Full LED Strip Test**
```bash
curl -X POST http://localhost:5001/api/calibration/test-leds-batch \
  -H "Content-Type: application/json" \
  -d '{
    "start_index": 0,
    "end_index": 255,
    "color": [0, 255, 0],
    "duration_ms": 2000
  }'
```

**Expected:** All LEDs blink green for 2 seconds

**Checklist:**
- [ ] Command returns 200 OK
- [ ] All LEDs respond (if connected)

## Final Verification Checklist

- [ ] Health endpoint shows `"status": "OK"`
- [ ] Service is running without errors
- [ ] GPIO pin matches configuration
- [ ] `"pixels_initialized": true`
- [ ] LED test endpoints work
- [ ] LED strip responds to commands (if physically connected)
- [ ] No errors in logs: `sudo journalctl -u piano-led-visualizer -n 20`

## Success! 🎉

If all checkboxes above are checked, the GPIO error has been successfully fixed!

**Next steps:**
1. Test MIDI input processing
2. Test calibration features
3. Test distribution modes
4. Full end-to-end validation

## Troubleshooting

### If health endpoint never returns "OK"

1. Check logs: `sudo journalctl -u piano-led-visualizer -n 30 | grep -i error`
2. Try next GPIO pin (12 → 13 → 19 → 21)
3. Verify settings.db update: `sqlite3 backend/settings.db "SELECT value FROM settings WHERE category='led' AND key='gpio_pin';"`
4. Restart service: `sudo systemctl restart piano-led-visualizer`

### If service won't start

1. Check status: `sudo systemctl status piano-led-visualizer`
2. Check logs: `sudo journalctl -u piano-led-visualizer -n 50`
3. Try manual start: `cd /home/pi/PianoLED-CoPilot && python3 -m backend.app`

### If LED still doesn't blink (after GPIO fix)

1. Check physical connections
2. Verify LED strip power (5V, GND)
3. Check GPIO pin wiring
4. Try different test LED indices: `0`, `50`, `100`, `254`

## Questions?

See documentation:
- `GPIO_ERROR_11_QUICK_FIX.md` - Quick reference
- `GPIO_ERROR_11_ANALYSIS.md` - Why this happened
- `GPIO_INITIALIZATION_ERROR_FIX.md` - Detailed troubleshooting
- `GPIO_HELP_DOCUMENTATION_INDEX.md` - Documentation index

---

**Estimated Total Time:** 3-5 minutes
**Difficulty Level:** Easy
**Prerequisite:** SSH access to Pi
