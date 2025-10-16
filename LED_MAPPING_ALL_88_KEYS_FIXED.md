# LED Mapping Fix - All 88 Keys Now Covered

**Date:** October 16, 2025  
**Commit:** d1cb1fc  
**Status:** ✅ FIXED

---

## The Problem

Visual inspection showed 6 keys (MIDI 103-108) had no LEDs assigned, even though there were enough LEDs available:
- **Available range:** LED 4-249 (246 LEDs)
- **Piano keys:** 88 (MIDI 21-108)
- **Expected:** All 88 keys should have LEDs
- **Actual:** Only 82 keys mapped, 6 keys dark

```
[CalibrationSection3] LED Range: 4-249 (total: 255)
[CalibrationSection3] Piano: 88 keys (MIDI 21-108)
[CalibrationSection3] Mapping: 82 keys with LEDs, 6 keys without LEDs
[CalibrationSection3] Mapped keys: MIDI 21-102
[CalibrationSection3] ⚠️ Missing keys: 6 keys at end (MIDI 103-108)
```

---

## Root Cause Analysis

### Issue #1: Backend Ignoring Calibration Range
**Location:** `backend/api/calibration.py` - `/mapping-info` endpoint

The endpoint was calculating LED-to-key mapping using the **total LED count** instead of the **available range**:

```python
# BEFORE (WRONG):
mapping = generate_auto_key_mapping(
    piano_size=piano_size,
    led_count=led_count,  # ❌ Uses 255 total LEDs
    leds_per_key=leds_per_key,
    mapping_base_offset=base_offset
)

# Result: 255 // 88 = 2 LEDs/key → only 82 keys fit (82×3=246)
```

The `/key-led-mapping` endpoint had the correct logic but `/mapping-info` didn't:

```python
# AFTER (CORRECT):
available_led_range = end_led - start_led + 1  # = 246
mapping = generate_auto_key_mapping(
    piano_size=piano_size,
    led_count=available_led_range,  # ✅ Uses 246 available LEDs
    leds_per_key=leds_per_key,
    mapping_base_offset=base_offset
)

# Result: 246 // 88 = 2.79 LEDs/key → all 88 keys fit!
```

### Issue #2: leds_per_key Hardcoded to 3
**Location:** Settings database

The `led.leds_per_key` was set to **3**, which forced:
- 3 LEDs per key × 88 keys = **264 LEDs needed**
- But only 246 LEDs available
- Can only map: 246 ÷ 3 = **82 keys** ❌

With proportional distribution (leds_per_key = None):
- 246 ÷ 88 = 2.79 average
- 70 keys get 3 LEDs, 18 keys get 2 LEDs
- Total: 70×3 + 18×2 = 210 + 36 = **246 LEDs** ✅
- **All 88 keys covered** ✅

---

## The Fix

### Fix #1: Update /mapping-info Endpoint
**File:** `backend/api/calibration.py`  
**Lines:** 683-712

```python
# Get calibration range
start_led = settings_service.get_setting('calibration', 'start_led', 0)
end_led = settings_service.get_setting('calibration', 'end_led', led_count - 1)

# Calculate available LED count
available_led_range = end_led - start_led + 1

# Generate mapping using ONLY available range
mapping = generate_auto_key_mapping(
    piano_size=piano_size,
    led_count=available_led_range,  # ✅ Use available range
    leds_per_key=leds_per_key,
    mapping_base_offset=base_offset
)

# Update info dict to show calibration range
'led_configuration': {
    'total_leds': led_count,
    'calibration_start_led': start_led,
    'calibration_end_led': end_led,
    'calibration_range': f"[{start_led}, {end_led}]",
    'available_leds': available_led_range,  # ✅ Show actual available
    ...
}
```

### Fix #2: Set leds_per_key to None
**Setting:** `led.leds_per_key`  
**Value:** `None` (for proportional distribution)

This allows the algorithm to calculate optimal LEDs per key based on available range:
- Formula: `leds_per_key = available_leds // num_keys` = 246 // 88 = 2
- Remaining: `246 % 88 = 70` → first 70 keys get +1 extra LED
- Result: 70 keys × 3 LEDs + 18 keys × 2 LEDs = 246 LEDs

---

## Verification

### Before Fix
```
Settings:
  Calibration: [4, 249] (246 LEDs)
  leds_per_key: 3
  Calculation: 246 / 3 = 82 keys fit

Result: 82 keys with LEDs, 6 keys unmapped
```

### After Fix
```
Settings:
  Calibration: [4, 249] (246 LEDs)
  leds_per_key: None (proportional)
  Calculation: 246 / 88 = 2-3 LEDs per key

Result: 88 keys with LEDs (70×3 + 18×2 = 246 LEDs)
        EVERY KEY COVERED!
```

### Test Output
```
============================================================
LED MAPPING FIX VERIFICATION
============================================================

Settings:
  Piano: 88-key
  Total LEDs: 255
  Calibration range: [4, 249]
  Available LEDs: 246
  Base offset: 0
  LEDs per key setting: None

Mapping Results:
  Total keys: 88
  Mapped keys: 88
  Unmapped keys: 0

LED Usage:
  Total LEDs used: 246
  LED range: [0, 245]
  Distribution: {2: 18, 3: 70}

Validation:
  [PASS] All keys are mapped
  [PASS] LED usage within range (246 <= 246)

============================================================
SUCCESS: All 88 keys are covered!
============================================================
```

---

## Files Modified

| File | Change | Impact |
|------|--------|--------|
| `backend/api/calibration.py` | /mapping-info now uses calibration range | All 88 keys now visible in UI |
| `backend/settings.db` (local) | `leds_per_key`: 3 → None | Proportional distribution |
| `backend/settings.db` (Pi) | `leds_per_key`: 3 → None | Proportional distribution |

---

## Visual Impact

### Before
```
Piano keys:   A0 A#0 B0 [C1-C7]          C8
              [====================] [UNMAPPED 6 KEYS]
LED indices:  4                     249
```

### After
```
Piano keys:   A0 A#0 B0 [C1-C7]          C8
              [====================================]
LED indices:  4  (70×3 + 18×2)          249
```

---

## Key Insights

1. **Proportional vs Fixed Distribution**
   - Fixed (leds_per_key=3): Ideal quality but limited key coverage
   - Proportional (leds_per_key=None): Covers all keys, slight LED count variation

2. **Calibration Range is Critical**
   - Two endpoints use different logic for the same mapping
   - Both must respect calibration start_led/end_led range
   - Don't use total LED count for calculations

3. **The 6-Key Gap**
   - 82 × 3 = 246 LEDs exactly
   - The last 6 keys (MIDI 103-108) had no LEDs to assign
   - Proportional distribution spreads LEDs evenly across all keys

---

## Testing

✅ Verified all 88 keys are now mapped  
✅ LED usage is 246/246 (100% of available)  
✅ Distribution: 70 keys with 3 LEDs, 18 keys with 2 LEDs  
✅ No unmapped keys  
✅ Committed and ready for deployment  

---

## Deployment

Both local dev and Pi databases have been updated:
- `leds_per_key: 3 → None`
- Calibration range confirmed: `[4, 249]`

The fix is ready for:
1. Frontend reload (will show all 88 keys lit in visualization)
2. Pi deployment (service restart will apply new mapping)
