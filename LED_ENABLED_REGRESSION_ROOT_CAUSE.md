# LED Enabled Setting Regression - Root Cause Analysis

## Issue Summary
After deploying the Phase 1 physical LED analysis code, the `led|enabled` setting was temporarily being set to `false` during service initialization, causing LEDs to run in simulation mode instead of controlling actual hardware.

## Timeline
- **16:22:46** - Service starts after Phase 1 deployment: `led|enabled = true` ✓
- **16:24:18** - During service operation: `led|enabled = false` ✗ (database backup shows value changed)
- **16:38:20** - After fix deployed: `led|enabled = true` ✓ (persistent and stable)

## Root Cause Discovery

### Step 1: Database Investigation
Discovered that the `led|enabled` setting's data_type changed between backups:
- **Before issue (backup.1760730995)**: `led|enabled|true|boolean` ✓
- **During issue (backup.1760732658)**: `led|enabled|false|number` ✗
- **After fix (current)**: `led|enabled|true|boolean` ✓

### Step 2: Code Analysis
Found the bug in `backend/services/settings_service.py` method `_get_data_type()`:

**Buggy Code (lines 743-754):**
```python
def _get_data_type(self, value: Any) -> str:
    """Get the data type string for a value."""
    if isinstance(value, str):
        return 'string'
    elif isinstance(value, (int, float)):
        return 'number'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, list):
        return 'array'
    else:
        return 'object'
```

### Step 3: Python Type System Issue
In Python, `bool` is a **subclass of `int`**:
```python
>>> isinstance(True, int)
True
>>> isinstance(True, bool)
True
```

This means when checking `isinstance(value, (int, float))` BEFORE checking for `bool`, boolean values match the int check first and get classified as 'number' instead of 'boolean'.

## Impact Chain

1. **Boolean stored with wrong type:**
   - Value: `true`
   - Type: `number` (incorrect)
   - Stored in database as: `led|enabled|true|number`

2. **Type confusion during operations:**
   - The incorrect type could cause conversion issues in downstream code
   - Value gets corrupted or reset to default during migrations/normalizations

3. **Service behavior:**
   - LED controller reads the corrupted setting
   - Falls back to disabled mode when type validation fails
   - LEDs run in simulation instead of controlling hardware

## The Fix

**Fixed Code (lines 743-755):**
```python
def _get_data_type(self, value: Any) -> str:
    """Get the data type string for a value."""
    # CRITICAL: Check bool BEFORE int/float because bool is a subclass of int in Python
    # This prevents booleans from being stored with data_type='number'
    if isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, str):
        return 'string'
    elif isinstance(value, (int, float)):
        return 'number'
    elif isinstance(value, list):
        return 'array'
    else:
        return 'object'
```

**Key Change:** Move `isinstance(value, bool)` check BEFORE `isinstance(value, (int, float))`

## Database Cleanup

Two settings were affected with incorrect data_types:
1. `led|enabled` - was stored as 'number', now 'boolean'
2. `calibration|allow_led_sharing` - was stored as 'number', now 'boolean'

Applied fix:
```sql
UPDATE settings SET data_type='boolean' 
WHERE data_type='number' AND (value='true' OR value='false')
```

## Verification

✅ Fixed code committed: `9d46b52`  
✅ LEDs remain enabled across service restarts  
✅ LED test endpoint responding correctly  
✅ LED enabled setting persists as `true|boolean`  
✅ Phase 1 calibration endpoints operational  

## Lessons Learned

1. **Type check order matters** - In Python, check subclasses before superclasses
2. **Boolean is tricky** - `bool` is a subclass of `int`, not just a related type
3. **Database validation** - Data types should match schema expectations
4. **Type coercion risks** - Wrong types can cause silent failures during conversion

## Prevention

- Added explicit comment in code explaining the bool/int relationship
- Consider adding unit tests for `_get_data_type()` to catch this regression
- Add schema validation on database writes to catch type mismatches early
