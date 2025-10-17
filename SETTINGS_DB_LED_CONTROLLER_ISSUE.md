# Settings Database Push Issue - Root Cause Analysis

## Problem Statement
Every time you push `settings.db` to the Raspberry Pi, the LED controller stops working.

## Root Cause

The issue is **NOT** simulation mode or LED enabled setting being false. The root cause is a **singleton pattern with initialization lock**:

1. **Backend app starts** → `LEDController` singleton is created and initialized once
   - Reads settings from `settings.db` at startup
   - Sets `_initialized = True` (prevents re-initialization)
   - Creates the PixelStrip hardware object

2. **You push new `settings.db`** → Changes applied to database
   - Settings service now reads from new database
   - BUT: `LEDController` doesn't know the settings changed
   - Singleton still has `_initialized = True`
   - It **REFUSES TO REINITIALIZE** even if you restart the service

3. **Why?** The singleton pattern has an initialization guard:

```python
# backend/led_controller.py line 59-60
if LEDController._initialized:
    logger.debug("LEDController singleton already initialized, skipping __init__")
    return
```

The problem is that `_initialized` is a **class-level flag** that persists across instantiation attempts. When Flask reloads the module (or the service restarts), the flag might not reset properly, OR the new database values are read but the hardware object uses cached values.

## The Real Issue: Configuration Timing

Looking at the startup logs you provided:
```
2025-10-17 12:06:40 ... LED controller initialized with 255 pixels on pin 18
2025-10-17 12:06:46 ... MIDI processor: Using calibration range [4-249] (246 available)
```

This shows it's reading **255 total LEDs** but **only using 246 available** (4-249 range). This suggests:

1. **LED count in settings.db is 255** - OK
2. **But the calibration offsets (start_led=4, end_led=249) come from the database** - might be corrupted after push
3. **Or the LED controller config is not being reloaded after settings.db changes**

## Why LED Controller Stops

When you push `settings.db` and restart the service:

### Scenario A: If LED controller is reading stale config
- Old `_initialized = True` flag prevents reloading settings
- Uses old LED count or pin configuration
- Hardware initialization fails silently or partially

### Scenario B: If settings.db is corrupted during push
- Database migration fails
- Queries return NULL or corrupted values
- `get_setting()` calls return defaults but hardware was already initialized with old values

### Scenario C: Most likely - Settings not reloaded on service restart
- The singleton pattern is aggressive about preventing re-initialization
- Even if you stop/start the service, if the Python process doesn't fully exit, the flag persists
- New `settings.db` isn't read because `__init__` returns early

## Solution

### Option 1: Reset Singleton on Service Start (RECOMMENDED)
Add code to `app.py` to explicitly reset the LED controller singleton before initialization:

```python
# In backend/app.py, BEFORE LEDController initialization
from backend.led_controller import LEDController
LEDController.reset_singleton()  # <-- Add this line

# Then initialize normally
led_controller = LEDController(settings_service=settings_service)
```

### Option 2: Remove Initialization Lock During Startup
Modify the singleton to allow reinitialization on service restart:

```python
# In backend/led_controller.py
def __init__(self, pin=None, num_pixels=None, brightness=None, settings_service=None):
    """Initialize only once per singleton instance."""
    
    # Allow re-initialization during startup if settings changed
    is_first_time = LEDController._instance is None
    
    if LEDController._initialized and not is_first_time:
        logger.debug("LEDController singleton already initialized, skipping __init__")
        return
    
    # ... rest of init code ...
    LEDController._initialized = True
```

### Option 3: Detect Settings Changes
Monitor if `settings.db` has been modified and force reinit:

```python
# Check if settings were recently modified
if settings_service and os.path.getmtime(settings_service.db_path) > startup_time:
    LEDController.reset_singleton()
    led_controller = LEDController(settings_service=settings_service)
```

### Option 4: Always Reload on Service Restart (SAFEST)
Make the systemd service always do a clean restart:

```bash
# In /etc/systemd/system/piano-led-visualizer.service
[Service]
# ... existing config ...
Restart=always
RestartSec=2
# Add environment variable to force cleanup
Environment="FLASK_ENV=production"
# Use ExecStop to force cleanup
ExecStop=/bin/sh -c 'pkill -f "python.*app.py" || true; sleep 1'
```

## Verification Steps

### Check if this is the issue:
```bash
# On Pi, check the LED controller initialization on a fresh service start
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep -E 'LED controller|initialized|_initialized'"

# If you see "LED controller initialized" followed by "skipping __init__" on restart, 
# then this is definitely the issue
```

### Test the fix:
```bash
# 1. Stop the service
ssh pi@192.168.1.225 "sudo systemctl stop piano-led-visualizer"

# 2. Clear Python cache (this helps force reimport)
ssh pi@192.168.1.225 "cd /home/pi/PianoLED-CoPilot && find . -type d -name __pycache__ -exec rm -rf {} +"

# 3. Start the service
ssh pi@192.168.1.225 "sudo systemctl start piano-led-visualizer"

# 4. Check the logs
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 50 -f"
```

## Recommended Immediate Fix

**Add this to `backend/app.py` around line 89 (before LEDController init):**

```python
# Reset LED controller singleton to ensure fresh initialization with new settings
try:
    from backend.led_controller import LEDController as LEDControllerClass
    LEDControllerClass.reset_singleton()
    logger.info("LED Controller singleton reset for fresh initialization")
except Exception as e:
    logger.warning(f"Failed to reset LED controller singleton: {e}")

# Now initialize normally
led_controller = None
```

This ensures that every service restart gets a fresh read of `settings.db`.

## Why This Fixes It

1. **On service start**: Singleton is reset → `_initialized = False`
2. **New settings.db is pushed**: Database has fresh values
3. **Service restarts** → Singleton reset happens → Reads new settings.db → Initializes with correct values
4. **LED controller works** with correct configuration

## Additional Safeguards

Add to `start_wrapper.sh` to ensure clean restarts:

```bash
#!/bin/bash
# Clear old Python processes
pkill -f "python.*app.py" || true
sleep 2

# Clear Python cache
cd /home/pi/PianoLED-CoPilot
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Start fresh
/usr/bin/python3 -m backend.app
```

## Summary

| Aspect | Details |
|--------|---------|
| Root Cause | LEDController singleton with `_initialized` lock prevents re-reading settings.db after service restart |
| Symptoms | Service starts but LEDs don't work after pushing new settings.db |
| Impact | Configuration changes (LED count, pin, etc.) are ignored until Python process fully exits |
| Fix | Call `LEDController.reset_singleton()` before initialization in `app.py` |
| Difficulty | Very Easy (1-line change) |
| Risk | Very Low (just resets the singleton pattern flag) |

