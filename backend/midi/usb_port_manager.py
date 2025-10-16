import threading
import time
from collections import deque
from typing import Deque, List, Optional, Tuple

from backend.logging_config import get_logger

try:
    import mido
    MIDO_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    mido = None  # type: ignore
    MIDO_AVAILABLE = False

logger = get_logger(__name__)


class USBMIDIPortManager:
    """Manage the lifecycle of a single USB MIDI input port."""

    def __init__(self):
        self._queue: Deque[Tuple[object, float]] = deque()
        self._queue_lock = threading.Lock()
        self._input_port = None
        self._device_name: Optional[str] = None
        self._listening = False

    @property
    def is_listening(self) -> bool:
        return self._listening

    @property
    def device_name(self) -> Optional[str]:
        return self._device_name

    def list_devices(self) -> List[str]:
        if not MIDO_AVAILABLE:
            return []
        try:
            return list(mido.get_input_names())
        except Exception as exc:
            logger.warning("Failed to enumerate MIDI devices: %s", exc)
            return []

    def start(self, device_name: Optional[str] = None) -> bool:
        if not MIDO_AVAILABLE:
            logger.warning("mido library not available - cannot start USB MIDI port")
            return False

        self.stop()

        candidate = device_name or self._auto_select_device()
        if not candidate:
            logger.warning("No USB MIDI devices available")
            return False

        try:
            self._input_port = mido.open_input(candidate, callback=self._on_midi_message)
            self._device_name = candidate
            self._listening = True
            logger.info("USB MIDI port '%s' opened", candidate)
            return True
        except Exception as exc:
            logger.error("Failed to open USB MIDI device '%s': %s", candidate, exc)
            self._input_port = None
            self._device_name = None
            self._listening = False
            return False

    def stop(self) -> None:
        if self._input_port is not None:
            try:
                self._input_port.close()
                logger.info("USB MIDI port '%s' closed", self._device_name)
            except Exception as exc:
                logger.debug("Error closing MIDI port '%s': %s", self._device_name, exc)
        self._input_port = None
        self._device_name = None
        self._listening = False
        with self._queue_lock:
            self._queue.clear()

    def drain(self) -> List[Tuple[object, float]]:
        messages: List[Tuple[object, float]] = []
        with self._queue_lock:
            while self._queue:
                messages.append(self._queue.popleft())
        return messages

    def _auto_select_device(self) -> Optional[str]:
        devices = self.list_devices()
        for name in devices:
            if any(skip in name for skip in ('Through', 'RtMidOut', 'USB-USB')):
                continue
            return name
        return devices[0] if devices else None

    def _on_midi_message(self, msg) -> None:
        timestamp = time.time()
        with self._queue_lock:
            self._queue.append((msg, timestamp))

    def cleanup(self) -> None:
        self.stop()
