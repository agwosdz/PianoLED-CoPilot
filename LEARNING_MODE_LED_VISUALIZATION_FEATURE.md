# 🎹 Learning Mode LED Visualization - Complete Feature

## Overview

The learning mode now includes **visual LED feedback** to guide the student through practice. When playback pauses waiting for notes, the LEDs illuminate to show exactly which notes need to be played.

---

## LED Feedback System

### 1. **Expected Notes Visualization** (During Pause)

When learning mode pauses waiting for notes, the LEDs show:

- **Dim Color** (50% brightness): Notes you still need to play
  - Left hand: Coral-red (FF6B6B) at 50% brightness
  - Right hand: Blue (006496) at 50% brightness

- **Bright Color** (100% brightness): Notes you've already played correctly
  - Left hand: Coral-red (FF6B6B) at full brightness
  - Right hand: Blue (006496) at full brightness

- **All Other LEDs**: Off (dark)

**Example:**
```
Expected notes for right hand: [72, 74, 76]
User has played: [72, 74]

LED Display:
- Note 72 LED: Blue (bright) - ✓ played
- Note 74 LED: Blue (bright) - ✓ played  
- Note 76 LED: Blue (dim)    - ⏳ waiting for this
- All others:  Off           - Not needed
```

### 2. **Wrong Note Feedback** (Red LEDs)

When you play a note that's not expected:

- **Red Color** (255, 0, 0): Incorrect note played
- Provides immediate visual feedback that the note wasn't needed
- Turns off automatically when correct notes are played

**Example:**
```
Expected notes for right hand: [72, 74]
User plays: [60]  (wrong note)

LED Display:
- Note 60 LED: Red (bright) - ✗ wrong note!
- Note 72 LED: Off          - Still waiting
- Note 74 LED: Off          - Still waiting
```

---

## Implementation Details

### Methods Added to PlaybackService

#### `_highlight_expected_notes(expected_left, expected_right, played_left, played_right)`

**Purpose:** Display which notes need to be played (called when pause occurs)

**Parameters:**
- `expected_left`: Set of MIDI notes expected from left hand
- `expected_right`: Set of MIDI notes expected from right hand  
- `played_left`: Set of notes already played by left hand
- `played_right`: Set of notes already played by right hand

**Behavior:**
1. Gets hand colors from learning mode settings
2. Creates "bright" and "dim" versions of each hand's color
3. Maps each expected note to LED indices
4. Sets bright color for played notes, dim for unsatisfied notes
5. Turns off all other LEDs

**Colors Used:**
```python
# Default colors (from learning mode settings)
left_hand_color = '#ff6b6b'   # Coral-red (RGB: 255, 107, 107)
right_hand_color = '#006496'  # Blue (RGB: 0, 100, 150)

# Brightness levels
bright = 100% (full RGB values)
dim = 50% (half RGB values)
```

---

#### `_highlight_wrong_notes(wrong_notes)`

**Purpose:** Show wrong notes in red for immediate feedback

**Parameters:**
- `wrong_notes`: Set of MIDI notes that were played incorrectly

**Behavior:**
1. Maps each wrong note to LED indices
2. Sets all wrong note LEDs to bright red (255, 0, 0)
3. Logs which LEDs were highlighted

**Color Used:**
```python
red_color = (255, 0, 0)  # Bright red
```

---

### Integration with Pause Check

The LED visualization is called from `_check_learning_mode_pause()`:

```python
# In _check_learning_mode_pause():

# When wrong notes detected
if wrong_left_notes or wrong_right_notes:
    all_wrong = wrong_left_notes | wrong_right_notes
    logger.info(f"Learning mode: Wrong notes played: {sorted(all_wrong)}")
    self._highlight_wrong_notes(all_wrong)  # ← Light up wrong notes in red

# When pause occurs
if should_pause and (expected_left_notes or expected_right_notes):
    # Visualize expected notes on LEDs
    self._highlight_expected_notes(expected_left_notes, expected_right_notes, 
                                  played_left_notes, played_right_notes)  # ← Show what to play
    logger.debug(f"Learning mode pausing at {self._current_time:.2f}s")
```

---

## User Experience Flow

