#!/usr/bin/env python3
"""
Playback Service - Coordinates MIDI playback with LED visualization
Integrates MIDI parsing and LED control for real-time playback
"""

import logging
import threading
import time
import json
import os
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque
from backend.logging_config import get_logger

logger = get_logger(__name__)

try:
    from led_controller import LEDController
except ImportError:
    LEDController = None

try:
    from midi_parser import MIDIParser
except ImportError:
    MIDIParser = None

try:
    from .performance_monitor import PerformanceMonitor
except ImportError:
    PerformanceMonitor = None

try:
    from backend.usb_midi_output_service import USBMIDIOutputService
except ImportError:
    USBMIDIOutputService = None

try:
    from backend.config import get_config, get_piano_specs
except ImportError:
    logging.warning("Config module not available, using defaults")
    def get_config(key, default):
        return default
    def get_piano_specs(piano_size):
        return {'keys': 88, 'midi_start': 21, 'midi_end': 108}

class PlaybackState(Enum):
    """Playback state enumeration"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class NoteEvent:
    """Represents a single note event in the MIDI sequence"""
    time: float  # Time in seconds from start
    note: int    # MIDI note number (0-127)
    velocity: int  # Note velocity (0-127)
    duration: float  # Note duration in seconds
    channel: int = 0  # MIDI channel

@dataclass
class PlaybackStatus:
    """Current playback status information"""
    state: PlaybackState
    current_time: float
    total_duration: float
    filename: Optional[str]
    progress_percentage: float
    error_message: Optional[str] = None

class PlaybackService:
    """Service for coordinating MIDI playback with LED visualization"""
    
    def __init__(self, led_controller=None, num_leds: Optional[int] = None, midi_parser=None, settings_service: Optional[Any] = None, midi_output_service: Optional[Any] = None):
        """
        Initialize playback service with configurable piano specifications.
        
        Args:
            led_controller: LED controller instance
            num_leds: Number of LEDs in the strip (optional, loaded from settings if not provided)
            midi_parser: MIDI parser instance for file parsing
            settings_service: Settings service instance for retrieving configuration
            midi_output_service: MIDI output service for sending notes to USB keyboard
        """
        self._led_controller = led_controller
        self._settings_service = settings_service
        self._midi_output_service = midi_output_service
        self.piano_size = '88-key'
        
        if self._settings_service:
            self._load_settings_from_service(num_leds_override=num_leds)
        else:
            self._load_settings_from_config(num_leds_override=num_leds)
        
        # Precompute key-to-LED mapping for performance
        self._precomputed_mapping = self._generate_key_mapping()
        self._midi_parser = midi_parser or (MIDIParser(settings_service=settings_service) if MIDIParser else None)
        
        # OPTIMIZATION: Pre-computed expected notes lookup (Phase 2A)
        # Dictionary maps (time_bin, hand) -> set(notes) for O(1) lookups instead of O(n) iteration
        self._expected_notes_by_window: Dict[Tuple[int, str], set] = {}
        self._expected_notes_window_size = 50  # Time bins in milliseconds for grouping
        
        # OPTIMIZATION: Cached color conversions (Phase 2A)
        self._left_color_bright = None
        self._right_color_bright = None
        self._left_color_dim = None
        self._right_color_dim = None
        
        # OPTIMIZATION: Cached note-to-LED lookups (Phase 2A)
        self._note_to_leds_cache: Dict[int, List[int]] = {}
        
        # OPTIMIZATION: Batch LED update state tracking (Phase 2A)
        self._last_led_state: Dict[int, tuple] = {}
        
        # Playback state
        self._state = PlaybackState.IDLE
        self._current_time = 0.0
        self._total_duration = 0.0
        self._filename = None
        self._note_events: List[NoteEvent] = []
        self._active_notes: Dict[int, float] = {}  # note -> end_time
        
        # Threading
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Callbacks for real-time updates
        self._status_callbacks: List[Callable[[PlaybackStatus], None]] = []
        
        # Timing precision
        self._start_time = 0.0
        self._pause_time = 0.0
        
        # New Story 1.8 features
        self._tempo_multiplier = 1.0  # 1.0 = normal speed, 0.5 = half speed, 2.0 = double speed
        self._volume_multiplier = 1.0  # 0.0 = mute, 1.0 = full volume
        self._loop_enabled = False
        self._loop_start = 0.0
        self._loop_end = 0.0
        
        # MIDI output configuration
        self._midi_output_enabled = False
        self._midi_notes_sent: Dict[int, bool] = {}  # Track which MIDI notes are currently on
        
        # Learning mode configuration
        self._learning_mode_enabled = False
        self._left_hand_wait_for_notes = False
        self._right_hand_wait_for_notes = False
        # Timestamped queues: [(note, timestamp), ...] - tracks notes with when they were played
        # Bounded deques prevent unbounded memory growth (max 5000 notes each, FIFO)
        self._left_hand_notes_queue: deque = deque(maxlen=5000)
        self._right_hand_notes_queue: deque = deque(maxlen=5000)
        self._timing_window_ms = 500
        self._expected_notes: Dict[str, set] = {'left': set(), 'right': set()}  # Expected notes for current time window
        self._last_queue_cleanup = time.time()  # For periodic queue cleanup
        self._queue_cleanup_interval = 1.0  # Cleanup old notes every 1 second
        self._queue_max_age_seconds = 5.0  # Keep notes for up to 5 seconds
        # Wrong note flash timing
        self._last_wrong_flash_time = -1.0  # When the wrong note flash was triggered (initialized to expired time)
        self._wrong_flash_duration = 0.3  # How long wrong notes stay red (seconds)
        self._wrong_flash_triggered_this_window = False  # Flag to prevent rapid timer resets on consecutive wrong notes
        self._last_expected_notes: set = set()  # Track expected notes to detect window changes
        
        # Load MIDI output settings
        self._load_midi_output_settings()
        
        # Load learning mode settings
        self._load_learning_mode_settings()
        
        # OPTIMIZATION: Initialize color cache (Phase 2A)
        self._refresh_color_cache()
        
        # OPTIMIZATION: Pre-build note-to-LED cache (Phase 2A)
        self._prebuild_note_to_leds_cache()
        
        # OPTIMIZATION: Pre-compute expected notes from loaded events (Phase 2A)
        # This will be called after loading MIDI file, but we initialize here
        self._precompute_expected_notes()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor() if PerformanceMonitor else None
        
        logger.info(f"PlaybackService initialized with {self.num_leds} LEDs, MIDI output: {self._midi_output_enabled}")
    
    def _load_settings_from_service(self, num_leds_override: Optional[int] = None) -> None:
        """Load runtime configuration from the settings service."""
        piano_config_getter = getattr(self._settings_service, 'get_piano_configuration', None)
        led_config_getter = getattr(self._settings_service, 'get_led_configuration', None)
        get_setting = getattr(self._settings_service, 'get_setting', None)

        piano_config = piano_config_getter() if callable(piano_config_getter) else {}
        if not isinstance(piano_config, dict):
            piano_config = {}

        led_config = led_config_getter() if callable(led_config_getter) else {}
        if not isinstance(led_config, dict):
            led_config = {}

        default_piano_size = '88-key'
        if callable(get_setting):
            piano_size = piano_config.get('size') or get_setting('piano', 'size', default_piano_size)
        else:
            piano_size = piano_config.get('size', default_piano_size)

        piano_specs = self._get_piano_specs(piano_size)
        led_count_default = piano_specs.get('keys', 88)
        if callable(get_setting):
            led_count_value = led_config.get('led_count', get_setting('led', 'led_count', led_count_default))
            orientation = led_config.get('orientation', get_setting('led', 'led_orientation', 'normal'))
        else:
            led_count_value = led_config.get('led_count', led_count_default)
            orientation = led_config.get('orientation', 'normal')

        if num_leds_override is not None:
            led_count_value = num_leds_override

        try:
            self.num_leds = max(1, int(led_count_value))
        except (TypeError, ValueError):
            self.num_leds = led_count_default

        self.piano_size = piano_size
        self.led_orientation = orientation

        self.mapping_mode = get_setting('led', 'mapping_mode', 'auto') if callable(get_setting) else 'auto'
        self.leds_per_key = get_setting('led', 'leds_per_key', 3) if callable(get_setting) else 3
        self.mapping_base_offset = get_setting('led', 'mapping_base_offset', 0) if callable(get_setting) else 0
        self.key_mapping = get_setting('led', 'key_mapping', {}) if callable(get_setting) else {}

        midi_start_default = piano_specs['midi_start']
        midi_end_default = piano_specs['midi_end']

        if callable(get_setting):
            self.min_midi_note = piano_config.get('midi_start', get_setting('piano', 'midi_start', midi_start_default))
            self.max_midi_note = piano_config.get('midi_end', get_setting('piano', 'midi_end', midi_end_default))
        else:
            self.min_midi_note = piano_config.get('midi_start', midi_start_default)
            self.max_midi_note = piano_config.get('midi_end', midi_end_default)

    def _load_midi_output_settings(self) -> None:
        """Load MIDI output configuration from settings service."""
        if not self._settings_service:
            self._midi_output_enabled = False
            return

        try:
            get_setting = getattr(self._settings_service, 'get_setting', None)
            if callable(get_setting):
                self._midi_output_enabled = get_setting('hardware', 'midi_output_enabled', False)
                midi_output_device = get_setting('hardware', 'midi_output_device', '')
                
                # If MIDI output is enabled and we have a service, connect to device
                if self._midi_output_enabled and self._midi_output_service and USBMIDIOutputService:
                    if midi_output_device:
                        self._midi_output_service.connect(midi_output_device)
                    else:
                        self._midi_output_service.connect()  # Auto-select first device
                    logger.info(f"MIDI output enabled: {midi_output_device or 'auto-select'}")
            else:
                self._midi_output_enabled = False
        except Exception as e:
            logger.error(f"Error loading MIDI output settings: {e}")
            self._midi_output_enabled = False

    def _load_learning_mode_settings(self) -> None:
        """Load learning mode configuration from settings service."""
        if not self._settings_service:
            self._learning_mode_enabled = False
            return

        try:
            get_setting = getattr(self._settings_service, 'get_setting', None)
            if callable(get_setting):
                self._left_hand_wait_for_notes = get_setting('learning_mode', 'left_hand_wait_for_notes', False)
                self._right_hand_wait_for_notes = get_setting('learning_mode', 'right_hand_wait_for_notes', False)
                self._timing_window_ms = get_setting('learning_mode', 'timing_window_ms', 500)
                
                # Learning mode is enabled if either hand has wait_for_notes enabled
                self._learning_mode_enabled = self._left_hand_wait_for_notes or self._right_hand_wait_for_notes
                
                if self._learning_mode_enabled:
                    logger.info(f"Learning mode enabled - Left hand: {self._left_hand_wait_for_notes}, Right hand: {self._right_hand_wait_for_notes}, Timing: {self._timing_window_ms}ms")
            else:
                self._learning_mode_enabled = False
        except Exception as e:
            logger.error(f"Error loading learning mode settings: {e}")
            self._learning_mode_enabled = False

    def _load_settings_from_config(self, num_leds_override: Optional[int] = None) -> None:
        """Fallback configuration loading from static config values."""
        piano_size = get_config('piano_size', '88-key')
        piano_specs = get_piano_specs(piano_size)

        self.piano_size = piano_size
        fallback_leds = piano_specs.get('keys', 88) or 88
        chosen_leds = num_leds_override if num_leds_override is not None else fallback_leds
        self.num_leds = chosen_leds
        self.led_orientation = get_config('led_orientation', 'normal')

        self.mapping_mode = get_config('mapping_mode', 'auto')
        self.leds_per_key = get_config('leds_per_key', 3)
        self.mapping_base_offset = get_config('mapping_base_offset', 0)
        self.key_mapping = get_config('key_mapping', {})

        self.min_midi_note = piano_specs['midi_start']
        self.max_midi_note = piano_specs['midi_end']

    def refresh_runtime_settings(self) -> None:
        """Reload runtime configuration and regenerate note mappings."""
        if self._settings_service:
            self._load_settings_from_service()
        else:
            self._load_settings_from_config()

        self._precomputed_mapping = self._generate_key_mapping()
        self._load_midi_output_settings()
        self._load_learning_mode_settings()
        logger.debug(
            "Playback service settings refreshed: num_leds=%s orientation=%s mapping_mode=%s",
            self.num_leds,
            self.led_orientation,
            self.mapping_mode
        )
        logger.info("PlaybackService settings refreshed")

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
    
    # ==================== OPTIMIZATION HELPER METHODS (Phase 2A) ====================
    
    def _refresh_color_cache(self) -> None:
        """
        OPTIMIZATION: Cache color conversions to avoid repeated hex-to-RGB conversions.
        Called at init time and when settings change.
        """
        try:
            # Get hand colors from settings
            if self._settings_service:
                left_white_hex = self._settings_service.get_setting('learning', 'left_hand_white_color') or '#ff6b6b'
                right_white_hex = self._settings_service.get_setting('learning', 'right_hand_white_color') or '#006496'
            else:
                left_white_hex = '#ff6b6b'
                right_white_hex = '#006496'
            
            # Convert hex to RGB once and cache
            self._left_color_bright = self._hex_to_rgb(left_white_hex)
            self._right_color_bright = self._hex_to_rgb(right_white_hex)
            
            # Pre-compute dim versions (50% brightness)
            self._left_color_dim = tuple(int(c * 0.5) for c in self._left_color_bright)
            self._right_color_dim = tuple(int(c * 0.5) for c in self._right_color_bright)
            
            logger.debug(f"Color cache refreshed: L={self._left_color_bright}, R={self._right_color_bright}")
        except Exception as e:
            logger.error(f"Error refreshing color cache: {e}")
            # Fallback to defaults
            self._left_color_bright = (255, 107, 107)
            self._right_color_bright = (0, 100, 150)
            self._left_color_dim = (127, 53, 53)
            self._right_color_dim = (0, 50, 75)
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color string to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _prebuild_note_to_leds_cache(self) -> None:
        """
        OPTIMIZATION: Pre-build cache of note-to-LED mappings for all 88 piano keys.
        Avoids repeated lookups during playback.
        """
        try:
            self._note_to_leds_cache.clear()
            for note in range(self.min_midi_note, self.max_midi_note + 1):
                # Use precomputed mapping if available
                if note in self._precomputed_mapping:
                    led_indices = self._precomputed_mapping[note]
                    valid_indices = [idx for idx in led_indices if 0 <= idx < self.num_leds]
                    if valid_indices:
                        self._note_to_leds_cache[note] = valid_indices
                        continue
                
                # Fallback to single LED mapping
                single_led = self._map_note_to_led(note)
                if 0 <= single_led < self.num_leds:
                    self._note_to_leds_cache[note] = [single_led]
            
            logger.debug(f"Built note-to-LED cache for {len(self._note_to_leds_cache)} notes")
        except Exception as e:
            logger.error(f"Error building note-to-LED cache: {e}")
    
    def _precompute_expected_notes(self) -> None:
        """
        OPTIMIZATION: Pre-compute expected notes grouped by time windows for O(1) lookup.
        Called after loading MIDI file.
        
        Builds dictionary: {(time_bin, hand): set(notes)}
        """
        try:
            self._expected_notes_by_window.clear()
            
            if not self._note_events:
                return
            
            # Group events by time bins (windows) and hand
            timing_window_seconds = self._timing_window_ms / 1000.0
            
            for event in self._note_events:
                # Determine hand (left < 60, right >= 60)
                hand = 'left' if event.note < 60 else 'right'
                
                # Calculate time bin (integer index based on timing window)
                time_bin = int(event.time / timing_window_seconds)
                
                # Create key and add to dictionary
                key = (time_bin, hand)
                if key not in self._expected_notes_by_window:
                    self._expected_notes_by_window[key] = set()
                self._expected_notes_by_window[key].add(event.note)
            
            logger.info(f"Pre-computed expected notes: {len(self._expected_notes_by_window)} time windows")
        except Exception as e:
            logger.error(f"Error pre-computing expected notes: {e}")
    
    def _get_expected_notes_fast(self, window_start: float, window_end: float) -> Tuple[set, set]:
        """
        OPTIMIZATION: Fast lookup of expected notes using pre-computed dictionary.
        Replaces O(n) iteration with O(k) where k = number of time bins in range (typically 1-2).
        
        Args:
            window_start: Start time of window
            window_end: End time of window
            
        Returns:
            Tuple of (expected_left_notes, expected_right_notes)
        """
        timing_window_seconds = self._timing_window_ms / 1000.0
        start_bin = int(window_start / timing_window_seconds)
        end_bin = int(window_end / timing_window_seconds) + 1  # Include partial bins
        
        expected_left = set()
        expected_right = set()
        
        # Collect notes from all relevant time bins
        for time_bin in range(start_bin, end_bin + 1):
            if (time_bin, 'left') in self._expected_notes_by_window:
                expected_left.update(self._expected_notes_by_window[(time_bin, 'left')])
            if (time_bin, 'right') in self._expected_notes_by_window:
                expected_right.update(self._expected_notes_by_window[(time_bin, 'right')])
        
        return expected_left, expected_right
    
    def _map_note_to_leds_cached(self, note: int) -> List[int]:
        """
        OPTIMIZATION: Use cached note-to-LED lookups instead of computing each time.
        
        Args:
            note: MIDI note number
            
        Returns:
            List of LED indices for this note
        """
        return self._note_to_leds_cache.get(note, [])
    
    # ==================== END OPTIMIZATION METHODS ====================
    
    @property
    def state(self) -> PlaybackState:
        """Get current playback state"""
        return self._state
    
    @property
    def current_time(self) -> float:
        """Get current playback time"""
        return self._current_time
    
    @property
    def filename(self) -> Optional[str]:
        """Get current filename"""
        return self._filename
    
    @property
    def total_duration(self) -> float:
        """Get total duration"""
        return self._total_duration
    
    @property
    def notes(self) -> List[NoteEvent]:
        """Get loaded note events"""
        return self._note_events
    
    @property
    def led_controller(self):
        """Get LED controller instance"""
        return self._led_controller

    @led_controller.setter
    def led_controller(self, value):
        """Set LED controller"""
        self._led_controller = value
    
    @property
    def tempo_multiplier(self) -> float:
        """Get current tempo multiplier"""
        return self._tempo_multiplier
    
    @property
    def volume_multiplier(self) -> float:
        """Get current volume multiplier"""
        return self._volume_multiplier
    
    @property
    def loop_enabled(self) -> bool:
        """Get loop enabled status"""
        return self._loop_enabled
    
    @property
    def loop_start(self) -> float:
        """Get loop start time"""
        return self._loop_start
    
    @property
    def loop_end(self) -> float:
        """Get loop end time"""
        return self._loop_end
    
    def add_status_callback(self, callback: Callable[[PlaybackStatus], None]):
        """Add a callback for status changes"""
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[PlaybackStatus], None]):
        """Remove a status callback"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status_change(self):
        """Notify all callbacks of status change"""
        status = self.get_status()
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def seek_to_time(self, time_seconds: float) -> bool:
        """Seek to a specific time in the playback"""
        try:
            if not self._note_events:
                logger.error("No MIDI file loaded for seeking")
                return False
            
            # Clamp time to valid range
            time_seconds = max(0.0, min(time_seconds, self._total_duration))
            
            # Update current time
            self._current_time = time_seconds
            
            # If playing, adjust start time to maintain sync
            if self._state == PlaybackState.PLAYING:
                self._start_time = time.time() - self._current_time / self._tempo_multiplier
            
            # Clear active notes and update LEDs
            self._active_notes.clear()
            if self._led_controller:
                self._led_controller.turn_off_all()
            
            logger.info(f"Seeked to {time_seconds:.2f}s")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to seek: {e}")
            return False
    
    def set_tempo(self, multiplier: float) -> bool:
        """Set tempo multiplier (1.0 = normal, 0.5 = half speed, 2.0 = double speed)"""
        try:
            # Clamp tempo to reasonable range
            multiplier = max(0.1, min(multiplier, 4.0))
            
            # If playing, adjust start time to maintain current position
            if self._state == PlaybackState.PLAYING:
                current_real_time = time.time()
                elapsed_playback_time = (current_real_time - self._start_time) * self._tempo_multiplier
                self._start_time = current_real_time - elapsed_playback_time / multiplier
            
            self._tempo_multiplier = multiplier
            logger.info(f"Tempo set to {multiplier:.2f}x")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set tempo: {e}")
            return False
    
    def set_volume(self, multiplier: float) -> bool:
        """Set volume multiplier (0.0 = mute, 1.0 = full volume)"""
        try:
            # Clamp volume to valid range
            multiplier = max(0.0, min(multiplier, 1.0))
            self._volume_multiplier = multiplier
            logger.info(f"Volume set to {multiplier:.2f}")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def set_loop(self, enabled: bool, start_time: float = 0.0, end_time: float = 0.0) -> bool:
        """Set loop parameters"""
        try:
            self._loop_enabled = enabled
            if enabled:
                # Validate and set loop points
                start_time = max(0.0, min(start_time, self._total_duration))
                end_time = max(start_time + 1.0, min(end_time, self._total_duration))
                self._loop_start = start_time
                self._loop_end = end_time
                logger.info(f"Loop enabled: {start_time:.2f}s - {end_time:.2f}s")
            else:
                logger.info("Loop disabled")
            
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set loop: {e}")
            return False
    
    def load_midi_file(self, filename: str) -> bool:
        """
        Load and parse MIDI file for playback.
        
        Args:
            filename: Path to MIDI file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(filename):
                logger.error(f"MIDI file not found: {filename}")
                self._state = PlaybackState.ERROR
                self._notify_status_change()
                return False
            
            # Use MIDI parser if available, otherwise fall back to demo notes
            self._filename = filename
            
            if self._midi_parser:
                # Parse actual MIDI file
                parsed_data = self._midi_parser.parse_file(filename)
                if parsed_data:
                    self._note_events = self._convert_parsed_notes(parsed_data)
                else:
                    logger.warning(f"Failed to parse MIDI file {filename}, using demo notes")
                    self._note_events = self._generate_demo_notes()
            else:
                logger.warning("No MIDI parser available, using demo notes")
                self._note_events = self._generate_demo_notes()
            
            self._total_duration = max(event.time + event.duration for event in self._note_events) if self._note_events else 0
            
            # OPTIMIZATION: Re-build caches after loading new MIDI file (Phase 2A)
            self._prebuild_note_to_leds_cache()
            self._precompute_expected_notes()
            
            self._state = PlaybackState.IDLE
            self._current_time = 0.0
            
            logger.info(f"Loaded MIDI file: {filename} ({len(self._note_events)} notes, {self._total_duration:.1f}s)")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to load MIDI file {filename}: {e}")
            self._state = PlaybackState.ERROR
            self._notify_status_change()
            return False
    
    def _generate_demo_notes(self) -> List[NoteEvent]:
        """Generate demo note events for testing"""
        notes = []
        
        # Generate a simple scale pattern
        scale_notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale
        
        for i, note in enumerate(scale_notes):
            # Each note plays for 0.5 seconds, starting every 0.6 seconds
            notes.append(NoteEvent(
                time=i * 0.6,
                note=note,
                velocity=80,
                duration=0.5
            ))
        
        # Add some harmony
        for i in range(4):
            notes.append(NoteEvent(
                time=i * 1.2 + 0.3,
                note=scale_notes[i] + 12,  # Octave higher
                velocity=60,
                duration=0.8
            ))
        
        return sorted(notes, key=lambda x: x.time)
    
    def _convert_parsed_notes(self, parsed_data: Dict[str, Any]) -> List[NoteEvent]:
        """
        Convert parsed MIDI data to NoteEvent objects.
        
        Args:
            parsed_data: Dictionary containing parsed MIDI data
            
        Returns:
            List[NoteEvent]: Converted note events
        """
        notes = []
        
        try:
            # Extract events from parsed data
            # The MIDI parser returns structure: {'events': [{'time': int, 'note': int, 'velocity': int, 'type': str, 'led_index': int}]}
            if 'events' in parsed_data:
                # Group note_on and note_off events to calculate durations
                active_notes = {}  # note -> (start_time, velocity)
                
                for event_data in parsed_data['events']:
                    note_num = event_data.get('note', 60)
                    time_ms = event_data.get('time', 0)
                    time_sec = time_ms / 1000.0  # Convert milliseconds to seconds
                    velocity = event_data.get('velocity', 80)
                    event_type = event_data.get('type', 'on')
                    
                    if event_type == 'on' and velocity > 0:
                        # Note starts
                        active_notes[note_num] = (time_sec, velocity)
                    elif event_type == 'off' or (event_type == 'on' and velocity == 0):
                        # Note ends
                        if note_num in active_notes:
                            start_time, note_velocity = active_notes[note_num]
                            duration = max(0.1, time_sec - start_time)  # Minimum duration of 0.1s
                            
                            notes.append(NoteEvent(
                                time=start_time,
                                note=note_num,
                                velocity=note_velocity,
                                duration=duration,
                                channel=0
                            ))
                            
                            del active_notes[note_num]
                
                # Handle any remaining active notes (notes that never got a note_off)
                max_time = max([event['time'] / 1000.0 for event in parsed_data['events']], default=0)
                for note_num, (start_time, velocity) in active_notes.items():
                    duration = max(0.5, max_time - start_time)  # Default duration
                    notes.append(NoteEvent(
                        time=start_time,
                        note=note_num,
                        velocity=velocity,
                        duration=duration,
                        channel=0
                    ))
            
            logger.info(f"Converted {len(notes)} notes from parsed MIDI data")
            
        except Exception as e:
            logger.error(f"Error converting parsed MIDI data: {e}")
            # Fall back to demo notes on error
            notes = self._generate_demo_notes()
        
        return sorted(notes, key=lambda x: x.time)
    
    def start_playback(self) -> bool:
        """
        Start playback of loaded MIDI file.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            if self._state == PlaybackState.PLAYING:
                logger.warning("Playback already in progress")
                return True
            
            if not self._note_events:
                logger.error("No MIDI file loaded")
                return False
            
            # Reset events
            self._stop_event.clear()
            self._pause_event.clear()
            
            # Load and reset learning mode
            self._load_learning_mode_settings()
            self._left_hand_notes_queue.clear()
            self._right_hand_notes_queue.clear()
            self._last_queue_cleanup = time.time()
            
            # Start performance monitoring
            if self.performance_monitor:
                self.performance_monitor.reset_metrics()
                self.performance_monitor.start_monitoring()
            
            # Start playback thread
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
            
            self._state = PlaybackState.PLAYING
            self._start_time = time.time() - self._current_time / self._tempo_multiplier  # Account for resume and tempo
            
            logger.info("Playback started")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            self._state = PlaybackState.ERROR
            self._notify_status_change()
            return False
    
    def pause_playback(self) -> bool:
        """
        Pause or resume playback.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self._state == PlaybackState.PLAYING:
                self._pause_event.set()
                self._state = PlaybackState.PAUSED
                self._pause_time = time.time()
                logger.info("Playback paused")
            elif self._state == PlaybackState.PAUSED:
                self._pause_event.clear()
                self._state = PlaybackState.PLAYING
                # Adjust start time to account for pause duration
                pause_duration = time.time() - self._pause_time
                self._start_time += pause_duration
                logger.info("Playback resumed")
            else:
                logger.warning(f"Cannot pause/resume from state: {self._state}")
                return False
            
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause/resume playback: {e}")
            return False
    
    def stop_playback(self) -> bool:
        """
        Stop playback and reset position.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._stop_event.set()
            self._pause_event.clear()
            
            # Wait for playback thread to finish
            if self._playback_thread and self._playback_thread.is_alive():
                self._playback_thread.join(timeout=1.0)
            
            # Stop performance monitoring
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()
            
            # Turn off all LEDs
            if self._led_controller:
                self._led_controller.turn_off_all()
            
            # Send MIDI note_off for all active notes
            if self._midi_output_enabled and self._midi_output_service:
                for note in list(self._active_notes.keys()):
                    self._send_midi_note_off(note)
            
            self._state = PlaybackState.STOPPED
            self._current_time = 0.0
            self._active_notes.clear()
            self._midi_notes_sent.clear()
            
            logger.info("Playback stopped")
            self._notify_status_change()
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop playback: {e}")
            return False
    
    def _playback_loop(self):
        """Main playback loop running in separate thread"""
        try:
            logger.info("Playback loop started")
            last_status_update = 0
            last_led_update = 0
            
            # Reload learning mode settings at start of playback
            if self._learning_mode_enabled:
                self._load_learning_mode_settings()
            
            while not self._stop_event.is_set():
                current_loop_time = time.time()
                
                # Handle pause
                if self._pause_event.is_set():
                    time.sleep(0.05)  # Reduced pause check interval
                    continue
                
                # Handle learning mode pause
                if self._learning_mode_enabled:
                    should_pause = self._check_learning_mode_pause()
                    if should_pause:
                        # Update LEDs even while paused (shows expected notes and flash countdown)
                        self._update_leds()
                        time.sleep(0.05)  # Brief sleep before checking again
                        continue
                
                # Update current time with tempo adjustment
                self._current_time = (current_loop_time - self._start_time) * self._tempo_multiplier
                
                # Handle loop functionality
                if self._loop_enabled and self._current_time >= self._loop_end:
                    logger.info(f"Loop: jumping from {self._current_time:.2f}s to {self._loop_start:.2f}s")
                    self._current_time = self._loop_start
                    self._start_time = current_loop_time - self._current_time / self._tempo_multiplier
                    self._active_notes.clear()
                    if self._led_controller:
                        self._led_controller.turn_off_all()
                
                # Check if playback is complete (only if not looping)
                elif self._current_time >= self._total_duration:
                    logger.info("Playback completed")
                    break
                
                # Process note events
                note_processing_start = time.time()
                self._process_note_events()
                
                # Track note processing performance
                if self.performance_monitor:
                    note_processing_time = time.time() - note_processing_start
                    self.performance_monitor.record_note_processing_time(note_processing_time)
                
                # Update LED display (limit to 60 FPS max)
                if current_loop_time - last_led_update >= 0.0167:  # ~60 FPS
                    self._update_leds()
                    
                    # Track LED update
                    if self.performance_monitor:
                        self.performance_monitor.record_led_update()
                    
                    last_led_update = current_loop_time
                
                # Notify status update (limit to 4 Hz)
                if current_loop_time - last_status_update >= 0.25:  # Every 0.25 seconds
                    self._notify_status_change()
                    last_status_update = current_loop_time
                
                # Sleep for timing precision (reduced for better responsiveness)
                time.sleep(0.005)  # 5ms resolution
            
            # Playback finished
            if not self._stop_event.is_set():
                # Natural completion
                self._state = PlaybackState.STOPPED
                self._current_time = self._total_duration
                if self._led_controller:
                    self._led_controller.turn_off_all()
                self._notify_status_change()
            
        except Exception as e:
            logger.error(f"Error in playback loop: {e}")
            self._state = PlaybackState.ERROR
            self._notify_status_change()
    
    def _process_note_events(self):
        """Process note events at current time, including MIDI output"""
        current_time = self._current_time
        
        # Find notes that should start now
        for event in self._note_events:
            if abs(event.time - current_time) < 0.02:  # 20ms tolerance
                if event.note not in self._active_notes:
                    self._active_notes[event.note] = current_time + event.duration
                    self._midi_notes_sent[event.note] = False  # Mark as not yet sent to MIDI output
                    
                    # Send MIDI output if enabled
                    if self._midi_output_enabled and self._midi_output_service:
                        self._send_midi_note_on(event.note, event.velocity)
                    
                    logger.debug(f"Note ON: {event.note} at {current_time:.2f}s")
        
        # Remove notes that should end
        notes_to_remove = []
        for note, end_time in self._active_notes.items():
            if current_time >= end_time:
                notes_to_remove.append(note)
                
                # Send MIDI note_off if enabled
                if self._midi_output_enabled and self._midi_output_service:
                    self._send_midi_note_off(note)
                
                logger.debug(f"Note OFF: {note} at {current_time:.2f}s")
        
        for note in notes_to_remove:
            del self._active_notes[note]
            if note in self._midi_notes_sent:
                del self._midi_notes_sent[note]
    
    def _cleanup_old_queued_notes(self) -> None:
        """
        Periodically clean up old notes from learning mode queues.
        
        This prevents unbounded memory growth by removing notes that are too old
        to be relevant for the current timing window. Called approximately every
        second when learning mode is active.
        
        Notes older than _queue_max_age_seconds are removed.
        """
        current_time = time.time()
        if current_time - self._last_queue_cleanup < self._queue_cleanup_interval:
            return  # Not time for cleanup yet
        
        self._last_queue_cleanup = current_time
        
        # Calculate cutoff time: keep notes from last N seconds
        cutoff_time = self._current_time - self._queue_max_age_seconds
        
        # Filter out old notes from left hand queue
        old_left_count = len(self._left_hand_notes_queue)
        self._left_hand_notes_queue = deque(
            ((note, ts) for note, ts in self._left_hand_notes_queue
             if ts >= cutoff_time),
            maxlen=5000
        )
        left_removed = old_left_count - len(self._left_hand_notes_queue)
        
        # Filter out old notes from right hand queue
        old_right_count = len(self._right_hand_notes_queue)
        self._right_hand_notes_queue = deque(
            ((note, ts) for note, ts in self._right_hand_notes_queue
             if ts >= cutoff_time),
            maxlen=5000
        )
        right_removed = old_right_count - len(self._right_hand_notes_queue)
        
        if left_removed > 0 or right_removed > 0:
            logger.debug(f"Queue cleanup at {self._current_time:.2f}s: "
                        f"removed {left_removed} left, {right_removed} right notes "
                        f"(older than {self._queue_max_age_seconds}s)")
    
    def record_midi_note_played(self, note: int, hand: str) -> None:
        """
        Record that a MIDI note was played by a specific hand during learning mode.
        
        Stores note with PLAYBACK timestamp (not wall clock time!) in a queue.
        Uses playback time to match against expected notes in the MIDI file.
        
        Args:
            note: MIDI note number (0-127)
            hand: 'left' or 'right'
        """
        # Only record if learning mode is enabled
        if not self._learning_mode_enabled:
            logger.debug(f"Ignoring note {note} - learning mode not enabled")
            return
        
        # CRITICAL: Use playback time, NOT wall clock time!
        # This must match self._current_time used in _check_learning_mode_pause()
        playback_time = self._current_time
        
        logger.info(f"🎵 RECORDING NOTE: {note} ({hand} hand) at playback time {playback_time:.3f}s (enabled={self._learning_mode_enabled})")
        
        if hand == 'left':
            self._left_hand_notes_queue.append((note, playback_time))
            logger.info(f"   └─ Left queue now has {len(self._left_hand_notes_queue)} notes: {[(n, f'{t:.2f}s') for n, t in list(self._left_hand_notes_queue)[-3:]]}")
        elif hand == 'right':
            self._right_hand_notes_queue.append((note, playback_time))
            logger.info(f"   └─ Right queue now has {len(self._right_hand_notes_queue)} notes: {[(n, f'{t:.2f}s') for n, t in list(self._right_hand_notes_queue)[-3:]]}")
        else:
            logger.warning(f"Unknown hand: {hand}")
    
    def _check_learning_mode_pause(self) -> bool:
        """
        Check if playback should pause for learning mode.
        
        Uses timestamped note queues to filter notes within the current timing window.
        Only counts notes that were played within the expected time range.
        Visualizes expected notes on LEDs during pause.
        When all required notes are played correctly:
        1. Visualizes the satisfied notes on LEDs
        2. Clears pressed keys from memory
        3. Advances to playback of the next note(s)
        
        Returns:
            bool: True if should pause, False if should continue
        """
        if not self._learning_mode_enabled:
            return False
        
        # Periodically clean up old notes to prevent unbounded memory growth
        self._cleanup_old_queued_notes()
        
        # If neither hand requires notes, don't pause
        if not self._left_hand_wait_for_notes and not self._right_hand_wait_for_notes:
            return False
        
        # Get the current timing window
        # Look at notes that are CURRENTLY ACTIVE (already started, not yet ended)
        timing_window_seconds = self._timing_window_ms / 1000.0
        
        # Find expected notes that are currently playing or about to play
        # Include notes that started up to 1 second ago (for overlap/legato)
        # and notes that start in the next 0.5 seconds
        window_start = self._current_time - 1.0  # Look back 1 second
        window_end = self._current_time + timing_window_seconds
        
        # OPTIMIZATION: Use fast lookup (Phase 2A) instead of O(n) iteration
        # This replaces the loop that checked all events
        if self._expected_notes_by_window:
            # Use pre-computed expected notes lookup
            expected_left_notes, expected_right_notes = self._get_expected_notes_fast(window_start, window_end)
        else:
            # Fallback to slow path if caches not ready
            expected_left_notes = set()
            expected_right_notes = set()
            
            for event in self._note_events:
                # Include notes that START within our window
                # (They may have already started or be about to start)
                if window_start <= event.time < window_end:
                    if event.note < 60:  # Left hand (below Middle C)
                        expected_left_notes.add(event.note)
                    else:  # Right hand (Middle C and above)
                        expected_right_notes.add(event.note)
        
        # Detect window changes to reset flash state
        # When we move to a new set of expected notes, reset the flash trigger flag
        current_expected = expected_left_notes | expected_right_notes
        if current_expected != self._last_expected_notes:
            self._wrong_flash_triggered_this_window = False
            self._last_expected_notes = current_expected
        
        # Extract notes from queues that fall within the EXPECTED timing window
        # CRITICAL FIX: Use same window as expected notes to avoid dead zones
        # Notes must be within [window_start, window_end] to be considered "played"
        # Use LISTS to preserve consecutive identical notes (not sets!)
        played_left_notes = []
        played_right_notes = []
        
        # Use the SAME timing window for acceptance as for expected notes
        # This eliminates the "dead zone" where notes are expected but not accepted
        acceptance_start = window_start
        acceptance_end = window_end
        
        for note, timestamp in self._left_hand_notes_queue:
            if acceptance_start <= timestamp <= acceptance_end:
                played_left_notes.append(note)
        
        for note, timestamp in self._right_hand_notes_queue:
            if acceptance_start <= timestamp <= acceptance_end:
                played_right_notes.append(note)
        
        # Debug: Show current state every ~500ms (not every frame!)
        if int(self._current_time * 2) != int((self._current_time - 0.01) * 2):  # Every ~500ms
            logger.info(f"📊 Learning mode check at {self._current_time:.2f}s:"
                       f" Expected L:{sorted(expected_left_notes)} R:{sorted(expected_right_notes)} |"
                       f" Played L:{played_left_notes} R:{played_right_notes} |"
                       f" L.queue:{len(self._left_hand_notes_queue)} R.queue:{len(self._right_hand_notes_queue)}")
        
        # Convert played note lists to sets for comparison (deduplicates for subset check)
        played_left_set = set(played_left_notes)
        played_right_set = set(played_right_notes)
        
        # Check if all expected notes have been played
        left_satisfied = True
        right_satisfied = True
        
        if self._left_hand_wait_for_notes and expected_left_notes:
            left_satisfied = expected_left_notes.issubset(played_left_set)
        
        if self._right_hand_wait_for_notes and expected_right_notes:
            right_satisfied = expected_right_notes.issubset(played_right_set)
        
        # CRITICAL: Check for WRONG notes first - these take priority over satisfaction!
        # If user plays any wrong notes, we must PAUSE and force them to correct before continuing
        wrong_left_notes = played_left_set - expected_left_notes
        wrong_right_notes = played_right_set - expected_right_notes
        
        has_expected_notes = expected_left_notes or expected_right_notes
        
        if wrong_left_notes or wrong_right_notes:
            all_wrong = wrong_left_notes | wrong_right_notes
            logger.warning(f"❌ Wrong notes played: {sorted(all_wrong)}")
            self._highlight_wrong_notes(all_wrong)
            # Record when the wrong flash was triggered, but only once per timing window
            # This prevents rapid timer resets when multiple wrong notes are played in quick succession
            if not self._wrong_flash_triggered_this_window:
                self._last_wrong_flash_time = self._current_time
                self._wrong_flash_triggered_this_window = True
            
            # CRITICAL: Show expected notes on LEDs to guide user
            if has_expected_notes:
                self._highlight_expected_notes(expected_left_notes, expected_right_notes,
                                              played_left_notes, played_right_notes)
            
            logger.debug(f"Learning mode PAUSING - user played wrong notes, must correct before proceeding")
            # RETURN TRUE HERE: Pause playback until wrong notes are corrected
            # Do NOT clear queue - we need to keep the wrong notes for visual feedback
            # Do NOT proceed to satisfaction check - wrong notes take absolute priority
            return True
        
        # Only if NO wrong notes: check if all required notes are satisfied
        all_satisfied = left_satisfied and right_satisfied
        
        # If all required notes are satisfied: clear them and proceed
        if all_satisfied and has_expected_notes:
            logger.info(f"Learning mode: ✓ All required notes satisfied at {self._current_time:.2f}s. "
                       f"Left: {sorted(expected_left_notes)}, Right: {sorted(expected_right_notes)}")
            
            # Show satisfied notes on LEDs briefly (bright colors)
            self._highlight_expected_notes(expected_left_notes, expected_right_notes,
                                          played_left_notes, played_right_notes)
            
            # CLEAR PRESSED KEYS: Remove notes from queues that are now satisfied
            # This prevents them from carrying over to the next measure
            notes_to_clear = expected_left_notes | expected_right_notes
            
            # Remove cleared notes from queues
            self._left_hand_notes_queue = deque(
                (note, ts) for note, ts in self._left_hand_notes_queue
                if note not in notes_to_clear
            )
            self._right_hand_notes_queue = deque(
                (note, ts) for note, ts in self._right_hand_notes_queue
                if note not in notes_to_clear
            )
            
            logger.info(f"Learning mode: Cleared satisfied notes from queues. "
                       f"Remaining left queue: {len(self._left_hand_notes_queue)}, "
                       f"Remaining right queue: {len(self._right_hand_notes_queue)}")
            
            # PROCEED TO PLAYBACK: Return False to allow playback to continue
            # This will advance the playback time to the next note
            return False
        
        # If there are no expected notes at all, don't pause (let playback continue)
        if not has_expected_notes:
            logger.debug(f"No expected notes at {self._current_time:.2f}s, continuing playback")
            return False
        
        # Not all required notes satisfied yet - show guidance and pause
        logger.debug(f"Learning mode PAUSING - waiting for all required notes")
        
        # Visualize expected notes on LEDs to show user what's needed
        self._highlight_expected_notes(expected_left_notes, expected_right_notes, 
                                      played_left_notes, played_right_notes)
        
        # Return True: Pause playback until all notes are played correctly
        return True
    
    def _send_midi_note_on(self, note: int, velocity: int) -> None:
        """
        Send MIDI note_on with velocity adjustment for volume multiplier.
        
        Args:
            note: MIDI note number
            velocity: Original velocity from MIDI file
        """
        try:
            # Apply volume multiplier to velocity
            adjusted_velocity = max(1, int(velocity * self._volume_multiplier))
            adjusted_velocity = min(127, adjusted_velocity)
            
            self._midi_output_service.send_note_on(note, adjusted_velocity, channel=0)
            self._midi_notes_sent[note] = True
            logger.debug(f"Sent MIDI note_on: note={note}, velocity={adjusted_velocity}")
        except Exception as e:
            logger.error(f"Error sending MIDI note_on: {e}")
    
    def _send_midi_note_off(self, note: int) -> None:
        """
        Send MIDI note_off message.
        
        Args:
            note: MIDI note number
        """
        try:
            if self._midi_notes_sent.get(note, False):
                self._midi_output_service.send_note_off(note, channel=0)
                logger.debug(f"Sent MIDI note_off: note={note}")
        except Exception as e:
            logger.error(f"Error sending MIDI note_off: {e}")
    
    def _highlight_expected_notes(self, expected_left: set, expected_right: set, 
                                  played_left, played_right) -> None:
        """
        Highlight expected notes on LEDs to show user which notes to play.
        
        Unsatisfied expected notes are shown in yellow/green (per-hand colors with reduced brightness).
        Already-played notes are shown in bright color (indicating success).
        
        If a wrong note flash is still active (within 300ms of trigger), shows red instead.
        After the flash timeout expires, returns to normal highlighting.
        
        Args:
            expected_left: Set of expected MIDI notes for left hand
            expected_right: Set of expected MIDI notes for right hand
            played_left: List or set of notes already played by left hand
            played_right: List or set of notes already played by right hand
        """
        if not self._led_controller:
            return
        
        # Convert played notes to sets if they're lists (for membership checking)
        if isinstance(played_left, list):
            played_left = set(played_left)
        if isinstance(played_right, list):
            played_right = set(played_right)
        
        # Check if wrong note flash is still active
        flash_elapsed = self._current_time - self._last_wrong_flash_time
        if flash_elapsed < self._wrong_flash_duration:
            # Flash is still active, don't update highlights yet
            logger.debug(f"Wrong note flash active ({flash_elapsed:.3f}s / {self._wrong_flash_duration}s)")
            return
        
        # Flash has expired, show normal highlighting
        try:
            led_data = {}
            
            # OPTIMIZATION: Use cached colors (Phase 2A) instead of re-computing each time
            left_color_bright = self._left_color_bright or (255, 107, 107)
            right_color_bright = self._right_color_bright or (0, 100, 150)
            left_color_dim = self._left_color_dim or (127, 53, 53)
            right_color_dim = self._right_color_dim or (0, 50, 75)
            
            # Highlight expected left hand notes
            for note in expected_left:
                # OPTIMIZATION: Use cached note-to-LED lookup (Phase 2A)
                led_indices = self._map_note_to_leds_cached(note)
                # Bright color if played, dim if not
                color = left_color_bright if note in played_left else left_color_dim
                for led_index in led_indices:
                    if 0 <= led_index < self.num_leds:
                        led_data[led_index] = color
            
            # Highlight expected right hand notes
            for note in expected_right:
                # OPTIMIZATION: Use cached note-to-LED lookup (Phase 2A)
                led_indices = self._map_note_to_leds_cached(note)
                # Bright color if played, dim if not
                color = right_color_bright if note in played_right else right_color_dim
                for led_index in led_indices:
                    if 0 <= led_index < self.num_leds:
                        led_data[led_index] = color
            
            # Turn off all LEDs first, then set learning mode highlights
            self._led_controller.turn_off_all()
            
            if led_data:
                self._led_controller.set_multiple_leds(led_data, auto_show=True)
                logger.debug(f"Learning mode: Highlighted {len(led_data)} LEDs for expected notes")
        
        except Exception as e:
            logger.error(f"Error highlighting expected notes: {e}")
    
    def _highlight_wrong_notes(self, wrong_notes: set) -> None:
        """
        Highlight wrong notes in red to provide immediate feedback.
        
        Args:
            wrong_notes: Set of MIDI notes that were played incorrectly
        """
        if not self._led_controller or not wrong_notes:
            return
        
        try:
            led_data = {}
            red_color = (255, 0, 0)  # Bright red
            
            # Light up wrong notes in red
            for note in wrong_notes:
                led_indices = self._map_note_to_leds(note)
                for led_index in led_indices:
                    if 0 <= led_index < self.num_leds:
                        led_data[led_index] = red_color
            
            if led_data:
                self._led_controller.set_multiple_leds(led_data, auto_show=True)
                logger.info(f"Learning mode: Highlighted {len(led_data)} LEDs in red for wrong notes")
        
        except Exception as e:
            logger.error(f"Error highlighting wrong notes: {e}")
    
    def _update_leds(self):
        """Update LED display based on active notes"""
        if not self._led_controller:
            return
        
        try:
            # Prepare LED data for batch update
            led_data = {}
            
            # Map active notes to LEDs using multi-LED mapping
            for note in self._active_notes.keys():
                led_indices = self._map_note_to_leds(note)
                color = self._get_note_color(note)
                # Apply volume multiplier to brightness
                adjusted_color = tuple(int(c * self._volume_multiplier) for c in color)
                
                # Set color for all LEDs mapped to this note
                for led_index in led_indices:
                    if 0 <= led_index < self.num_leds:
                        led_data[led_index] = adjusted_color
            
            # Turn off all LEDs first, then set active ones
            self._led_controller.turn_off_all()
            
            # Use batch update for better performance
            if led_data:
                self._led_controller.set_multiple_leds(led_data, auto_show=True)
        
        except Exception as e:
            logger.error(f"Error updating LEDs: {e}")
    
    def _map_note_to_led(self, note: int) -> int:
        """
        Map MIDI note to LED index with configuration and orientation support.
        
        Args:
            note: MIDI note number (0-127)
            
        Returns:
            int: LED index
        """
        # Use configured piano range
        if note < self.min_midi_note:
            note = self.min_midi_note
        elif note > self.max_midi_note:
            note = self.max_midi_note
        
        # Map to logical LED range
        piano_range = self.max_midi_note - self.min_midi_note
        logical_index = int((note - self.min_midi_note) * (self.num_leds - 1) / piano_range)
        
        return logical_index
    
    def _map_note_to_leds(self, note: int) -> List[int]:
        """
        Map MIDI note to multiple LED indices based on configuration.
        
        Args:
            note: MIDI note number (0-127)
            
        Returns:
            List[int]: List of LED indices for this note
        """
        # Use precomputed mapping if available
        if note in self._precomputed_mapping:
            led_indices = self._precomputed_mapping[note]
            # Filter to ensure all indices are within bounds
            valid_indices = [idx for idx in led_indices if 0 <= idx < self.num_leds]
            if valid_indices:
                return valid_indices
        
        # Fallback to single LED mapping for backward compatibility
        single_led = self._map_note_to_led(note)
        return [single_led] if 0 <= single_led < self.num_leds else []
    
    def _generate_key_mapping(self) -> Dict[int, List[int]]:
        """
        Generate key-to-LED mapping based on configuration.
        Uses the calibrated adjusted mapping which includes offsets, trims, and selections.
        
        Returns:
            Dict[int, List[int]]: Mapping of MIDI note to list of LED indices
        """
        try:
            # Try to use calibrated adjusted mapping first (includes offsets, trims, selections)
            if self._settings_service:
                try:
                    from backend.config import get_canonical_led_mapping
                    result = get_canonical_led_mapping(self._settings_service)
                    if result.get('success'):
                        canonical_mapping = result.get('mapping', {})
                        if canonical_mapping:
                            # Convert key indices (0-87) to MIDI notes (21-108)
                            midi_mapping = {}
                            for key_index, led_indices in canonical_mapping.items():
                                midi_note = key_index + 21  # Convert index to MIDI note
                                if isinstance(led_indices, list) and led_indices:
                                    midi_mapping[midi_note] = led_indices
                            
                            if midi_mapping:
                                logger.info(f"Using canonical LED mapping with {len(midi_mapping)} keys (includes calibration adjustments)")
                                return midi_mapping
                except Exception as e:
                    logger.warning(f"Could not load canonical LED mapping: {e}, falling back to auto-generated")
            
            # Fallback to auto-generated mapping if canonical not available
            from backend.config import generate_auto_key_mapping
            
            if self.mapping_mode == 'manual' and self.key_mapping:
                # Use manual mapping from configuration
                mapping = {}
                for note_str, led_indices in self.key_mapping.items():
                    try:
                        note = int(note_str)
                        indices: List[int]
                        if isinstance(led_indices, int):
                            indices = [led_indices]
                        elif isinstance(led_indices, list):
                            indices = []
                            for raw_idx in led_indices:
                                try:
                                    indices.append(int(raw_idx))
                                except (TypeError, ValueError):
                                    continue
                        else:
                            try:
                                indices = [int(led_indices)]
                            except (TypeError, ValueError):
                                continue

                        if self.led_orientation == 'reversed':
                            indices = [self.num_leds - 1 - idx for idx in indices if 0 <= idx < self.num_leds]
                        else:
                            indices = [idx for idx in indices if 0 <= idx < self.num_leds]

                        mapping[note] = indices
                    except (ValueError, TypeError):
                        continue
                return mapping
            
            elif self.mapping_mode in ['auto', 'proportional']:
                # Use auto-generated mapping
                auto_mapping = generate_auto_key_mapping(
                    piano_size=self.piano_size,
                    led_count=self.num_leds,
                    led_orientation='normal',
                    leds_per_key=self.leds_per_key,
                    mapping_base_offset=self.mapping_base_offset
                )
                return auto_mapping
            
            else:
                # Fallback to single LED mapping
                mapping = {}
                for note in range(self.min_midi_note, self.max_midi_note + 1):
                    single_led = self._map_note_to_led(note)
                    if 0 <= single_led < self.num_leds:
                        mapping[note] = [single_led]
                return mapping
                
        except Exception as e:
            logger.error(f"Error generating key mapping: {e}")
            # Fallback to single LED mapping
            mapping = {}
            for note in range(self.min_midi_note, self.max_midi_note + 1):
                single_led = self._map_note_to_led(note)
                if 0 <= single_led < self.num_leds:
                    mapping[note] = [single_led]
            return mapping
    
    def _get_note_color(self, note: int) -> tuple:
        """
        Get color for a note based on its pitch.
        
        Args:
            note: MIDI note number
            
        Returns:
            tuple: RGB color tuple
        """
        # Color mapping based on note position in octave
        note_in_octave = note % 12
        colors = [
            (255, 0, 0),    # C - Red
            (255, 127, 0),  # C# - Orange
            (255, 255, 0),  # D - Yellow
            (127, 255, 0),  # D# - Yellow-Green
            (0, 255, 0),    # E - Green
            (0, 255, 127),  # F - Green-Cyan
            (0, 255, 255),  # F# - Cyan
            (0, 127, 255),  # G - Cyan-Blue
            (0, 0, 255),    # G# - Blue
            (127, 0, 255),  # A - Blue-Purple
            (255, 0, 255),  # A# - Purple
            (255, 0, 127),  # B - Purple-Red
        ]
        
        return colors[note_in_octave]
    
    def get_status(self) -> PlaybackStatus:
        """Get current playback status"""
        progress = 0.0
        if self._total_duration > 0:
            progress = min(100.0, (self._current_time / self._total_duration) * 100)
        
        return PlaybackStatus(
            state=self._state,
            current_time=self._current_time,
            total_duration=self._total_duration,
            filename=self._filename,
            progress_percentage=progress,
            error_message=None if self._state != PlaybackState.ERROR else "Playback error occurred"
        )
    
    def is_playback_active(self) -> bool:
        """Check if playback is currently active (playing, not paused or idle)"""
        return self._state == PlaybackState.PLAYING
    
    def get_extended_status(self) -> Dict[str, Any]:
        """Get extended playback status including new controls"""
        basic_status = self.get_status()
        return {
            'state': basic_status.state.value,
            'current_time': basic_status.current_time,
            'total_duration': basic_status.total_duration,
            'filename': basic_status.filename,
            'progress_percentage': basic_status.progress_percentage,
            'error_message': basic_status.error_message,
            'tempo_multiplier': self._tempo_multiplier,
            'volume_multiplier': self._volume_multiplier,
            'loop_enabled': self._loop_enabled,
            'loop_start': self._loop_start,
            'loop_end': self._loop_end
        }
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop_playback()
            self._status_callbacks.clear()
            logger.info("PlaybackService cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
