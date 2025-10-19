# MIDI Tempo Processing - Visual Breakdown

## Current (BROKEN) Flow

```
┌─────────────────────────────────────────────────────────────┐
│ MIDI FILE: "Piano Sonata.mid" (Actually 180 BPM)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EXTRACT METADATA (extract_metadata)                         │
│                                                              │
│ Correctly reads:                                             │
│ • set_tempo message: 333333 µs/beat (= 180 BPM)  ✓          │
│ • Converts to: 180 BPM                             ✓          │
│                                                              │
│ Stores in: metadata = {tempo: 180, ...}           ✓          │
└─────────────────────────────────────────────────────────────┘
                          ↓
                    METADATA STORED
                    (NOT USED!)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CREATE NOTE SEQUENCE (create_note_sequence)                 │
│                                                              │
│ tempo = 500000  # ☝️ HARDCODED!                            │
│                 # Should read: 333333 from file             │
│                                                              │
│ For each event:                                              │
│   time_ms = (500000 µs / 1M) / ticks_per_beat               │
│           × event_ticks × 1000                              │
│                                                              │
│ Result: Calculates as if 120 BPM (not 180 BPM!)  ✗          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PLAYBACK SERVICE receives timing data                       │
│                                                              │
│ Duration: 2:40 (expected) → becomes 4:00 (wrong!)           │
│ Notes play too slow: 1.5x slower than intended              │
│ LED timing: Out of sync with MIDI notes                     │
│ USB MIDI output: Notes sent at wrong times                  │
└─────────────────────────────────────────────────────────────┘
```

## Fixed Flow

```
┌─────────────────────────────────────────────────────────────┐
│ MIDI FILE: "Piano Sonata.mid" (180 BPM)                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CREATE NOTE SEQUENCE (create_note_sequence)                 │
│                                                              │
│ EXTRACT TEMPO FIRST:                                        │
│ for track in midi_file.tracks:                             │
│     for msg in track:                                       │
│         if msg.type == 'set_tempo':                        │
│             tempo = msg.tempo  # 333333 µs/beat ✓          │
│             bpm = 60_000_000 / 333333 = 180 BPM ✓          │
│                                                              │
│ For each event:                                              │
│   time_ms = (333333 µs / 1M) / ticks_per_beat    ✓          │
│           × event_ticks × 1000                              │
│                                                              │
│ Result: Uses actual 180 BPM! ✓                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EXTRACT METADATA (extract_metadata)                         │
│ (now receives correct tempo context)                        │
│                                                              │
│ metadata = {tempo: 180, ...}  ✓                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PLAYBACK SERVICE receives timing data                       │
│                                                              │
│ Duration: 2:40 (expected) → becomes 2:40 (correct!) ✓      │
│ Notes play at correct speed ✓                               │
│ LED timing: Synced with MIDI notes ✓                        │
│ USB MIDI output: Notes sent at correct times ✓              │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Comparison

### BEFORE (Wrong)

```python
def _create_note_sequence(self, events, midi_file):
    ticks_per_beat = midi_file.ticks_per_beat
    tempo = 500000  # ❌ HARDCODED - ignores file tempo!
    
    timed_events = []
    for event in events:
        time_ms = self._ticks_to_milliseconds(
            event['time_ticks'], 
            ticks_per_beat, 
            tempo  # Always 500000!
        )
        # ... add to timed_events ...
    
    return timed_events
```

### AFTER (Correct)

```python
def _create_note_sequence(self, events, midi_file):
    ticks_per_beat = midi_file.ticks_per_beat
    
    # ✓ Extract actual tempo from MIDI file
    tempo = 500000  # Default: 120 BPM in microseconds per beat
    
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo  # Use actual tempo!
                bpm = int(60_000_000 / tempo)
                logger.info(f"Using MIDI tempo: {bpm} BPM ({tempo} µs/beat)")
                break
        if tempo != 500000:
            break  # Found tempo, stop searching
    
    timed_events = []
    for event in events:
        time_ms = self._ticks_to_milliseconds(
            event['time_ticks'], 
            ticks_per_beat, 
            tempo  # Now uses actual tempo! ✓
        )
        # ... add to timed_events ...
    
    return timed_events
