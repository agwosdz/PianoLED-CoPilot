# Right Trim Fix - Key Index Conversion

## The Issue

Right trim (and potentially all trims) weren't working because of a **key index mismatch**:

### The Bug

In `backend/api/calibration.py` line 878, we were storing trims with the wrong key:

```python
# BEFORE (WRONG):
converted_trims[midi_note] = trim_value  # ← Storing by MIDI note

# AFTER (FIXED):
converted_trims[key_index] = trim_value  # ← Now storing by key index
```

### Why This Matters

1. The base LED mapping dict uses **KEY INDICES** (0-87) as keys
   - Physics allocation returns indices, not MIDI notes

2. The `apply_calibration_offsets_to_mapping()` function loops over mapping keys:
   ```python
   for midi_note, led_indices in mapping.items():  # midi_note is actually a key_index!
       if midi_note_int in normalized_key_led_trims:  # Lookup fails if keys don't match!
   ```

3. Key offsets were ALREADY being converted to indices:
   ```python
   converted_offsets = {}
   for midi_note_str, offset_value in key_offsets.items():
       key_index = midi_note_int - 21
       converted_offsets[key_index] = offset_value  # ← Correct
   ```

4. **Trims needed the same treatment:**
   ```python
   converted_trims = {}
   for midi_note_str, trim_value in key_led_trims.items():
       key_index = midi_note - 21
       converted_trims[key_index] = trim_value  # ← NOW FIXED
   ```

### The Fix

Changed one line in `backend/api/calibration.py` (line 878):

```diff
- converted_trims[midi_note] = trim_value
+ converted_trims[key_index] = trim_value
```

This ensures both offsets and trims use the same key format (key indices) when passed to `apply_calibration_offsets_to_mapping()`.

## Key Index Conversion Reference

| MIDI Note | Key Index |
|-----------|-----------|
| 21 (A1) | 0 |
| 22 (A#1) | 1 |
| 60 (Middle C) | 39 |
| 88 (E6) | 67 |
| 108 (C8) | 87 |

**Formula:** `key_index = midi_note - 21`

## Data Flow After Fix

```
Frontend sends MIDI 50 with trim L1/R0
  ↓
Backend stores in DB: key_led_trims['50'] = {left_trim: 1, right_trim: 0}
  ↓
get_key_led_mapping() fetches it:
  key_led_trims = {'50': {left_trim: 1, right_trim: 0}}
  ↓
Converts to indices:
  converted_trims = {29: {left_trim: 1, right_trim: 0}}  # MIDI 50 → index 29
  ↓
Passes to apply_calibration_offsets_to_mapping():
  key_led_trims={29: {...}}
  ↓
Loop: for midi_note (actually index), led_indices in mapping.items():
      if 29 in normalized_key_led_trims:  # ← NOW MATCHES!
          Apply trim ✅
```

## Why Only Right Trim Failed (Hypothesis)

This is unclear, but possible reasons:
1. **Intermittent failure:** If key indices happened to match MIDI notes (e.g., index 50 = MIDI note 71), trim might work sometimes
2. **Cascading offsets:** Left trim might have hidden the problem by luck
3. **Specific key range:** Maybe only certain keys failed

The root cause was the key mismatch preventing the trim from being found at all.

## Testing the Fix

```bash
# 1. Save adjustment with right trim only
POST /api/calibration/key-offset/50
{
  "offset": 0,
  "left_trim": 0,
  "right_trim": 1
}

# 2. Get mapping
GET /api/calibration/key-led-mapping

# 3. Verify right trim was applied
# Key 50 should have fewer LEDs than original allocation

# 4. Check logs for:
# "Converted trim: MIDI 50 → index 29"
# "Applied trim L0/R1"
```

## Code Changes

**File:** `backend/api/calibration.py`  
**Function:** `get_key_led_mapping()`  
**Line:** 878  
**Change:** Use `key_index` instead of `midi_note` when storing trim

## Related Fixes

This fix ensures consistency with how offsets are handled - both now use key indices internally.

---

**Status:** ✅ FIXED

Test the fix by saving adjustments with:
- Right trim only
- Left trim only
- Both trims
- Compare with previous results

Expected behavior: All trims should now work correctly and consistently apply to the backend mapping.
