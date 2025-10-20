import os
from typing import List, Dict, Any, Optional, Tuple
import logging
from backend.logging_config import get_logger

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
    from backend.config import get_config, get_piano_specs
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
        self._settings_service = settings_service
        self._key_led_mapping = None  # Cached adjusted key-to-LED mapping (with offsets/trims)
        if settings_service:
            piano_size = settings_service.get_setting('piano', 'size', '88-key')
            piano_specs = self._get_piano_specs(piano_size)
            self.led_count = led_count if led_count is not None else settings_service.get_setting('led', 'led_count', 246)
            self.led_orientation = settings_service.get_setting('led', 'led_orientation', 'normal')
        else:
            # Fallback to config.py
            try:
                from backend.config import get_config, get_piano_specs
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

    def refresh_runtime_settings(self, settings_service=None) -> None:
        """Refresh MIDI parser runtime configuration from settings service."""
        try:
            ss = settings_service or getattr(self, '_settings_service', None)
            if not ss:
                return

            piano_size = ss.get_setting('piano', 'size', self.piano_size)
            piano_specs = self._get_piano_specs(piano_size)
            led_count_value = ss.get_setting('led', 'led_count', self.led_count)
            try:
                led_count = max(1, int(led_count_value))
            except (TypeError, ValueError):
                led_count = self.led_count

            orientation = ss.get_setting('led', 'led_orientation', self.led_orientation)

            self.piano_size = piano_size
            self.led_count = led_count
            self.led_orientation = orientation
            self.min_midi_note = piano_specs['midi_start']
            self.max_midi_note = piano_specs['midi_end']
            
            # Invalidate cached mapping so it gets reloaded on next use
            self._key_led_mapping = None

            logger.info(f"MIDI parser runtime settings refreshed for {piano_size} piano with {self.led_count} LEDs, orientation: {self.led_orientation}")
        except Exception as e:
            logger.warning(f"Failed to refresh MIDI parser settings: {e}")
        
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
    
    def _detect_track_hand(self, track_name: Optional[str], note_range: Tuple[int, int], track_channels: set, track_index: int, total_tracks: int) -> Tuple[str, float, str]:
        """
        Detect if a track is for left hand, right hand, both, or unknown.
        
        Returns:
            Tuple of (hand, confidence, detection_method)
            hand: 'right', 'left', 'both', or 'unknown'
            confidence: 0.0-1.0
            detection_method: 'name', 'channel', 'range', 'order', or 'unknown'
        """
        
        # Pattern 1: Check track name (highest priority, highest confidence)
        if track_name:
            name_lower = track_name.lower().strip()
            
            # Right hand patterns
            if any(pat in name_lower for pat in ['right hand', 'right', 'rh ', 'treble', 'melody', 'soprano']):
                logger.debug(f"Track {track_index} detected as RIGHT by name: '{track_name}'")
                return ('right', 0.95, 'name')
            
            # Left hand patterns
            if any(pat in name_lower for pat in ['left hand', 'left', 'lh ', 'bass', 'bass line', 'alto']):
                logger.debug(f"Track {track_index} detected as LEFT by name: '{track_name}'")
                return ('left', 0.95, 'name')
            
            # Both patterns
            if any(pat in name_lower for pat in ['piano', 'both', 'combined', 'full']):
                logger.debug(f"Track {track_index} detected as BOTH by name: '{track_name}'")
                return ('both', 0.90, 'name')
        
        # Pattern 2: Check note range (high confidence)
        min_note, max_note = note_range
        middle_c = 60  # MIDI note for Middle C
        
        # Clear left hand (all notes well below middle C)
        if max_note < 48:  # Everything below C3
            logger.debug(f"Track {track_index} detected as LEFT by range: {min_note}-{max_note}")
            return ('left', 0.85, 'range')
        
        # Clear right hand (all notes well above middle C)
        if min_note > 72:  # Everything above C5
            logger.debug(f"Track {track_index} detected as RIGHT by range: {min_note}-{max_note}")
            return ('right', 0.85, 'range')
        
        # Likely left hand (mostly in lower range)
        if max_note <= middle_c and min_note < 48:
            logger.debug(f"Track {track_index} detected as LEFT by range: {min_note}-{max_note} (mostly lower)")
            return ('left', 0.75, 'range')
        
        # Likely right hand (mostly in upper range)
        if min_note >= middle_c and max_note > 72:
            logger.debug(f"Track {track_index} detected as RIGHT by range: {min_note}-{max_note} (mostly upper)")
            return ('right', 0.75, 'range')
        
        # Pattern 3: Check MIDI channels (lower priority)
        if track_channels:
            channels_list = sorted(list(track_channels))
            # This is less reliable but can help
            primary_channel = channels_list[0]
            # Channel convention varies, so low confidence
            if primary_channel in [0, 1]:  # Common for right hand
                logger.debug(f"Track {track_index} tentatively RIGHT by channel: {channels_list}")
                return ('right', 0.5, 'channel')
            elif primary_channel in [2, 3]:  # Sometimes left hand
                logger.debug(f"Track {track_index} tentatively LEFT by channel: {channels_list}")
                return ('left', 0.5, 'channel')
        
        # Pattern 4: Track order as last resort (lowest priority, lowest confidence)
        if total_tracks == 2:
            if track_index == 0:
                logger.debug(f"Track {track_index} guessed as RIGHT by order (first of 2 tracks)")
                return ('right', 0.3, 'order')
            elif track_index == 1:
                logger.debug(f"Track {track_index} guessed as LEFT by order (second of 2 tracks)")
                return ('left', 0.3, 'order')
        
        # Unable to determine
        logger.debug(f"Track {track_index} hand detection inconclusive, marking as unknown")
        return ('unknown', 0.0, 'unknown')
    
    def _analyze_tracks(self, midi_file) -> List[Dict[str, Any]]:
        """
        Analyze all tracks in MIDI file to determine hand assignments.
        
        Returns:
            List of track info dictionaries with hand detection
        """
        track_info = []
        
        for track_idx, track in enumerate(midi_file.tracks):
            # Extract track name from metadata
            track_name = None
            track_channels = set()
            all_notes = []
            
            for msg in track:
                if msg.type == 'track_name':
                    track_name = msg.name
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    all_notes.append(msg.note)
                    track_channels.add(msg.channel)
                elif msg.type == 'note_off':
                    all_notes.append(msg.note)
                    track_channels.add(msg.channel)
            
            # Calculate statistics
            if all_notes:
                min_note = min(all_notes)
                max_note = max(all_notes)
                note_count = len(all_notes)
            else:
                min_note = 0
                max_note = 0
                note_count = 0
            
            # Detect hand
            hand, confidence, detection_method = self._detect_track_hand(
                track_name, 
                (min_note, max_note), 
                track_channels,
                track_idx,
                len(midi_file.tracks)
            )
            
            info = {
                'index': track_idx,
                'name': track_name or f'Track {track_idx}',
                'channels': sorted(list(track_channels)) if track_channels else [],
                'hand': hand,
                'confidence': confidence,
                'detection_method': detection_method,
                'note_count': note_count,
                'note_range': [min_note, max_note] if all_notes else [0, 0]
            }
            
            track_info.append(info)
            logger.info(f"Track {track_idx}: {info['name']} | Hand: {hand} (conf: {confidence:.2f}, method: {detection_method}) | Notes: {note_count} | Range: {min_note}-{max_note}")
        
        return track_info
        
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
            
            # Analyze tracks for hand detection
            track_info = self._analyze_tracks(midi_file)
            
            # Extract all note events from all tracks
            all_events = self._extract_note_events(midi_file, track_info)
            
            # Convert to timed sequence
            note_sequence = self._create_note_sequence(all_events, midi_file)
            
            # Calculate total duration
            duration = max([event['time'] for event in note_sequence], default=0)
            
            # Extract metadata
            metadata = self._extract_metadata(midi_file, track_info)
            
            return {
                'duration': duration,
                'events': note_sequence,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error parsing MIDI file {file_path}: {str(e)}")
            raise ValueError(f"Invalid MIDI file: {str(e)}")
    
    def _extract_note_events(self, midi_file, track_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract note on/off events from all tracks in the MIDI file.
        
        Args:
            midi_file: Loaded MIDI file object
            track_info: List of track info dictionaries with hand classification
            
        Returns:
            List of note events with timing information and hand classification
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
        events = []
        
        for track_idx, track in enumerate(midi_file.tracks):
            current_time = 0
            track_hand = track_info[track_idx]['hand'] if track_idx < len(track_info) else 'unknown'
            track_name = track_info[track_idx]['name'] if track_idx < len(track_info) else f'Track {track_idx}'
            
            for msg in track:
                current_time += msg.time
                
                # Process note on events
                if msg.type == 'note_on' and msg.velocity > 0:
                    events.append({
                        'time_ticks': current_time,
                        'note': msg.note,
                        'velocity': msg.velocity,
                        'type': 'on',
                        'track': track_idx,
                        'track_name': track_name,
                        'hand': track_hand
                    })
                
                # Process note off events (including note_on with velocity 0)
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    events.append({
                        'time_ticks': current_time,
                        'note': msg.note,
                        'velocity': 0,
                        'type': 'off',
                        'track': track_idx,
                        'track_name': track_name,
                        'hand': track_hand
                    })
        
        logger.info(f"Extracted {len(events)} note events from {len(midi_file.tracks)} tracks with hand classification")
        return events
    
    def _create_note_sequence(self, events: List[Dict[str, Any]], midi_file) -> List[Dict[str, Any]]:
        """
        Convert MIDI events to a time-ordered sequence with absolute timing.
        Handles tempo changes within the MIDI file.
        
        Args:
            events: List of note events with tick timing
            midi_file: MIDI file object for timing calculations
            
        Returns:
            Time-ordered list of note events with millisecond timing
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
        ticks_per_beat = midi_file.ticks_per_beat
        
        # Extract all tempo change points from the MIDI file
        tempo_map = {}  # time_ticks → tempo in microseconds per beat
        default_tempo = 500000  # 120 BPM
        
        for track in midi_file.tracks:
            current_time = 0
            for msg in track:
                current_time += msg.time
                if msg.type == 'set_tempo':
                    tempo_map[current_time] = msg.tempo
                    bpm = int(60_000_000 / msg.tempo)
                    logger.debug(f"Tempo change at tick {current_time}: {bpm} BPM ({msg.tempo} µs/beat)")
        
        # Sort tempo changes by time
        tempo_times = sorted(tempo_map.keys()) if tempo_map else []
        current_tempo = tempo_map.get(tempo_times[0], default_tempo) if tempo_times else default_tempo
        tempo_idx = 1  # Next tempo index to check
        
        if tempo_times:
            initial_bpm = int(60_000_000 / current_tempo)
            logger.info(f"Starting tempo: {initial_bpm} BPM ({current_tempo} µs/beat)")
        else:
            logger.info(f"Using default tempo: 120 BPM ({default_tempo} µs/beat)")
        
        # Convert events to absolute time and map to LEDs
        timed_events = []
        
        for event in events:
            event_ticks = event['time_ticks']
            
            # Update tempo if we've reached a tempo change point
            while tempo_idx < len(tempo_times) and event_ticks >= tempo_times[tempo_idx]:
                current_tempo = tempo_map[tempo_times[tempo_idx]]
                tempo_idx += 1
                bpm = int(60_000_000 / current_tempo)
                logger.debug(f"Applied tempo change: {bpm} BPM at tick {event_ticks}")
            
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
                    'led_index': led_index,
                    'track': event['track'],
                    'track_name': event['track_name'],
                    'hand': event['hand']
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
        Map MIDI note number to LED strip position using adjusted key-to-LED mapping.
        This mapping includes all offsets, trims, and LED selection overrides.
        
        Args:
            midi_note: MIDI note number (0-127)
            
        Returns:
            First LED index from the mapped range, or None if note is outside range or not mapped
        """
        # Only map notes within piano range
        if midi_note < self.min_midi_note or midi_note > self.max_midi_note:
            return None
        
        # Get adjusted key-to-LED mapping on first use
        if self._key_led_mapping is None:
            try:
                if self._settings_service:
                    from backend.config import get_canonical_led_mapping
                    result = get_canonical_led_mapping(self._settings_service)
                    self._key_led_mapping = result.get('mapping', {}) if result.get('success') else {}
                else:
                    self._key_led_mapping = {}
                
                if self._key_led_mapping:
                    logger.debug(f"Loaded adjusted key-to-LED mapping with {len(self._key_led_mapping)} keys")
                else:
                    logger.warning("Could not load adjusted key-to-LED mapping, will use fallback")
            except Exception as e:
                logger.warning(f"Error loading adjusted key-to-LED mapping: {e}, using fallback")
                self._key_led_mapping = {}
        
        # Convert MIDI note to key index (0-based from C0/MIDI 21)
        key_index = midi_note - self.min_midi_note
        
        # Try to get from adjusted mapping first
        if self._key_led_mapping and key_index in self._key_led_mapping:
            led_list = self._key_led_mapping[key_index]
            if led_list and len(led_list) > 0:
                # Return first LED in the mapped range
                return led_list[0]
        
        # Fallback to simple logical mapping if adjusted mapping not available or empty
        logical_index = key_index
        
        # Ensure within LED strip bounds
        if logical_index >= self.led_count:
            return None
        
        return logical_index
    
    def _extract_metadata(self, midi_file, track_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract metadata from MIDI file.
        
        Args:
            midi_file: Loaded MIDI file object
            track_info: List of track info dictionaries with hand classification
            
        Returns:
            Dictionary containing metadata with track analysis
        """
        if not MIDO_AVAILABLE:
            raise RuntimeError("mido library not available")
            
        metadata = {
            'tracks': len(midi_file.tracks),
            'ticks_per_beat': midi_file.ticks_per_beat,
            'type': midi_file.type,
            'title': None,
            'tempo': 120,  # Default BPM
            'track_info': track_info  # NEW: Include track analysis with hand detection
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
