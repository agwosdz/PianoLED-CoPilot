# Multi-Track Hand Detection - Implementation Complete

## Summary

Hand detection has been implemented in `backend/midi_parser.py` to classify MIDI tracks as left hand, right hand, both, or unknown based on multiple heuristics.

## What Was Changed

### 1. **New Methods in MIDIParser**

#### `_detect_track_hand()`
Detects if a track is for left/right hand using 4-level priority:

1. **Track Name** (highest priority, 95% confidence)
   - Looks for: "right", "left", "rh", "lh", "treble", "bass", etc.
   
2. **Note Range** (high priority, 75-85% confidence)
   - Notes below C3 (MIDI 48) → left hand
   - Notes above C5 (MIDI 72) → right hand
   - Mixed patterns → "both" or unknown
   
3. **MIDI Channels** (medium priority, 50% confidence)
   - Channels 0-1 → right hand (common convention)
   - Channels 2-3 → left hand (sometimes used)
   
4. **Track Order** (fallback, 30% confidence)
   - For 2-track files: first track = right, second = left

Returns: `(hand: str, confidence: float, detection_method: str)`

#### `_analyze_tracks()`
Analyzes all tracks in MIDI file and returns list of track info:

```python
{
    'index': 0,                          # Track number
    'name': 'Right Hand',                # Track name from MIDI
    'channels': [0, 1],                  # MIDI channels used
    'hand': 'right',                     # Detected hand
    'confidence': 0.95,                  # 0.0-1.0 confidence
    'detection_method': 'name',          # How it was detected
    'note_count': 128,                   # Number of notes
    'note_range': [60, 108]              # Min and max notes
}
```

### 2. **Enhanced Data Structures**

#### Note Events Now Include
```python
{
    'time': 1000,           # milliseconds
    'note': 60,             # MIDI note
    'velocity': 100,        # Velocity
    'type': 'on',           # 'on' or 'off'
    'led_index': 30,        # LED position
    'track': 0,             # Track index
    'track_name': 'Right Hand',  # Track name
    'hand': 'right'         # Hand classification
}
```

#### Metadata Now Includes
```python
'metadata': {
    'tracks': 2,
    'track_info': [
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
```

### 3. **Updated Methods**

- `parse_file()` - Now calls `_analyze_tracks()` before extracting events
- `_extract_note_events()` - Now accepts `track_info` parameter and tags events with hand info
- `_create_note_sequence()` - Preserves `track_name` and `hand` from events
- `_extract_metadata()` - Now accepts `track_info` parameter and includes it in metadata

## API Response Example

```json
{
  "duration": 45000,
  "metadata": {
    "tracks": 2,
    "ticks_per_beat": 480,
    "type": 1,
    "title": "Moonlight Sonata",
    "tempo": 120,
    "track_info": [
      {
        "index": 0,
        "name": "Right Hand",
        "channels": [0],
        "hand": "right",
        "confidence": 0.95,
        "detection_method": "name",
        "note_count": 256,
        "note_range": [60, 108]
      },
      {
        "index": 1,
        "name": "Left Hand",
        "channels": [1],
        "hand": "left",
        "confidence": 0.95,
        "detection_method": "name",
        "note_count": 185,
        "note_range": [21, 59]
      }
    ]
  },
  "events": [
    {
      "time": 100,
      "note": 76,
      "velocity": 80,
      "type": "on",
      "led_index": 55,
      "track": 0,
      "track_name": "Right Hand",
      "hand": "right"
    },
    {
      "time": 150,
      "note": 36,
      "velocity": 60,
      "type": "on",
      "led_index": 15,
      "track": 1,
      "track_name": "Left Hand",
      "hand": "left"
    }
  ]
}
```

## Hand Detection Patterns

### Pattern 1: Track Name (Most Reliable)

**Right hand patterns:**
- "Right Hand"
- "Right"
- "RH"
- "Treble"
- "Melody"
- "Soprano"

**Left hand patterns:**
- "Left Hand"
- "Left"
- "LH"
- "Bass"
- "Bass Line"
- "Alto"

**Both patterns:**
- "Piano"
- "Both"
- "Combined"
- "Full"

**Example files:**
```
Track 0: "Right Hand" → right (95% confidence)
Track 1: "Left Hand"  → left (95% confidence)
```

### Pattern 2: Note Range (Reliable)

Uses MIDI note ranges with Middle C (MIDI 60) as reference:

| Note Range | Detection | Confidence |
|-----------|-----------|-----------|
| All below C3 (48) | Left hand | 85% |
| All above C5 (72) | Right hand | 85% |
| Mostly lower | Left hand | 75% |
| Mostly upper | Right hand | 75% |
| Mixed | Both/Unknown | Low |

