#!/usr/bin/env python3
"""
USB MIDI Input Service - Real-time MIDI input processing
Handles USB MIDI device detection, input processing, and LED visualization
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from logging_config import get_logger

logger = get_logger(__name__)

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    mido = None

try:
    from led_controller import LEDController
except ImportError:
    LEDController = None

# Configuration imports with fallbacks
try:
    from config import get_config, get_piano_specs
except ImportError:
    def get_config(key, default=None):
        return default
    def get_piano_specs(piano_size):
        return {'midi_start': 21, 'midi_end': 108, 'keys': 88}

class MIDIInputState(Enum):
    """MIDI input service state enumeration"""
    IDLE = "idle"
    LISTENING = "listening"
    ERROR = "error"

@dataclass
class MIDIDevice:
    """Represents a MIDI input device"""
    name: str
    id: int
    type: str = "usb"
    status: str = "available"

@dataclass
class MIDIInputEvent:
    """Represents a real-time MIDI input event"""
    timestamp: float
    note: int
    velocity: int
    channel: int
    event_type: str  # 'note_on' or 'note_off'

class USBMIDIInputService:
    """Service for real-time USB MIDI input processing and LED visualization"""
    
    def __init__(self, led_controller=None, 
                 websocket_callback: Optional[Callable] = None,
                 settings_service=None):
        """
        Initialize USB MIDI input service.
        
        Args:
            led_controller: LED controller instance for real-time visualization
            websocket_callback: Callback function for WebSocket event broadcasting
            settings_service: Settings service instance for retrieving configuration
        """
        self._led_controller = led_controller
        self._websocket_callback = websocket_callback
        self.settings_service = settings_service
        self._controller_led_capacity: Optional[int] = None

        if self.settings_service:
            self._load_settings_from_service()
        else:
            self._load_settings_from_config()

        self._sync_led_geometry()

        # Generate precomputed mapping for performance
        self._precomputed_mapping = self._generate_key_mapping()
        
        # Service state
        self._state = MIDIInputState.IDLE
        self._current_device: Optional[str] = None
        self._input_port = None
        
        # Active notes tracking for sustain and LED management
        self._active_notes: Dict[int, Dict[str, Any]] = {}  # note -> {velocity, timestamp, led_index}
        
        # Threading for real-time input processing
        self._input_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # Performance tracking
        self._event_count = 0
        self._last_event_time = 0.0
        
        # Check MIDI availability
        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - MIDI input disabled")
            self._state = MIDIInputState.ERROR

    def _load_settings_from_service(self):
        """Load runtime configuration from the settings service."""
        piano_config_getter = getattr(self.settings_service, 'get_piano_configuration', None)
        led_config_getter = getattr(self.settings_service, 'get_led_configuration', None)
        get_setting = getattr(self.settings_service, 'get_setting', None)

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

        led_count_default = 246
        if callable(get_setting):
            led_count_value = led_config.get('led_count', get_setting('led', 'led_count', led_count_default))
            orientation = led_config.get('orientation', get_setting('led', 'led_orientation', 'normal'))
        else:
            led_count_value = led_config.get('led_count', led_count_default)
            orientation = led_config.get('orientation', 'normal')

        try:
            self.num_leds = max(1, int(led_count_value))
        except (TypeError, ValueError):
            self.num_leds = led_count_default

        self.piano_size = piano_size
        self.led_orientation = orientation

        # Multi-LED mapping configuration from settings
        self.mapping_mode = get_setting('led', 'mapping_mode', 'auto') if callable(get_setting) else 'auto'
        self.leds_per_key = get_setting('led', 'leds_per_key', 3) if callable(get_setting) else 3
        self.mapping_base_offset = get_setting('led', 'mapping_base_offset', 0) if callable(get_setting) else 0
        self.key_mapping = get_setting('led', 'key_mapping', {}) if callable(get_setting) else {}

        piano_specs = get_piano_specs(self.piano_size)
        midi_start_default = piano_specs['midi_start']
        midi_end_default = piano_specs['midi_end']

        if callable(get_setting):
            self.min_midi_note = piano_config.get('midi_start', get_setting('piano', 'midi_start', midi_start_default))
            self.max_midi_note = piano_config.get('midi_end', get_setting('piano', 'midi_end', midi_end_default))
        else:
            self.min_midi_note = piano_config.get('midi_start', midi_start_default)
            self.max_midi_note = piano_config.get('midi_end', midi_end_default)

    def _load_settings_from_config(self):
        """Fallback configuration loading from static config."""
        self.piano_size = get_config('piano_size', '88-key')
        self.num_leds = get_config('led_count', 246)
        self.led_orientation = get_config('led_orientation', 'normal')

        # Multi-LED mapping configuration
        self.mapping_mode = get_config('mapping_mode', 'auto')
        self.leds_per_key = get_config('leds_per_key', 3)
        self.mapping_base_offset = get_config('mapping_base_offset', 0)
        self.key_mapping = get_config('key_mapping', {})

        piano_specs = get_piano_specs(self.piano_size)
        self.min_midi_note = piano_specs['midi_start']
        self.max_midi_note = piano_specs['midi_end']
    
    @property
    def state(self) -> MIDIInputState:
        """Get current service state"""
        return self._state
    
    @property
    def current_device(self) -> Optional[str]:
        """Get currently selected MIDI device"""
        return self._current_device
    
    @property
    def active_notes(self) -> Dict[int, Dict[str, Any]]:
        """Get currently active notes"""
        return self._active_notes.copy()
    
    @property
    def is_listening(self) -> bool:
        """Check if service is actively listening for MIDI input"""
        return self._state == MIDIInputState.LISTENING and self._running

    def _sync_led_geometry(self) -> None:
        """Ensure internal LED geometry matches the active controller."""
        if not self._led_controller:
            return

        controller_leds = getattr(self._led_controller, 'num_pixels', None)
        if isinstance(controller_leds, int) and controller_leds > 0:
            previous_capacity = self._controller_led_capacity
            if previous_capacity != controller_leds:
                logger.debug(
                    "USB MIDI service detected controller capacity change (was=%s now=%s)",
                    previous_capacity,
                    controller_leds
                )
            self._controller_led_capacity = controller_leds
            if self.num_leds > controller_leds:
                logger.debug(
                    "Clamping mapping LED count %s to controller capacity %s",
                    self.num_leds,
                    controller_leds
                )
                self.num_leds = controller_leds

        controller_orientation = getattr(self._led_controller, 'led_orientation', None)
        if isinstance(controller_orientation, str) and controller_orientation:
            if controller_orientation != self.led_orientation:
                logger.debug(
                    "USB MIDI service adopting controller orientation '%s' (was '%s')",
                    controller_orientation,
                    self.led_orientation
                )
            self.led_orientation = controller_orientation

    def update_led_controller(self, led_controller) -> None:
        """Update the LED controller reference used for real-time output."""
        self._led_controller = led_controller
        self._sync_led_geometry()
        logger.debug(
            "USB MIDI service LED controller reference updated (id=%s, leds=%s)",
            hex(id(self._led_controller)) if self._led_controller else None,
            getattr(self._led_controller, 'num_pixels', 'unknown')
        )

    def refresh_runtime_settings(self) -> None:
        """Reload runtime configuration from the active settings source."""
        if self.settings_service:
            self._load_settings_from_service()
        else:
            self._load_settings_from_config()

        self._sync_led_geometry()
        self._precomputed_mapping = self._generate_key_mapping()
        self._active_notes.clear()
        logger.debug(
            "USB MIDI service settings refreshed: mapping_leds=%s controller_capacity=%s orientation=%s mapping_mode=%s",
            self.num_leds,
            self._controller_led_capacity,
            self.led_orientation,
            self.mapping_mode
        )
        logger.info("USB MIDI input service settings refreshed")
    
    def get_available_devices(self) -> List[MIDIDevice]:
        """
        Get list of available MIDI input devices.
        
        Returns:
            List of MIDIDevice objects representing available devices
        """
        if not MIDO_AVAILABLE:
            logger.warning("mido not available - no MIDI devices")
            return []
        
        try:
            device_names = mido.get_input_names()
            devices = []
            
            for idx, name in enumerate(device_names):
                devices.append(MIDIDevice(
                    name=name,
                    id=idx,
                    type="usb",
                    status="available"
                ))
            
            logger.info(f"Found {len(devices)} MIDI input devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error getting MIDI devices: {e}")
            return []
    
    def start_listening(self, device_name: Optional[str] = None) -> bool:
        """
        Start listening for MIDI input from specified device.
        
        Args:
            device_name: Name of MIDI device to use (auto-select if None)
            
        Returns:
            True if listening started successfully, False otherwise
        """
        if not MIDO_AVAILABLE:
            logger.error("Cannot start listening - mido not available")
            return False
        
        if self._running:
            logger.warning("Already listening for MIDI input")
            return True
        
        try:
            # Auto-select device if none specified
            if device_name is None:
                available_devices = self.get_available_devices()
                if not available_devices:
                    logger.error("No MIDI devices available")
                    self._state = MIDIInputState.ERROR
                    return False
                device_name = available_devices[0].name
                logger.info(f"Auto-selected MIDI device: {device_name}")
            
            # Open MIDI input port
            self._input_port = mido.open_input(device_name)
            self._current_device = device_name
            
            # Start input processing thread
            self._stop_event.clear()
            self._running = True
            self._input_thread = threading.Thread(
                target=self._input_processing_loop,
                name="USBMIDIInput",
                daemon=True
            )
            self._input_thread.start()
            
            self._state = MIDIInputState.LISTENING
            logger.info(f"Started MIDI input listening on device: {device_name}")
            
            # Notify via WebSocket
            self._broadcast_status_update()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MIDI listening: {e}")
            self._state = MIDIInputState.ERROR
            self._cleanup_input_port()
            return False
    
    def stop_listening(self) -> bool:
        """
        Stop listening for MIDI input.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._running:
            logger.info("MIDI input not currently running")
            return True
        
        try:
            # Signal stop and wait for thread
            self._running = False
            self._stop_event.set()
            
            if self._input_thread and self._input_thread.is_alive():
                self._input_thread.join(timeout=2.0)
                if self._input_thread.is_alive():
                    logger.warning("MIDI input thread did not stop gracefully")
            
            # Clean up resources
            self._cleanup_input_port()
            self._clear_all_leds()
            
            self._state = MIDIInputState.IDLE
            self._current_device = None
            
            logger.info("Stopped MIDI input listening")
            
            # Notify via WebSocket
            self._broadcast_status_update()
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping MIDI input: {e}")
            return False
    
    def _input_processing_loop(self):
        """
        Main loop for processing MIDI input messages.
        Runs in separate thread for real-time processing.
        """
        logger.info("MIDI input processing loop started")
        
        try:
            while self._running and not self._stop_event.is_set():
                try:
                    # Check for MIDI messages with timeout
                    if self._input_port:
                        # Use polling to allow for clean shutdown
                        msg = self._input_port.poll()
                        if msg:
                            self._process_midi_message(msg)
                        else:
                            # Small sleep to prevent busy waiting
                            time.sleep(0.001)  # 1ms
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Error in MIDI input loop: {e}")
                    # Continue processing unless it's a critical error
                    if "device" in str(e).lower() or "port" in str(e).lower():
                        break
                    time.sleep(0.01)  # Brief pause before retry
                    
        except Exception as e:
            logger.error(f"Critical error in MIDI input processing: {e}")
            self._state = MIDIInputState.ERROR
        
        finally:
            logger.info("MIDI input processing loop ended")
    
    def _process_midi_message(self, msg):
        """
        Process a single MIDI message and update LEDs accordingly.
        
        Args:
            msg: MIDI message from mido
        """
        try:
            # DEBUG: Log all incoming MIDI messages
            logger.info(f"MIDI DEBUG: Received message: {msg} (type={msg.type}, channel={getattr(msg, 'channel', 'N/A')})")
            
            current_time = time.time()
            self._event_count += 1
            self._last_event_time = current_time
            
            # Process note on events
            if msg.type == 'note_on' and msg.velocity > 0:
                logger.info(f"MIDI DEBUG: Note ON - {msg.note}, velocity={msg.velocity}, active notes: {sorted(self._active_notes.keys())}")
                self._handle_note_on(msg.note, msg.velocity, msg.channel, current_time)
            
            # Process note off events (including note_on with velocity 0)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                logger.info(f"MIDI DEBUG: Note OFF - {msg.note}, active notes: {sorted(self._active_notes.keys())}")
                self._handle_note_off(msg.note, msg.channel, current_time)
            
            # Log other MIDI events for debugging
            elif msg.type in ['control_change', 'program_change', 'pitchwheel']:
                logger.info(f"MIDI DEBUG: {msg.type}: {msg}")
            else:
                logger.info(f"MIDI DEBUG: Other message type: {msg}")
                
        except Exception as e:
            logger.error(f"Error processing MIDI message {msg}: {e}")
    
    def _handle_note_on(self, note: int, velocity: int, channel: int, timestamp: float):
        """
        Handle MIDI note on event.
        
        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (1-127)
            channel: MIDI channel (0-15)
            timestamp: Event timestamp
        """
        try:
            # Map MIDI note to LED indices (multi-LED support)
            led_indices = self._map_note_to_leds(note)
            if not led_indices:
                return  # Note outside LED range
            
            # Calculate LED color and brightness based on velocity
            color = self._get_note_color(note)
            brightness = self._velocity_to_brightness(velocity)
            
            # Apply brightness to color
            final_color = tuple(int(c * brightness) for c in color)
            
            # Update all mapped LEDs
            if self._led_controller:
                for led_index in led_indices:
                    success, error = self._led_controller.turn_on_led(led_index, final_color, auto_show=False)
                    if not success:
                        logger.warning(f"Failed to turn on LED {led_index}: {error}")
                # Show all changes at once for better performance
                success, error = self._led_controller.show()
                if not success:
                    logger.warning(f"Failed to show LEDs: {error}")
            
            # Track active note with all LED indices
            self._active_notes[note] = {
                'velocity': velocity,
                'timestamp': timestamp,
                'led_indices': led_indices,  # Changed from led_index to led_indices
                'channel': channel,
                'color': final_color
            }
            
            # Create event for WebSocket broadcast
            event = MIDIInputEvent(
                timestamp=timestamp,
                note=note,
                velocity=velocity,
                channel=channel,
                event_type='note_on'
            )
            
            # Broadcast event
            self._broadcast_midi_event(event, led_indices=led_indices)
            self._broadcast_debug_mapping('note_on', note, velocity, led_indices)
            
            logger.debug(f"Note ON: {note} (LEDs {led_indices}) velocity {velocity}")
            
        except Exception as e:
            logger.error(f"Error handling note on {note}: {e}")
    
    def _handle_note_off(self, note: int, channel: int, timestamp: float):
        """
        Handle MIDI note off event.
        
        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15)
            timestamp: Event timestamp
        """
        try:
            # Check if note was active
            if note not in self._active_notes:
                return  # Note wasn't active
            
            note_info = self._active_notes[note]
            led_indices = note_info.get('led_indices', [])
            
            # Handle backward compatibility with old led_index format
            if not led_indices and 'led_index' in note_info:
                led_indices = [note_info['led_index']]
            
            # Turn off all mapped LEDs
            if self._led_controller and led_indices:
                for led_index in led_indices:
                    success, error = self._led_controller.turn_off_led(led_index, auto_show=False)
                    if not success:
                        logger.warning(f"Failed to turn off LED {led_index}: {error}")
                # Show all changes at once for better performance
                success, error = self._led_controller.show()
                if not success:
                    logger.warning(f"Failed to show LEDs: {error}")
            
            # Remove from active notes
            del self._active_notes[note]
            
            # Create event for WebSocket broadcast
            event = MIDIInputEvent(
                timestamp=timestamp,
                note=note,
                velocity=0,
                channel=channel,
                event_type='note_off'
            )
            
            # Broadcast event
            self._broadcast_midi_event(event, led_indices=led_indices)
            self._broadcast_debug_mapping('note_off', note, 0, led_indices)
            
            logger.debug(f"Note OFF: {note} (LEDs {led_indices})")
            
        except Exception as e:
            logger.error(f"Error handling note off {note}: {e}")
    
    def _generate_key_mapping(self) -> Dict[int, List[int]]:
        """
        Generate precomputed key mapping based on configuration.
        
        Returns:
            Dictionary mapping MIDI note to list of LED indices
        """
        mapping = {}
        
        if self.mapping_mode == 'manual' and self.key_mapping:
            # Use manual mapping from configuration
            for note_str, led_indices in self.key_mapping.items():
                try:
                    note = int(note_str)
                    indices: List[int] = []
                    if isinstance(led_indices, int):
                        indices = [led_indices]
                    elif isinstance(led_indices, list):
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

                    indices = [idx for idx in indices if 0 <= idx < self.num_leds]
                    if not indices:
                        logger.debug(
                            "Skipping manual mapping for note %s due to empty/invalid indices after clamping",
                            note
                        )
                        continue

                    mapping[note] = indices
                except (ValueError, TypeError):
                    continue
        else:
            # Generate automatic mapping (auto or proportional)
            from config import generate_auto_key_mapping
            auto_mapping = generate_auto_key_mapping(
                piano_size=self.piano_size,
                led_count=self.num_leds,
                led_orientation='normal',
                leds_per_key=self.leds_per_key,
                mapping_base_offset=self.mapping_base_offset
            )
            
            # Convert to our format
            for note in range(self.min_midi_note, self.max_midi_note + 1):
                if note in auto_mapping:
                    led_indices = auto_mapping[note]
                    normalized: List[int] = []
                    if isinstance(led_indices, int):
                        normalized = [led_indices]
                    elif isinstance(led_indices, list):
                        for raw_idx in led_indices:
                            try:
                                normalized.append(int(raw_idx))
                            except (TypeError, ValueError):
                                continue

                    normalized = [idx for idx in normalized if 0 <= idx < self.num_leds]
                    if normalized:
                        mapping[note] = normalized
        
        return mapping
    
    def _map_note_to_leds(self, midi_note: int) -> List[int]:
        """
        Map MIDI note number to list of LED indices using precomputed mapping.
        
        Args:
            midi_note: MIDI note number (0-127)
            
        Returns:
            List of physical LED indices or empty list if note is outside range
        """
        capacity_limit = self._controller_led_capacity if self._controller_led_capacity else self.num_leds
        usable_limit = min(self.num_leds, capacity_limit)

        if midi_note in self._precomputed_mapping:
            raw_indices = self._precomputed_mapping[midi_note]
            if isinstance(raw_indices, list):
                filtered = [idx for idx in raw_indices if 0 <= idx < usable_limit]
                if filtered:
                    return filtered
            elif isinstance(raw_indices, int) and 0 <= raw_indices < usable_limit:
                return [raw_indices]
        
        # Fallback to single LED mapping for backward compatibility
        single_led = self._map_note_to_led(midi_note)
        return [single_led] if single_led is not None and 0 <= single_led < usable_limit else []
    
    def _map_note_to_led(self, midi_note: int) -> Optional[int]:
        """
        Map MIDI note number to LED strip position with orientation support.
        
        Args:
            midi_note: MIDI note number (0-127)
            
        Returns:
            Physical LED index (0-based) or None if note is outside range
        """
        if midi_note < self.min_midi_note or midi_note > self.max_midi_note:
            return None
        
        # Calculate logical LED index (0 to num_leds-1)
        note_range = self.max_midi_note - self.min_midi_note
        logical_index = int((midi_note - self.min_midi_note) * (self.num_leds - 1) / note_range)
        logical_index = max(0, min(logical_index, self.num_leds - 1))
        
        return logical_index
    
    def _get_note_color(self, note: int) -> tuple:
        """
        Get RGB color for a MIDI note based on pitch.
        
        Args:
            note: MIDI note number
            
        Returns:
            RGB color tuple (0-255)
        """
        # Color mapping based on chromatic scale
        note_in_octave = note % 12
        
        # Color wheel mapping for chromatic notes
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
            (127, 0, 255),  # A - Blue-Magenta
            (255, 0, 255),  # A# - Magenta
            (255, 0, 127),  # B - Magenta-Red
        ]
        
        return colors[note_in_octave]
    
    def _velocity_to_brightness(self, velocity: int) -> float:
        """
        Convert MIDI velocity to LED brightness factor.
        
        Args:
            velocity: MIDI velocity (0-127)
            
        Returns:
            Brightness factor (0.0-1.0)
        """
        # Map velocity to brightness with minimum threshold
        min_brightness = 0.1
        max_brightness = 1.0
        
        normalized_velocity = velocity / 127.0
        return min_brightness + (normalized_velocity * (max_brightness - min_brightness))
    
    def _clear_all_leds(self):
        """Clear all LEDs and reset active notes."""
        try:
            if self._led_controller:
                success, error = self._led_controller.turn_off_all()
                if not success:
                    logger.warning(f"Failed to turn off all LEDs: {error}")
            
            self._active_notes.clear()
            logger.debug("Cleared all LEDs and active notes")
            
        except Exception as e:
            logger.error(f"Error clearing LEDs: {e}")
    
    def _cleanup_input_port(self):
        """Clean up MIDI input port resources."""
        try:
            if self._input_port:
                self._input_port.close()
                self._input_port = None
                logger.debug("Closed MIDI input port")
        except Exception as e:
            logger.error(f"Error closing MIDI input port: {e}")
    
    def _broadcast_midi_event(self, event: MIDIInputEvent, led_indices: Optional[List[int]] = None):
        """Broadcast MIDI event via WebSocket."""
        if self._websocket_callback:
            try:
                # Send event to unified manager (which will broadcast unified_midi_event)
                event_data = {
                    'timestamp': event.timestamp,
                    'note': event.note,
                    'velocity': event.velocity,
                    'channel': event.channel,
                    'event_type': event.event_type,
                    'source': f"USB:{self._current_device or 'unknown'}"
                }
                self._websocket_callback(event.event_type, event_data)
                # Temporary debugging to confirm note events reach frontend
                logger.info(
                    "[debug] emitted %s via websocket with LEDs %s",
                    event.event_type,
                    led_indices
                )
                
                # Also broadcast direct midi_input event for backward compatibility
                if led_indices is None:
                    led_indices = self._active_notes.get(event.note, {}).get('led_indices', [])
                legacy_event_data = {
                    'type': 'midi_input_event',
                    'timestamp': event.timestamp,
                    'note': event.note,
                    'velocity': event.velocity,
                    'channel': event.channel,
                    'event_type': event.event_type,
                    'active_notes': len(self._active_notes),
                    'led_indices': led_indices,
                    'mapping': {
                        'mode': self.mapping_mode,
                        'leds_per_key': self.leds_per_key,
                        'base_offset': self.mapping_base_offset,
                        'orientation': self.led_orientation,
                        'key_mapping_entry': self.key_mapping.get(str(event.note)) or self.key_mapping.get(event.note)
                    }
                }
                self._websocket_callback('midi_input', legacy_event_data)
                logger.info(
                    "[debug] emitted midi_input payload: note=%s leds=%s mapping=%s",
                    event.note,
                    led_indices,
                    legacy_event_data['mapping']
                )
            except Exception as e:
                logger.error(f"Error broadcasting MIDI event: {e}")

    def _broadcast_debug_mapping(self, event_type: str, note: int, velocity: int, led_indices: List[int]):
        """Emit detailed mapping info for temporary debugging in the web console."""
        if not self._websocket_callback:
            return

        try:
            # Report the parameters that drive note-to-LED decisions so the UI can log them.
            debug_payload = {
                'event_type': event_type,
                'note': note,
                'velocity': velocity,
                'led_indices': led_indices,
                'mapping': {
                    'mode': self.mapping_mode,
                    'leds_per_key': self.leds_per_key,
                    'base_offset': self.mapping_base_offset,
                    'orientation': self.led_orientation,
                    'manual_mapping_used': event_type == 'note_on' and (
                        str(note) in self.key_mapping or note in self.key_mapping
                    ),
                    'manual_entry': self.key_mapping.get(str(note)) or self.key_mapping.get(note)
                }
            }
            self._websocket_callback('debug_midi_mapping', debug_payload)
        except Exception as exc:
            logger.error(f"Error broadcasting debug mapping payload: {exc}")
    
    def _broadcast_status_update(self):
        """Broadcast service status update via WebSocket."""
        if self._websocket_callback:
            try:
                # Use background task for status updates to avoid blocking MIDI processing
                import socketio
                if hasattr(socketio, 'start_background_task'):
                    socketio.start_background_task(self._do_broadcast_status_update)
                else:
                    # Fallback to direct call
                    self._do_broadcast_status_update()
            except Exception as e:
                logger.error(f"Error broadcasting status update: {e}")
    
    def _do_broadcast_status_update(self):
        """Actual status broadcast implementation for background task."""
        if self._websocket_callback:
            try:
                status_data = {
                    'type': 'midi_input_status',
                    'state': self._state.value,
                    'device': self._current_device,
                    'active_notes': len(self._active_notes),
                    'event_count': self._event_count,
                    'last_event_time': self._last_event_time
                }
                self._websocket_callback('midi_input_status', status_data)
                
                # Also notify the manager about device status changes
                self._websocket_callback('device_status', {
                    'device': self._current_device,
                    'state': self._state.value,
                    'is_listening': self.is_listening,
                    'devices': [d.__dict__ for d in self.get_available_devices()]
                })
            except Exception as e:
                logger.error(f"Error in background broadcast of status update: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status information.
        
        Returns:
            Dictionary containing service status
        """
        return {
            'state': self._state.value,
            'device': self._current_device,
            'is_listening': self.is_listening,
            'active_notes': len(self._active_notes),
            'event_count': self._event_count,
            'last_event_time': self._last_event_time,
            'available_devices': [d.__dict__ for d in self.get_available_devices()]
        }
    
    def cleanup(self):
        """Clean up service resources."""
        logger.info("Cleaning up USB MIDI input service")
        self.stop_listening()
        self._clear_all_leds()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
