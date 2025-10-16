import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from backend.logging_config import get_logger

try:
    from config import get_config, get_piano_specs, generate_auto_key_mapping
except ImportError:  # pragma: no cover - fallback for tests/tools
    def get_config(key: str, default: Any = None) -> Any:
        return default

    def get_piano_specs(piano_size: str) -> Dict[str, Any]:
        return {'keys': 88, 'midi_start': 21, 'midi_end': 108}

    def generate_auto_key_mapping(  # type: ignore
        piano_size: str,
        led_count: int,
        led_orientation: str = 'normal',
        leds_per_key: Optional[int] = None,
        mapping_base_offset: Optional[int] = None,
    ) -> Dict[int, List[int]]:
        specs = get_piano_specs(piano_size)
        start = specs['midi_start']
        end = specs['midi_end']
        if led_count <= 0:
            return {}
        mapping: Dict[int, List[int]] = {}
        span = max(1, end - start)
        for midi_note in range(start, end + 1):
            logical_index = int((midi_note - start) * (led_count - 1) / span)
            mapping[midi_note] = [logical_index]
        return mapping

logger = get_logger(__name__)


@dataclass
class ProcessedMIDIEvent:
    timestamp: float
    note: int
    velocity: int
    channel: int
    event_type: str
    led_indices: List[int]


