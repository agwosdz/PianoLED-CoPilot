# MIDI Tempo Fix - Implementation Ready

## The Problem (One Sentence)
Tempo from MIDI files is extracted and stored in metadata but **never used** during timing calculations - all files are treated as 120 BPM.

---

## The Fix (Two Options)

### OPTION 1: Simple Fix (Recommended)

**Location**: `backend/midi_parser.py`, function `_create_note_sequence()`, around line 203

**Current Code**:
```python
def _create_note_sequence(self, events: List[Dict[str, Any]], midi_file) -> List[Dict[str, Any]]:
    """
    Convert MIDI events to a time-ordered sequence with absolute timing.
    ...
    """
    if not MIDO_AVAILABLE:
        raise RuntimeError("mido library not available")
        
    # Calculate ticks per second for timing conversion
    ticks_per_beat = midi_file.ticks_per_beat
    tempo = 500000  # Default tempo (120 BPM) in microseconds per beat  ← PROBLEM HERE
    
    # Convert events to absolute time and map to LEDs
    timed_events = []
    ...
```

**Replace with**:
```python
def _create_note_sequence(self, events: List[Dict[str, Any]], midi_file) -> List[Dict[str, Any]]:
    """
    Convert MIDI events to a time-ordered sequence with absolute timing.
    ...
    """
    if not MIDO_AVAILABLE:
        raise RuntimeError("mido library not available")
        
    # Calculate ticks per second for timing conversion
    ticks_per_beat = midi_file.ticks_per_beat
    tempo = 500000  # Default tempo (120 BPM) in microseconds per beat
    
    # Extract actual tempo from MIDI file if available
    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                bpm = int(60_000_000 / msg.tempo)
                logger.info(f"Parsed MIDI tempo: {bpm} BPM")
                break
        if tempo != 500000:
            break
    
    # Convert events to absolute time and map to LEDs
    timed_events = []
    ...
```

**Changes**:
- Add 8 lines to extract tempo from MIDI file
- Use extracted tempo instead of hardcoded default
- Add logging for debugging

**Testing**: All existing tests should pass (default 120 BPM stays same)

---

### OPTION 2: Robust Fix (Future-Proof)

**For handling multiple tempo changes in one MIDI file**

```python
def _create_note_sequence(self, events: List[Dict[str, Any]], midi_file) -> List[Dict[str, Any]]:
    """
    Convert MIDI events to a time-ordered sequence with absolute timing.
    Handles tempo changes within the MIDI file.
    """
    if not MIDO_AVAILABLE:
        raise RuntimeError("mido library not available")
        
    ticks_per_beat = midi_file.ticks_per_beat
    
    # Extract all tempo change points
    tempo_map = {}  # time_ticks → tempo in microseconds per beat
    default_tempo = 500000  # 120 BPM
    
    for track in midi_file.tracks:
        current_time = 0
        for msg in track:
            current_time += msg.time
            if msg.type == 'set_tempo':
                tempo_map[current_time] = msg.tempo
                logger.debug(f"Tempo change at tick {current_time}: {int(60_000_000 / msg.tempo)} BPM")
    
    # Sort tempo changes by time
    tempo_times = sorted(tempo_map.keys()) if tempo_map else []
    current_tempo = tempo_map.get(tempo_times[0], default_tempo) if tempo_times else default_tempo
    tempo_idx = 1  # Next tempo index to check
    
    # Convert events to absolute time and map to LEDs
    timed_events = []
    
    for event in events:
        event_ticks = event['time_ticks']
        
        # Update tempo if we've reached a tempo change point
        while tempo_idx < len(tempo_times) and event_ticks >= tempo_times[tempo_idx]:
            current_tempo = tempo_map[tempo_times[tempo_idx]]
            tempo_idx += 1
        
        # Convert ticks to milliseconds using current tempo
        time_ms = self._ticks_to_milliseconds(event_ticks, ticks_per_beat, current_tempo)
        
        # Map MIDI note to LED position
        led_index = self._map_note_to_led(event['note'])
        
        # Only include notes that map to valid LED positions
        if led_index is not None:
            timed_events.append({
                'time': time_ms,
                'note': event['note'],
                'velocity': event['velocity'],
                'type': event['type'],
                'led_index': led_index
            })
    
    # Sort events by time
    timed_events.sort(key=lambda x: x['time'])
    
    logger.info(f"Created sequence with {len(timed_events)} timed events")
    return timed_events
```

**When to use**: If MIDI files with tempo changes need support

---

## Testing the Fix

### Unit Test to Add

**File**: `backend/tests/test_midi_parser.py`

