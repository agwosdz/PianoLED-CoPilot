# Trim Data Cleanup on Zero Trim - Fix

**Date:** October 19, 2025  
**Issue:** MIDI 37 showing [50, 51] instead of original [49, 50, 51]  
**Root Cause:** Old trim data persisted when saving with 0/0 trim  
**Status:** ✅ FIXED

## The Problem

When a key had a previous trim saved and was later adjusted with NO trim (0/0), the old trim remained in the database and continued affecting the mapping.

### Example Scenario
```
Step 1: MIDI 37 original mapping
  [49, 50, 51]

Step 2: User saves with trim L1/R0
  Saved: key_led_trims['37'] = {left_trim: 1, right_trim: 0}
  Mapping now: [50, 51]

Step 3: User re-adjusts same key with NO trim (offset only)
  Sends: offset=0, left_trim=0, right_trim=0
  Backend: Doesn't save trim (condition: if left_trim > 0 or right_trim > 0)
  Result: key_led_trims['37'] still has {left_trim: 1, right_trim: 0} ✗
  Mapping: Still [50, 51] (should be [49, 50, 51]) ✗
```

## Root Cause

In `backend/api/calibration.py` line 491-494:

```python
# WRONG: Only saves trim if at least one is > 0
if left_trim > 0 or right_trim > 0:
    key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})
    key_led_trims[str(midi_note)] = {...}
    settings_service.set_setting('calibration', 'key_led_trims', key_led_trims)
# If both are 0, nothing happens and old trim remains!
```

## The Fix

Always update the trim entry, clearing it if both values are zero:

```python
# CORRECT: Always update trim, clearing if both are 0
key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})

if left_trim > 0 or right_trim > 0:
    # Save trim if any trim is non-zero
    key_led_trims[str(midi_note)] = {
        'left_trim': left_trim,
        'right_trim': right_trim
    }
else:
    # Clear trim if both are zero (no trim)
    if str(midi_note) in key_led_trims:
        del key_led_trims[str(midi_note)]

settings_service.set_setting('calibration', 'key_led_trims', key_led_trims)
```

## Data Flow

### Before Fix
```
Save with trim L0/R0
  ↓
Backend: if 0 > 0 or 0 > 0: FALSE
  ↓
Skip updating key_led_trims
  ↓
Old trim data remains in DB ✗
  ↓
Mapping still applies old trim ✗
```

### After Fix
```
Save with trim L0/R0
  ↓
Backend: Check both conditions
  ↓
Both are 0: Delete old trim entry ✓
  ↓
key_led_trims[midi_note] removed ✓
  ↓
Mapping applies NO trim ✓
```

## Usage Scenarios

### Scenario 1: Add trim, then remove it
```
1. Save: MIDI 37, offset=0, trim L1/R0
   → key_led_trims['37'] = {L: 1, R: 0}
   → Mapping: [50, 51]

2. Re-adjust same key with NO trim
   Send: offset=0, trim L0/R0
   → key_led_trims['37'] deleted (AFTER FIX) ✓
   → Mapping: [49, 50, 51]
```

### Scenario 2: Change trim values
```
1. Save with trim L1/R0
   → key_led_trims['37'] = {L: 1, R: 0}

2. Re-adjust with trim L0/R1
   → key_led_trims['37'] = {L: 0, R: 1}
   → Mapping updated correctly ✓
```

### Scenario 3: Add offset, then change to no offset
```
1. Save with offset +2, no trim
   → key_offsets['37'] = 2
   → Mapping: [base + 2]

2. Re-adjust with offset 0, no trim
   → key_offsets['37'] deleted (already worked)
   → key_led_trims['37'] deleted (NOW WORKS WITH FIX) ✓
   → Mapping: fully restored to base ✓
```

## Technical Details

### Trim Update Logic (After Fix)

```python
# Step 1: Fetch current trims
key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {}) or {}

# Step 2: Check if we need to save or clear
if left_trim > 0 or right_trim > 0:
    # At least one trim is active: SAVE
    key_led_trims[str(midi_note)] = {
        'left_trim': left_trim,
        'right_trim': right_trim
    }
else:
    # Both trims are 0: CLEAR
    if str(midi_note) in key_led_trims:
        del key_led_trims[str(midi_note)]

# Step 3: Persist to database
settings_service.set_setting('calibration', 'key_led_trims', key_led_trims)
```

## Database Impact

### Before Fix
```
MIDI 37 history:
  1. Save with L1/R0: key_led_trims['37'] = {L: 1, R: 0}
  2. Save with L0/R0: key_led_trims['37'] = {L: 1, R: 0} ← STUCK!
```

### After Fix
```
MIDI 37 history:
  1. Save with L1/R0: key_led_trims['37'] = {L: 1, R: 0}
  2. Save with L0/R0: key_led_trims['37'] = DELETED ✓
```

## Related Fixes

This fix complements the previous fixes:
1. ✅ Right trim conversion (key_index instead of midi_note)
2. ✅ Delete also removes trims
3. ✅ **NEW: Save with 0/0 trim clears old trim data**

## Testing

### Test Case 1: Verify Old Trim Removal
```
1. Set MIDI 37: offset=0, trim L1/R0
   → Display: "Adjusted: 50 - 51" (trimmed)
   → Logs: "Trim saved for MIDI 37"

2. Re-adjust MIDI 37: offset=0, trim L0/R0
   → Backend should log: "Trim cleared for MIDI 37"
   → Display: "Adjusted: 49 - 51" (restored)
```

### Test Case 2: Verify Trim Update Works
```
1. Set MIDI 37: trim L1/R0 → [50, 51]
2. Re-adjust: trim L0/R1 → [49, 50]
   → Trim value updated correctly ✓
```

### Test Case 3: Mixed Scenarios
```
1. MIDI 50: offset +2, trim L1/R1
   → Mapping: adjusted with offset and trim

2. Re-save MIDI 50: offset 0, trim L0/R0
   → Both offset and trim should be cleared
   → Mapping: fully restored to base
```

## Verification Commands

After fix, verify:
```bash
# Check database for MIDI 37
sqlite3 settings.db "SELECT value FROM settings WHERE key = 'key_led_trims'"

# Should NOT contain '37' after saving with L0/R0
# Example result: {"22": {"left_trim": 1, "right_trim": 0}}  # No '37'
```

## Code Changes

| File | Function | Line | Change |
|------|----------|------|--------|
| calibration.py | set_key_offset() | 492-504 | Always update trim entry, clear if both are 0 |

---

**Fix Deployed!** 🎉

Now when you save an adjustment with 0/0 trim (no trim), any previous trim data for that key will be properly cleared, allowing the mapping to restore to the original allocation.

**How to verify:** 
1. Save MIDI 37 with trim L1/R0 (shows 2 LEDs)
2. Re-save MIDI 37 with L0/R0 (should now show 3 LEDs)
