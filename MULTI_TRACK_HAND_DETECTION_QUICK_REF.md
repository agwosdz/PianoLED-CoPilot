# Multi-Track Hand Detection - Quick Reference

## What's New

Multi-track MIDI files now automatically detect which track represents the left hand vs right hand.

## Detection Methods (Priority Order)

| Priority | Method | Pattern | Confidence | Example |
|----------|--------|---------|-----------|---------|
| 1 | Track Name | "Right Hand", "Left Hand", "RH", "LH", "Treble", "Bass" | 95% | "Right Hand" → right |
| 2 | Note Range | High notes (>72) → right, Low notes (<48) → left | 75-85% | All notes C5-C8 → right |
| 3 | MIDI Channel | Channel 0-1 → right, Channel 2-3 → left | 50% | Channel 0 → right |
| 4 | Track Order | First track → right, Last track → left | 30% | 2-track file, track 0 → right |

## New Fields in API Response

### Metadata (metadata.track_info)
```json
{
  "index": 0,
  "name": "Right Hand",
  "hand": "right",                    // NEW: 'right', 'left', 'both', 'unknown'
  "confidence": 0.95,                 // NEW: 0.0-1.0
  "detection_method": "name",         // NEW: how it was detected
  "note_count": 256,
  "note_range": [60, 108],
  "channels": [0]                     // NEW: MIDI channels
}
```

### Events (metadata.events)
```json
{
  "time": 1000,
  "note": 60,
  "velocity": 100,
  "type": "on",
  "led_index": 30,
  "track": 0,
  "track_name": "Right Hand",         // NEW
  "hand": "right"                     // NEW: hand classification
}
```

## Code Changes Summary

**File Modified:** `backend/midi_parser.py`

**New Methods:**
- `_detect_track_hand()` - Determines hand for a track
- `_analyze_tracks()` - Analyzes all tracks for hand classification

**Modified Methods:**
- `parse_file()` - Now calls track analysis
- `_extract_note_events()` - Now receives track info, adds hand to events
- `_create_note_sequence()` - Preserves hand info in events
- `_extract_metadata()` - Now includes track analysis

**Breaking Changes:** None (backward compatible)

## Detection Examples

### Example 1: Clear Track Names
```
Track 0: "Right Hand"
  → hand: 'right', confidence: 0.95, method: 'name'

Track 1: "Left Hand"
  → hand: 'left', confidence: 0.95, method: 'name'
```

### Example 2: Range-Based Detection
```
Track 0: Notes 60-108 (all upper range)
  → hand: 'right', confidence: 0.85, method: 'range'

Track 1: Notes 21-59 (all lower range)
  → hand: 'left', confidence: 0.85, method: 'range'
```

### Example 3: Mixed/Unclear
```
Track 0: "Piano", Notes 30-90 (full range)
  → hand: 'both', confidence: 0.90, method: 'name'

Track 1: "Strings", Notes 50-100 (not piano)
  → hand: 'unknown', confidence: 0.0, method: 'unknown'
```

## Typical Log Output

```
INFO: Loaded MIDI file: file.mid with 2 tracks
Track 0: Right Hand | Hand: right (conf: 0.95, method: name) | Notes: 256 | Range: 60-108
Track 1: Left Hand | Hand: left (conf: 0.95, method: name) | Notes: 185 | Range: 21-59
INFO: Extracted 441 note events from 2 tracks with hand classification
```

## Using Hand Information

### In Frontend
```javascript
// Display hand info
const metadata = response.metadata;
for (const track of metadata.track_info) {
  console.log(`${track.name}: ${track.hand} (${(track.confidence*100).toFixed(0)}% confident)`);
}

// Filter events by hand
const rightHandEvents = response.events.filter(e => e.hand === 'right');
const leftHandEvents = response.events.filter(e => e.hand === 'left');
```

### In Backend
```python
# Access hand info
result = parser.parse_file("file.mid")

for track in result['metadata']['track_info']:
    print(f"{track['name']}: {track['hand']}")

# Filter events by hand
right_hand = [e for e in result['events'] if e.get('hand') == 'right']
left_hand = [e for e in result['events'] if e.get('hand') == 'left']
```

## Confidence Levels

| Confidence | Interpretation |
|-----------|-----------------|
| 0.95 | Very confident (explicit track name) |
| 0.90 | Confident (explicit marker like "Piano" + name) |
| 0.85 | Quite confident (clear note range patterns) |
| 0.75 | Moderately confident (mixed but clear patterns) |
| 0.50 | Low confidence (MIDI channel based) |
| 0.30 | Very low (fallback to track order) |
| 0.00 | Unknown (unable to determine) |

## Common Patterns

### Pattern 1: Beethoven Moonlight Sonata
```
Track 0: "Right Hand" (notes 60-108)
  → right, 95% confidence, name method

Track 1: "Left Hand" (notes 21-59)
  → left, 95% confidence, name method
```

### Pattern 2: Bach Prelude (No Names)
```
Track 0: Unlabeled (notes 60-100, mostly high)
  → right, 85% confidence, range method

Track 1: Unlabeled (notes 20-50, mostly low)
  → left, 85% confidence, range method
```

### Pattern 3: Single Track File
```
Track 0: "Piano Piece" (notes 25-110, full range)
  → both, 90% confidence, name method
```

### Pattern 4: Complex File
```
Track 0: "Strings" (notes 48-85)
  → unknown, 0% confidence, unknown method

Track 1: "Piano RH" (notes 60-108)
  → right, 95% confidence, name method

Track 2: "Piano LH" (notes 21-59)
  → left, 95% confidence, name method
```

## Future Use Cases

### 1. Different Colors Per Hand
```
- Right hand: Blue LEDs
- Left hand: Red LEDs
- Both: Green LEDs
```

### 2. Separate Playback
```
Play only right hand: POST /api/playback/hand?hand=right
Play only left hand: POST /api/playback/hand?hand=left
Play both (default): POST /api/playback/hand?hand=both
```

### 3. UI Display
```
File: Moonlight Sonata (2 tracks, 95% confident)
├─ Right Hand (95% confident)
└─ Left Hand (95% confident)

[◇] Show Right Hand  [◇] Show Left Hand
```

### 4. Learning System
Track which detections were correct vs incorrect to improve algorithm.

## Backward Compatibility

✅ **Fully backward compatible**
- Old code ignoring `hand` and `track_name` fields continues to work
- All additions are new fields, no removals or renames
- Existing playback functionality unchanged

## Testing

Quick test:
```bash
cd /path/to/PianoLED-CoPilot
python3 -c "
from backend.midi_parser import MIDIParser
p = MIDIParser()
r = p.parse_file('path/to/file.mid')
for t in r['metadata']['track_info']:
    print(f\"{t['name']}: {t['hand']} ({t['confidence']:.0%})\")
"
```

See `MULTI_TRACK_HAND_DETECTION_TEST.md` for comprehensive test guide.

## Implementation Details

**Files:** `backend/midi_parser.py`
**Lines Added:** ~150
**Syntax:** ✅ Verified
**Type Hints:** ✅ Complete
**Logging:** ✅ Debug and Info levels

## Summary

Hand detection automatically classifies MIDI tracks as:
- `'right'` - Right hand (upper notes)
- `'left'` - Left hand (lower notes)
- `'both'` - Both hands (full keyboard)
- `'unknown'` - Unable to determine

Each classification includes a confidence score (0.0-1.0) and the detection method used.

All MIDI events and metadata now include hand information for flexible playback control and visualization.

