# LED Controller Singleton Pattern - Visual Explanation

## The Singleton Pattern Issue

### What is a Singleton?
A singleton is a class that can only have ONE instance. Once created, subsequent calls return that same instance.

```python
class LEDController:
    _instance = None  # ← Only one instance allowed
    _initialized = False  # ← Initialization guard
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if LEDController._initialized:
            return  # ← PROBLEM: Won't initialize again
        
        # initialization code...
        LEDController._initialized = True
```

## The Problem: Visual Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ CURRENT BEHAVIOR (BROKEN)                                           │
└─────────────────────────────────────────────────────────────────────┘

TIME: 0:00 - Service Starts (First Time)
├─ LEDController.__init__() called
├─ _initialized = False ✅
├─ Reads settings.db version 1
│  ├─ LED count: 255
│  ├─ Pin: 18
│  └─ Brightness: 0.5
├─ Initializes hardware ✅
├─ _initialized = True (LOCKS)
└─ Service running ✅

TIME: 0:05 - You Edit settings.db (Push New Version 2)
├─ New file:
│  ├─ LED count: 255 (same)
│  ├─ Pin: 18 (same)
│  └─ Brightness: 0.8 (CHANGED)
└─ settings.db updated ✅

TIME: 0:10 - Service Restarts
├─ start_wrapper.sh runs
├─ Flask app.py loads
├─ LEDController.__init__() called
├─ _initialized = True (still True!) ❌
├─ function RETURNS without reading settings.db ❌
├─ Hardware still using OLD brightness (0.5) ❌
└─ Service running but with STALE CONFIG ❌

RESULT: New brightness setting (0.8) is IGNORED

┌─────────────────────────────────────────────────────────────────────┐
│ THE FIX: Reset Singleton Before Initialization                      │
└─────────────────────────────────────────────────────────────────────┘

TIME: 0:00 - Service Starts (First Time)
├─ reset_singleton() called ← NEW!
├─ _initialized = False ✅
├─ LEDController.__init__() called
├─ Reads settings.db version 1 ✅
├─ Initializes hardware ✅
├─ _initialized = True
└─ Service running ✅

TIME: 0:05 - You Edit settings.db (Push New Version 2)
├─ New file with brightness: 0.8 ✅
└─ settings.db updated ✅

TIME: 0:10 - Service Restarts
├─ reset_singleton() called ← KEY FIX!
├─ _initialized = False (CLEARED!) ✅
├─ LEDController.__init__() called
├─ Reads settings.db version 2 ✅
├─ Brightness: 0.8 ✅
├─ Initializes hardware with NEW config ✅
├─ _initialized = True
└─ Service running with FRESH CONFIG ✅

RESULT: New brightness setting (0.8) is APPLIED ✓
```

## Code Comparison

### BEFORE (Broken)
```python
# backend/app.py (line ~89)

try:
    led_controller = LEDController(settings_service=settings_service)
    # ↑ If _initialized=True, this returns immediately without re-reading settings
```

### AFTER (Fixed)
```python
# backend/app.py (line ~90-105)

# CRITICAL FIX: Reset LEDController singleton to ensure fresh initialization
try:
    LEDController.reset_singleton()  # ← CLEARS THE LOCK!
    logger.info("LED Controller singleton reset - will initialize with current settings.db")
except Exception as e:
    logger.warning(f"Failed to reset LED controller singleton: {e}")

try:
    led_controller = LEDController(settings_service=settings_service)
    # ↑ Now _initialized=False, so __init__ fully executes and reads fresh settings
```

## What reset_singleton() Does

```python
@classmethod
def reset_singleton(cls) -> None:
    """Reset the singleton instance. Clears the initialization lock."""
    if cls._instance is not None:
        try:
            cls._instance._cleanup_strip()  # Clean up old hardware
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    cls._instance = None
    cls._initialized = False  # ← THE KEY LINE: Clear the lock
    logger.info("LEDController singleton has been reset")
```

So it:
1. Cleans up the old LED strip if one exists
2. Sets `_instance = None` (allows new instance creation)
3. Sets `_initialized = False` (allows __init__ to fully run)

## Why This Matters

| Before Fix | After Fix |
|-----------|-----------|
| Push settings.db | Push settings.db |
| Restart service | Restart service |
| `_initialized = True` ❌ | `reset_singleton()` ✅ |
| Skips init | Full init happens |
| Uses OLD config ❌ | Reads NEW config ✅ |
| LEDs don't work | LEDs work ✅ |

## The Startup Sequence (After Fix)

```
start_wrapper.sh
  ↓
Kills old processes
  ↓
Clears Python cache
  ↓
Runs: python3 app.py
  ↓
Flask app initializes
  ↓
reset_singleton() called ← Clears lock
  ↓
LEDController.__init__() → Reads settings.db ← Fresh read!
  ↓
_initialized = True ← Lock applies
  ↓
Service Ready ✅
```

## Real Example: You Push settings.db with Different Values

### Push Version 2 of settings.db
```json
{
  "led": {
    "enabled": true,
    "led_count": 255,
    "brightness": 0.8,  ← CHANGED from 0.5
    "led_orientation": "normal"  ← NEW
  }
}
```

### Before Fix
```
Service restarts
  ↓
LEDController.__init__() checks: _initialized = True
  ↓
RETURNS EARLY - NO INITIALIZATION
  ↓
Uses old values:
  - brightness: 0.5 ❌
  - led_orientation: normal ✅ (by luck)
  ↓
Result: Brightness doesn't change
```

### After Fix
```
Service restarts
  ↓
reset_singleton() sets _initialized = False ✅
  ↓
LEDController.__init__() runs FULLY
  ↓
Reads settings.db version 2
  ↓
Uses new values:
  - brightness: 0.8 ✅
  - led_orientation: normal ✅
  ↓
Result: Brightness changes as expected ✅
```

## Why Singleton Pattern Was Used

Good reasons:
- ✅ Prevents multiple LED strip instances (hardware conflict)
- ✅ Ensures single point of control
- ✅ Prevents resource leaks

The problem:
- ❌ The `_initialized` lock was too aggressive
- ❌ Didn't account for service restarts with config changes
- ❌ No way to force reinitialization

The fix:
- ✅ Reset the lock on every service startup
- ✅ Allows singleton pattern to continue (only one instance)
- ✅ Forces fresh configuration read on each restart
- ✅ No breaking changes to existing code

## Summary

**The Issue**: `_initialized = True` after first startup, prevents re-reading config

**The Fix**: Call `reset_singleton()` at startup to clear `_initialized = False`

**The Result**: Service restart with new settings.db now works correctly ✅

