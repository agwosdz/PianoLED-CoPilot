# GPIO Settings Key Aliasing Fix

## Problem

The LED GPIO settings were suffering from a **naming convention mismatch** between frontend and backend:

- **Frontend (UX)**: Writes settings using camelCase keys like `gpioPin`, `dataPin`, `clockPin`
- **Backend (Code)**: Reads settings using snake_case keys like `gpio_pin`, `data_pin`, `clock_pin`
- **Database**: Inconsistently stored both formats, causing backend to read wrong value

This led to **repeating failures** where:
1. User sets GPIO pin to 19 in UI → stored as `gpioPin=19` in DB
2. Backend tries to read `gpio_pin` → doesn't find it, uses default 18
3. LEDs initialize on wrong pin (18 instead of 19)
4. Service fails or LEDs don't work

## Root Cause Analysis

The issue occurred in multiple layers:

### Layer 1: Frontend Settings Page
File: `frontend/src/routes/settings/+page.svelte`
```typescript
payload.led = {
  data_pin: dataPin,
  // Frontend reads from both led.data_pin and gpio.data_pin
  ...
}
payload.gpio = {
  data_pin: gpioDataPin,  // ← Uses snake_case when sending to API
  ...
}
```

### Layer 2: Backend Settings Service
File: `backend/services/settings_service.py`
- `set_setting()` calls `SettingsValidator.resolve_key_alias()` to normalize keys
- But the alias map was **incomplete** - missing `gpioPin → gpio_pin` mapping

### Layer 3: LED Controller Initialization
File: `backend/led_controller.py` line 105
```python
pin = get_setting('led', 'gpio_pin', 19)  # ← Reads snake_case only
```

### Layer 4: Database State
The settings database would accumulate entries like:
- `led|gpioPin|19` (written by old frontend)
- `led|gpio_pin|18` (leftover from earlier sessions)
- `led|data_pin|19` (from gpio.data_pin)

Backend would read the wrong one.

## Solution

### Fix 1: Add Key Aliasing in Settings Validator
File: `backend/services/settings_validator.py`

```python
_KEY_ALIASES = {
    'led': {
        'ledOrientation': 'led_orientation',
        'orientation': 'led_orientation',
        'ledCount': 'led_count',
        'LED_COUNT': 'led_count',
        'count': 'led_count',
        'gpioPin': 'gpio_pin',  # ← NEW: Frontend camelCase → backend snake_case
        'data_pin': 'gpio_pin',  # ← NEW: gpio.data_pin → led.gpio_pin
    },
    'gpio': {
        'gpioPin': 'gpio_pin',
        'dataPin': 'data_pin',
        'clockPin': 'clock_pin',
    }
}
```

**How it works:**
1. When frontend sends `gpioPin: 19`
2. `set_setting('led', 'gpioPin', 19)` is called
3. `resolve_key_alias('led', 'gpioPin')` returns `'gpio_pin'`
4. Backend stores as `led|gpio_pin|19` (canonical form)
5. `get_setting('led', 'gpio_pin', 19)` always reads correct value

### Fix 2: Database Cleanup
Removed all duplicate/legacy GPIO keys:
- ❌ `led|gpioPin` (legacy, now aliased)
- ❌ `led|clock_pin` (not used for WS2812B)
- ✅ `led|gpio_pin|19` (canonical)
- ✅ `led|led_channel|1` (required for Pi Zero 2 W)

### Fix 3: Service Restart
Deploy updated `settings_validator.py` and restart service to apply fixes.

## Validation

After deployment, verify:

```bash
# 1. Check database has correct canonical keys
sqlite3 /home/pi/PianoLED-CoPilot/backend/settings.db \
  "SELECT category, key, value FROM settings WHERE category='led' AND key IN ('gpio_pin', 'led_channel');"

# Expected output:
# led|gpio_pin|19
# led|led_channel|1

# 2. Check service initialized on correct GPIO
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 5 | grep 'LED controller'"

# Expected output should show:
# LED controller initialized with 255 pixels on pin 19 (freq=800000, dma=10, channel=1)
```

## Prevention Going Forward

### For Backend Developers:
- **Always use snake_case** for internal settings keys: `gpio_pin`, `led_channel`, `data_pin`
- **Add aliases** in `_KEY_ALIASES` if frontend uses different naming
- **Never store duplicate keys** - the alias system should normalize them at write time

### For Frontend Developers:
- **Use any naming style** in the component (camelCase, snake_case)
- **Know that `set_setting()` normalizes** via the alias map
- **Verify in backend logs** what key was actually stored

### Configuration Best Practices:

```python
# ✅ GOOD: Backend reads canonical name, frontend sends any format
pin = settings_service.get_setting('led', 'gpio_pin', 19)

# ✅ GOOD: Alias maps different frontend names to canonical backend names
'gpioPin': 'gpio_pin',  # Frontend camelCase → backend snake_case

# ❌ BAD: Multiple sources of truth with different names
led|gpioPin = 19
led|gpio_pin = 18
# → Backend won't know which is correct
```

## Timeline of Previous Occurrences

This same issue repeated multiple times during development:

1. **Session 1**: GPIO 18 default caused initial LED issues
2. **Phase 4 (Oct 17)**: Discovered `gpio_pin=18` vs `gpioPin=19` mismatch in DB
3. **Phase 5 (Oct 17, again)**: LEDs stopped working → database corrupted again
4. **This fix**: Added permanent aliasing to prevent recurrence

The aliasing system ensures the **last recurrence** of this issue.

## Files Modified

- ✅ `backend/services/settings_validator.py` - Added key aliases for GPIO settings
- ✅ Database cleaned - removed duplicate keys
- ✅ Service restarted with updated code

## Related Documentation

- `LED_INDEXING_TERMINOLOGY.md` - Clarifies LED number, LED index, calibration range terminology
- `GPIO_PIN_NAMING_MISMATCH_FIX.md` - Previous analysis of this same issue
- `DEPLOYMENT_GUIDE.md` - Instructions for deploying to Pi
