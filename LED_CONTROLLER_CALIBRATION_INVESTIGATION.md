# LED Controller Issue Investigation

## Observation
- User says: "maybe something else broke the LED CONTROLLER with the last updates to calibration.py"
- LEDs are initializing successfully (logs show: "LED controller initialized with 255 pixels on pin 18")
- BUT: LEDs stop responding after pushing settings.db and restarting service

## Hypothesis
calibration.py changes may not directly break the LED controller, but rather:
1. The LED controller initializes fine
2. But when calibration.py is imported, something interferes with LED functionality
3. OR: An endpoint in calibration.py is being called that damages the LED controller state

## Investigation Checklist

### Check 1: Module-level code execution in calibration.py
- [x] Reviewed calibration.py lines 1-55
- [x] Result: Only function definitions and blueprint creation, no problematic module-level code

### Check 2: Import side effects from backend.config
- [x] calibration.py imports from backend.config: generate_auto_key_mapping, apply_calibration_offsets_to_mapping, validate_auto_mapping_config, get_piano_specs, calculate_physical_led_mapping
- [x] Reviewed backend/config.py 
- [x] Result: These are just function definitions, no module-level code that touches LED controller

### Check 3: LED controller initialization order
- [x] calibration_bp imported at line 996 in app.py
- [x] LED controller initialized at line 100+
- [x] Result: LED controller initialized BEFORE calibration_bp imported ✅

### Check 4: Module-level endpoint registration
- [x] Reviewed calibration.py lines 40-55
- [x] Result: Only Blueprint created, routes defined with @decorators, no code executed ✅

## Possible Issues

### Issue 1: get_led_controller() function
Location: calibration.py line 34

Current implementation:
```python
def get_led_controller():
    try:
        from flask import current_app
        if current_app and hasattr(current_app, 'config'):
            led_ctrl = current_app.config.get('led_controller')
            if led_ctrl is not None:
                return led_ctrl
        from backend.app import led_controller
        return led_controller
    except Exception as e:
        logger.error(f"Error getting LED controller: {e}", exc_info=True)
        return None
```

**Problem**: This could fail if:
- current_app is not available (outside request context)
- led_controller not in app.config
- Circular import issues
- led_controller is None (not initialized)

**Risk**: If any endpoint is called that uses get_led_controller(), and it fails, the endpoint logs an error but continues. But this doesn't break the LED controller itself.

### Issue 2: LED endpoints that might break state

Potential problem endpoints in calibration.py:
1. `/test-led/<index>` - Lights up LED then schedules turn-off
2. `/led-on/<index>` - Lights up LED persistently
3. `/leds-on` - Batch LED operations
4. `/turn-off-led/<index>` - Turns off LED

**Concern**: If `_turn_off_led_after_delay()` or LED operations leave the controller in a bad state, subsequent LED operations might fail.

### Issue 3: Settings changes affecting LED count

If settings.db changes and sets an incorrect LED count:
- Old LED count: 255
- New LED count: 1 or 0 (by mistake)
- LED controller wouldn't reinitialize
- LEDs would appear broken

BUT: User said they're pushing settings.db deliberately, so presumably with correct values.

## Questions for User

To help diagnose, please check:

1. **Are the LEDs physically responding at all after restart?**
   - Try: `curl -X POST http://192.168.1.225:5001/api/calibration/test-led/100`
   - Do LEDs light up?

2. **What changed in calibration.py recently?**
   - Any new imports?
   - Any changes to LED controller initialization?
   - Any changes to how endpoints access the LED controller?

3. **Does it happen consistently?**
   - Every time you push settings.db?
   - Only after specific setting changes?
   - Only if you change certain settings (brightness, count, etc.)?

4. **What's in the new settings.db?**
   - Is `led.enabled` still true?
   - Is `led.led_count` still 255?
   - Is `led.gpio_pin` still 18?

5. **Check the logs after the issue occurs:**
   ```bash
   ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 100 | grep -E 'ERROR|error|Exception|exception|LED|led'"
   ```

## Recommended Fixes

### Fix 1: Ensure LED controller survives calibration.py import
Modify calibration.py to be more defensive about LED controller access:

```python
def get_led_controller():
    """Safe retrieval of LED controller with fallback"""
    try:
        # Try app config first
        try:
            from flask import current_app
            if current_app and hasattr(current_app, 'config'):
                led_ctrl = current_app.config.get('led_controller')
                if led_ctrl is not None:
                    return led_ctrl
        except RuntimeError:
            # Outside request context
            pass
        
        # Fallback to direct import
        from backend.app import led_controller
        if led_controller is None:
            logger.warning("LED controller is None in app")
        return led_controller
    except Exception as e:
        logger.error(f"Error getting LED controller: {e}", exc_info=True)
        return None
```

### Fix 2: Add LED controller health check
Create a healthcheck endpoint that verifies LED controller state:

```python
@calibration_bp.route('/health', methods=['GET'])
def led_health_check():
    """Check if LED controller is in good state"""
    led_ctrl = get_led_controller()
    
    if not led_ctrl:
        return jsonify({
            'status': 'ERROR',
            'led_controller_exists': False
        }), 503
    
    return jsonify({
        'status': 'OK',
        'led_controller_exists': True,
        'num_pixels': getattr(led_ctrl, 'num_pixels', None),
        'pixels_initialized': bool(getattr(led_ctrl, 'pixels', None)),
        'led_enabled': getattr(led_ctrl, 'led_enabled', None),
    }), 200
```

Then after restarting, check:
```bash
curl http://192.168.1.225:5001/api/calibration/health
```

### Fix 3: Log all LED controller method calls
Add logging to see what's happening with LEDs:

```python
# In calibration.py, wrap LED operations
def safe_turn_on_led(index, color):
    led_ctrl = get_led_controller()
    if not led_ctrl:
        logger.error("Cannot turn on LED: controller not available")
        return False, "No LED controller"
    
    try:
        logger.info(f"Turning ON LED {index} with color {color}")
        success, error = led_ctrl.turn_on_led(index, color, auto_show=True)
        logger.info(f"Result: success={success}, error={error}")
        return success, error
    except Exception as e:
        logger.error(f"Error turning on LED {index}: {e}", exc_info=True)
        return False, str(e)
```

## Next Steps

1. **Identify exactly what breaks**: Run the health check endpoint to see LED controller state
2. **Test specific operations**: Try turning on/off individual LEDs via curl
3. **Review calibration.py changes**: What specifically was added/changed recently?
4. **Isolate the cause**: Is it settings.db push, calibration.py changes, or something else?
5. **Apply fix once root cause identified**

