#!/usr/bin/env python3
"""
USB MIDI Output Service - coordinates MIDI message sending to USB keyboards
Allows playback to send note events to connected USB MIDI devices
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from backend.logging_config import get_logger

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False

logger = get_logger(__name__)


class MIDIOutputState(Enum):
    """MIDI output state enumeration"""
    IDLE = "idle"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MIDIDevice:
    """Represents a MIDI output device"""
    name: str
    id: int
    type: str = "output"
    status: str = "available"


class USBMIDIOutputService:
    """Service for sending MIDI events to USB keyboard devices"""

    def __init__(self, settings_service: Optional[Any] = None, websocket_callback: Optional[Callable] = None):
        """
        Initialize USB MIDI output service.

        Args:
            settings_service: Settings service for configuration
            websocket_callback: Callback for WebSocket events
        """
        self._settings_service = settings_service
        self._websocket_callback = websocket_callback
        self._output_port: Optional[Any] = None
        self._device_name: Optional[str] = None
        self._state = MIDIOutputState.IDLE
        self._lock = threading.Lock()

        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - USB MIDI output disabled")

    @property
    def is_connected(self) -> bool:
        """Check if output device is connected"""
        return self._output_port is not None

    @property
    def current_device(self) -> Optional[str]:
        """Get currently connected device name"""
        return self._device_name

    @property
    def state(self) -> MIDIOutputState:
        """Get current state"""
        return self._state

    def get_available_devices(self) -> List[MIDIDevice]:
        """
        Get list of available MIDI output devices.

        Returns:
            List[MIDIDevice]: Available devices
        """
        if not MIDO_AVAILABLE:
            logger.debug("mido not available for device enumeration")
            return []

        devices: List[MIDIDevice] = []
        try:
            output_names = mido.get_output_names()
            for index, name in enumerate(output_names):
                status = 'connected' if self.is_connected and name == self._device_name else 'available'
                devices.append(MIDIDevice(name=name, id=index, status=status))
            logger.debug(f"Found {len(devices)} MIDI output devices")
        except Exception as e:
            logger.error(f"Failed to enumerate MIDI output devices: {e}")

        return devices

    def connect(self, device_name: Optional[str] = None) -> bool:
        """
        Connect to a MIDI output device.

        Args:
            device_name: Name of device to connect to, or None to auto-select

        Returns:
            bool: True if connected successfully
        """
        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - cannot connect to MIDI output")
            return False

        with self._lock:
            try:
                # Disconnect from current device if any
                if self._output_port:
                    try:
                        self._output_port.close()
                    except Exception:
                        pass
                    self._output_port = None
                    self._device_name = None

                # Get available devices
                available_devices = mido.get_output_names()
                if not available_devices:
                    logger.warning("No MIDI output devices available")
                    self._state = MIDIOutputState.ERROR
                    return False

                # Select device
                target_device = device_name
                if not target_device or target_device not in available_devices:
                    # Auto-select first available device
                    target_device = available_devices[0]
                    logger.info(f"Auto-selected MIDI output device: {target_device}")

                # Open device
                self._output_port = mido.open_output(target_device)
                self._device_name = target_device
                self._state = MIDIOutputState.CONNECTED

                logger.info(f"Connected to MIDI output device: {target_device}")
                self._broadcast_status()
                return True

            except Exception as e:
                logger.error(f"Failed to connect to MIDI output device: {e}")
                self._output_port = None
                self._device_name = None
                self._state = MIDIOutputState.ERROR
                self._broadcast_status()
                return False

    def disconnect(self) -> bool:
        """
        Disconnect from current MIDI output device.

        Returns:
            bool: True if disconnected successfully
        """
        with self._lock:
            try:
                if self._output_port:
                    self._output_port.close()
                    self._output_port = None
                    self._device_name = None
                    self._state = MIDIOutputState.IDLE
                    logger.info("Disconnected from MIDI output device")
                    self._broadcast_status()
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from MIDI output: {e}")
                return False

    def send_note_on(self, note: int, velocity: int, channel: int = 0) -> bool:
        """
        Send MIDI note_on message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)

        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected:
            logger.debug(f"MIDI output not connected, ignoring note_on: {note}")
            return False

        try:
            # Clamp values to valid ranges
            note = max(0, min(127, note))
            velocity = max(0, min(127, velocity))
            channel = max(0, min(15, channel))

            msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            with self._lock:
                if self._output_port:
                    self._output_port.send(msg)
            logger.debug(f"Sent MIDI note_on: note={note}, velocity={velocity}, channel={channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to send MIDI note_on: {e}")
            return False

    def send_note_off(self, note: int, channel: int = 0) -> bool:
        """
        Send MIDI note_off message.

        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15)

        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected:
            logger.debug(f"MIDI output not connected, ignoring note_off: {note}")
            return False

        try:
            # Clamp values to valid ranges
            note = max(0, min(127, note))
            channel = max(0, min(15, channel))

            msg = mido.Message('note_off', note=note, channel=channel)
            with self._lock:
                if self._output_port:
                    self._output_port.send(msg)
            logger.debug(f"Sent MIDI note_off: note={note}, channel={channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to send MIDI note_off: {e}")
            return False

    def send_control_change(self, control: int, value: int, channel: int = 0) -> bool:
        """
        Send MIDI control change message.

        Args:
            control: CC number (0-127)
            value: CC value (0-127)
            channel: MIDI channel (0-15)

        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected:
            return False

        try:
            control = max(0, min(127, control))
            value = max(0, min(127, value))
            channel = max(0, min(15, channel))

            msg = mido.Message('control_change', control=control, value=value, channel=channel)
            with self._lock:
                if self._output_port:
                    self._output_port.send(msg)
            logger.debug(f"Sent MIDI CC: control={control}, value={value}, channel={channel}")
            return True

        except Exception as e:
            logger.error(f"Failed to send MIDI CC: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current output service status"""
        return {
            'state': self._state.value,
            'device': self._device_name,
            'is_connected': self.is_connected,
            'available_devices': [d.name for d in self.get_available_devices()],
        }

    def _broadcast_status(self) -> None:
        """Broadcast status update via WebSocket"""
        if self._websocket_callback:
            try:
                self._websocket_callback('midi_output_status', self.get_status())
            except Exception as e:
                logger.error(f"Error broadcasting MIDI output status: {e}")

    def cleanup(self) -> None:
        """Clean up and disconnect"""
        try:
            self.disconnect()
            logger.info("USB MIDI output service cleaned up")
        except Exception as e:
            logger.error(f"Error during MIDI output cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
