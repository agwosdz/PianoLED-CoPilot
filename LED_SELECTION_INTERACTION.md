# LED Selection Interaction Implementation

## Overview
Users can now click on piano keys in the visual representation to light up the corresponding LEDs on the physical hardware. This provides real-time visual feedback for calibration.

## Features
✅ Click a piano key to light up mapped LEDs (white color)
✅ LEDs stay lit until another key is selected
✅ Select another key to turn off previous LEDs and light new ones
✅ Click the same key to deselect and turn off all LEDs
✅ Graceful error handling if hardware unavailable

## Architecture

### Frontend (CalibrationSection3.svelte)
Located: `frontend/src/lib/components/CalibrationSection3.svelte`

**New Functions:**
1. `lightUpLedRange(ledIndices: number[])`
   - Takes array of LED indices to light up
   - Calls `/api/calibration/led-on/{led_index}` for each LED
   - Uses white color (255, 255, 255) for better visibility
   - Handles errors gracefully

2. `turnOffAllLeds()`
   - Calls `/api/led/off` to turn off all LEDs
   - Doesn't require parameters
   - Graceful error handling

3. `handleKeyClick(midiNote: number)` [UPDATED]
   - Orchestrates selection logic:
     - If same key clicked: deselect and turn off LEDs
     - If different key clicked: turn off previous LEDs, then light new ones
     - If first key selection: just light up the LEDs
   - Async function with proper await for LED operations

**Event Binding:**
```svelte
on:click={() => handleKeyClick(key.midiNote)}
```

### Backend (calibration.py)
Located: `backend/api/calibration.py`

**New Endpoint:**
```
POST /api/calibration/led-on/{led_index}
```

**Purpose:**
- Light up a specific LED persistently (white color)
- Stays on until turned off via `/api/led/off`

**Implementation:**
```python
@calibration_bp.route('/led-on/<int:led_index>', methods=['POST'])
def turn_on_led_persistent(led_index: int):
    # Validate LED index
    # Light up with white color (255, 255, 255)
    # No auto-off timer (persistent)
```

**Key Differences from `/test-led/{led_index}`:**
- White (255, 255, 255) vs cyan (0, 255, 255)
- Persistent (no 3-sec timer) vs auto-off after 3 seconds
- No background task scheduling

### Backend (hardware_test.py)
Located: `backend/api/hardware_test.py`

**Existing Endpoint Used:**
```
POST /api/led/off
```

**Purpose:**
- Turns off all LEDs at once
- Called when deselecting keys

## API Call Sequence

### Scenario 1: Select Key A
```
1. User clicks Key A (MIDI 21)
2. handleKeyClick(21) called
3. selectedNote = null, so just light up
4. GET /api/calibration/key-led-mapping → fetch LED indices [0, 1, 2]
5. For each LED: POST /api/calibration/led-on/0, /led-on/1, /led-on/2
6. Result: LEDs 0, 1, 2 light up in white
```

### Scenario 2: Select Key B (different key)
```
1. User clicks Key B (MIDI 22)
2. handleKeyClick(22) called
3. selectedNote = 21 (previous), so turn off first
4. POST /api/led/off → all LEDs turn off
5. selectedNote = 22
6. GET /api/calibration/key-led-mapping → fetch LED indices [3, 4, 5]
7. For each LED: POST /api/calibration/led-on/3, /led-on/4, /led-on/5
8. Result: Previous LEDs off, new LEDs 3, 4, 5 light up in white
```

### Scenario 3: Deselect Key B (click same key)
```
1. User clicks Key B (MIDI 22) again
2. handleKeyClick(22) called
3. selectedNote = 22 (same), so deselect
4. selectedNote = null
5. POST /api/led/off → all LEDs turn off
6. Result: All LEDs off
```

## LED Colors Used

| Purpose | Color | RGB |
|---------|-------|-----|
| Global Offset Test | Cyan | (0, 255, 255) |
| Key Selection | White | (255, 255, 255) |
| Off | Black | (0, 0, 0) |

## Error Handling

**Frontend:**
- Try/catch blocks on all fetch calls
- Console warnings/errors logged
- Non-blocking failures (component continues to work)

**Backend:**
- LED index validation (must be in [0, led_count-1])
- LED controller availability check
- Graceful degradation (returns 200 if hardware unavailable)

**Result:**
- Feature works in simulation mode (no hardware)
- Graceful failure if LED controller unavailable
- Console logs for debugging

## Testing

### Manual Testing Steps
1. Start backend: `python -m backend.app`
2. Start frontend: `npm run dev`
3. Navigate to Settings → Calibration
4. In "Piano LED Mapping" section:
   - Click a white key → corresponding LEDs light up white
   - Click a black key → corresponding LEDs light up white
   - Click another key → previous LEDs off, new ones light up
   - Click same key again → all LEDs off

### Hardware Requirements
- Physical LED strip connected (or simulation mode)
- LEDController initialized in backend
- LED GPIO pins configured

### Simulation Testing
- Works in simulation mode (no hardware)
- Console shows LED on/off operations
- No actual LED activity but API calls succeed

## Files Modified

1. **frontend/src/lib/components/CalibrationSection3.svelte**
   - Added `lightUpLedRange()` function
   - Added `turnOffAllLeds()` function
   - Updated `handleKeyClick()` to manage LED state
   - Updated event binding to use new handler

2. **backend/api/calibration.py**
   - Added new route: `/led-on/<int:led_index>`
   - Added function: `turn_on_led_persistent()`
   - Uses white color and persistent lighting

## Benefits

1. **Visual Feedback**: Users see exact LEDs for each key
2. **Calibration Aid**: Helps verify key-to-LED mapping is correct
3. **Hardware Testing**: Quick way to test LED functionality
4. **User Friendly**: Intuitive click-to-light interaction
5. **Safe**: Validates all LED indices before accessing

## Future Enhancements

- [ ] Add RGB color picker to choose LED color
- [ ] Add LED range selector (first/last LED only, or all LEDs)
- [ ] Add animation options (fade, blink, pulse)
- [ ] Save/load LED test patterns
- [ ] Performance optimization for high LED counts

## References

- LED API: `backend/api/calibration.py` lines 564-633
- LED off API: `backend/api/hardware_test.py` line 205
- Frontend component: `frontend/src/lib/components/CalibrationSection3.svelte`
- Calibration store: `frontend/src/lib/stores/calibration.ts`