class MidiEventProcessor:
    """Translate MIDI messages into LED operations and mapping events."""

    def __init__(
        self,
        led_controller=None,
        settings_service=None,
        config_getter: Callable[[str, Any], Any] = get_config,
        piano_specs_resolver: Callable[[str], Dict[str, Any]] = get_piano_specs,
    ):
        self._led_controller = led_controller
        self._settings_service = settings_service
        self._config_getter = config_getter
        self._piano_specs_resolver = piano_specs_resolver

        self.piano_size: str = '88-key'
        self.min_midi_note: int = 21
        self.max_midi_note: int = 108
        self.mapping_mode: str = 'auto'
        self.leds_per_key: int = 3
        self.mapping_base_offset: int = 0
        self.key_mapping: Dict[Any, Any] = {}
        self.num_leds: int = 1
        self.led_orientation: str = 'normal'
        self._configured_led_count: int = 1
        self._controller_led_capacity: int = 1
        
        # Calibration offsets
        self.global_offset: int = 0
        self.key_offsets: Dict[int, int] = {}
        self.calibration_enabled: bool = False

        self._precomputed_mapping: Dict[int, List[int]] = {}
        self._active_notes: Dict[int, Dict[str, Any]] = {}

        self.refresh_runtime_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_led_controller(self, led_controller) -> None:
        self._led_controller = led_controller
        self.refresh_runtime_settings()

    def refresh_runtime_settings(self) -> None:
        logger.info("MIDI event processor refreshing runtime settings...")
        self._load_settings()
        self._sync_controller_geometry()
        self._precomputed_mapping = self._generate_key_mapping()
        self._active_notes.clear()
        logger.info(
            "MIDI event processor refreshed: leds=%d orientation=%s mapping=%s",
            self.num_leds,
            self.led_orientation,
            self.mapping_mode,
        )

    def handle_message(self, msg, timestamp: Optional[float] = None) -> List[ProcessedMIDIEvent]:
        """Process a mido message and return processed note events."""
        timestamp = timestamp if timestamp is not None else time.time()
        processed_events: List[ProcessedMIDIEvent] = []

        msg_type = getattr(msg, 'type', None)
        if msg_type == 'note_on' and getattr(msg, 'velocity', 0) > 0:
            event = self._handle_note_on(msg.note, msg.velocity, getattr(msg, 'channel', 0), timestamp)
            if event:
                processed_events.append(event)
        elif msg_type in ('note_off', 'polytouch') or (msg_type == 'note_on' and getattr(msg, 'velocity', 0) == 0):
            event = self._handle_note_off(msg.note, getattr(msg, 'channel', 0), timestamp)
            if event:
                processed_events.append(event)
        elif msg_type == 'control_change':
            logger.debug("Ignoring control_change message (%s) in LED processor", msg)
        else:
            logger.debug("Unhandled MIDI message type '%s'", msg_type)

        return processed_events

    def clear_all_leds(self) -> None:
        if self._led_controller:
            try:
                self._led_controller.turn_off_all()
            except Exception as exc:
                logger.warning("Failed to clear LEDs: %s", exc)
        self._active_notes.clear()

    def get_status(self) -> Dict[str, Any]:
        return {
            'num_leds': self.num_leds,
            'orientation': self.led_orientation,
            'active_notes': len(self._active_notes),
            'mapping_mode': self.mapping_mode,
        }

    def copy_active_notes(self) -> Dict[int, Dict[str, Any]]:
        return {note: dict(data) for note, data in self._active_notes.items()}

    def map_note_to_led(self, midi_note: int) -> Optional[int]:
        return self._map_note_to_led(midi_note)

    def map_note_to_leds(self, midi_note: int) -> List[int]:
        return self._map_note_to_leds(midi_note)

    def copy_precomputed_mapping(self) -> Dict[int, List[int]]:
        return {key: list(value) for key, value in self._precomputed_mapping.items()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        if self._settings_service:
            get_setting = getattr(self._settings_service, 'get_setting', None)

            piano_config: Dict[str, Any] = {}
            if hasattr(self._settings_service, 'get_piano_configuration'):
                try:
                    maybe_config = self._settings_service.get_piano_configuration()
                    if isinstance(maybe_config, dict):
                        piano_config = dict(maybe_config)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Failed to load piano configuration from settings service: %s", exc)

            if not piano_config and callable(get_setting):
                size_from_settings = get_setting('piano', 'piano_size', get_setting('piano', 'size', None))
                piano_config = {
                    'size': size_from_settings,
                    'midi_start': get_setting('piano', 'midi_start', None),
                    'midi_end': get_setting('piano', 'midi_end', None),
                }

            raw_piano_size = piano_config.get('size') if isinstance(piano_config, dict) else None
            self.piano_size = raw_piano_size or self._config_getter('piano_size', '88-key')

            specs = self._piano_specs_resolver(self.piano_size)

            raw_min_note = piano_config.get('midi_start') if isinstance(piano_config, dict) else None
            raw_max_note = piano_config.get('midi_end') if isinstance(piano_config, dict) else None

            if (not isinstance(raw_min_note, int)) and callable(get_setting):
                raw_min_note = get_setting('piano', 'midi_start', None)
            if (not isinstance(raw_max_note, int)) and callable(get_setting):
                raw_max_note = get_setting('piano', 'midi_end', None)

            self.min_midi_note = int(raw_min_note) if isinstance(raw_min_note, int) else specs['midi_start']
            self.max_midi_note = int(raw_max_note) if isinstance(raw_max_note, int) else specs['midi_end']

            led_config: Dict[str, Any] = {}
            if hasattr(self._settings_service, 'get_led_configuration'):
                try:
                    maybe_led = self._settings_service.get_led_configuration()
                    if isinstance(maybe_led, dict):
                        led_config = dict(maybe_led)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Failed to load LED configuration from settings service: %s", exc)

            if not led_config and callable(get_setting):
                led_config = {
                    'led_count': get_setting('led', 'led_count', None),
                    'orientation': get_setting('led', 'led_orientation', None),
                }

            led_count_value = led_config.get('led_count', None) if isinstance(led_config, dict) else None
            if led_count_value is None and callable(get_setting):
                led_count_value = get_setting('led', 'led_count', None)
            if led_count_value is None:
                led_count_value = self._config_getter('led_count', 1)

            try:
                self.num_leds = max(1, int(led_count_value))
            except (TypeError, ValueError):
                self.num_leds = 1
            self._configured_led_count = self.num_leds

            orientation_value = led_config.get('orientation') if isinstance(led_config, dict) else None
            if not orientation_value and callable(get_setting):
                orientation_value = get_setting('led', 'led_orientation', None)
            self.led_orientation = orientation_value or self._config_getter('led_orientation', 'normal')

            if callable(get_setting):
                self.mapping_mode = get_setting('led', 'mapping_mode', 'auto')
                self.leds_per_key = get_setting('led', 'leds_per_key', None)  # Default to None for proportional
                self.mapping_base_offset = get_setting('led', 'mapping_base_offset', 0)
                self.key_mapping = get_setting('led', 'key_mapping', {}) or {}
                
                # Load calibration settings including LED range
                self.global_offset = get_setting('calibration', 'global_offset', 0)
                self.calibration_enabled = get_setting('calibration', 'calibration_enabled', False)
                
                # CRITICAL: Load calibration range for accurate mapping
                start_led = get_setting('calibration', 'start_led', 0)
                end_led = get_setting('calibration', 'end_led', self.num_leds - 1)
                available_led_range = end_led - start_led + 1
                
                logger.info(
                    "MIDI processor calibration: start_led=%d, end_led=%d, available=%d, configured_total=%d",
                    start_led, end_led, available_led_range, self.num_leds
                )
                
                # Use available range for mapping, not total LED count
                # This ensures proportional distribution across all 88 keys
                # Only apply if range is actually limited (not full 0-N range)
                if start_led > 0 or end_led < self.num_leds - 1:
                    logger.info(
                        "MIDI processor: Using calibration range [%d-%d] (%d available) for mapping instead of total %d",
                        start_led, end_led, available_led_range, self.num_leds
                    )
                    self.num_leds = available_led_range
                    self.mapping_base_offset = start_led
                
                key_offsets_raw = get_setting('calibration', 'key_offsets', {}) or {}
                # Normalize key_offsets to ensure midi note keys are integers
                self.key_offsets = {}
                for note_key, offset in key_offsets_raw.items():
                    try:
                        midi_note = int(note_key)
                        self.key_offsets[midi_note] = int(offset)
                    except (TypeError, ValueError):
                        continue
            else:
                self.mapping_mode = 'auto'
                self.leds_per_key = None  # Default to None for proportional
                self.mapping_base_offset = 0
                self.key_mapping = {}
                self.global_offset = 0
                self.calibration_enabled = False
                self.key_offsets = {}
        else:
            self.piano_size = self._config_getter('piano_size', '88-key')
            specs = self._piano_specs_resolver(self.piano_size)
            self.min_midi_note = specs['midi_start']
            self.max_midi_note = specs['midi_end']
            self.num_leds = max(1, int(self._config_getter('led_count', 1)))
            self._configured_led_count = self.num_leds
            self.led_orientation = self._config_getter('led_orientation', 'normal')
            self.mapping_mode = self._config_getter('mapping_mode', 'auto')
            self.leds_per_key = self._config_getter('leds_per_key', None)  # Default to None for proportional
            self.mapping_base_offset = self._config_getter('mapping_base_offset', 0)
            self.key_mapping = self._config_getter('key_mapping', {}) or {}
            self.global_offset = 0
            self.calibration_enabled = False
            self.key_offsets = {}

    def _sync_controller_geometry(self) -> None:
        controller_leds = getattr(self._led_controller, 'num_pixels', None)
        if isinstance(controller_leds, int) and controller_leds > 0:
            if controller_leds != self.num_leds:
                logger.debug(
                    "MidiEventProcessor aligning LED capacity (configured=%s controller=%s)",
                    self._configured_led_count,
                    controller_leds,
                )
            self._controller_led_capacity = controller_leds
        else:
            self._controller_led_capacity = self._configured_led_count

        self.num_leds = max(1, min(self._configured_led_count, self._controller_led_capacity))

        controller_orientation = getattr(self._led_controller, 'led_orientation', None)
        if isinstance(controller_orientation, str) and controller_orientation:
            self.led_orientation = controller_orientation

    def _handle_note_on(self, note: int, velocity: int, channel: int, timestamp: float) -> Optional[ProcessedMIDIEvent]:
        led_indices = self._map_note_to_leds(note)
        if not led_indices:
            return None

        color = self._get_note_color(note)
        brightness = self._velocity_to_brightness(velocity)
        final_color = tuple(int(component * brightness) for component in color)

        if self._led_controller:
            # Log which processor instance is updating LEDs (for debugging duplication)
            logger.info(
                "MIDI_PROCESSOR[%s]: NOTE_ON note=%d velocity=%d led_count=%d leds=%s",
                id(self), note, velocity, self.num_leds, led_indices
            )
            for led_index in led_indices:
                success, error = self._led_controller.turn_on_led(led_index, final_color, auto_show=False)
                if not success:
                    logger.debug("LED %s failed to turn on: %s", led_index, error)
            show_success, error = self._led_controller.show()
            if not show_success and error:
                logger.debug("LED show failed: %s", error)

        self._active_notes[note] = {
            'velocity': velocity,
            'timestamp': timestamp,
            'led_indices': led_indices,
            'channel': channel,
            'color': final_color,
        }

        return ProcessedMIDIEvent(
            timestamp=timestamp,
            note=note,
            velocity=velocity,
            channel=channel,
            event_type='note_on',
            led_indices=list(led_indices),
        )

    def _handle_note_off(self, note: int, channel: int, timestamp: float) -> Optional[ProcessedMIDIEvent]:
        note_info = self._active_notes.pop(note, None)
        led_indices = note_info.get('led_indices') if note_info else []

        if self._led_controller and led_indices:
            # Log which processor instance is updating LEDs (for debugging duplication)
            logger.info(
                "MIDI_PROCESSOR[%s]: NOTE_OFF note=%d led_count=%d leds=%s",
                id(self), note, self.num_leds, led_indices
            )
            for led_index in led_indices:
                success, error = self._led_controller.turn_off_led(led_index, auto_show=False)
                if not success:
                    logger.debug("LED %s failed to turn off: %s", led_index, error)
            show_success, error = self._led_controller.show()
            if not show_success and error:
                logger.debug("LED show failed: %s", error)

        if not led_indices:
            led_indices = self._map_note_to_leds(note)

        return ProcessedMIDIEvent(
            timestamp=timestamp,
            note=note,
            velocity=0,
            channel=channel,
            event_type='note_off',
            led_indices=list(led_indices),
        )

    def _generate_key_mapping(self) -> Dict[int, List[int]]:
        mapping: Dict[int, List[int]] = {}

        if self.mapping_mode == 'manual' and self.key_mapping:
            for note_str, led_indices in self.key_mapping.items():
                try:
                    midi_note = int(note_str)
                except (TypeError, ValueError):
                    continue

                normalized: List[int] = []
                if isinstance(led_indices, int):
                    normalized = [led_indices]
                elif isinstance(led_indices, list):
                    for raw_idx in led_indices:
                        try:
                            normalized.append(int(raw_idx))
                        except (TypeError, ValueError):
                            continue
                else:
                    try:
                        normalized = [int(led_indices)]
                    except (TypeError, ValueError):
                        normalized = []

                normalized = [idx for idx in normalized if 0 <= idx < self.num_leds]
                if normalized:
                    mapping[midi_note] = normalized
        else:
            auto_mapping = generate_auto_key_mapping(
                piano_size=self.piano_size,
                led_count=self.num_leds,
                led_orientation=self.led_orientation,
                leds_per_key=self.leds_per_key,
                mapping_base_offset=self.mapping_base_offset,
            )

            for midi_note in range(self.min_midi_note, self.max_midi_note + 1):
                if midi_note not in auto_mapping:
                    continue
                led_indices = auto_mapping[midi_note]
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
                    mapping[midi_note] = normalized

        return mapping

    def _map_note_to_led(self, midi_note: int) -> Optional[int]:
        if midi_note < self.min_midi_note or midi_note > self.max_midi_note:
            return None

        if self.num_leds <= 1:
            return 0

        note_range = self.max_midi_note - self.min_midi_note
        if note_range <= 0:
            return 0

        logical_index = int((midi_note - self.min_midi_note) * (self.num_leds - 1) / note_range)
        return max(0, min(logical_index, self.num_leds - 1))

    def _map_note_to_leds(self, midi_note: int) -> List[int]:
        """Map MIDI note to LED indices, applying calibration offsets."""
        mapped = self._precomputed_mapping.get(midi_note)
        if isinstance(mapped, list) and mapped:
            led_indices = [idx for idx in mapped if 0 <= idx < self.num_leds]
        elif isinstance(mapped, int) and 0 <= mapped < self.num_leds:
            led_indices = [mapped]
        else:
            fallback = self._map_note_to_led(midi_note)
            led_indices = [fallback] if fallback is not None else []
        
        # Apply calibration offsets if enabled
        if self.calibration_enabled and led_indices:
            adjusted_indices = []
            
            for led_idx in led_indices:
                # Start with the LED index
                adjusted_idx = led_idx
                
                # Apply global offset
                adjusted_idx += self.global_offset
                
                # Apply per-key offset if available
                if midi_note in self.key_offsets:
                    adjusted_idx += self.key_offsets[midi_note]
                
                # Clamp to valid LED range
                adjusted_idx = max(0, min(adjusted_idx, self.num_leds - 1))
                adjusted_indices.append(adjusted_idx)
            
            return adjusted_indices
        
        return led_indices

    @staticmethod
    def _get_note_color(note: int) -> tuple:
        colors = [
            (255, 0, 0),
            (255, 127, 0),
            (255, 255, 0),
            (127, 255, 0),
            (0, 255, 0),
            (0, 255, 127),
            (0, 255, 255),
            (0, 127, 255),
            (0, 0, 255),
            (127, 0, 255),
            (255, 0, 255),
            (255, 0, 127),
        ]
        return colors[note % 12]

    @staticmethod
    def _velocity_to_brightness(velocity: int) -> float:
        min_brightness = 0.1
        max_brightness = 1.0
        normalized_velocity = max(0, min(velocity, 127)) / 127.0
        return min_brightness + (normalized_velocity * (max_brightness - min_brightness))

    @property
    def controller_led_capacity(self) -> int:
        return self._controller_led_capacity

    @property
    def configured_led_count(self) -> int:
        return self._configured_led_count