```

**Difference**: ~8 lines added to extract and use actual tempo

---

## Tempo Conversion Reference

### BPM ↔ Microseconds Per Beat

```
Formula: µs_per_beat = 60_000_000 / BPM

Examples:
  40 BPM  → 1,500,000 µs (very slow)
  90 BPM  →   666,667 µs (slow)
  120 BPM →   500,000 µs (default/standard)
  140 BPM →   428,571 µs (moderate)
  180 BPM →   333,333 µs (fast)
  200 BPM →   300,000 µs (very fast)
```

### Tick Conversion

```
Given:
  Event: 960 ticks
  Ticks per beat: 480
  Tempo: 500000 µs/beat (120 BPM)

Calculation:
  seconds_per_tick = (500000 µs / 1,000,000) / 480
                   = 0.5 / 480
                   = 0.001042 seconds
  
  time_ms = 960 ticks × 0.001042 sec/tick × 1000 ms/sec
          = 1000 ms = 1 second

Change tempo to 180 BPM (333333 µs):
  seconds_per_tick = (333333 µs / 1,000,000) / 480
                   = 0.333 / 480
                   = 0.000694 seconds
  
  time_ms = 960 ticks × 0.000694 sec/tick × 1000 ms/sec
          = 667 ms ≈ 0.67 seconds (1.5x faster ✓)
```

---

## Real-World Impact Example

### Scenario: User plays "Jingle Bells" (180 BPM, 1:30 duration)

#### Current (Broken) System
```
File loaded: "Jingle Bells.mid"
Detected tempo: 180 BPM ✓ (stored in metadata)
Parsing tempo: 120 BPM ✗ (hardcoded)

Display shows: Duration 1:30
User clicks play...
LED visualization: ❌ Moves in slow-motion
MIDI keyboard: ❌ Notes arrive late
Playback actual duration: 2:15 (1.5x slower!)

User experience: "The file is broken, plays too slow"
```

#### After Fix
```
File loaded: "Jingle Bells.mid"
Detected tempo: 180 BPM ✓
Parsing tempo: 180 BPM ✓

Display shows: Duration 1:30
User clicks play...
LED visualization: ✓ Smooth, correct speed
MIDI keyboard: ✓ Notes arrive on time
Playback actual duration: 1:30 ✓

User experience: "Perfect! Sounds like the piano"
```

---

## Integration Points

### What Gets the Fixed Timing Data

1. **PlaybackService** (`backend/playback_service.py`)
   - Receives `parsed_data['events']` with correct `time` values
   - Uses for `_process_note_events()` timing
   - Affects MIDI output timing

2. **Frontend Display** (`frontend/src/routes/listen/+page.svelte`)
   - Receives `totalDuration` from API
   - Displays correct song length
   - Progress bar calculates correctly

3. **API Response** (`backend/app.py`)
   - Returns accurate `total_duration` in playback status
   - Frontend can calculate progress accurately

### No Breaking Changes
All downstream code already expects the same data structure:
```python
event = {
    'time': int,        # milliseconds ✓
    'note': int,        # MIDI note ✓
    'velocity': int,    # 0-127 ✓
    'type': str,        # 'on' or 'off' ✓
    'led_index': int    # LED position ✓
}
```

Only the `time` value changes (to be correct) - structure stays same.

---

## Summary Table

| Aspect | Current | Fixed |
|--------|---------|-------|
| Tempo extraction | ✓ Done | ✓ Done |
| Tempo storage | ✓ In metadata | ✓ In metadata |
| Tempo use in timing | ❌ Hardcoded | ✓ Used |
| Duration accuracy | ❌ 120 BPM only | ✓ All tempos |
| MIDI timing | ❌ Inaccurate | ✓ Accurate |
| LED sync | ❌ Out of sync | ✓ In sync |
| Code change | — | ~8 lines |
| Risk level | — | Very low |

---

**The fix is simple, safe, and high-impact.**
