# MIDI File Processing Analysis - Tempo & Timing Handling

## Executive Summary

**Current Status**: ⚠️ **CRITICAL ISSUE FOUND**

Tempo from MIDI files is **NOT being used** during playback. The parser extracts tempo metadata but never applies it during timing calculations.

---

## Current MIDI Processing Flow

### 1. **File Parsing** (`backend/midi_parser.py`)

```
MIDI File (binary)
    ↓
Load with mido.MidiFile()
    ↓
Extract Note Events (_extract_note_events)
├─ Iterate all tracks
├─ Extract note_on/note_off messages with MIDI ticks
└─ Returns events with time_ticks (NOT milliseconds yet)
    ↓
Create Note Sequence (_create_note_sequence)
├─ Gets ticks_per_beat from MIDI file ✓
├─ Gets tempo (DEFAULT 500000 µs = 120 BPM) ❌ NOT EXTRACTED
├─ Converts ticks → milliseconds using _ticks_to_milliseconds()
└─ Returns events with absolute time in milliseconds
    ↓
Extract Metadata (_extract_metadata)
├─ Reads tracks count ✓
├─ Reads ticks_per_beat ✓
├─ Reads set_tempo meta messages ✓
└─ Converts to BPM ✓ (200-300 lines down, not used in conversion!)
    ↓
Return parsed data
└─ metadata.tempo available but NEVER USED
```

### 2. **The Problem: Hardcoded Default Tempo**

In `midi_parser.py` line 203-204:

```python
def _create_note_sequence(self, events, midi_file):
    # ... existing code ...
    tempo = 500000  # Default tempo (120 BPM) in microseconds per beat
    # ☝️ HARDCODED! Never reads actual tempo from file
```

This means:
- All MIDI files are treated as **120 BPM** regardless of actual tempo
- Tempo changes in the MIDI file are ignored
- A file with tempo marking of 180 BPM plays at 120 BPM

---

## Where Tempo IS Extracted (But Not Used)

### `_extract_metadata()` at line 279-307:

```python
def _extract_metadata(self, midi_file):
    metadata = {
        'tracks': len(midi_file.tracks),
        'ticks_per_beat': midi_file.ticks_per_beat,
        'type': midi_file.type,
        'title': None,
        'tempo': 120  # Default BPM
    }
    
    # Extract title and tempo from meta messages
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'track_name' and not metadata['title']:
                metadata['title'] = msg.name
            elif msg.type == 'set_tempo':
                # Convert microseconds per beat to BPM
                metadata['tempo'] = int(60_000_000 / msg.tempo)  # ✓ CORRECT
                break
    
    return metadata
```

✓ This code **correctly** extracts tempo  
✗ But it's **completely disconnected** from the timing conversion logic

---

## How Timing Conversion Works

### Current (Wrong) Way:

```python
def _ticks_to_milliseconds(self, ticks, ticks_per_beat, tempo):
    # tempo = 500000 (hardcoded as 120 BPM)
    seconds_per_tick = (tempo / 1_000_000) / ticks_per_beat
    return int(ticks * seconds_per_tick * 1000)

# Example: File with 180 BPM
# But tempo parameter is always 500000 (120 BPM default)
# Result: File plays 1.5x SLOWER than it should
```

### How It Should Work:

```python
# 1. Extract tempo from MIDI file first
set_tempo_msg = find_set_tempo_message(midi_file)
if set_tempo_msg:
    tempo = set_tempo_msg.tempo  # Microseconds per beat
else:
    tempo = 500000  # Default 120 BPM

# 2. Use extracted tempo for all timing calculations
time_ms = self._ticks_to_milliseconds(event_ticks, ticks_per_beat, tempo)
```

---

## Impact & Symptoms

### What Users Experience:

| MIDI File Tempo | Expected | Actual | Result |
|---|---|---|---|
| 120 BPM | 4:00 min | 4:00 min | ✓ Correct |
| 180 BPM | 2:40 min | 4:00 min | ✗ 1.5x SLOWER |
| 90 BPM | 5:20 min | 4:00 min | ✗ 1.33x FASTER |
| Tempo changes | Variable | 120 BPM fixed | ✗ Ignores changes |

### Affected Areas:

1. ❌ **Playback Timing** - Wrong duration and speed
2. ❌ **MIDI Output** - Notes sent at wrong times
3. ❌ **LED Timing** - LEDs light up out of sync with audio
4. ❌ **Pause/Resume** - Position calculations wrong
5. ⚠️ **Metadata** - Duration returned is incorrect

---

## The Fix Required

### Step 1: Extract Tempo Early

Modify `_create_note_sequence()` to:

