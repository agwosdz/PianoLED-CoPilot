# LED 4 Offset Bug Fix

## Problem

The LED mapping was skipping LED 4, the first LED in the calibration range:
- `start_led: 4` (configuration)
- `Key 0 → LEDs [5, 6, 7]` (actual mapping - LED 4 missing!)

This meant LED 4 was never lit, even though it was in the usable range.

## Root Cause

In `backend/config_led_mapping_advanced.py` lines 159-161, the code was calculating LED midpoints incorrectly:

```python
# BEFORE (❌ WRONG):
led_midpoint_led_pos = led_offset  # 0-based offset from start_led
led_midpoint_mm = led_midpoint_led_pos * led_spacing_mm * scale_factor
```

The problem: `led_offset` is relative to `start_led` (0-based), but the physical position calculation needs the **absolute LED index**.

**Example:**
- When LED 4 is being processed:
  - `led_offset = 0` (because 4 - 4 = 0)
  - `led_midpoint_led_pos = 0` (using led_offset)
  - `led_midpoint_mm = 0 * 5mm * scale = 0mm` ❌ Wrong! LED 4 is at 20mm physically
  - Key position ranges don't include 0mm, so LED 4 never gets assigned

## Solution

Use the **absolute LED index** instead of relative offset:

```python
# AFTER (✅ CORRECT):
led_midpoint_led_pos = led_idx  # Absolute LED position (4, 5, 6, etc.)
led_midpoint_mm = led_midpoint_led_pos * led_spacing_mm
```

This ensures:
- LED 4: `led_midpoint_mm = 4 * 5mm = 20mm` ✅
- LED 5: `led_midpoint_mm = 5 * 5mm = 25mm` ✅
- LED 249: `led_midpoint_mm = 249 * 5mm = 1245mm` ✅

All LEDs now map to physical positions correctly.

## Results After Fix

**Before:**
```
start_led: 4
Key 0 → LEDs [5, 6, 7]  ❌ Skips LED 4
Key 1 → LEDs [8, 9, 10]
...
```

**After:**
```
start_led: 4
Key 0 → LEDs [4, 5, 6, 7, 8]   ✅ Includes LED 4
Key 1 → LEDs [6, 7, 8, 9, 10]
Key 2 → LEDs [9, 10, 11, 12, 13]
...
Key 87 → LEDs [246, 247, 248, 249] ✅ Ends at LED 249

✅ All 246 LEDs (4-249) now used
✅ No LEDs skipped
✅ Clean partitioning for no-overlap mode
```

## Terminology Clarification

To avoid this confusion in the future:

| Term | Meaning | Range | Example |
|------|---------|-------|---------|
| **LED Number** | Physical LED ID | 0-254 | "LED 47" |
| **Calibration Range** | Usable LEDs | start_led to end_led | [4, 249] |
| **Key Index** | Piano key (0-based) | 0-87 | "Key 0" = A0 |
| **MIDI Note** | Musical note number | 21-108 | "MIDI 42" = F#2 |
| **LED Index** | Absolute position in strip | 0-254 | Use for calculations |
| **LED Offset** | Relative to start_led | 0-245 | Used in loops |

**Key Rule:** Always use **absolute LED indices** for physical calculations!

## Code Changes

**File:** `backend/config_led_mapping_advanced.py`

**Lines 159-161:**
```python
# OLD:
led_midpoint_led_pos = led_offset
led_midpoint_mm = led_midpoint_led_pos * led_spacing_mm * scale_factor

# NEW:
led_midpoint_led_pos = led_idx  # Use absolute LED index
led_midpoint_mm = led_midpoint_led_pos * led_spacing_mm
```

## Verification

✅ Tested on Raspberry Pi Zero 2 W
✅ All 246 LEDs (4-249) now assigned
✅ No LEDs skipped
✅ No overlapping assignments (in no-overlap mode)
✅ Correct LED starts at first key

## Impact

**Affected Features:**
- LED to key calibration mapping
- Visual display of which keys light which LEDs
- Proper use of the full LED range

**No Breaking Changes:**
- API response format unchanged
- Frontend continues to work correctly
- Settings format unchanged
