# GPIO Pin Configuration Mismatch Fix

## Problem

The LED controller was initializing on **GPIO 18** instead of the configured **GPIO 19**, causing the health endpoint to display the wrong pin number.

**Evidence:**
```json
{
  "pin": 18,  // ❌ Wrong! Should be 19
  "status": "OK"
}
```

And service logs showed:
```
LED controller initialized with 255 pixels on pin 18 (freq=800000, dma=10, channel=0)
```

## Root Cause

**Conflicting GPIO settings in the database:**

```sql
SELECT key, value FROM settings WHERE category='led' AND key LIKE '%gpio%';

gpio_pin     → 18   ❌ Backend was reading this (wrong value)
gpioPin      → 19   ✓ Frontend was writing this (correct value)
```

The backend's `settings_service.py` and `led_controller.py` are configured to read from the **snake_case key** `'gpio_pin'`, while the frontend and UX write to the **camelCase key** `'gpioPin'`. The database had both keys with different values, and the backend read the wrong one.

### Configuration Layers

**Backend expects (snake_case):**
- File: `backend/services/settings_service.py` line 185
- Key: `'gpio_pin'` (snake_case)

**Frontend provides (camelCase):**
- File: `frontend/src/lib/stores/settings.ts` line 125
- Key: `'gpioPin'` (camelCase)
- Mapping: `'gpioPin': ['led', 'gpioPin']`

### Why Both Keys Existed

The database had accumulated both naming conventions over time:
1. Initial setup created `gpioPin=19` (frontend format)
2. Later changes created `gpio_pin=18` (backend format)
3. Neither was deleted, causing a conflict

## Solution

**Clean up conflicting GPIO settings in the database:**

```sql
-- Delete the conflicting gpio_pin=18 entry
DELETE FROM settings WHERE category='led' AND key='gpio_pin' AND value='18';

-- Delete duplicate GPIO settings from the wrong category
DELETE FROM settings WHERE category='gpio' AND key IN ('data_pin', 'clock_pin', 'pins');

-- Insert the correct gpio_pin setting (backend expects snake_case)
INSERT OR REPLACE INTO settings (category, key, value, data_type, updated_at) 
VALUES ('led', 'gpio_pin', '19', 'number', datetime('now'));
```

**Final database state:**
```
led | gpio_pin  | 19  ✓  (backend reads this)
led | gpioPin   | 19  ✓  (frontend writes this - same value)
led | clock_pin | 19  ✓  (I2S config)
led | data_pin  | 19  ✓  (I2S config)
```

## Results After Fix

**Service logs now show correct GPIO:**
```
LED controller initialized with 255 pixels on pin 19 (freq=800000, dma=10, channel=1) ✅
```

**Health endpoint shows correct pin:**
```json
{
  "pin": 19,                    ✅
  "status": "OK",
  "pixels_initialized": true,   ✅
  "led_enabled": true           ✅
}
```

## Key Insights

### Naming Convention Mismatch

- **Backend (Python):** Uses snake_case (`gpio_pin`)
- **Frontend (TypeScript/Svelte):** Uses camelCase (`gpioPin`)
- **Database:** Should have consistent naming (was broken with both)

### Proper Fix Going Forward

The mapping layer in `frontend/src/lib/stores/settings.ts` handles the conversion:
```typescript
'gpioPin': ['led', 'gpio_pin']  // Frontend camelCase → Backend snake_case
```

This should work correctly IF the database has the proper backend key (`gpio_pin`), not the frontend key (`gpioPin`).

## Prevention

**Before deploying changes:**
1. Run a database audit to find inconsistent key names
2. Ensure only the backend's snake_case keys exist in the LED category
3. Use the settings API endpoint to verify the correct values are being read:
   ```bash
   curl http://localhost:5001/api/settings/ | jq '.led'
   ```

## Files Modified

- **Database:** `/home/pi/PianoLED-CoPilot/backend/settings.db`
  - Cleaned up duplicate GPIO settings
  - Ensured `gpio_pin=19` exists with correct value

## Current Working State

✅ GPIO pin: 19
✅ PWM Channel: 1
✅ LED Strip: 255 pixels WS2812B
✅ Calibration Range: LEDs 4-249
✅ Service Status: Running and responsive
