# Multi-Track Hand Detection - Testing Guide

## Quick Test: Parse a MIDI File

Create `test_hand_detection.py`:

```python
#!/usr/bin/env python3
"""Test multi-track hand detection"""

import sys
import json
sys.path.insert(0, '/path/to/PianoLED-CoPilot')

from backend.midi_parser import MIDIParser
from backend.services.settings_service import SettingsService

# Initialize
settings = SettingsService()
parser = MIDIParser(settings_service=settings)

# Parse a MIDI file
try:
    result = parser.parse_file("path/to/your/file.mid")
    
    print("\n" + "="*60)
    print("MIDI FILE ANALYSIS")
    print("="*60)
    
    # Show metadata
    meta = result['metadata']
    print(f"\nFile: {meta.get('title', 'Unknown')}")
    print(f"Tempo: {meta['tempo']} BPM")
    print(f"Total Tracks: {meta['tracks']}")
    print(f"Total Events: {len(result['events'])}")
    print(f"Duration: {result['duration']/1000:.1f} seconds")
    
    # Show track info
    print("\n" + "-"*60)
    print("TRACK ANALYSIS")
    print("-"*60)
    
    for track in meta['track_info']:
        print(f"\nTrack {track['index']}: {track['name']}")
        print(f"  Hand: {track['hand'].upper()}")
        print(f"  Confidence: {track['confidence']:.0%} ({track['detection_method']})")
        print(f"  Notes: {track['note_count']}")
        print(f"  Range: MIDI {track['note_range'][0]}-{track['note_range'][1]}")
        if track['channels']:
            print(f"  Channels: {', '.join(map(str, track['channels']))}")
    
    # Show sample events
    print("\n" + "-"*60)
    print("SAMPLE EVENTS (first 5)")
    print("-"*60)
    
    for i, event in enumerate(result['events'][:5]):
        hand_str = f"({event['hand']})" if event.get('hand') else ""
        print(f"\n{i+1}. {event['time']}ms - {event['track_name']} {hand_str}")
        print(f"   Type: NOTE_{event['type'].upper()}")
        print(f"   MIDI Note: {event['note']} (LED {event['led_index']})")
        print(f"   Velocity: {event['velocity']}")
    
    # Summary
    print("\n" + "-"*60)
    print("SUMMARY")
    print("-"*60)
    
    hands = {}
    for event in result['events']:
        hand = event.get('hand', 'unknown')
        hands[hand] = hands.get(hand, 0) + 1
    
    print("\nNotes per hand:")
    for hand, count in sorted(hands.items()):
        print(f"  {hand.upper()}: {count} notes")
    
    print("\n" + "="*60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

## Test Files to Use

### Test 1: Standard Piano MIDI
**File:** Any standard piano MIDI with 2 tracks
**Expected:** 
- Track 0: "Right Hand" → right (95% confidence, name method)
- Track 1: "Left Hand" → left (95% confidence, name method)

**Sample files:**
- Moonlight Sonata (Beethoven)
- Fur Elise (Beethoven)
- Prelude in C Major (Bach - WTC)

### Test 2: No Track Names
**File:** MIDI with 2 tracks but no names
**Expected:**
- Detection by note range (75-85% confidence)
- Track 0: high notes → right
- Track 1: low notes → left

### Test 3: Single Track
**File:** Single track MIDI
**Expected:**
- Detection: "unknown" or fallback to range analysis
- Low confidence (30% at best)

### Test 4: Complex File
**File:** Orchestral or multi-instrument MIDI
**Expected:**
- Multiple tracks with varying hands
- Some "unknown" if non-piano tracks
- Various confidence levels

## Expected Log Output

For a good 2-track piano file:

```
INFO: Loaded MIDI file: moonlight_sonata.mid with 2 tracks
DEBUG: Track 0 detected as RIGHT by name: 'Right Hand'
DEBUG: Track 1 detected as LEFT by name: 'Left Hand'
Track 0: Right Hand | Hand: right (conf: 0.95, method: name) | Notes: 256 | Range: 60-108
Track 1: Left Hand | Hand: left (conf: 0.95, method: name) | Notes: 185 | Range: 21-59
INFO: Extracted 441 note events from 2 tracks with hand classification
```

## Verification Checklist

### Metadata Structure
```python
# Each track in track_info should have:
assert 'index' in track
assert 'name' in track
assert 'hand' in track  # NEW
assert 'confidence' in track  # NEW
assert 'detection_method' in track  # NEW
assert 'note_count' in track
assert 'note_range' in track
assert 'channels' in track  # NEW

assert track['hand'] in ['right', 'left', 'both', 'unknown']
assert 0.0 <= track['confidence'] <= 1.0
assert track['detection_method'] in ['name', 'channel', 'range', 'order', 'unknown']
```

### Event Structure
```python
# Each event should have:
assert 'time' in event
assert 'note' in event
assert 'velocity' in event
assert 'type' in event
assert 'led_index' in event
assert 'track' in event
assert 'track_name' in event  # NEW
assert 'hand' in event  # NEW

