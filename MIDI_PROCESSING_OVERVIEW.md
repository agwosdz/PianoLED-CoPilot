# MIDI Processing - Comprehensive Overview

## Quick Answer to Your Question

> "How are we processing midi files, are we taking tempo, etc into account?"

**Short Answer**: 
- ✓ Tempo IS being extracted from MIDI files
- ✗ But it's NOT being used for timing calculations
- ✗ All files treated as 120 BPM regardless of actual tempo

**Impact**: Files play at wrong speed if tempo differs from 120 BPM

---

## What IS Being Processed Correctly

### 1. **Note Extraction** ✓
```
✓ Extracts note_on events with velocity
✓ Extracts note_off events  
✓ Handles multiple tracks
✓ Filters out-of-range notes
✓ Removes orphaned note_ons (without note_offs)
```

### 2. **LED Mapping** ✓
```
✓ Maps MIDI notes to piano keys (21-108 for 88-key)
✓ Maps piano keys to LED positions
✓ Handles LED orientation (normal/reversed)
✓ Supports different piano sizes (25/49/61/76/88-key)
```

### 3. **Multi-Track Support** ✓
```
✓ Merges all tracks into single timeline
✓ Sorts events by time
✓ Handles events from different tracks
```

### 4. **Velocity Handling** ✓
```
✓ Preserves MIDI velocity values (0-127)
✓ Uses velocity for LED brightness
✓ Applies volume multiplier in playback
✓ Sends velocity to USB MIDI output
```

### 5. **Note Duration Calculation** ✓
```
✓ Tracks note_on time
✓ Tracks note_off time
✓ Calculates duration = note_off - note_on
✓ Handles minimum duration (0.1s)
✓ Handles orphaned notes
```

### 6. **Metadata Extraction** ✓
```
✓ File format (Type 0/1/2)
✓ Track count
✓ Ticks per beat (PPQ)
✓ Title from track_name meta message
✓ TEMPO from set_tempo meta message ← Extracted but not used!
```

---

## What is NOT Being Processed Correctly

### 1. **TEMPO USAGE** ✗

**Extracted**: Yes, `_extract_metadata()` finds `set_tempo` messages  
**Stored**: Yes, in `metadata['tempo']` as BPM  
**Used**: No! Timing calculations hardcoded to 120 BPM

```python
# In _create_note_sequence() line 203:
tempo = 500000  # ← ALWAYS 120 BPM, never changed!
```

**Result**: 
- File with 180 BPM plays 1.5x SLOWER
- File with 90 BPM plays 1.33x FASTER
- Duration display incorrect
- MIDI output timing wrong

### 2. **TEMPO CHANGES** ✗

**Support Level**: None currently

**What This Means**:
- MIDI files with multiple `set_tempo` messages only use first one
- Or actually, they use hardcoded 120 BPM (see above)
- Files with gradual tempo changes ignored

**Affected Files**: 
- Orchestral pieces with tempo variations
- Modern compositions with tempo changes
- Anything other than constant-tempo piano pieces

---

## Processing Pipeline (Visual)

```
┌─────────────────────────────────────────┐
│ 1. Load MIDI File                       │
│    mido.MidiFile(file_path)             │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 2. Extract Note Events (✓ WORKS)        │
│    - Iterate all tracks                 │
│    - Find note_on/note_off messages     │
│    - Store with MIDI ticks timing       │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 3. Create Note Sequence (✗ BROKEN)      │
│    - Convert ticks → milliseconds       │
│    - Uses HARDCODED 120 BPM tempo       │
│    - Should use ACTUAL file tempo       │
│    - Map notes to LED indices           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 4. Extract Metadata (✓ WORKS)           │
│    - Read set_tempo message ✓           │
│    - Convert to BPM ✓                   │
│    - Store in metadata ✓                │
│    - BUT not used in step 3 ✗           │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 5. Return Parsed Data                   │
│    {                                    │
│      'events': [...]  ← wrong timing!   │
│      'duration': int  ← incorrect!      │
│      'metadata': {                      │
│        'tempo': 120   ← available       │
│        ...            but not used!     │
│      }                                  │
│    }                                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ 6. Playback Service Uses Data           │
│    Receives events with wrong timing    │
│    LED visualization: Wrong speed       │
│    MIDI output: Wrong timing            │
│    Duration: Incorrect                  │
└─────────────────────────────────────────┘
```

---

## Files Involved in Processing

### `backend/midi_parser.py` (Main Parser)

**Functions**:

| Function | Purpose | Status |
|----------|---------|--------|
| `__init__()` | Initialize with piano specs | ✓ OK |
| `parse_file()` | Main entry point | ✗ OK (returns wrong timing) |
| `_extract_note_events()` | Get note messages | ✓ OK |
| `_create_note_sequence()` | Convert to milliseconds | ✗ **BROKEN** |
| `_ticks_to_milliseconds()` | Tick → ms conversion | ✓ OK (but wrong input) |
| `_map_note_to_led()` | MIDI note → LED index | ✓ OK |
| `_extract_metadata()` | Get file metadata | ✓ OK (unused result) |
| `validate_file()` | Check valid MIDI | ✓ OK |

