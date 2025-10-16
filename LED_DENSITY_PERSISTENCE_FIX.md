# LED Density Persistence Issue - ROOT CAUSE & FIX

**Date:** October 16, 2025  
**Commit:** a745b50

## The Real Problem

Your console logs showed:
- ✅ Frontend sends `leds_per_meter: 144` in payload
- ✅ Frontend logs show final payload includes the value
- ❌ Backend receives update_settings WITHOUT `leds_per_meter`

**The value was being stripped somewhere between frontend sending and backend receiving!**

## Root Cause

In `frontend/src/lib/stores/settings.ts`, the `updateSettings()` function has a property whitelist that filters what can be sent to the backend:

```typescript
// Line 748-755
const allowedProps: Record<string, Set<string>> = {
    led: new Set([
        'enabled','led_count','max_led_count','led_channel','brightness',
        'led_type','led_strip_type','led_orientation','data_pin','clock_pin',
        'gpioPin','reverse_order','color_mode','colorScheme','color_profile',
        'color_temperature','gamma_correction','white_balance','performance_mode',
        'power_supply_voltage','power_supply_current','power_limiting_enabled',
        'max_power_watts','dither_enabled','update_rate',
        'thermal_protection_enabled','max_temperature_celsius','animationSpeed'
        // ❌ leds_per_meter WAS NOT HERE!
    ]),
    // ... other categories ...
};

// Line 810-815: Properties get filtered
for (const [cat, data] of Object.entries(sanitized)) {
    // ...
    for (const [k, v] of Object.entries(data || {})) {
        if (props.has(k)) filtered[k] = v;  // ← This removed leds_per_meter!
    }
}
```

## The Fix

Added `'leds_per_meter'` to the allowed properties list for the `led` category:

```typescript
led: new Set([
    'enabled','led_count','max_led_count','led_channel','brightness',
    'led_type','led_strip_type','led_orientation','data_pin','clock_pin',
    'gpioPin','reverse_order','color_mode','colorScheme','color_profile',
    'color_temperature','gamma_correction','white_balance','performance_mode',
    'power_supply_voltage','power_supply_current','power_limiting_enabled',
    'max_power_watts','dither_enabled','update_rate',
    'thermal_protection_enabled','max_temperature_celsius','animationSpeed',
    'leds_per_meter'  // ✅ ADDED!
]),
```

## Why This Happened

The settings store has a security/consistency feature where it only allows specific properties to be sent to the backend (to prevent sending unexpected data). When `leds_per_meter` was added to the backend schema and frontend UI, it was **not added to this whitelist**.

So the frontend properly prepared the payload with `leds_per_meter: 144`, but then the store's sanitization function silently stripped it out before sending.

## Verification Steps

To verify the fix:

1. **Hard refresh browser** (Ctrl+Shift+R or Cmd+Shift+R) to load new frontend code
2. **Go to Settings → LED Configuration**
3. **Change LED Density dropdown to 144**
4. **Click Save** - you should see "Settings saved successfully!"
5. **Reload page** - value should now be 144 (not revert to 200)
6. **Check database:**
   ```bash
   sqlite3 settings.db "SELECT value FROM settings WHERE category='led' AND key='leds_per_meter';"
   # Should return: 144
   ```

## Timeline

- **Earlier Fix:** Added `leds_per_meter` to backend validator schema ✅
- **Earlier Fix:** Changed GPIO from 19 to 18 ✅
- **Today's Fix:** Added `leds_per_meter` to frontend allowedProps whitelist ✅

All three fixes were necessary for the feature to work end-to-end!

## Related Files

- `frontend/src/lib/stores/settings.ts` - Updated allowedProps
- `backend/services/settings_validator.py` - Added schema (fixed earlier)
- `backend/led_controller.py` - Uses GPIO 18 (fixed earlier)
