# Delete Adjustment - Full Cleanup Fix

**Date:** October 19, 2025  
**Issue:** Deleting adjustments didn't restore original mapping  
**Root Cause:** Deleting offsets but leaving trims behind  
**Status:** ✅ FIXED

## The Problem

When a user deleted an adjustment (offset + trim):
1. Backend deleted the offset ✓
2. Backend left the trim in place ✗
3. LED mapping still applied the remaining trim
4. Display showed trimmed allocation instead of base allocation

### Example
```
Original base mapping for key 50: [49, 50, 51]

User creates adjustment:
  offset: +0
  trim: L1/R0
  result: [50, 51]

User deletes adjustment:
  Backend deletes offset ✓
  Backend leaves trim L1/R0 ✗
  Mapping still applies trim
  Result: [50, 51] (trim still active)
  Expected: [49, 50, 51] (restored)
```

## The Fix

**File:** `backend/api/calibration.py`  
**Function:** `delete_key_offset()`  
**Change:** Also delete the corresponding trim when deleting an offset

### Before
```python
def delete_key_offset(midi_note):
    key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
    
    if str(midi_note) in key_offsets:
        del key_offsets[str(midi_note)]  # ← Only deleted offset
        settings_service.set_setting('calibration', 'key_offsets', key_offsets)
```

### After
```python
def delete_key_offset(midi_note):
    key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
    key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})
    
    if str(midi_note) in key_offsets:
        del key_offsets[str(midi_note)]
        settings_service.set_setting('calibration', 'key_offsets', key_offsets)
    
    # ✅ NEW: Also clean up trims
    if str(midi_note) in key_led_trims:
        del key_led_trims[str(midi_note)]
        settings_service.set_setting('calibration', 'key_led_trims', key_led_trims)
```

## Impact

### Before Fix
```
Delete adjustment for key 50
  ↓
Offset removed: key_offsets = {}
  ↓
Trim remains: key_led_trims['50'] = {L: 1, R: 0}
  ↓
Backend mapping applies trim
  ↓
Display shows [50, 51] (WRONG) ❌
```

### After Fix
```
Delete adjustment for key 50
  ↓
Offset removed: key_offsets = {}
  ↓
Trim removed: key_led_trims = {}
  ↓
Backend mapping applies nothing
  ↓
Display shows [49, 50, 51] (CORRECT) ✅
```

## User Experience

### Before
```
1. Adjust key 50: offset +0, trim L1/R0
2. Display: "Adjusted LEDs: 50 - 51" ✓
3. Click Delete
4. Display: "Adjusted LEDs: 50 - 51" ✗ (Should be 49-51!)
5. Mismatch between UI and backend
```

### After
```
1. Adjust key 50: offset +0, trim L1/R0
2. Display: "Adjusted LEDs: 50 - 51" ✓
3. Click Delete
4. Display: "Adjusted LEDs: 49 - 51" ✓ (Correctly restored!)
5. Perfect consistency
```

## Testing

### Test Case 1: Delete offset only (no trim)
```
1. Save: key 50, offset +2, trim L0/R0
2. Verify mapping shows offset applied
3. Delete
4. Verify mapping restored to base
5. Expected: ✓ Works correctly
```

### Test Case 2: Delete offset + trim
```
1. Save: key 50, offset 0, trim L1/R1
2. Verify mapping shows trim applied
3. Delete
4. Verify mapping restored to base (no trim)
5. Expected: ✓ Now works with fix!
```

### Test Case 3: Delete complex adjustment
```
1. Save: key 50, offset +2, trim L1/R0
2. Verify mapping: [base + 2, then trim]
3. Delete
4. Verify mapping restored to base (no offset, no trim)
5. Expected: ✓ Completely clean
```

## Code Changes Summary

| Item | Details |
|------|---------|
| File | backend/api/calibration.py |
| Function | delete_key_offset() |
| Lines Changed | ~528-575 |
| Changes | Fetch key_led_trims, delete trim entry, update setting |
| Logging | Added message when trim deleted |

## Related Functionality

### Delete Flow (Complete)
```
Frontend: Click Delete
  ↓
API: DELETE /api/calibration/key-offset/<midi_note>
  ↓
Backend: delete_key_offset()
  ├─ Delete offset from key_offsets
  ├─ Delete trim from key_led_trims (✅ NOW DONE)
  └─ Update last_calibration timestamp
  ↓
Frontend: loadStatus()
  ├─ Updates key_offsets
  └─ Updates key_led_trims
  ↓
Frontend: updateLedMapping()
  └─ Fetches /key-led-mapping (applies no offset/trim)
  ↓
Display: Shows base allocation
```

### Add Flow (For Comparison)
```
Frontend: Save adjustment
  ↓
API: PUT /api/calibration/key-offset/<midi_note>
  ├─ Save offset
  └─ Save trim
  ↓
Backend: apply_calibration_offsets_to_mapping()
  ├─ Apply offset
  └─ Apply trim
  ↓
Display: Shows adjusted allocation
```

## Database State

### Before Delete
```
key_offsets = {'50': 0}
key_led_trims = {'50': {'left_trim': 1, 'right_trim': 0}}
```

### After Delete (Before Fix)
```
key_offsets = {}          ✓ Cleaned
key_led_trims = {'50': {'left_trim': 1, 'right_trim': 0}}  ✗ Still there!
```

### After Delete (After Fix)
```
key_offsets = {}          ✓ Cleaned
key_led_trims = {}        ✓ Cleaned
```

## Verification

Check backend logs after deletion:
```
Key offset for MIDI note 50 deleted
Key LED trim for MIDI note 50 deleted
```

Check frontend display:
- Adjustment removed from list ✓
- Adjusted LED range reverts to base ✓
- Trim badge disappears ✓

---

**Fix Complete!** 🎉

Now deleting an adjustment fully cleans up both offset and trim data, allowing the mapping to properly restore to the original base allocation.
