# LED Settings Defaults Updated

**Date:** October 16, 2025  
**Commit:** c182c4f  
**Status:** ✅ Defaults configured for new installations

---

## Changes Made

Updated `backend/services/settings_service.py` default settings schema:

| Setting | Before | After | Reason |
|---------|--------|-------|--------|
| `led.enabled` | **False** | **True** | LEDs enabled by default ✅ |
| `led.gpio_pin` | **19** | **18** | Correct GPIO (19 has PWM conflicts) ✅ |
| `leds_per_key` | **3** | **None** | Proportional distribution (all 88 keys) ✅ |

---

## Impact

### New Installations
When a fresh database is created (no existing settings.db):
- LEDs will be **enabled by default**
- GPIO pin **18** will be used automatically
- All 88 keys will be mapped with **proportional LED distribution**
- No manual configuration needed for basic setup

### Existing Deployments
- **No impact** - existing databases keep their current settings
- Must manually update settings if desired:
  - On Pi: already fixed earlier (enabled=True, gpio_pin=18)
  - Dev machine: remains disabled (correct for dev without hardware)

---

## Configuration Behavior

### Default Settings Schema (in code)
```python
'led': {
    'enabled': {'type': 'boolean', 'default': True},      # NEW: Enabled by default
    'gpio_pin': {'type': 'number', 'default': 18},        # NEW: GPIO 18
    'leds_per_key': {'type': 'number', 'default': None},  # NEW: Proportional
    ...
}
```

### How Defaults Are Used
1. **First-time setup**: Creates database with schema defaults
2. **Existing database**: Uses values from database (no change)
3. **Missing setting**: Falls back to schema default in code
4. **Manual override**: User can change settings anytime

### Proportional Distribution
With `leds_per_key = None`:
- Formula: `available_leds / num_keys`
- Example: 246 LEDs ÷ 88 keys = 2.79 per key
- Distribution: 70 keys × 3 LEDs + 18 keys × 2 LEDs
- Result: **All 88 keys covered**, perfect utilization

---

## Testing

### Verify Defaults in Code
```python
from backend.services.settings_service import SettingsService
service = SettingsService()

# These will be the defaults for NEW installations
schema = service._defaults_schema
print(schema['led']['enabled']['default'])      # True
print(schema['led']['gpio_pin']['default'])     # 18
print(schema['led']['leds_per_key']['default']) # None
```

### Existing Database
```python
# Existing database still has old values
service.get_setting('led', 'enabled')      # False (from database)
service.get_setting('led', 'gpio_pin')     # 19 (from database)
service.get_setting('led', 'leds_per_key') # None (uses default since not in DB)
```

---

## Deployment Checklist

- [x] Updated default settings in settings_service.py
- [x] Verified syntax with py_compile
- [x] Tested defaults retrieval
- [x] Committed to main branch
- [x] No breaking changes to existing deployments

**New installations will now:**
1. Start with LEDs enabled ✅
2. Use GPIO 18 automatically ✅
3. Get optimal key coverage (88/88) ✅
4. Require minimal configuration ✅

---

## Files Modified

| File | Change |
|------|--------|
| `backend/services/settings_service.py` | Updated `_get_default_settings_schema()` |

**Lines changed:** 3 defaults in LED section

---

## Summary

✅ **LED enabled by default** - New users don't need to enable LEDs manually  
✅ **Correct GPIO pin** - GPIO 18 instead of problematic GPIO 19  
✅ **Full key coverage** - Proportional distribution covers all 88 keys  
✅ **No impact on existing** - Production systems keep current settings  
✅ **Faster onboarding** - New installations work out of the box  

Perfect for end users and deployments! 🎉
