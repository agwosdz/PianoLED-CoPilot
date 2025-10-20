# Multi-Track Hand Detection Implementation Plan

## Overview
Use MIDI file track information to identify which hand (left or right) each track represents. This allows different LED visualization or effects for left vs right hand parts.

## Strategy

### Common MIDI File Patterns

Most piano MIDI files follow these conventions:

1. **Track Name Convention**
   - Track names like "Left Hand", "Right Hand", "Treble", "Bass"
   - Or abbreviated: "RH", "LH", "R", "L"

2. **MIDI Channel Convention** (less common but valid)
   - Channel 0 (1) for right hand
   - Channel 1 (2) for left hand

3. **Note Range Convention** (fallback)
   - Notes below Middle C (~MIDI 60) = Left hand
   - Notes above Middle C = Right hand

4. **Track Order Convention** (fallback)
   - First track(s) = Right hand
   - Last track(s) = Left hand
   - Or track 0 = right, track 1 = left

### Detection Priority

1. **Primary:** Check track name for explicit hand labels
2. **Secondary:** Check MIDI channel assignment
3. **Tertiary:** Analyze note ranges in track
4. **Fallback:** Use track order

## Implementation

### Data Structure

```python
class TrackInfo:
    """Information about a MIDI track"""
    
    index: int              # Track index in MIDI file (0-based)
    name: str               # Track name from MIDI metadata
    channel: Optional[int]  # Primary MIDI channel used (if any)
    hand: str               # Detected hand: 'right', 'left', 'both', or 'unknown'
    confidence: float       # 0.0-1.0 confidence level of detection
    detection_method: str   # How hand was detected: 'name', 'channel', 'range', 'order', 'unknown'
    note_range: tuple       # (min_note, max_note) in track
    note_count: int         # Number of notes in track
```

### API Changes

**MIDIParser.parse_file() response enhancement:**

```python
{
    'duration': float,
    'events': List[Dict],
    'metadata': {
        'tracks': int,
        'ticks_per_beat': int,
        'type': str,
        'title': str,
        'tempo': int,
        'track_info': [               # NEW: Track analysis
            {
                'index': 0,
                'name': 'Right Hand',
                'hand': 'right',
                'confidence': 0.95,
                'detection_method': 'name',
                'note_count': 128,
                'note_range': [60, 108]
            },
            {
                'index': 1,
                'name': 'Left Hand',
                'hand': 'left',
                'confidence': 0.95,
                'detection_method': 'name',
                'note_count': 85,
                'note_range': [21, 59]
            }
        ]
    }
}
```

### Event Structure Enhancement

Each note event can optionally include track info:

```python
{
    'time': float,
    'note': int,
    'velocity': int,
    'type': str,  # 'on' or 'off'
    'led_index': int,
    'track': int,           # Track index
    'hand': str,            # 'right', 'left', 'both', 'unknown' 
    'track_name': str       # Track name for reference
}
```

## Implementation Steps

### Step 1: Add Track Analysis to MIDIParser

**File:** `backend/midi_parser.py`

Add method `_analyze_tracks()`:
- Extract track names from MIDI metadata
- Detect MIDI channels used in each track
- Analyze note ranges
- Classify each track as right/left/both/unknown

### Step 2: Enhance parse_file()

Update to include track information in metadata and events.

### Step 3: Update PlaybackService

Allow filtering/processing by hand:
- Option to play only right hand
- Option to play only left hand
- Option to apply different effects per hand

### Step 4: Frontend Integration (Future)

- Display hand information in UI
- Option to toggle left/right hand visibility
- Different colors for left vs right

## Hand Detection Algorithm

```
For each track:
  1. Extract track name
  2. Check name for explicit hand labels
     - If found (high confidence): return that hand
  
  3. Check all notes in track for MIDI channels
  4. If single primary channel: use channel convention
  
  5. Analyze note ranges
     - If all notes > MIDI 60: likely right hand
     - If all notes < MIDI 60: likely left hand
     - If mixed: likely both or complex arrangement
  
  6. If still unknown, use track order
     - First track: right hand (guess)
     - Last track: left hand (guess)
  
  Return: (hand, confidence, method)
```

## Hand Detection Patterns

### Pattern 1: Track Name
```
Names to check (case-insensitive):
- "right hand", "right", "rh", "treble", "melody"  → right
- "left hand", "left", "lh", "bass"                → left
- "piano", "combined", "all"                        → both
```

### Pattern 2: MIDI Channel
```
Convention (less reliable):
- Channel 0 or 1  → right hand (often default)
- Channel 2 or 3  → left hand (sometimes used)
```

### Pattern 3: Note Range
```
Reference: Middle C = MIDI 60

- Min note < 48 or Max note < 60  → likely left hand
- Min note > 60 or Max note > 96  → likely right hand
- Both ranges mixed               → both or complex
```

## Example MIDI Files

### Standard 2-Track Piano

```
Track 0: "Right Hand"
  - MIDI Channel: 0
  - Notes: 60-108 (C4 to C8)
  - Hand: right (confidence: 0.95, method: name)

Track 1: "Left Hand"
  - MIDI Channel: 0
  - Notes: 21-59 (A0 to B3)
  - Hand: left (confidence: 0.95, method: name)
```

### Complex Multi-Track

```
Track 0: "Piano" or "Melody"
  - Notes: 60-96
  - Hand: right (confidence: 0.7, method: range)

Track 1: "Bass" or "Accompaniment"
  - Notes: 21-55
  - Hand: left (confidence: 0.8, method: range + name)
```

## Fallback Behavior

If hand detection is uncertain:
- Include `confidence` score (0.0-1.0)
- Set `hand: 'unknown'` with low confidence
- Log the detection process
- Frontend can handle as appropriate

## Testing Strategy

Create test MIDI files with:
1. Explicit track names ("Right Hand", "Left Hand")
2. Different MIDI channels
3. Distinct note ranges
4. Mixed patterns
5. No track names or metadata

Verify detection for each pattern.

## Future Enhancements

1. **Machine Learning:** Train model to classify hands by note patterns
2. **User Overrides:** Allow manual track classification
3. **Settings Integration:** Store hand assignments in settings DB
4. **Playback Filtering:** Play only left/right hand on demand
5. **Different Effects:** Apply different LED effects per hand

## API Endpoints (Future)

```
GET /api/midi/track-info/<filename>
  Returns: Track analysis for uploaded MIDI file

POST /api/midi/play-hands/<filename>?hands=left
POST /api/midi/play-hands/<filename>?hands=right
POST /api/midi/play-hands/<filename>?hands=both
  Returns: Plays specific hand(s) from file
```

## Files to Modify

1. **backend/midi_parser.py**
   - Add `_analyze_tracks()` method
   - Add `_detect_track_hand()` method
   - Enhance `parse_file()` return value
   - Enhance event structure

2. **backend/playback_service.py** (future)
   - Add hand filtering logic
   - Add playback options for specific hands

3. **backend/config.py** (future)
   - Add hand detection configuration
   - Add hand preferences

## Success Criteria

✅ Accurately detect hand for 90%+ of standard piano MIDI files
✅ Provide confidence scores for each detection
✅ Log detection process for debugging
✅ Include hand info in all MIDI parsing responses
✅ Graceful fallback for ambiguous files
✅ No breaking changes to existing API