assert event['hand'] in ['right', 'left', 'both', 'unknown']
```

## Test Scenarios

### Scenario 1: Perfect Detection
```
Input: file with explicit "Right Hand" and "Left Hand" names
File format: Standard MIDI type 1, 2 tracks
Expected outcome:
  ✅ Track 0 detected as right (95% confidence, name method)
  ✅ Track 1 detected as left (95% confidence, name method)
  ✅ All events have correct hand classification
```

### Scenario 2: Range-Based Detection
```
Input: file with no track names, but clear high/low ranges
File format: Two distinct tracks
Expected outcome:
  ✅ High notes track detected as right (75% confidence, range method)
  ✅ Low notes track detected as left (75% confidence, range method)
  ✅ Some events may have "unknown" hand if ambiguous
```

### Scenario 3: Mixed Signals
```
Input: file with track name "Piano" + mixed note ranges
File format: Single or multiple tracks
Expected outcome:
  ⚠️ Hand detected as "both" (90% confidence, name method)
  ⚠️ If range contradicts: use name (higher priority)
  ⚠️ Some uncertainty in detection
```

### Scenario 4: Ambiguous File
```
Input: file with no name, single track, mixed notes
File format: Single track MIDI
Expected outcome:
  ⚠️ Hand detected as "unknown" (low confidence)
  ⚠️ Detection method: "unknown" or "order"
  ⚠️ Range analysis inconclusive
```

## Debugging

### Enable Debug Logging

```python
import logging
from backend.logging_config import get_logger

logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)

# Then parse
result = parser.parse_file("file.mid")
```

### Check Individual Track Detection

```python
# Manual test
hand, confidence, method = parser._detect_track_hand(
    track_name="Right Hand",
    note_range=(60, 108),
    track_channels={0},
    track_index=0,
    total_tracks=2
)
print(f"{hand} ({confidence:.0%}) via {method}")
# Expected: right (0.95) via name
```

### Verify Event Propagation

```python
# Check first few events have hand info
for i, event in enumerate(result['events'][:3]):
    assert 'hand' in event, f"Event {i} missing 'hand'"
    assert 'track_name' in event, f"Event {i} missing 'track_name'"
    print(f"Event {i}: {event['track_name']} ({event['hand']})")
```

## Common Issues

### Issue 1: All Tracks Detected as "unknown"

**Cause:** No track names, ambiguous note ranges, or single track

**Solution:**
1. Check file has multiple tracks
2. Check note ranges are distinct
3. Add track names to MIDI file if possible

**Debug:**
```python
meta = result['metadata']
print(f"Tracks: {meta['tracks']}")
print(f"Track info:")
for t in meta['track_info']:
    print(f"  {t['index']}: {t['hand']} ({t['confidence']:.1%}, {t['detection_method']})")
```

### Issue 2: Tracks Detected with Low Confidence

**Cause:** Ambiguous patterns or conflicting signals

**Solution:**
1. Check if file has explicit track names → rename if possible
2. Check note ranges → may need manual mapping

**Debug:**
```python
for track in result['metadata']['track_info']:
    if track['confidence'] < 0.7:
        print(f"Track {track['index']}: Low confidence detection")
        print(f"  Method: {track['detection_method']}")
        print(f"  Name: {track['name']}")
        print(f"  Notes: {track['note_range']}")
```

### Issue 3: Wrong Hand Detection

**Cause:** Track name has misleading text, or note range doesn't match actual hand

**Solution:**
1. Verify track name in original MIDI file
2. Check note range manually
3. May need to use "Both" instead of separating hands

**Debug:**
```python
track = result['metadata']['track_info'][0]
print(f"Track: {track['name']}")
print(f"Detected: {track['hand']} ({track['confidence']:.0%})")
print(f"Method: {track['detection_method']}")
print(f"Notes: {track['note_count']}, Range: {track['note_range']}")
```

## Performance Test

```python
import time
from backend.midi_parser import MIDIParser

parser = MIDIParser()

# Time parsing
files = ["file1.mid", "file2.mid", "file3.mid"]
for file in files:
    start = time.time()
    result = parser.parse_file(file)
    elapsed = time.time() - start
    
    print(f"{file}: {elapsed:.3f}s ({len(result['events'])} events)")
    # Expected: <1s for most files
```

## Integration Test

After implementing hand detection, test with PlaybackService:

```python
from backend.playback_service import PlaybackService
from backend.midi_parser import MIDIParser

parser = MIDIParser(settings_service=settings)
playback = PlaybackService(midi_parser=parser, ...)

# Start playback
playback.play_file("moonlight_sonata.mid")

# Check that events have hand info
# (would need to access internal state or add logging)
```

## Report Template

Use this when testing:

```
TEST REPORT: [MIDI File Name]
=================================

File Information:
- Name: [filename]
- Tracks: [count]
- Duration: [seconds]
- Total Notes: [count]

Track Detection Results:
- Track 0: [name]
  - Detected Hand: [right/left/both/unknown]
  - Confidence: [%]
  - Method: [name/range/channel/order]
  - Notes: [count], Range: [min-max]
  
- Track 1: [name]
  - Detected Hand: [right/left/both/unknown]
  - Confidence: [%]
  - Method: [name/range/channel/order]
  - Notes: [count], Range: [min-max]

Verdict: ✅ PASS / ⚠️ WARN / ❌ FAIL

Issues Found:
- [none / list any problems]

Notes:
- [any observations]
```