**Example files:**
```
Track 0: Notes 60-108 (all upper) → right (85% confidence)
Track 1: Notes 21-59 (all lower) → left (85% confidence)
```

### Pattern 3: MIDI Channel (Less Reliable)

```
Channels 0-1 → right hand (50% confidence)
Channels 2-3 → left hand (50% confidence)
```

### Pattern 4: Track Order (Fallback)

```
2-track MIDI file:
- Track 0 → right hand (30% confidence)
- Track 1 → left hand (30% confidence)
```

## Logging Output

When parsing a 2-track MIDI file:

```
INFO: Loaded MIDI file: moonlight_sonata.mid with 2 tracks
Track 0: Right Hand | Hand: right (conf: 0.95, method: name) | Notes: 256 | Range: 60-108
Track 1: Left Hand | Hand: left (conf: 0.95, method: name) | Notes: 185 | Range: 21-59
INFO: Extracted 441 note events from 2 tracks with hand classification
```

## Testing

### Test Case 1: Standard 2-Track Piano
```
Input: Moonlight Sonata with explicit "Right Hand" and "Left Hand" track names
Expected: 95% confidence, "name" method
```

### Test Case 2: No Track Names, Clear Note Ranges
```
Input: Bach file with 2 tracks, no names, clear high/low ranges
Expected: 75-85% confidence, "range" method
```

### Test Case 3: Single Track
```
Input: Single track MIDI file
Expected: "unknown" with low confidence (30% at best via order)
```

### Test Case 4: Complex Multi-Track
```
Input: Orchestral MIDI with 10+ tracks, mixed purposes
Expected: Confidence varies by track, may be "unknown" for percussion/strings
```

## Future Enhancements

### 1. **Playback Filtering**
Add endpoints to play only specific hands:
```
POST /api/playback/hand?hand=right  # Play only right hand
POST /api/playback/hand?hand=left   # Play only left hand
```

### 2. **Different Effects Per Hand**
- Right hand: Blue LEDs
- Left hand: Red LEDs
- Both: Green LEDs

### 3. **Settings Integration**
Store hand preferences in settings database:
- Allow users to override detected hands
- Save custom mappings

### 4. **Machine Learning**
Train classifier on note patterns to improve detection accuracy.

### 5. **Frontend Display**
Show hand information in UI:
```
File: Moonlight Sonata (2 tracks)
- Track 0: Right Hand (95% confident) [60-108]
- Track 1: Left Hand (95% confident) [21-59]
```

## Code Statistics

**Lines added:** ~150
**Lines modified:** 4 method signatures
**New methods:** 2 (`_detect_track_hand`, `_analyze_tracks`)
**Breaking changes:** None (all additions are backward compatible)
**Syntax:** ✅ Verified

## Backward Compatibility

✅ **Fully backward compatible** - existing code will continue to work:
- Old callers can ignore new `hand` and `track_name` fields in events
- Old callers can ignore new `track_info` in metadata
- All changes are additive, no fields were removed or renamed

## Next Steps

1. **Test with real MIDI files**
   - Standard piano pieces (2 tracks)
   - Complex orchestral files
   - Single-track files
   
2. **Integration with PlaybackService**
   - Could add filtering by hand
   - Could apply different colors/effects per hand

3. **Frontend Integration**
   - Display hand info in UI
   - Show confidence levels
   - Allow toggling left/right hand visibility

4. **Database Storage**
   - Store detected hands in settings
   - Allow user corrections
   - Build up training data for ML

## Files Modified

1. `backend/midi_parser.py` - Main implementation
   - Added 2 new methods
   - Updated 4 method signatures
   - Enhanced event and metadata structures

## Verification

✅ **Syntax Check:** `python -m py_compile backend/midi_parser.py` - PASSED
✅ **Type Hints:** All methods properly annotated
✅ **Logging:** Comprehensive debug and info logging
✅ **Documentation:** Docstrings for all new methods

## Example Usage

```python
from backend.midi_parser import MIDIParser

parser = MIDIParser(settings_service=settings)
result = parser.parse_file("moonlight_sonata.mid")

# Access track info
for track in result['metadata']['track_info']:
    print(f"Track {track['index']}: {track['name']}")
    print(f"  Hand: {track['hand']} ({track['confidence']:.1%} confidence)")
    print(f"  Notes: {track['note_count']}")
    print(f"  Range: {track['note_range']}")

# Access events with hand info
for event in result['events'][:5]:
    print(f"Time {event['time']}ms: {event['track_name']} ({event['hand']}) - Note {event['note']}")
```

