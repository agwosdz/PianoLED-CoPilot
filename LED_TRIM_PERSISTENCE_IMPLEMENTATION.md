# LED Trim Persistence Implementation

## Overview

Implemented a persistent LED trimming system that calculates and stores left/right trim values for each key, allowing LED customizations to survive page reloads without directly saving individual LED selections.

## Architecture

### Data Model

Instead of saving individual LED selections per key, we calculate and persist:
- **`left_trim`**: Number of LEDs trimmed from the LEFT side of the original allocation
- **`right_trim`**: Number of LEDs trimmed from the RIGHT side of the original allocation

**Example:**
- Original allocation: LEDs [50, 51, 52, 53]
- User deselects LED 50: `left_trim = 1`
- Result: [51, 52, 53]
- User deselects LED 53: `right_trim = 1`  
- Final result: [51, 52]

### Storage Structure

**Database field**: `calibration.key_led_trims`
```json
{
  "45": {"left_trim": 1, "right_trim": 0},
  "60": {"left_trim": 0, "right_trim": 2},
  "72": {"left_trim": 1, "right_trim": 1}
}
```

## Implementation Details

### Backend Changes

#### 1. Settings Schema (`backend/services/settings_service.py`)
Added new field to calibration section:
```python
'key_led_trims': {
    'type': 'object',
    'default': {},
    'description': 'Per-key LED trim adjustments {midi_note: {left_trim: int, right_trim: int}}'
}
```

#### 2. API Endpoint (`backend/api/calibration.py`)
New PUT endpoint: `/api/calibration/key-led-trim/<midi_note>`

**Request body:**
```json
{
  "left_trim": 1,
  "right_trim": 0
}
```

**Features:**
- Validates MIDI note (0-127)
- Validates trim values (0-100)
- Stores trim data in settings
- Broadcasts `key_led_trim_changed` event via WebSocket
- Logs changes for debugging

### Frontend Changes

#### 1. LED Trim Calculation (`frontend/src/lib/components/CalibrationSection3.svelte`)

When user saves an adjustment, the system:

1. **Counts left trim:**
   ```javascript
   for (let i = 0; i < currentKeyLEDAllocation.length; i++) {
     if (!selectedLEDsForNewKey.has(currentKeyLEDAllocation[i])) {
       leftTrim++;
     } else {
       break; // Stop at first selected LED
     }
   }
   ```

2. **Counts right trim:**
   ```javascript
   for (let i = currentKeyLEDAllocation.length - 1; i >= 0; i--) {
     if (!selectedLEDsForNewKey.has(currentKeyLEDAllocation[i])) {
       rightTrim++;
     } else {
       break; // Stop at first selected LED
     }
   }
   ```

3. **Saves via API:**
   ```javascript
   await calibrationService.setKeyLedTrim(midiNote, {
     left_trim: leftTrim,
     right_trim: rightTrim
   });
   ```

#### 2. CalibrationService Method (`frontend/src/lib/stores/calibration.ts`)

Added `setKeyLedTrim` method:
```typescript
async setKeyLedTrim(midiNote: number, trimData: { left_trim: number; right_trim: number }): Promise<void> {
  // PUT /api/calibration/key-led-trim/<midiNote>
  // Sends trim data and reloads status
}
```

## Data Flow

1. **User selects MIDI note** in details panel → Clicks "Add Offset"
2. **Form opens** with pre-filled MIDI note
3. **User customizes LEDs** (toggles green/gray)
4. **User clicks "Add Adjustment"**
5. **Frontend calculates trim values** based on original vs. modified allocation
6. **Sends to backend:**
   - Offset value via `/api/calibration/key-offset/<note>`
   - Trim values via `/api/calibration/key-led-trim/<note>`
7. **Backend persists** both to database
8. **WebSocket broadcasts** events
9. **On page reload:** Status endpoint returns all saved trim values
10. **Mapping logic uses trim values** to reconstruct adjusted allocations

## Integration with Mapping Logic (Next Phase)

The mapping logic should use trim values to adjust LED allocations:

```typescript
// Original allocation from mapping
const originalLEDs = [50, 51, 52, 53];

// Apply trim values
const leftTrim = key_led_trims[midiNote]?.left_trim ?? 0;
const rightTrim = key_led_trims[midiNote]?.right_trim ?? 0;

// Effective range after trimming
const adjustedLEDs = originalLEDs.slice(leftTrim, originalLEDs.length - rightTrim);

// Result: [51, 52] if left_trim=1, right_trim=1
```

Additionally, trim values enable adjacent key LED reallocation:
- If current key has `left_trim > 0`, previous key could use those extra LEDs
- If current key has `right_trim > 0`, next key could use those extra LEDs

## Benefits

✅ **Persistent:** Survives page reloads
✅ **Clean storage:** Only stores trim deltas, not full LED lists
✅ **Maintainable:** Simple integer values, easy to understand
✅ **Flexible:** Enables adjacent key LED borrowing
✅ **Scalable:** Works with any number of keys and LED counts
✅ **Independent:** Doesn't rely on UI state, purely data-driven

## Testing Checklist

- [ ] Add offset for MIDI 45 with LED customization (remove 1 from left)
- [ ] Verify `left_trim=1, right_trim=0` in database
- [ ] Reload page
- [ ] Verify trim values persist and are displayed correctly
- [ ] Add offset for MIDI 60 with trim on both sides
- [ ] Verify multiple keys can have different trim values
- [ ] Test edge cases (trim all LEDs, no trim, etc.)
- [ ] Verify WebSocket broadcasts work
- [ ] Test that mapping logic correctly applies trims

## Files Modified

1. `backend/services/settings_service.py` - Added `key_led_trims` schema field
2. `backend/api/calibration.py` - Added `/key-led-trim/<midi_note>` endpoint
3. `frontend/src/lib/components/CalibrationSection3.svelte` - Calculate and save trim values
4. `frontend/src/lib/stores/calibration.ts` - Added `setKeyLedTrim()` method

## Future Enhancements

1. **Adjacent Key Borrowing:** Use trim values to reallocate LEDs to neighboring keys
2. **Automatic Rebalancing:** Redistribute LEDs based on trim patterns
3. **Visual Indicators:** Show trim values in the adjustments list
4. **Bulk Operations:** Apply consistent trim patterns across multiple keys