```python
def test_parse_file_with_custom_tempo(self):
    """Test that MIDI file tempo is correctly parsed and used"""
    # Create MIDI file with 180 BPM tempo
    filepath = os.path.join(self.temp_dir, 'test_180bpm.mid')
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    
    # Add set_tempo message (333333 µs = 180 BPM)
    track.append(mido.MetaMessage('set_tempo', tempo=333333, time=0))
    
    # Add note events
    track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
    
    mid.tracks.append(track)
    mid.save(filepath)
    
    # Parse the file
    result = self.parser.parse_file(filepath)
    
    # Check metadata
    self.assertEqual(result['metadata']['tempo'], 180)
    
    # Check timing: with 480 ticks and 180 BPM,
    # note should start at ~0ms and end at ~667ms
    # (not 1000ms which would be 120 BPM)
    events = result['events']
    self.assertEqual(len(events), 2)  # note_on and note_off
    
    # With 180 BPM, duration should be ~667ms instead of 1000ms
    note_off_time = events[1]['time']
    assert 600 < note_off_time < 700, f"Expected ~667ms, got {note_off_time}ms"


def test_parse_file_default_tempo(self):
    """Test that files without set_tempo use default 120 BPM"""
    # Create MIDI file WITHOUT tempo specification
    filepath = os.path.join(self.temp_dir, 'test_default_tempo.mid')
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    
    # NO set_tempo message - should use 120 BPM default
    track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
    
    mid.tracks.append(track)
    mid.save(filepath)
    
    # Parse the file
    result = self.parser.parse_file(filepath)
    
    # Check metadata - should have default
    self.assertEqual(result['metadata']['tempo'], 120)
    
    # Check timing - should be 1000ms (120 BPM default)
    events = result['events']
    note_off_time = events[1]['time']
    assert 950 < note_off_time < 1050, f"Expected ~1000ms, got {note_off_time}ms"
```

---

## Deployment Checklist

- [ ] Read complete analysis (`MIDI_TEMPO_ANALYSIS.md`)
- [ ] Choose Option 1 (Simple) or Option 2 (Robust)
- [ ] Apply code changes to `backend/midi_parser.py`
- [ ] Add unit tests from above
- [ ] Run test suite: `pytest backend/tests/test_midi_parser.py -v`
- [ ] Run full test suite: `pytest`
- [ ] Test with a 180 BPM MIDI file
- [ ] Verify duration shows correctly
- [ ] Check MIDI output timing with USB keyboard
- [ ] Commit with message: "Fix: Use actual MIDI tempo for timing calculations"

---

## Impact Summary

### What Changes
- ✓ Playback duration becomes accurate
- ✓ Playback speed matches file tempo
- ✓ LED visualization syncs correctly
- ✓ MIDI output sends notes at correct times

### What Stays the Same
- ✗ API response structure (unchanged)
- ✗ Frontend code (unchanged)
- ✗ PlaybackService (unchanged)
- ✗ Backward compatibility (files with 120 BPM play same)

### Risk Assessment
- **Code Risk**: Very Low (8 lines in isolated function)
- **Testing Risk**: Low (existing tests should pass)
- **User Impact**: High Positive (fixes broken playback)
- **Breaking Changes**: None

---

## Code Review Points

When reviewing this fix:

1. ✓ Does tempo extraction happen in the right place?
   - Yes, in `_create_note_sequence()` before timing calculations

2. ✓ Is the default tempo preserved?
   - Yes, still 500000 µs (120 BPM) if no set_tempo found

3. ✓ Are there any side effects?
   - No, only affects timing calculation accuracy

4. ✓ Is logging appropriate?
   - Yes, logs extracted BPM for debugging

5. ✓ Does it handle edge cases?
   - Yes, falls back to 120 BPM if set_tempo not found
   - Yes, stops searching after first tempo found (most files only have one)

---

## Troubleshooting

### After Fix: File plays faster than expected
**Cause**: File actually has lower BPM than assumed  
**Check**: `tail -f logs/` while playing - should show extracted BPM

### After Fix: Error in metadata tempo
**Cause**: MIDI file corrupted  
**Check**: Try with different MIDI file - should work normally

### Tests failing
**Cause**: Test assumptions about 120 BPM  
**Fix**: Update test expectations based on actual tempos

---

## Ready to Implement

Choose implementation option and apply changes to:
- `backend/midi_parser.py` line ~203 in `_create_note_sequence()`

Estimated time: **10 minutes**  
Risk level: **Very Low**  
Impact: **High Positive**

---

**Status**: ✅ Ready to implement
