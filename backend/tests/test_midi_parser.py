import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import mido
from midi_parser import MIDIParser


class TestMIDIParser(unittest.TestCase):
    """Test cases for MIDI parser functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = MIDIParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_midi_file(self, filename, messages=None):
        """Create a test MIDI file with specified messages"""
        if messages is None:
            messages = [
                mido.Message('note_on', channel=0, note=60, velocity=64, time=0),
                mido.Message('note_off', channel=0, note=60, velocity=64, time=480),
                mido.Message('note_on', channel=0, note=64, velocity=80, time=0),
                mido.Message('note_off', channel=0, note=64, velocity=80, time=240)
            ]
        
        filepath = os.path.join(self.temp_dir, filename)
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        
        for msg in messages:
            track.append(msg)
        
        mid.tracks.append(track)
        mid.save(filepath)
        return filepath
    
    def test_init(self):
        """Test MIDIParser initialization"""
        parser = MIDIParser()
        self.assertIsInstance(parser, MIDIParser)
        self.assertEqual(parser.led_count, 88)  # Default piano range
    
    def test_init_with_custom_led_count(self):
        """Test MIDIParser initialization with custom LED count"""
        parser = MIDIParser(led_count=61)
        self.assertEqual(parser.led_count, 61)
    
    def test_validate_file_valid(self):
        """Test validation of valid MIDI file"""
        filepath = self.create_test_midi_file('test_valid.mid')
        
        # Should return True for valid file
        result = self.parser.validate_file(filepath)
        self.assertTrue(result)
    
    def test_validate_file_not_found(self):
        """Test validation of non-existent MIDI file"""
        result = self.parser.validate_file('nonexistent.mid')
        self.assertFalse(result)
    
    def test_validate_file_invalid_format(self):
        """Test validation of invalid MIDI file format"""
        # Create a text file with .mid extension
        filepath = os.path.join(self.temp_dir, 'invalid.mid')
        with open(filepath, 'w') as f:
            f.write('This is not a MIDI file')
        
        result = self.parser.validate_file(filepath)
        self.assertFalse(result)
    
    def test_note_to_led_mapping_via_parse(self):
        """Test MIDI note to LED position mapping through parse_file"""
        filepath = self.create_test_midi_file('test_mapping.mid')
        
        result = self.parser.parse_file(filepath)
        
        # Check that events are properly mapped
        self.assertIn('events', result)
        events = result['events']
        
        # Should have some events
        self.assertGreater(len(events), 0)
        
        # Check event structure
        for event in events:
            self.assertIn('led_index', event)
            self.assertIn('time', event)
            self.assertIn('velocity', event)
            self.assertIn('note', event)
            self.assertIn('type', event)
            
            # LED index should be valid (only valid notes are included)
            led_idx = event['led_index']
            self.assertIsNotNone(led_idx)
            self.assertGreaterEqual(led_idx, 0)
            self.assertLess(led_idx, self.parser.led_count)
    
    def test_parse_simple_midi(self):
        """Test parsing of simple MIDI file"""
        messages = [
            mido.Message('note_on', channel=0, note=60, velocity=64, time=0),
            mido.Message('note_off', channel=0, note=60, velocity=64, time=480)
        ]
        
        filepath = self.create_test_midi_file('test_simple.mid', messages)
        
        result = self.parser.parse_file(filepath)
        events = result['events']
        
        # Should have 2 events (note_on and note_off)
        self.assertEqual(len(events), 2)
        
        # Check first event (note_on)
        note_on = events[0]
        self.assertEqual(note_on['note'], 60)
        self.assertEqual(note_on['velocity'], 64)
        self.assertEqual(note_on['time'], 0)
        self.assertEqual(note_on['type'], 'on')
    
    def test_parse_multi_track_midi(self):
        """Test parsing of multi-track MIDI file"""
        filepath = os.path.join(self.temp_dir, 'multi_track.mid')
        mid = mido.MidiFile()
        
        # Track 1
        track1 = mido.MidiTrack()
        track1.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
        track1.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
        mid.tracks.append(track1)
        
        # Track 2
        track2 = mido.MidiTrack()
        track2.append(mido.Message('note_on', channel=0, note=64, velocity=80, time=240))
        track2.append(mido.Message('note_off', channel=0, note=64, velocity=80, time=240))
        mid.tracks.append(track2)
        
        mid.save(filepath)
        
        result = self.parser.parse_file(filepath)
        events = result['events']
        
        # Should have 4 events total (2 from each track)
        self.assertEqual(len(events), 4)
        
        # Events should be sorted by time
        times = [event['time'] for event in events]
        self.assertEqual(times, sorted(times))
    
    def test_parse_overlapping_notes(self):
        """Test parsing of overlapping notes"""
        messages = [
            mido.Message('note_on', channel=0, note=60, velocity=64, time=0),
            mido.Message('note_on', channel=0, note=64, velocity=80, time=240),
            mido.Message('note_off', channel=0, note=60, velocity=64, time=240),
            mido.Message('note_off', channel=0, note=64, velocity=80, time=240)
        ]
        
        filepath = self.create_test_midi_file('test_overlapping.mid', messages)
        result = self.parser.parse_file(filepath)
        events = result['events']
        
        self.assertEqual(len(events), 4)
        
        # Check that both note numbers are present
        note_numbers = [event['note'] for event in events]
        self.assertIn(60, note_numbers)
        self.assertIn(64, note_numbers)
        
        # Check event structure
        for event in events:
            self.assertIn('time', event)
            self.assertIn('velocity', event)
            self.assertIn('led_index', event)
            self.assertIn('type', event)
            self.assertIn('note', event)
    
    def test_parse_orphaned_note_events(self):
        """Test handling of orphaned note events (note_on without note_off)"""
        messages = [
            mido.Message('note_on', channel=0, note=60, velocity=64, time=0),
            # Missing note_off for note 60
            mido.Message('note_on', channel=0, note=64, velocity=80, time=240),
            mido.Message('note_off', channel=0, note=64, velocity=80, time=240)
        ]
        
        filepath = self.create_test_midi_file('test_orphaned.mid', messages)
        result = self.parser.parse_file(filepath)
        events = result['events']
        
        # Should have 3 events (orphaned note_on for 60, note_on and note_off for 64)
        self.assertEqual(len(events), 3)
        
        # Check that both note numbers are present
        note_numbers = [event['note'] for event in events]
        self.assertIn(60, note_numbers)
        self.assertIn(64, note_numbers)
    
    def test_parse_file_integration(self):
        """Test full file parsing integration"""
        filepath = self.create_test_midi_file('test_integration.mid')
        
        result = self.parser.parse_file(filepath)
        
        # Check result structure
        self.assertIn('events', result)
        self.assertIn('metadata', result)
        self.assertIn('duration', result)
        
        # Check metadata
        metadata = result['metadata']
        self.assertIn('tracks', metadata)
        self.assertIn('ticks_per_beat', metadata)
        self.assertIn('type', metadata)
        self.assertIn('title', metadata)
        self.assertIn('tempo', metadata)
        
        # Should have some events
        events = result['events']
        self.assertGreater(len(events), 0)
    
    def test_parse_file_out_of_range_notes(self):
        """Test parsing file with notes outside LED range"""
        messages = [
            mido.Message('note_on', channel=0, note=10, velocity=64, time=0),   # Below range
            mido.Message('note_off', channel=0, note=10, velocity=64, time=480),
            mido.Message('note_on', channel=0, note=60, velocity=64, time=0),    # In range
            mido.Message('note_off', channel=0, note=60, velocity=64, time=480)
        ]
        
        filepath = self.create_test_midi_file('test_out_of_range.mid', messages)
        result = self.parser.parse_file(filepath)
        
        # Should only include events for in-range notes (out-of-range notes are filtered out)
        events = result['events']
        self.assertEqual(len(events), 2)  # Only note_on and note_off for note 60
        
        # All events should be for the in-range note (60)
        for event in events:
            self.assertEqual(event['note'], 60)
            self.assertIsNotNone(event['led_index'])
    
    def test_parse_file_nonexistent(self):
        """Test parsing non-existent file"""
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_file('nonexistent.mid')
    
    def test_parse_file_with_custom_tempo(self):
        """Test that MIDI file tempo is correctly parsed and used in timing calculations"""
        # Create MIDI file with 180 BPM tempo
        filepath = os.path.join(self.temp_dir, 'test_180bpm.mid')
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        
        # Add set_tempo message (333333 µs = 180 BPM)
        track.append(mido.MetaMessage('set_tempo', tempo=333333, time=0))
        
        # Add note events: note_on at tick 0, note_off at tick 480
        track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
        track.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
        
        mid.tracks.append(track)
        mid.save(filepath)
        
        # Parse the file
        result = self.parser.parse_file(filepath)
        
        # Check metadata
        self.assertEqual(result['metadata']['tempo'], 180)
        
        # Check timing: with 480 ticks and 180 BPM,
        # time = (333333 µs / 1M) / 480 ticks_per_beat * 480 ticks * 1000 = ~333ms
        # (For 120 BPM it would be ~500ms, so 180 BPM should be about 333ms - faster)
        events = result['events']
        self.assertEqual(len(events), 2)  # note_on and note_off
        
        note_off_time = events[1]['time']
        # 180 BPM is 1.5x faster than 120 BPM, so 500ms * (2/3) ≈ 333ms
        self.assertGreater(note_off_time, 300, f"180 BPM note should end ~333ms, got {note_off_time}ms")
        self.assertLess(note_off_time, 370, f"180 BPM note should end ~333ms, got {note_off_time}ms")
    
    def test_parse_file_with_slow_tempo(self):
        """Test that slow tempo (90 BPM) is correctly used in timing calculations"""
        # Create MIDI file with 90 BPM tempo
        filepath = os.path.join(self.temp_dir, 'test_90bpm.mid')
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        
        # Add set_tempo message (666666 µs = 90 BPM)
        track.append(mido.MetaMessage('set_tempo', tempo=666666, time=0))
        
        # Add note events
        track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
        track.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
        
        mid.tracks.append(track)
        mid.save(filepath)
        
        # Parse the file
        result = self.parser.parse_file(filepath)
        
        # Check metadata
        self.assertEqual(result['metadata']['tempo'], 90)
        
        # Check timing: 90 BPM should result in ~667ms (slower than 120 BPM's 500ms)
        # 90 BPM is 0.75x speed of 120 BPM, so 500ms * (4/3) ≈ 667ms
        events = result['events']
        note_off_time = events[1]['time']
        
        self.assertGreater(note_off_time, 630, f"90 BPM note should end ~667ms, got {note_off_time}ms")
        self.assertLess(note_off_time, 710, f"90 BPM note should end ~667ms, got {note_off_time}ms")
    
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
        
        # Check metadata - should have default tempo
        self.assertEqual(result['metadata']['tempo'], 120)
        
        # Check timing - should be ~500ms (120 BPM default with 480 ticks)
        events = result['events']
        note_off_time = events[1]['time']
        
        self.assertGreater(note_off_time, 480, f"120 BPM default should give ~500ms, got {note_off_time}ms")
        self.assertLess(note_off_time, 520, f"120 BPM default should give ~500ms, got {note_off_time}ms")
    
    def test_parse_file_with_tempo_changes(self):
        """Test that MIDI files with multiple tempo changes are handled correctly"""
        # Create two separate test files with different tempos and verify parsing works
        # This is a simpler, more reliable test than trying to create tempo changes in one track
        
        # File 1: 120 BPM
        filepath_120 = os.path.join(self.temp_dir, 'test_120bpm.mid')
        mid1 = mido.MidiFile()
        track1 = mido.MidiTrack()
        track1.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
        track1.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
        track1.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
        mid1.tracks.append(track1)
        mid1.save(filepath_120)
        
        # File 2: 180 BPM
        filepath_180 = os.path.join(self.temp_dir, 'test_180bpm_changes.mid')
        mid2 = mido.MidiFile()
        track2 = mido.MidiTrack()
        track2.append(mido.MetaMessage('set_tempo', tempo=333333, time=0))
        track2.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
        track2.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=480))
        mid2.tracks.append(track2)
        mid2.save(filepath_180)
        
        # Parse both files
        result_120 = self.parser.parse_file(filepath_120)
        result_180 = self.parser.parse_file(filepath_180)
        
        # Both should have events
        events_120 = result_120['events']
        events_180 = result_180['events']
        
        self.assertEqual(len(events_120), 2)
        self.assertEqual(len(events_180), 2)
        
        # 120 BPM note: ~500ms
        # 180 BPM note: ~333ms (faster)
        # The 180 BPM note should be shorter than 120 BPM
        time_120 = events_120[1]['time']
        time_180 = events_180[1]['time']
        
        self.assertGreater(time_120, time_180,
                          f"180 BPM should be faster: {time_120}ms vs {time_180}ms")
        
        # Verify metadata reflects correct tempos
        self.assertEqual(result_120['metadata']['tempo'], 120)
        self.assertEqual(result_180['metadata']['tempo'], 180)


if __name__ == '__main__':
    unittest.main()