### Scenario: Student Learning a Simple 4-Note Phrase

```
Step 1: MIDI File Playing
┌─────────────────────────────────┐
│ Time: 2.0 seconds               │
│ Expected notes: [72, 74]         │
│ (Right hand C5, D5)              │
│                                  │
│ ALL LEDs OFF - playback rolling  │
│ (normal playback display)        │
└─────────────────────────────────┘
        ↓ (notes appear in timing window)

Step 2: Playback PAUSES (Learning Mode Activated)
┌─────────────────────────────────┐
│ PAUSE!                           │
│ Expected: [72, 74]               │
│ Student: (hasn't played yet)     │
│                                  │
│ LED Display:                     │
│ - Note 72: Blue (dim)   ⏳      │
│ - Note 74: Blue (dim)   ⏳      │
│ - Others: Off                    │
│                                  │
│ Message: "Play the right hand!" │
└─────────────────────────────────┘
        ↓ (student plays note)

Step 3: Student Plays First Note
┌─────────────────────────────────┐
│ Expected: [72, 74]               │
│ Student: [72]                    │
│                                  │
│ LED Display:                     │
│ - Note 72: Blue (bright) ✓      │
│ - Note 74: Blue (dim)   ⏳      │
│ - Others: Off                    │
│                                  │
│ Feedback: First note correct!   │
└─────────────────────────────────┘
        ↓ (student plays second note)

Step 4: Student Plays Second Note
┌─────────────────────────────────┐
│ Expected: [72, 74]               │
│ Student: [72, 74]                │
│                                  │
│ LED Display:                     │
│ - Note 72: Blue (bright) ✓      │
│ - Note 74: Blue (bright) ✓      │
│ - Others: Off                    │
│                                  │
│ Feedback: All correct!          │
│ → PAUSE RELEASES                │
│ → Playback RESUMES              │
└─────────────────────────────────┘
        ↓ (playback continues)

Step 5: Playback Resumes
┌─────────────────────────────────┐
│ Time: 2.5 seconds                │
│ Expected notes: [48, 50]         │
│ (Left hand C3, D3)               │
│                                  │
│ LED Display shows next phrase    │
│ - Note 48: Coral (dim)  ⏳      │
│ - Note 50: Coral (dim)  ⏳      │
│ - Others: Off                    │
│                                  │
│ Playback continues...           │
└─────────────────────────────────┘
```

---

## Wrong Note Scenario

```
Step 1: Expected Right Hand Notes [72, 74]
┌──────────────────────────┐
│ Playback PAUSED          │
│ Note 72: Blue (dim) ⏳  │
│ Note 74: Blue (dim) ⏳  │
└──────────────────────────┘
      ↓ (student plays wrong note)

Step 2: Student Plays Wrong Note [60]
┌──────────────────────────┐
│ Note 60: Red (bright) ✗  │
│ Note 72: Blue (dim) ⏳  │
│ Note 74: Blue (dim) ⏳  │
│                          │
│ Log: "Wrong notes: [60]" │
└──────────────────────────┘
      ↓ (red LED feedback, then student plays correct notes)

Step 3: Student Plays Correct Notes [72, 74]
┌──────────────────────────┐
│ Note 60: Off             │
│ Note 72: Blue (bright) ✓│
│ Note 74: Blue (bright) ✓│
│                          │
│ Red fades, correct shown │
│ Pause releases...        │
└──────────────────────────┘
```

---

## Color Reference

### Hand Colors (from Learning Mode Settings)

| Hand | Setting Key | Default | RGB |
|------|-------------|---------|-----|
| Left | `left_hand_white_color` | #FF6B6B | (255, 107, 107) |
| Right | `right_hand_white_color` | #006496 | (0, 100, 150) |

### Brightness Levels

| State | Multiplier | Example (Right Hand Blue) |
|-------|-----------|---------------------------|
| Unsatisfied (waiting) | 50% | (0, 50, 75) |
| Satisfied (played) | 100% | (0, 100, 150) |
| Wrong note | 100% | (255, 0, 0) |

---

## Technical Notes

### LED Mapping