```python
def _create_note_sequence(self, events, midi_file):
    ticks_per_beat = midi_file.ticks_per_beat
    
    # EXTRACT TEMPO FROM MIDI FILE
    tempo = 500000  # Default: 120 BPM in microseconds per beat
    
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo  # Microseconds per beat
                logger.info(f"Extracted tempo from MIDI: {tempo} µs/beat = {int(60_000_000 / tempo)} BPM")
                break
        if tempo != 500000:
            break  # Found tempo, stop looking
    
    # Convert events using ACTUAL tempo
    timed_events = []
    for event in events:
        time_ms = self._ticks_to_milliseconds(
            event['time_ticks'], 
            ticks_per_beat, 
            tempo  # Use extracted tempo, not default!
        )
        # ... rest of conversion ...
```

### Step 2: Handle Tempo Changes (Advanced)

MIDI files can have multiple `set_tempo` messages. For advanced support:

```python
def _create_note_sequence(self, events, midi_file):
    # Extract all tempo changes with their timing
    tempo_changes = []
    
    for track in midi_file.tracks:
        current_time = 0
        for msg in track:
            current_time += msg.time
            if msg.type == 'set_tempo':
                tempo_changes.append({
                    'time_ticks': current_time,
                    'tempo': msg.tempo,
                    'bpm': int(60_000_000 / msg.tempo)
                })
    
    # Sort by time
    tempo_changes.sort(key=lambda x: x['time_ticks'])
    
    # Apply appropriate tempo to each event
    current_tempo = 500000  # Default
    tempo_idx = 0
    
    for event in events:
        # Find active tempo at this event's time
        while (tempo_idx < len(tempo_changes) and 
               tempo_changes[tempo_idx]['time_ticks'] <= event['time_ticks']):
            current_tempo = tempo_changes[tempo_idx]['tempo']
            tempo_idx += 1
        
        # Use active tempo for this event
        time_ms = self._ticks_to_milliseconds(
            event['time_ticks'],
            ticks_per_beat,
            current_tempo
        )
        # ...
```

---

## Files Affected by Fix

### `backend/midi_parser.py`
- **Function**: `_create_note_sequence()` (line 194-234)
- **Change**: Extract `set_tempo` message before timing conversion
- **Impact**: All MIDI files parsed with correct tempo

### Related Files (No Changes Needed)

| File | Usage | Status |
|------|-------|--------|
| `backend/playback_service.py` | Uses parsed events | ✓ OK (receives corrected timings) |
| `backend/app.py` | API endpoints | ✓ OK (uses parser output) |
| `frontend` | Displays duration | ✓ OK (uses corrected duration) |

---

## Testing the Fix

### Test Case 1: Standard Tempo

```python
# Create MIDI with 120 BPM (set_tempo = 500000 µs)
# Should match current behavior
result = parser.parse_file('120bpm_file.mid')
assert result['metadata']['tempo'] == 120
assert result['duration'] == expected_duration  # Should match current
```

### Test Case 2: Fast Tempo

```python
# Create MIDI with 180 BPM (set_tempo = 333333 µs)
result = parser.parse_file('180bpm_file.mid')
assert result['metadata']['tempo'] == 180
# Duration should be 2/3 of 120 BPM version
assert result['duration'] == (expected_duration * 120 / 180)
```

### Test Case 3: Slow Tempo

```python
# Create MIDI with 90 BPM (set_tempo = 666666 µs)
result = parser.parse_file('90bpm_file.mid')
assert result['metadata']['tempo'] == 90
# Duration should be 4/3 of 120 BPM version
assert result['duration'] == (expected_duration * 120 / 90)
```

### Test Case 4: Tempo Changes

```python
# Create MIDI with multiple set_tempo messages
# Should handle transitions correctly
result = parser.parse_file('tempo_changes.mid')
# Event times should reflect tempo changes
```

---

## Implementation Priority

### CRITICAL (Fix Now)
- ✗ Hardcoded tempo in `_create_note_sequence()`
- Impact: All MIDI files have wrong timing
- Time to fix: ~15 minutes

### HIGH (After Critical)
- ⚠️ Add unit tests for tempo handling
- Add logging for extracted tempo
- Document tempo behavior

### NICE TO HAVE
- Tempo change support (mid-file tempo changes)
- UI display of detected tempo vs playback tempo
- Tempo override UI control

---

## Summary

### Current State
```
MIDI File has 180 BPM
    ↓
Parser extracts & logs it (in metadata)
    ↓
But uses hardcoded 120 BPM for timing
    ↓
Result: File plays 1.5x SLOWER
```

### After Fix
```
MIDI File has 180 BPM
    ↓
Parser extracts tempo early
    ↓
Uses actual tempo (180 BPM) for timing
    ↓
Result: File plays at correct speed ✓
```

### Code Complexity
- **Current**: 1 place (hardcoded)
- **After Fix**: 1-2 lines changed in 1 function
- **With Tempo Changes**: ~20 additional lines

This is a **simple, high-impact fix** that requires minimal code changes.

---

**Status**: Ready to implement once approved.
