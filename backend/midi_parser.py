import os
from typing import List, Dict, Any, Optional
import logging
from logging_config import get_logger

# Try to import mido with fallback
try:
    import mido
    MIDO_AVAILABLE = True
    logger = get_logger(__name__)
    logger.info("mido library loaded successfully")
except ImportError as e:
    logger = get_logger(__name__)
    logger.warning(f"mido library not available: {e}")
    MIDO_AVAILABLE = False
    mido = None

try:
    from config import get_config, get_piano_specs
except ImportError:
    logging.warning("Config module not available, using defaults")
    def get_config(key, default):
        return default
    def get_piano_specs(piano_size):
        return {'keys': 88, 'midi_start': 21, 'midi_end': 108}

class MIDIParser:
    """Service for parsing MIDI files into timed note sequences for LED visualization."""
    
    def __init__(self, led_count: int = None, settings_service=None):
        """
        Initialize MIDI parser with configurable piano specifications.
        
        Args:
            led_count: Number of LEDs (optional, loaded from settings if not provided)
            settings_service: Settings service instance for retrieving configuration
        """
        # Load configuration values
        if settings_service:
            piano_size = settings_service.get_setting('piano', 'size', '88-key')
            piano_specs = self._get_piano_specs(piano_size)
            self.led_count = led_count if led_count is not None else settings_service.get_setting('led', 'led_count', 246)
            self.led_orientation = settings_service.get_setting('led', 'led_orientation', 'normal')
        else:
            # Fallback to config.py
            try:
                from config import get_config, get_piano_specs
                piano_size = get_config('piano_size', '88-key')
                piano_specs = get_piano_specs(piano_size)
                self.led_count = led_count if led_count is not None else piano_specs['keys']
                self.led_orientation = get_config('led_orientation', 'normal')
            except ImportError:
                piano_specs = {'keys': 88, 'midi_start': 21, 'midi_end': 108}
                self.led_count = led_count if led_count is not None else 88
                self.led_orientation = 'normal'
        
        self.min_midi_note = piano_specs['midi_start']
        self.max_midi_note = piano_specs['midi_end']
        self.piano_size = piano_size
        
        logger.info(f"MIDI parser initialized for {piano_size} piano with {self.led_count} LEDs, MIDI range {self.min_midi_note}-{self.max_midi_note}, orientation: {self.led_orientation}")
        
    def _get_piano_specs(self, piano_size: str) -> Dict[str, Any]:
        """Get piano specifications based on size."""
        specs = {
            '88-key': {'keys': 88, 'midi_start': 21, 'midi_end': 108},
            '76-key': {'keys': 76, 'midi_start': 28, 'midi_end': 103},
            '61-key': {'keys': 61, 'midi_start': 36, 'midi_end': 96},
            '49-key': {'keys': 49, 'midi_start': 36, 'midi_end': 84},
            '25-key': {'keys': 25, 'midi_start': 48, 'midi_end': 72}
        }
        return specs.get(piano_size, specs['88-key'])
        
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a MIDI file into a timed sequence of note events.
        
        Args:
            file_path: Path to the MIDI file
            
        Returns:
            Dictionary containing parsed note sequence and metadata
            
        Raises:
            FileNotFoundError: If MIDI file doesn't exist
            ValueError: If file is not a valid MIDI file
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available - cannot parse MIDI files")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"MIDI file not found: {file_path}")
            
        try:
            # Load MIDI file
            midi_file = mido.MidiFile(file_path)
            logger.info(f"Loaded MIDI file: {file_path} with {len(midi_file.tracks)} tracks")
            
            # Extract all note events from all tracks
            all_events = self._extract_note_events(midi_file)
            
            # Convert to timed sequence
            note_sequence = self._create_note_sequence(all_events, midi_file)
            
            # Calculate total duration
            duration = max([event['time'] for event in note_sequence], default=0)
            
            # Extract metadata
            metadata = self._extract_metadata(midi_file)
            
            return {
                'duration': duration,
                'events': note_sequence,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error parsing MIDI file {file_path}: {str(e)}")
            raise ValueError(f"Invalid MIDI file: {str(e)}")
    
    def _extract_note_events(self, midi_file) -> List[Dict[str, Any]]:
        """
        Extract note on/off events from all tracks in the MIDI file.
        
        Args:
            midi_file: Loaded MIDI file object
            
        Returns:
            List of note events with timing information
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
        events = []
        
        for track_idx, track in enumerate(midi_file.tracks):
            current_time = 0
            
            for msg in track:
                current_time += msg.time
                
                # Process note on events
                if msg.type == 'note_on' and msg.velocity > 0:
                    events.append({
                        'time_ticks': current_time,
                        'note': msg.note,
                        'velocity': msg.velocity,
                        'type': 'on',
                        'track': track_idx
                    })
                
                # Process note off events (including note_on with velocity 0)
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    events.append({
                        'time_ticks': current_time,
                        'note': msg.note,
                        'velocity': 0,
                        'type': 'off',
                        'track': track_idx
                    })
        
        logger.info(f"Extracted {len(events)} note events from {len(midi_file.tracks)} tracks")
        return events
    
    def _create_note_sequence(self, events: List[Dict[str, Any]], midi_file) -> List[Dict[str, Any]]:
        """
        Convert MIDI events to a time-ordered sequence with absolute timing.
        
        Args:
            events: List of note events with tick timing
            midi_file: MIDI file object for timing calculations
            
        Returns:
            Time-ordered list of note events with millisecond timing
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
        # Calculate ticks per second for timing conversion
        ticks_per_beat = midi_file.ticks_per_beat
        tempo = 500000  # Default tempo (120 BPM) in microseconds per beat
        
        # Convert events to absolute time and map to LEDs
        timed_events = []
        
        for event in events:
            # Convert ticks to milliseconds
            time_ms = self._ticks_to_milliseconds(event['time_ticks'], ticks_per_beat, tempo)
            
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
    
    def _ticks_to_milliseconds(self, ticks: int, ticks_per_beat: int, tempo: int) -> int:
        """
        Convert MIDI ticks to milliseconds.
        
        Args:
            ticks: MIDI ticks
            ticks_per_beat: Ticks per quarter note
            tempo: Microseconds per beat
            
        Returns:
            Time in milliseconds
        """
        # Calculate seconds per tick
        seconds_per_tick = (tempo / 1_000_000) / ticks_per_beat
        
        # Convert to milliseconds
        return int(ticks * seconds_per_tick * 1000)
    
    def _map_note_to_led(self, midi_note: int) -> Optional[int]:
        """
        Map MIDI note number to LED strip position with orientation support.
        
        Args:
            midi_note: MIDI note number (0-127)
            
        Returns:
            LED index (0-based) or None if note is outside range
        """
        # Only map notes within piano range
        if midi_note < self.min_midi_note or midi_note > self.max_midi_note:
            return None
            
        # Map to logical LED position (0-based)
        logical_index = midi_note - self.min_midi_note
        
        # Ensure within LED strip bounds
        if logical_index >= self.led_count:
            return None
        
        return logical_index
    
    def _extract_metadata(self, midi_file) -> Dict[str, Any]:
        """
        Extract metadata from MIDI file.
        
        Args:
            midi_file: Loaded MIDI file object
            
        Returns:
            Dictionary containing metadata
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
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
                    metadata['tempo'] = int(60_000_000 / msg.tempo)
                    break
        
        return metadata
    
    def validate_file(self, file_path: str) -> bool:
        """
        Validate if a file is a proper MIDI file.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if valid MIDI file, False otherwise
        """
        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - cannot validate MIDI files")
            return False
            
        try:
            if not os.path.exists(file_path):
                return False
                
            # Try to load the file
            midi_file = mido.MidiFile(file_path)
            
            # Check if it has at least one track
            if len(midi_file.tracks) == 0:
                return False
                
            return True
            
        except Exception as e:
            logger.warning(f"MIDI validation failed for {file_path}: {str(e)}")
            return False
