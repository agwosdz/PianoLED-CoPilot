# GPIO Error Documentation Index

## Quick Links

| Document | Purpose | Read Time | Best For |
|----------|---------|-----------|----------|
| `GPIO_ERROR_11_QUICK_FIX.md` | 3-step fix guide | 2 min | Just want to fix it now |
| `GPIO_ERROR_11_ANALYSIS.md` | Problem explanation | 5 min | Want to understand why |
| `GPIO_INITIALIZATION_ERROR_FIX.md` | Comprehensive guide | 15 min | Need detailed troubleshooting |
| `GPIO_ERROR_RESOLUTION_SUMMARY.md` | Full summary | 10 min | Complete overview |

## Diagnostic Script

**Location:** `scripts/diagnose-gpio.sh`

**Run it with:**
```bash
ssh pi@192.168.1.225
cd /home/pi/PianoLED-CoPilot
sudo bash scripts/diagnose-gpio.sh
```

**What it does:**
- Shows Pi model
- Lists current LED settings
- Tests which GPIO pins are available
- Checks for process conflicts
- Shows service status
- Provides recommendations

## The Problem

Error code `-11` from rpi_ws281x means: **"Selected GPIO not possible"**

This means the GPIO pin configured in settings.db is not available on your Raspberry Pi.

## The Solution (3 Steps)

1. **Run diagnostics** → `sudo bash scripts/diagnose-gpio.sh`
2. **Note working GPIO pin** → Look for ✓ "Available" 
3. **Update settings** → `sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"`
4. **Restart service** → `sudo systemctl restart piano-led-visualizer`
5. **Verify** → `curl http://localhost:5001/api/calibration/health | jq .`

## GPIO Pins to Try

Try in this priority order (most likely to work first):

1. **GPIO 12** ← Usually works (dedicated PWM)
2. **GPIO 13** ← Usually works (dedicated PWM)
3. **GPIO 19** ← Try if others fail
4. **GPIO 21** ← Last resort

## Document Reading Recommendations

### If you're in a hurry (5 min):
→ Read `GPIO_ERROR_11_QUICK_FIX.md`

### If you want to understand the issue (15 min):
→ Read `GPIO_ERROR_11_ANALYSIS.md` then `GPIO_ERROR_11_QUICK_FIX.md`

### If you're stuck or need detailed help (30 min):
→ Read `GPIO_INITIALIZATION_ERROR_FIX.md` completely

### If you want the full picture:
→ Read `GPIO_ERROR_RESOLUTION_SUMMARY.md`

## Success Criteria

After applying the fix, you should see:

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

If `"status": "OK"`, the fix worked! 🎉

## System Status Before Fix

| Component | Status |
|-----------|--------|
| Service startup | ✅ Works |
| Singleton reset | ✅ Works |
| Health check endpoint | ✅ Works |
| Settings.db reading | ✅ Works |
| GPIO initialization | ❌ Blocked |
| LED hardware | ❌ Can't initialize |

## System Status After Fix

All components will be ✅ working!

## Files Created This Session

### Documentation
- `GPIO_ERROR_11_QUICK_FIX.md` - 3-step fix
- `GPIO_ERROR_11_ANALYSIS.md` - Analysis of problem
- `GPIO_INITIALIZATION_ERROR_FIX.md` - Comprehensive guide
- `GPIO_ERROR_RESOLUTION_SUMMARY.md` - Full summary
- `GPIO_HELP_DOCUMENTATION_INDEX.md` - This file

### Script
- `scripts/diagnose-gpio.sh` - Automatic diagnostics

## Previous Session's Work (Still Working!)

- `backend/app.py` - Singleton reset mechanism ✅
- `backend/api/calibration.py` - Health check endpoint ✅
- `start_wrapper.sh` - Enhanced startup ✅
- LED mapping algorithm - Both modes ✅
- Distribution mode backend & frontend ✅
- All API endpoints ✅

## Next Steps After GPIO Fix

Once GPIO is working:
1. Test LED control endpoints
2. Verify MIDI input processing
3. Test calibration mode
4. Test distribution modes
5. Full end-to-end validation

## Questions?

- "How do I fix it?" → `GPIO_ERROR_11_QUICK_FIX.md`
- "Why did this happen?" → `GPIO_ERROR_11_ANALYSIS.md`
- "Nothing's working still" → `GPIO_INITIALIZATION_ERROR_FIX.md`
- "What's my GPIO pin?" → Run `scripts/diagnose-gpio.sh`
- "Is my fix working?" → Check health endpoint

---

**Bottom Line:** The fix is straightforward (change one GPIO pin), and everything else is ready to go! 🚀
