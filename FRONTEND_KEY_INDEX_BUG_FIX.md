# Frontend Key Index to MIDI Note Conversion Bug - FIXED

## Problem

The LED visualization was displaying the mapping starting at **LED 63** instead of **LED 4**, indicating that Key 21 was being treated as the first key instead of Key 0.

This was caused by a **mismatch between backend and frontend key representation**:

- **Backend**: Returns key indices (0-87) in the mapping dictionary
- **Frontend**: Was interpreting these key indices directly as MIDI notes without conversion
- **Result**: Key index 21 was treated as MIDI note 21 instead of MIDI note 42

## Root Cause Analysis

### Backend Behavior (Correct ✅)
```python
# backend/config_led_mapping_advanced.py, line 165
for key_idx in range(total_keys):  # 0-87
    key_led_mapping[key_idx] = [...]  # Uses key index as dict key
```

Response:
```json
{
  "mapping": {
    "0": [4, 5, 6, 7],      // Key 0 (MIDI 21) → LEDs 4-7
    "1": [7, 8, 9, 10],     // Key 1 (MIDI 22) → LEDs 7-10
    "21": [63, 64, 65, 66], // Key 21 (MIDI 42) → LEDs 63-66
    "87": [247, 248, 249]   // Key 87 (MIDI 108) → LEDs 247-249
  }
}
```

### Frontend Bug (Incorrect ❌)
```typescript
// frontend/src/lib/stores/calibration.ts, lines 437-440 (BEFORE FIX)
const mapping: Record<number, number[]> = {};
for (const [key, value] of Object.entries(data.mapping)) {
  const midiNote = parseInt(key, 10);  // ❌ Treats key as MIDI note!
  if (Number.isFinite(midiNote)) {
    mapping[midiNote] = value as number[];  // ❌ Wrong key!
  }
}

// Result in frontend:
// mapping = {
//   0: [4, 5, 6, 7],      // ❌ MIDI 0 (C-1, outside piano range)
//   1: [7, 8, 9, 10],     // ❌ MIDI 1
//   21: [63, 64, 65, 66], // ❌ Treated as MIDI 21, not 42
//   87: [247, 248, 249]   // ❌ Treated as MIDI 87, not 108
// }
```

### Frontend Fix (Correct ✅)
```typescript
// frontend/src/lib/stores/calibration.ts, lines 437-450 (AFTER FIX)
const mapping: Record<number, number[]> = {};
for (const [key, value] of Object.entries(data.mapping)) {
  const keyIndex = parseInt(key, 10);  // ✅ Correct: treat as key index
  if (Number.isFinite(keyIndex)) {
    const midiNote = 21 + keyIndex;  // ✅ Convert: key index → MIDI note
    mapping[midiNote] = value as number[];  // ✅ Correct key!
  }
}

// Result in frontend:
// mapping = {
//   21: [4, 5, 6, 7],      // ✅ Key 0 = MIDI 21 (A0)
//   22: [7, 8, 9, 10],     // ✅ Key 1 = MIDI 22 (A#0)
//   42: [63, 64, 65, 66],  // ✅ Key 21 = MIDI 42 (F#2)
//   108: [247, 248, 249]   // ✅ Key 87 = MIDI 108 (C8)
// }
```

## Mapping Reference

| Key Index | MIDI Note | Note Name | Map Says | Frontend Now Shows |
|-----------|-----------|-----------|----------|-------------------|
| 0         | 21        | A0        | ❌ MIDI 0 | ✅ MIDI 21 |
| 1         | 22        | A#0       | ❌ MIDI 1 | ✅ MIDI 22 |
| 20        | 41        | F2        | ❌ MIDI 20 | ✅ MIDI 41 |
| 21        | 42        | F#2       | ❌ MIDI 21 | ✅ MIDI 42 (LED 63) |
| 87        | 108       | C8        | ❌ MIDI 87 | ✅ MIDI 108 |

## Files Changed

- **frontend/src/lib/stores/calibration.ts**
  - Method: `getKeyLedMappingWithRange()`
  - Change: Added `const midiNote = 21 + keyIndex;` to convert key indices to MIDI notes
  - Lines: 437-450

## Impact

### Before Fix
- Visualization showed mapping starting at LED 63 for Key 21
- Calibration visualization was offset (showed wrong piano keys for LED ranges)
- Key offsets didn't map correctly to visual display

### After Fix
- Visualization correctly shows Key 0 (MIDI 21) starting at LED 4
- Each key now maps to the correct visual position
- Calibration visualization is accurate
- Key offsets now properly correlate to the visual display

## Testing

To verify the fix works:

1. **Check the mapping API response:**
   ```bash
   curl http://192.168.1.225:5001/api/calibration/key-led-mapping | jq '.mapping | to_entries | .[0:3]'
   ```
   
   Should show:
   ```json
   [
     {"key": "0", "value": [4, 5, 6, 7]},
     {"key": "1", "value": [7, 8, 9, 10]},
     {"key": "2", "value": [10, 11, 12, 13]}
   ]
   ```

2. **Frontend now converts these to MIDI notes:**
   - Key "0" → MIDI 21 (A0)
   - Key "1" → MIDI 22 (A#0)
   - etc.

3. **Calibration visualization should show:**
   - LEDs 4-7 lighting up for MIDI note 21 (first key)
   - LEDs 63-66 lighting up for MIDI note 42 (key index 21)
   - Proper key names displayed for each LED range

## Formula

```
MIDI Note = Key Index + 21

For 88-key piano:
- Key Index: 0-87
- MIDI Note: 21-108 (A0 to C8)
- First key (0): MIDI 21 (A0)
- Key 21: MIDI 42 (F#2, starts at LED 63)
- Last key (87): MIDI 108 (C8, ends at LED 249)
```

## Conclusion

This was a simple but critical type conversion bug where the frontend forgot to add 21 to the key index. The backend was correct all along - it was properly returning key indices (0-87) in the mapping dictionary. The frontend just needed to remember that MIDI notes for an 88-key piano start at 21, not 0.

✅ **FIXED**: Frontend now correctly converts key indices to MIDI notes for proper visualization and calibration.