The LEDs are mapped to MIDI notes using the calibrated mapping system:
- Each MIDI note can map to 1+ LED(s)
- Multi-note LEDs are supported (consecutive LEDs for one key)
- Mapping respects piano calibration settings

### Performance Considerations

- LED update happens only on state changes (pause/wrong notes)
- Not called every playback loop (only when needed)
- Minimal CPU overhead compared to regular playback updates
- Thread-safe deque operations for note tracking

### Error Handling

- Gracefully handles missing LED controller
- Validates LED indices before setting colors
- Converts hex color strings safely
- Logs all errors for debugging

---

## Configuration

The LED visualization uses settings from the Learning Mode API:

**GET `/api/learning/options`** returns:
```json
{
  "left_hand": {
    "wait_for_notes": bool,
    "white_color": "#RRGGBB",
    "black_color": "#RRGGBB"
  },
  "right_hand": {
    "wait_for_notes": bool,
    "white_color": "#RRGGBB",
    "black_color": "#RRGGBB"
  },
  "timing_window_ms": int
}
```

The `white_color` values are used for the LED visualization:
- Bright version: Full RGB values
- Dim version: 50% RGB values (0.5x multiplier)

---

## Testing the LED Visualization

### Test 1: Expected Notes Display

**Setup:**
1. Load a simple MIDI file with 2 right-hand notes
2. Enable "Wait for Right Hand" in learning options
3. Set timing window to 2000ms

**Steps:**
1. Start playback
2. When pause occurs, check LEDs
3. **Expected:** 2 blue LEDs lit (dim) - showing which notes to play

**Verification:**
```
✓ Pause occurs at expected time
✓ Blue LEDs appear for right hand notes
✓ LEDs are dim (50% brightness)
✓ All other LEDs are off
```

### Test 2: Progress Indication

**Setup:** Same as Test 1

**Steps:**
1. Playback pauses, blue LEDs show expected notes (dim)
2. Play first note on keyboard
3. Check LED brightness

**Expected:**
```
✓ First note LED becomes bright (100%)
✓ Second note LED stays dim (50%)
✓ Clear visual indication of progress
```

### Test 3: Wrong Note Feedback

**Setup:** Same as Test 1

**Steps:**
1. Playback pauses, showing 2 expected notes
2. Play a wrong note (not in the expected set)
3. Check LED color

**Expected:**
```
✓ Wrong note LED lights up RED
✓ Wrong note LED turns off after ~1 second
✓ Expected note LEDs remain visible
```

### Test 4: Pause Release

**Setup:** Same as Test 1

**Steps:**
1. Playback pauses, blue LEDs show expected notes
2. Play both expected notes
3. Observe playback

**Expected:**
```
✓ First note: LED becomes bright
✓ Second note: LED becomes bright
✓ Pause immediately releases
✓ Playback resumes
✓ LEDs turn off (normal playback display)
```

---

## Logging Output

When LED visualization is active, you'll see:

```
DEBUG: Learning mode pausing at 2.00s
DEBUG: Learning mode: Highlighted 2 LEDs for expected notes
INFO: Learning mode: Wrong notes played: [60]
INFO: Learning mode: Highlighted 1 LEDs in red for wrong notes
```

---

## Future Enhancements

1. **Animation During Pause**
   - Pulse expected notes to draw attention
   - Fade effect when notes are satisfied

2. **Progressive Difficulty**
   - Show only first note initially
   - Show remaining notes after first is played
   - Adaptive timing window

3. **Performance Statistics**
   - Green = all correct
   - Yellow = some mistakes
   - Red = significant mistakes
   - Display on LEDs or UI

4. **Hand Separation Visualization**
   - More distinct LED patterns for left vs right
   - Spatial separation of expected notes

---

## Summary

The LED visualization feature provides:

✅ **Visual Guidance** - Shows exactly which notes to play  
✅ **Progress Indication** - Bright LEDs for played notes  
✅ **Error Feedback** - Red LEDs for wrong notes  
✅ **Per-Hand Color Coding** - Different colors for left/right  
✅ **Immediate Feedback** - Updates as notes are played  
✅ **Accessibility** - Visual alternative to logs  

This makes the learning experience more intuitive and engaging! 🎹