### `backend/playback_service.py` (Uses Parsed Data)

**Receives**:
```python
parsed_data = {
    'events': [...],      # Contains events with millisecond times
    'duration': int,      # Total duration in milliseconds  
    'metadata': {...}     # Includes tempo (not used)
}
```

**Usage**:
- Stores events in `self._note_events`
- Uses `event.time` for playback scheduling
- All timing calculations assume correct millisecond values
- No tempo recalculation

**Issue**: Receives incorrect timing (because parser used wrong tempo)

### `backend/app.py` (API)

**Returns timing data**:
```python
{
    'state': '...',
    'filename': '...',
    'total_duration': duration_from_parser,  # Wrong if file not 120 BPM
    'current_time': ...,
    'error_message': ...
}
```

**Frontend Display**: Uses `total_duration` to show file length

---

## What SHOULD Happen vs What DOES Happen

### Scenario: Load 180 BPM MIDI file (2:40 actual duration)

**What SHOULD Happen**:
```
File loaded → Parser finds set_tempo = 180 BPM
           → Converts ticks using 180 BPM
           → Returns duration = 160,000 ms (2:40)
           → Playback at 180 BPM
           → Duration display: 2:40 ✓
```

**What ACTUALLY Happens**:
```
File loaded → Parser finds set_tempo = 180 BPM
           → Converts ticks using 120 BPM (hardcoded!) ✗
           → Returns duration = 240,000 ms (4:00) ✗
           → Playback at 120 BPM speed ✗
           → Duration display: 4:00 ✗
```

**User Observes**:
- File shows 4:00 instead of 2:40
- Playback is super slow-motion
- LEDs move too slow
- MIDI keyboard notes arrive late

---

## Code Locations

### Where Tempo IS Extracted

**File**: `backend/midi_parser.py`  
**Function**: `_extract_metadata()` (line 279-307)  
**Code**:
```python
elif msg.type == 'set_tempo':
    metadata['tempo'] = int(60_000_000 / msg.tempo)
```
✓ This works correctly

### Where Tempo SHOULD Be Used

**File**: `backend/midi_parser.py`  
**Function**: `_create_note_sequence()` (line 194-234)  
**Code**:
```python
tempo = 500000  # ← Should be: Extract from MIDI file
```
✗ This is hardcoded

### Where Tempo IS Stored (But Unused)

**File**: `backend/midi_parser.py`  
**Function**: `_extract_metadata()` returns to `parse_file()`  
**Result**: 
```python
return {
    'duration': ...,
    'events': ...,
    'metadata': {'tempo': 120, ...}  # ← Not used anywhere!
}
```

---

## Related Configuration (That IS Working)

### Piano Size Configuration
```python
# Correctly reads from settings
piano_size = settings.get_setting('piano', 'size')  # e.g., '88-key'
specs = _get_piano_specs(piano_size)                # Gets MIDI range
self.min_midi_note = specs['midi_start']            # e.g., 21
self.max_midi_note = specs['midi_end']              # e.g., 108
```
✓ This works - tempo extraction follows same pattern

### LED Orientation
```python
self.led_orientation = settings.get_setting('led', 'led_orientation')
```
✓ This works - used in playback service

### LED Count
```python
self.led_count = settings.get_setting('led', 'led_count')
```
✓ This works - used in note mapping

---

## Summary Findings

| Aspect | Processed? | Correct? | Used? |
|--------|-----------|----------|-------|
| MIDI note numbers | ✓ Yes | ✓ Yes | ✓ Yes |
| Note velocity | ✓ Yes | ✓ Yes | ✓ Yes |
| Note duration | ✓ Yes | ✓ Yes | ✓ Yes |
| LED mapping | ✓ Yes | ✓ Yes | ✓ Yes |
| **Tempo/BPM** | ✓ Yes | ✗ No | ✗ No |
| Track merging | ✓ Yes | ✓ Yes | ✓ Yes |
| File metadata | ✓ Yes | ✓ Yes | Partially |

---

## Documentation Files Created

1. **`MIDI_TEMPO_ANALYSIS.md`** - Deep technical analysis
2. **`MIDI_TEMPO_VISUAL_GUIDE.md`** - Visual diagrams and examples  
3. **`MIDI_TEMPO_FIX_READY.md`** - Implementation-ready fix code
4. **This file** - Comprehensive overview

---

## Next Steps

### If You Want to Fix This Now
→ See `MIDI_TEMPO_FIX_READY.md` for code ready to implement

### If You Want More Details
→ See `MIDI_TEMPO_ANALYSIS.md` for comprehensive analysis  
→ See `MIDI_TEMPO_VISUAL_GUIDE.md` for visual explanations

### If You Want to Understand Current Processing
→ This file has the overview

---

**Bottom Line**: 
- Tempo extraction works perfectly
- But it's disconnected from timing calculations
- Simple 8-line fix will make all MIDI files play at correct speed
- No other changes needed
- Low risk, high impact fix
