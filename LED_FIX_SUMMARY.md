# Quick Summary: LED Controller Settings.db Issue & Fix

## TL;DR

**Problem**: Every time you push `settings.db` to the Pi, LEDs stop working.

**Root Cause**: LEDController is a singleton with an initialization lock. The `_initialized = True` flag prevents it from re-reading the new settings.db after restart.

**Solution**: Added `LEDController.reset_singleton()` call at app startup to reset the flag, forcing fresh initialization.

**Files Changed**: 2
1. `backend/app.py` - Added singleton reset (1 function call)
2. `start_wrapper.sh` - Added cache cleanup for clean restarts

## The Real Issue

Your logs show:
```
2025-10-17 12:06:40 ... rpi_ws281x library loaded successfully  ← Hardware loaded
2025-10-17 12:06:40 ... LED controller initialized with 255 pixels  ← Initialized once
```

Then when you push new settings and restart:
- New `settings.db` arrives ✅
- Service stops/starts ✅  
- But LEDController.__init__() does this:
  ```python
  if LEDController._initialized:
      return  # ← SKIPS INITIALIZATION! Uses stale config
  ```
- LEDs don't respond ❌

## The Fix

In `backend/app.py` (around line 90):
```python
# Reset singleton to force fresh read from settings.db
LEDController.reset_singleton()

# Now initialize normally
led_controller = LEDController(settings_service=settings_service)
```

This ensures every service restart:
1. Clears the `_initialized` flag
2. Reads current `settings.db`
3. Initializes LEDs with fresh config

## Deploy It

```bash
# Copy fixed files
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/
scp start_wrapper.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/
ssh pi@192.168.1.225 "chmod +x /home/pi/PianoLED-CoPilot/start_wrapper.sh"

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"

# Verify (you should see "singleton reset" in logs)
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep singleton"
```

## Why This Works

| When | What Happens |
|------|--------------|
| Service starts (before) | singleton reads old settings, locks with `_initialized=True` |
| Push new `settings.db` | Database updated, but singleton still locked |
| Service restarts (after) | **`reset_singleton()` clears lock** → Reads new settings → LEDs work ✅ |

## Verification

After deploying, you should see in logs:
```
LED Controller singleton reset - will initialize with current settings.db
rpi_ws281x library loaded successfully
LED controller initialized with 255 pixels on pin 18
```

Then test:
```bash
# Change a setting
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.7}'

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"

# LEDs should respond with new settings ✅
```

## Impact
- **Risk**: Very Low (just resets a flag)
- **Downtime**: ~40 seconds per service restart
- **Files**: 2 small changes
- **Rollback**: `git checkout backend/app.py start_wrapper.sh`

## Documentation
See detailed analysis in:
- `SETTINGS_DB_LED_CONTROLLER_ISSUE.md` - Full root cause analysis
- `DEPLOY_LED_FIX.md` - Complete deployment guide

