# LED Trim Redistribution Logic - Implementation Plan

## Problem
Current trim logic simply removes LEDs from a key:
- `left_trim=1` removes the first LED (doesn't give it to previous key)
- `right_trim=1` removes the last LED (doesn't give it to next key)

This wastes LEDs and creates coverage gaps.

## Solution
Redistribute trimmed LEDs to adjacent keys:
- **Left trim**: LEDs removed from the left should be added to the PREVIOUS key
- **Right trim**: LEDs removed from the right should be added to the NEXT key

## Implementation Strategy

### Data Structure for Tracking
```python
# Track which LEDs are trimmed and their destinations
trim_redistributions = {
    midi_note: {
        'left_trimmed': [led_indices],  # LEDs to give to previous key
        'right_trimmed': [led_indices]  # LEDs to give to next key
    }
}
```

### Algorithm Flow
1. **Pass 1**: Calculate all trims and collect trimmed LEDs
2. **Pass 2**: Redistribute LEDs to adjacent keys
   - For left_trim: Add trimmed LEDs to the previous key's list
   - For right_trim: Add trimmed LEDs to the next key's list

### Edge Cases
- First key (MIDI 0): Left trim cannot go to previous (no previous key)
  - Option A: Discard left trimmed LEDs
  - Option B: Don't allow left trim on first key
  - **Selected: Option A** - Discard them (they're at the edge of the piano anyway)

- Last key (MIDI 127): Right trim cannot go to next (no next key)
  - Option A: Discard right trimmed LEDs
  - Option B: Don't allow right trim on last key
  - **Selected: Option A** - Discard them (they're at the edge of the piano)

- Middle keys: Trims should always have a destination

### Implementation Considerations
1. Need to know which MIDI notes exist in the mapping (to find "next" key)
2. Trimmed LEDs should be ADDED to adjacent keys, not REPLACE them
3. Order matters: left trimmed LEDs go at the START of next key's list, right trimmed go at END
4. Logging: Track redistributions for debugging

## Code Location
File: `backend/config.py`
Function: `apply_calibration_offsets_to_mapping()`
Area: Lines 988-1010 (current trim logic)

## Testing
After implementation:
- [ ] Key with left_trim=1 and next key gets that LED
- [ ] Key with right_trim=1 and previous key gets that LED
- [ ] First key with left_trim doesn't crash
- [ ] Last key with right_trim doesn't crash
- [ ] Mixed trims on adjacent keys work correctly
- [ ] Coverage is complete (no LEDs lost or duplicated)

