# Play and Learn Feature - Implementation Plan

## Overview
Transform the Play page into "Play and Learn" - an interactive learning mode that helps users practice playing MIDI files by learning which notes to play for left and right hands.

## User Story

**As a musician**, I want to practice playing along with MIDI files by:
1. Seeing which hand (left/right) should play each note
2. Optionally pausing playback until I play the correct notes
3. Visualizing left and right hand notes with different colors

## Feature 1: Wait for MIDI Notes

### Requirement
When enabled, playback will PAUSE (not stop) after starting a section, with LEDs remaining illuminated. Playback resumes only when the user plays the correct notes on the keyboard.

### How It Works

1. **Playback starts** → System plays first note sequence
2. **LEDs illuminate** → Show which notes should be played (by hand)
3. **Playback pauses** → Waits for user input
4. **User plays notes** → Matches LEDs on keyboard
5. **System verifies** → Checks if user played correct notes
6. **Playback resumes** → Continues when notes match

### Technical Details

**Comparison Methods:**
- Note number must match
- Timing window: +/- 500ms of expected time (flexible)
- Velocity can be flexible (user's control)
- Handle missing/extra notes gracefully

**Pause Logic:**
```
Current playback time: T
Next note event time: T + delta
Wait for user to play notes during [T, T + delta]
```

### State Machine

```
IDLE 
  ↓ play_file()
PLAYING_PAUSED (at first note boundary)
  ↓ user_plays_notes()
  ↓ verify_notes_match()
PLAYING → next pause point
  ↓
PLAYING_PAUSED
  ↓ (repeat)
FINISHED
```

## Feature 2: Color Configuration for Hands

### Requirement
Users can configure different colors for left and right hand notes, including white and black key variations.

### Color Targets

Each hand can have colors for:
1. **White keys** - Standard piano white keys
2. **Black keys** - Raised black keys

Total: 4 color configurations (L-white, L-black, R-white, R-black)

### Default Colors

```
Left Hand:
  - White keys: Red (#FF0000)
  - Black keys: Dark Red (#CC0000)

Right Hand:
  - White keys: Blue (#0000FF)
  - Black keys: Dark Blue (#0000CC)
```

### UI Components

For each hand section:
- Color picker for white keys
- Color picker for black keys
- Preview strip showing the colors
- Reset to default button

### Settings Storage

```json
{
  "learning_mode": {
    "left_hand_white": "#FF0000",
    "left_hand_black": "#CC0000",
    "right_hand_white": "#0000FF",
    "right_hand_black": "#0000CC",
    "wait_for_notes_enabled": false,
    "note_timing_window_ms": 500
  }
}
```

## Frontend Changes

### File: `frontend/src/routes/play/+page.svelte`

#### 1. Update Page Title
```svelte
<h1>Play and Learn</h1>
```

#### 2. New Learning Options Section
```
┌─ Learning Options ─────────────────────┐
│                                        │
│ ☐ Wait for MIDI Notes                 │
│   When checked, playback pauses until  │
│   you play the correct notes           │
│                                        │
├─ Left Hand ────────────────────────────┤
│ White Keys: [Color Picker]             │
│ Black Keys: [Color Picker]             │
│ [Reset to Default]                     │
│                                        │
├─ Right Hand ───────────────────────────┤
│ White Keys: [Color Picker]             │
│ Black Keys: [Color Picker]             │
│ [Reset to Default]                     │
│                                        │
│ ↕️ Note Timing Tolerance: 0.5 sec     │
└────────────────────────────────────────┘
```

### New Component: Learning Options Panel

```svelte
// LearningOptions.svelte
<script>
  export let waitForNotes = false;
  export let leftHandWhite = '#FF0000';
  export let leftHandBlack = '#CC0000';
  export let rightHandWhite = '#0000FF';
  export let rightHandBlack = '#0000CC';
  export let timingWindow = 500;
  
  async function saveLearningOptions() {
    // Call backend API to save
  }
  
  function resetToDefaults() {
    // Reset all colors
  }
</script>
```

## Backend Changes

### Playback Service Enhancements

#### 1. New Parameters
```python
# In playback_service.py

class PlaybackMode(Enum):
    NORMAL = "normal"
    LEARN_PAUSE = "learn_pause"

class PlaybackService:
    def play_file(
        self, 
        filename: str, 
        playback_mode: PlaybackMode = PlaybackMode.NORMAL,
        wait_for_notes: bool = False
    ):
        # New logic for learning mode
```

#### 2. Pause Logic
```python
def _should_pause_for_learning(self, current_event_idx: int) -> bool:
    """Check if we should pause for learning at this event"""
    if not self._wait_for_notes:
        return False
    
    event = self._events[current_event_idx]
    return event.get('hand') in ['left', 'right']

def pause_until_notes_match(self, expected_notes: List[int]) -> bool:
    """
    Pause playback until user plays expected notes
    Returns True if notes matched
    """
    self._state = PlaybackState.PAUSED
    self._resume_on_match = True
    self._expected_notes = expected_notes
    # Monitor incoming MIDI notes
    # Return True when notes match
```

#### 3. Note Verification
```python
def _verify_user_input(self, played_notes: List[int]) -> bool:
    """
    Verify that user played the expected notes
    
    Parameters:
    - played_notes: List of MIDI notes user played
    - timing_window: Tolerance in milliseconds
    
    Returns: True if notes match (within tolerance)
    """
    # Handle missing/extra notes gracefully
    # Consider timing tolerance
    # Could use fuzzy matching or exact matching
```

### New API Endpoints

```
GET /api/learning/options
  Returns current learning mode settings

POST /api/learning/options
  Updates learning mode settings
  Body: {
    wait_for_notes: bool,
    left_hand_white: str,    # hex color
    left_hand_black: str,
    right_hand_white: str,
    right_hand_black: str,
    timing_window_ms: int
  }

POST /api/playback/pause-for-learning
  Pauses playback for learning
  Body: {
    hand: str,  # 'left' or 'right'
    notes: [int]
  }

POST /api/playback/resume-after-notes
  Resumes playback when notes match
  Body: {
    played_notes: [int]
  }
```

### Color Application

#### In LEDController
```python
def apply_hand_color(
    self, 
    led_index: int, 
    hand: str,  # 'left' or 'right'
    is_black_key: bool = False
) -> tuple:
    """
    Get the color for a specific LED based on hand and key type
    """
    settings = self._settings_service.get_all_settings()
    
    if hand == 'left':
        key = 'left_hand_black' if is_black_key else 'left_hand_white'
    else:
        key = 'right_hand_black' if is_black_key else 'right_hand_white'
    
    color_hex = settings.get('learning_mode', {}).get(key, '#FFFFFF')
    return hex_to_rgb(color_hex)
```

## Settings Integration

### Settings Service Updates

```python
# In settings_service.py

DEFAULT_SETTINGS = {
    ...existing settings...,
    'learning_mode': {
        'wait_for_notes_enabled': False,
        'timing_window_ms': 500,
        'left_hand_white': '#FF0000',
        'left_hand_black': '#CC0000',
        'right_hand_white': '#0000FF',
        'right_hand_black': '#0000CC'
    }
}
```

## Implementation Phases

### Phase 1: Frontend Changes (Current)
1. ✅ Change page title to "Play and Learn"
2. ✅ Create Learning Options UI section
3. ✅ Add color pickers for hands
4. ✅ Add checkbox for "Wait for MIDI Notes"
5. ✅ Connect to backend APIs

### Phase 2: Backend Changes
1. Add settings schema for learning mode
2. Add API endpoints for learning options
3. Update PlaybackService for pause logic
4. Implement note verification
5. Apply hand-specific colors in playback

### Phase 3: Integration
1. Connect frontend to backend
2. Test pause/resume flow
3. Test note verification
4. Test color visualization
5. Full E2E testing

## Database/Settings Schema

```
Category: 'learning_mode'

Keys:
- 'wait_for_notes_enabled' (bool) - Default: False
- 'timing_window_ms' (int) - Default: 500
- 'left_hand_white' (str) - Default: '#FF0000'
- 'left_hand_black' (str) - Default: '#CC0000'
- 'right_hand_white' (str) - Default: '#0000FF'
- 'right_hand_black' (str) - Default: '#0000CC'
```

## UI Flow

### 1. User Interface

```
┌─────────────────────────────────────────────────────┐
│           Play and Learn                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Now Playing: Moonlight Sonata                      │
│  ▶ ■                                                │
│  |████████░░░░░░░░░░░░░░░░| 1:30 / 3:45            │
│                                                     │
│  ☑ Receive MIDI from USB Keyboard    🎹 Connected  │
│  ├─ Select Input Device: [Keyboard ▼]              │
│  └─ [Refresh]                                       │
│                                                     │
├─ Learning Options ────────────────────────────────┤
│                                                     │
│  ☐ Wait for MIDI Notes                             │
│    Playback pauses until you play matching notes   │
│                                                     │
│  ├─ Left Hand                                       │
│  │  White Keys: [■ Red] [Color picker]             │
│  │  Black Keys: [■ DarkRed] [Color picker]         │
│  │  [Reset to Default]                              │
│  │                                                  │
│  ├─ Right Hand                                      │
│  │  White Keys: [■ Blue] [Color picker]            │
│  │  Black Keys: [■ DarkBlue] [Color picker]        │
│  │  [Reset to Default]                              │
│  │                                                  │
│  └─ Note Timing Tolerance: [500 ms]                │
│                                                     │
├─ MIDI Song List ──────────────────────────────────┤
│  [List of songs...]                                 │
└─────────────────────────────────────────────────────┘
```

## Implementation Timeline

**Phase 1 (Today):** Frontend UI changes
- Update page title
- Create Learning Options component
- Add color picker inputs
- Add wait-for-notes checkbox

**Phase 2 (Next):** Backend API
- Settings schema
- API endpoints
- Note verification logic

**Phase 3 (Later):** Integration
- Connect frontend to backend
- Test full flow
- Polish UX

## Testing Strategy

### Manual Tests

1. **Wait for Notes**
   - Start playback with feature enabled
   - Verify playback pauses
   - Play correct notes → Resume
   - Play wrong notes → Stay paused
   - Play timing window test

2. **Color Configuration**
   - Change left hand white color
   - Verify LED updates reflect new color
   - Change right hand white color
   - Verify LED updates
   - Reset to defaults

3. **Integration**
   - Start with color + wait for notes
   - Pause/resume with hand-specific colors
   - Multi-hand playback

### Automated Tests

```python
# test_learning_mode.py
def test_pause_for_learning():
    # Start playback with wait_for_notes=True
    # Verify playback pauses at first boundary
    # Play notes
    # Verify resume

def test_color_configuration():
    # Set custom colors
    # Verify API returns correct colors
    # Verify LEDs use correct colors
```

## Success Criteria

✅ Page renamed to "Play and Learn"
✅ Learning Options UI displays correctly
✅ Color pickers work and persist
✅ Wait for Notes checkbox toggles
✅ Pause/resume flow works correctly
✅ Notes are verified properly
✅ Hand colors apply to LEDs
✅ Settings persist across sessions
✅ No breaking changes to existing features
✅ Full backward compatibility

