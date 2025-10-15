#!/usr/bin/env python3
"""
USB MIDI Input Service - real-time input coordination
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from logging_config import get_logger

from midi.midi_event_processor import MidiEventProcessor, ProcessedMIDIEvent
from midi.usb_port_manager import USBMIDIPortManager, MIDO_AVAILABLE

try:  # Re-exported for test patching compatibility
    from config import get_config, get_piano_specs  # noqa: F401
except ImportError:  # pragma: no cover - fallback when config unavailable
    def get_config(key, default=None):
        return default

    def get_piano_specs(piano_size):
        return {'midi_start': 21, 'midi_end': 108, 'keys': 88}

try:
    from led_controller import LEDController  # noqa: F401
except ImportError:  # pragma: no cover - LED optional
    LEDController = None

logger = get_logger(__name__)


class MIDIInputState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    ERROR = "error"


@dataclass
class MIDIDevice:
    name: str
    id: int
    type: str = "usb"
    status: str = "available"


@dataclass
class MIDIInputEvent:
    timestamp: float
    note: int
    velocity: int
    channel: int
    event_type: str


class USBMIDIInputService:
    """Coordinate USB MIDI input, LED mapping, and event broadcasting."""

    def __init__(
        self,
        led_controller=None,
        websocket_callback: Optional[Callable] = None,
        settings_service=None,
    ) -> None:
        self._led_controller = led_controller
        self._websocket_callback = websocket_callback
        self.settings_service = settings_service

        self._port_manager = USBMIDIPortManager()
        self._event_processor = MidiEventProcessor(
            led_controller=led_controller,
            settings_service=settings_service,
            config_getter=get_config,
            piano_specs_resolver=get_piano_specs,
        )

        self._state = MIDIInputState.IDLE if MIDO_AVAILABLE else MIDIInputState.ERROR
        self._current_device: Optional[str] = None

        self._processing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        self._event_count = 0
        self._last_event_time = 0.0

        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - USB MIDI listening disabled")

    @property
    def num_leds(self) -> int:
        return self._event_processor.num_leds

    @property
    def min_midi_note(self) -> int:
        return self._event_processor.min_midi_note

    @property
    def max_midi_note(self) -> int:
        return self._event_processor.max_midi_note

    @property
    def mapping_mode(self) -> str:
        return self._event_processor.mapping_mode

    @property
    def leds_per_key(self) -> int:
        return self._event_processor.leds_per_key

    @property
    def mapping_base_offset(self) -> int:
        return self._event_processor.mapping_base_offset

    @property
    def key_mapping(self) -> Dict[Any, Any]:
        return self._event_processor.key_mapping

    @property
    def led_orientation(self) -> str:
        return self._event_processor.led_orientation

    @property
    def _controller_led_capacity(self) -> int:
        return self._event_processor.controller_led_capacity

    @property
    def state(self) -> MIDIInputState:
        return self._state

    @property
    def current_device(self) -> Optional[str]:
        return self._current_device

    @property
    def is_listening(self) -> bool:
        return self._state == MIDIInputState.LISTENING and self._running

    @property
    def num_leds(self) -> int:
        return self._event_processor.num_leds

    @property
    def led_orientation(self) -> str:
        return self._event_processor.led_orientation

    @property
    def active_notes(self) -> Dict[int, Dict[str, Any]]:
        return self._event_processor.copy_active_notes()

    def update_led_controller(self, led_controller) -> None:
        self._led_controller = led_controller
        self._event_processor.update_led_controller(led_controller)

    def refresh_runtime_settings(self) -> None:
        self._event_processor.refresh_runtime_settings()
        logger.info(
            "USB MIDI service settings refreshed (leds=%s orientation=%s mapping=%s)",
            self.num_leds,
            self.led_orientation,
            self._event_processor.mapping_mode,
        )

    def start_listening(self, device_name: Optional[str] = None) -> bool:
        if self.is_listening:
            logger.debug("USB MIDI service already listening")
            return True

        if not self._port_manager.start(device_name):
            self._state = MIDIInputState.ERROR
            self._broadcast_status_update()
            return False

        self._current_device = self._port_manager.device_name
        self._stop_event.clear()
        self._running = True
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name="USBMIDIInput",
            daemon=True,
        )
        self._processing_thread.start()

        self._state = MIDIInputState.LISTENING
        logger.info("USB MIDI listening started on device '%s'", self._current_device)
        self._broadcast_status_update()
        return True

    def stop_listening(self) -> bool:
        if not self._running:
            return True

        self._running = False
        self._stop_event.set()

        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2.0)

        self._port_manager.stop()
        self._event_processor.clear_all_leds()

        self._current_device = None
        self._state = MIDIInputState.IDLE
        self._broadcast_status_update()
        logger.info("USB MIDI listening stopped")
        return True

    def _processing_loop(self) -> None:
        logger.debug("USB MIDI processing loop started")
        while not self._stop_event.is_set():
            drained = self._port_manager.drain()
            if not drained:
                time.sleep(0.002)
                continue

            for msg, msg_timestamp in drained:
                processed_events = self._event_processor.handle_message(msg, msg_timestamp)
                for event in processed_events:
                    self._event_count += 1
                    self._last_event_time = event.timestamp
                    self._broadcast_processed_event(event)
        logger.debug("USB MIDI processing loop exited")

    def _broadcast_processed_event(self, event: ProcessedMIDIEvent) -> None:
        self._broadcast_midi_event(event)
        self._broadcast_debug_mapping(
            event.event_type,
            event.note,
            event.velocity,
            event.led_indices,
        )
        self._log_event_diagnostics(event)

    def _broadcast_midi_event(self, event: ProcessedMIDIEvent) -> None:
        if not self._websocket_callback:
            return

        try:
            basic_event = {
                'timestamp': event.timestamp,
                'note': event.note,
                'velocity': event.velocity,
                'channel': event.channel,
                'event_type': event.event_type,
                'source': f"USB:{self._current_device or 'unknown'}",
                'device': self._current_device,
            }
            self._websocket_callback(event.event_type, basic_event)

            legacy_payload = {
                'type': 'midi_input_event',
                'timestamp': event.timestamp,
                'note': event.note,
                'velocity': event.velocity,
                'channel': event.channel,
                'event_type': event.event_type,
                'active_notes': len(self.active_notes),
                'led_indices': list(event.led_indices),
                'mapping': {
                    'mode': self._event_processor.mapping_mode,
                    'leds_per_key': self._event_processor.leds_per_key,
                    'base_offset': self._event_processor.mapping_base_offset,
                    'orientation': self.led_orientation,
                    'key_mapping_entry': self._event_processor.key_mapping.get(str(event.note))
                    or self._event_processor.key_mapping.get(event.note),
                },
            }
            self._websocket_callback('midi_input', legacy_payload)
        except Exception as exc:
            logger.error("Error broadcasting MIDI event: %s", exc)

    def _broadcast_debug_mapping(
        self,
        event_type: str,
        note: int,
        velocity: int,
        led_indices: List[int],
    ) -> None:
        if not self._websocket_callback:
            return

        try:
            payload = {
                'event_type': event_type,
                'note': note,
                'velocity': velocity,
                'led_indices': list(led_indices),
                'mapping': {
                    'mode': self._event_processor.mapping_mode,
                    'leds_per_key': self._event_processor.leds_per_key,
                    'base_offset': self._event_processor.mapping_base_offset,
                    'orientation': self.led_orientation,
                    'manual_mapping_used': event_type == 'note_on'
                    and (
                        str(note) in self._event_processor.key_mapping
                        or note in self._event_processor.key_mapping
                    ),
                    'manual_entry': self._event_processor.key_mapping.get(str(note))
                    or self._event_processor.key_mapping.get(note),
                },
            }
            self._websocket_callback('debug_midi_mapping', payload)
        except Exception as exc:
            logger.error("Error broadcasting debug mapping payload: %s", exc)

    def _log_event_diagnostics(self, event: ProcessedMIDIEvent) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return

        controller = self._led_controller
        controller_id = hex(id(controller)) if controller else 'None'
        led_count = getattr(controller, 'num_pixels', None)
        enabled = getattr(controller, 'led_enabled', None)

        logger.debug(
            "USB MIDI event processed | type=%s note=%s velocity=%s leds=%s mapped=%s controller_id=%s controller_leds=%s enabled=%s",
            event.event_type,
            event.note,
            event.velocity,
            self.num_leds,
            list(event.led_indices),
            controller_id,
            led_count,
            enabled,
        )

        if not event.led_indices:
            logger.warning(
                "USB MIDI note %s produced no LED indices (mapping_mode=%s, min_note=%s, max_note=%s, num_leds=%s)",
                event.note,
                self._event_processor.mapping_mode,
                self._event_processor.min_midi_note,
                self._event_processor.max_midi_note,
                self.num_leds,
            )

    def _broadcast_status_update(self) -> None:
        if not self._websocket_callback:
            return

        try:
            self._do_broadcast_status_update()
        except Exception as exc:
            logger.error("Error broadcasting USB MIDI status update: %s", exc)

    def _do_broadcast_status_update(self) -> None:
        if not self._websocket_callback:
            return

        try:
            status_data = {
                'type': 'midi_input_status',
                'state': self._state.value,
                'device': self._current_device,
                'active_notes': len(self.active_notes),
                'event_count': self._event_count,
                'last_event_time': self._last_event_time,
                'is_listening': self.is_listening,
            }
            self._websocket_callback('midi_input_status', status_data)

            devices = [MIDIDevice(name=name, id=idx) for idx, name in enumerate(self._port_manager.list_devices())]
            self._websocket_callback(
                'device_status',
                {
                    'device': self._current_device,
                    'state': self._state.value,
                    'is_listening': self.is_listening,
                    'devices': [device.__dict__ for device in devices],
                },
            )
        except Exception as exc:
            logger.error("Error broadcasting USB MIDI status: %s", exc)

    def get_available_devices(self) -> List[MIDIDevice]:
        names = self._port_manager.list_devices()
        return [MIDIDevice(name=name, id=index) for index, name in enumerate(names)]

    def get_status(self) -> Dict[str, Any]:
        return {
            'state': self._state.value,
            'device': self._current_device,
            'is_listening': self.is_listening,
            'active_notes': len(self.active_notes),
            'event_count': self._event_count,
            'last_event_time': self._last_event_time,
            'num_leds': self.num_leds,
            'orientation': self.led_orientation,
        }

    def cleanup(self) -> None:
        logger.info("Cleaning up USB MIDI service")
        self.stop_listening()
        self._port_manager.cleanup()

    def _map_note_to_led(self, midi_note: int) -> Optional[int]:
        return self._event_processor.map_note_to_led(midi_note)

    def _map_note_to_leds(self, midi_note: int) -> List[int]:
        return self._event_processor.map_note_to_leds(midi_note)

    def _generate_key_mapping(self) -> Dict[int, List[int]]:
        return self._event_processor.copy_precomputed_mapping()
