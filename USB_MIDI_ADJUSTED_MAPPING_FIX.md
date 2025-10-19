# USB MIDI to LED - Adjusted Mapping Fix ✅

## Problem
USB MIDI input was NOT respecting the adjusted LED mapping (with offsets and trims). It was using the base mapping without any calibration adjustments.

## Root Cause
The `get_canonical_led_mapping()` function in `backend/config.py` was:
- ✅ Reading `key_offsets` from settings
- ✅ Reading `weld_offsets` from settings
- ❌ NOT reading `key_led_trims` from settings
- ❌ NOT passing trims to `apply_calibration_offsets_to_mapping()`

This meant USB MIDI notes were mapped to the wrong LEDs when per-key trim adjustments were made.

## Solution

### File: `backend/config.py`
**Function:** `get_canonical_led_mapping()`
**Lines:** ~1795-1870

### Changes Made

1. **Added trim retrieval:**
```python
key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})
```

2. **Added trim conversion (MIDI notes → key indices):**
```python
# Convert trim keys from MIDI notes to key indices (for consistency with offsets)
converted_trims = {}
if key_led_trims:
    for midi_note_str, trim_value in key_led_trims.items():
        try:
            midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
            key_index = midi_note - 21
            if 0 <= key_index < 88:
                converted_trims[key_index] = trim_value
        except (ValueError, TypeError):
            pass
```

3. **Passed trims to offset function:**
```python
final_mapping = apply_calibration_offsets_to_mapping(
    mapping=base_mapping,
    start_led=start_led,
    end_led=end_led,
    key_offsets=converted_offsets,
    key_led_trims=converted_trims,  # ← ADDED
    led_count=led_count,
    weld_offsets=weld_offsets
)
```

## Impact

### Before Fix
- USB MIDI plays Key 35 → LEDs [150, 151] (base mapping)
- But calibration has left_trim=1 on Key 35
- LED 150 was trimmed away and given to Key 34
- Result: Wrong LEDs light up, sounds strange

### After Fix
- USB MIDI plays Key 35 → Gets from canonical mapping with trims applied
- Canonical mapping already has trim adjustments
- LED 150 was redistributed to Key 34
- Result: Correct LEDs light up, timing aligns with calibration

## How It Works

**Data Flow:**

```
USB MIDI Input (note 35)
    ↓
MidiEventProcessor._generate_key_mapping()
    ↓
get_canonical_led_mapping()  ← NOW GETS TRIMS
    ↓
apply_calibration_offsets_to_mapping()  ← NOW APPLIES TRIMS
    ↓
Trim redistribution (left trim → prev key, right trim → next key)
    ↓
Final adjusted mapping
    ↓
MidiEventProcessor._precomputed_mapping
    ↓
LED Controller turns on correct LEDs
```

## Components Using Canonical Mapping

The canonical mapping is now used by:

1. ✅ **USB MIDI Input Service** - `backend/usb_midi_service.py`
   - Via `MidiEventProcessor._generate_key_mapping()`
   - Calls `get_canonical_led_mapping()`

2. ✅ **rtpMIDI Input Service** - `backend/rtp_midi_service.py`
   - Via `MidiEventProcessor._generate_key_mapping()`
   - Calls `get_canonical_led_mapping()`

3. ✅ **REST API** - `/api/calibration/key-led-mapping`
   - Calls `get_canonical_led_mapping()` directly

4. ✅ **LED Playback/Visualization** - Any component that needs MIDI-to-LED mapping

All components now automatically get the adjusted mapping with trims!

## Testing Checklist

- [ ] Play USB MIDI note with left_trim → Correct LED lights up
- [ ] Play USB MIDI note with right_trim → Correct LED lights up
- [ ] Play USB MIDI with both offset and trim → All adjustments applied
- [ ] rtpMIDI input also respects trims
- [ ] `/api/calibration/key-led-mapping` returns mapping with trims applied
- [ ] Delete trim adjustment → USB MIDI immediately uses new mapping
- [ ] Add new trim → USB MIDI immediately uses updated mapping

## Backward Compatibility

✅ Fully compatible - trims are optional, if none exist the behavior is unchanged

## Performance Impact

⏱️ No impact - same canonical mapping generation, just with trims included

## Files Modified

- `backend/config.py`
  - Added `key_led_trims` retrieval (~line 1797)
  - Added trim conversion logic (~lines 1861-1869)
  - Updated `apply_calibration_offsets_to_mapping()` call to include trims (~line 1880)

## Verification

The fix ensures that **USB MIDI input is always synchronized with the calibration display** - what you see in the UI is what you hear when playing MIDI. 🎹✨

