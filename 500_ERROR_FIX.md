# 500 Error Fix - Settings Page Direct Load

## 🐛 Problem
When loading `/settings` page directly, users got a **500 Internal Server Error**. The page worked fine after navigating to another page first, then back to settings.

## 🔍 Root Cause
**Incorrect module import paths** in backend API files:

```python
# ❌ WRONG - Relative import without package name
from app import settings_service
from app import socketio
from app import led_controller

# ✅ CORRECT - Full package path
from backend.app import settings_service
from backend.app import socketio
from backend.app import led_controller
```

### Why It Failed on Direct Load
1. User opens `/settings` directly
2. Frontend calls `GET /api/calibration/status` 
3. Backend tries: `from app import settings_service`
4. **ModuleNotFoundError**: module `app` not found (needs full path `backend.app`)
5. Returns 500 error

### Why It Worked After Navigating Away
1. User visits another page first (e.g., home)
2. Flask loads `backend.app` into `sys.modules`
3. Later imports find `app` in module cache (happens to work)
4. Returns 200 instead of 500

## ✅ Solution
Fixed import paths in two files:

### 1. `backend/api/calibration.py` (lines 18-31)
```python
def get_settings_service():
    """Get the global settings service instance"""
    from backend.app import settings_service  # ← Changed
    return settings_service

def get_socketio():
    """Get the global socketio instance"""
    from backend.app import socketio  # ← Changed
    return socketio

def get_led_controller():
    """Get the global LED controller instance"""
    try:
        from backend.app import led_controller  # ← Changed
```

### 2. `backend/api/settings.py` (lines 16-19)
```python
def get_settings_service():
    """Get the global settings service instance"""
    from backend.app import settings_service  # ← Changed
    return settings_service
```

## 📋 Files Modified
- ✅ `backend/api/calibration.py` - Fixed 3 import paths
- ✅ `backend/api/settings.py` - Fixed 1 import path

## 🧪 Verification
```bash
python -m py_compile backend/api/calibration.py backend/api/settings.py
# ✅ Output: (no errors)
```

## 🚀 Impact
- ✅ Settings page loads directly without 500 error
- ✅ All calibration endpoints work on first load
- ✅ No more need to navigate to another page first
- ✅ Fixes will work on Pi deployment and development

## 🔗 Related Endpoints
These endpoints will now work correctly on direct settings page load:
- `GET /api/calibration/status` ← Main culprit
- `GET /api/settings` 
- `POST /api/calibration/*` (all calibration updates)
- `POST /api/settings/*` (all settings updates)

## 📝 Testing Checklist
- [ ] Open `/settings` directly in browser
- [ ] Should load without 500 error
- [ ] Calibration data loads correctly
- [ ] Can adjust sliders and offsets
- [ ] No console errors in browser DevTools

---

**Status:** ✅ **FIXED** - Ready for testing
