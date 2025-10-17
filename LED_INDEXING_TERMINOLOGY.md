# LED Indexing Terminology & Issues

## Clear Terminology Definitions

### 1. **LED NUMBER** (Physical LED on the strip)
- Range: 0 to 254 (for 255 total LEDs)
- What you see on the physical strip
- Example: "The red LED is #47"

### 2. **CALIBRATION RANGE** (start_led to end_led)
- `start_led`: First LED in the usable range (default: 4)
- `end_led`: Last LED in the usable range (default: 249)
- Total usable LEDs: 249 - 4 + 1 = 246 LEDs
- **Why not 0?** LEDs 0-3 might be used for other purposes or damaged

### 3. **KEY INDEX** (Piano key identifier)
- Range: 0 to 87 (for 88-key piano)
- Key 0 = A0 (MIDI note 21)
- Key 87 = C8 (MIDI note 108)
- NOT the same as LED number!

### 4. **MIDI NOTE** (Musical note number)
- Range: 21 to 108 (for 88-key piano)
- Conversion: `MIDI_note = 21 + key_index`
- Example: Key 0 → MIDI 21, Key 21 → MIDI 42

## Current Bug: LED 4 is Skipped

**Issue:** Key 0 is mapped to LEDs [5, 6, 7] instead of [4, 5, 6]

**Data:**
```
API Response: start_led = 4
API Response: Key 0 → LEDs [5, 6, 7]

PROBLEM: LED 4 is never assigned to any key!
```

**Root Cause:** In `config_led_mapping_advanced.py` line 159:

```python
led_midpoint_led_pos = led_offset  # ❌ WRONG: led_offset is 0-based
```

When calculating the physical position of an LED for coordinate matching, `led_offset` is being used directly. But `led_offset` ranges from 0 to (end_led - start_led), which is NOT the absolute LED position.

**Example:**
- When `led_offset = 0`, it calculates as if it's at position 0mm
- But it actually represents LED 4, which should be at position 4×5mm = 20mm
- This shifts the entire mapping too far right, skipping LED 4

## The Fix

Change line 159 in `config_led_mapping_advanced.py`:

```python
# BEFORE (❌ WRONG):
led_midpoint_led_pos = led_offset

# AFTER (✅ CORRECT):
led_midpoint_led_pos = led_idx - start_led
```

This ensures the position calculation is relative to the start of the LED range (start_led).

## Why This Matters

**For 88-key piano with 246 usable LEDs:**
- Each key gets ~2.8 LEDs on average
- Every LED counts!
- Skipping LED 4 means:
  - LED 4 never lights up
  - Key 0 (A0) gets fewer LEDs
  - Visual representation is off

## After Fix Verification

Expected after fix:
```
start_led: 4
Key 0 → LEDs [4, 5, 6]   ✅ Starts at LED 4
Key 1 → LEDs [7, 8, 9]   ✅ Continues correctly
Key 2 → LEDs [10, 11]    ✅ Clean partitioning
...
Key 87 → LEDs [248, 249] ✅ Ends at end_led
```

All 246 usable LEDs (4-249) should be assigned to exactly one key.

## Terminology in Code

**To avoid confusion, we should use clear variable names:**

```python
# Instead of ambiguous names:
led_idx          # Use: absolute_led_index (0-254)
start_led        # Use: calibration_start_led (4)
end_led          # Use: calibration_end_led (249)
led_offset       # Use: offset_from_start (0-245)

# For musical values:
key_idx          # Use: piano_key_index (0-87)
midi_note        # Use: midi_note (21-108)
```

## Impact on Frontend Display

The frontend `calibration.ts` uses:
```typescript
const midiNote = 21 + keyIndex;  // Correct conversion
mapping[midiNote] = value;        // Map by MIDI note
```

So if the backend returns:
```json
{"0": [4,5,6], "1": [7,8,9]}  // Key indices
```

The frontend converts to MIDI notes:
```json
{21: [4,5,6], 22: [7,8,9]}  // MIDI notes
```

This is correct! The frontend is doing its job. The bug is in the backend mapping generation.
