import types

import pytest

from backend import usb_midi_service as usb_service
from backend import midi_input_manager as midi_manager


class FakePortManager:
    def __init__(self):
        self.started_with = []
        self.failures = set()
        self.device_name = None
        self.stopped = False

    def start(self, device_name):
        self.started_with.append(device_name)
        if device_name in self.failures:
            return False
        name = device_name or 'AutoDevice'
        self.device_name = name
        return True

    def stop(self):
        self.stopped = True
        self.device_name = None

    def drain(self):
        return []

    def cleanup(self):
        self.stop()

    def list_devices(self):
        return ['AutoDevice']


class MonotonicClock:
    def __init__(self, value=100.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, delta):
        self.value += delta


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(usb_service, 'MIDO_AVAILABLE', True)
    instance = usb_service.USBMIDIInputService(led_controller=None, websocket_callback=None, settings_service=None)
    fake_port = FakePortManager()
    instance._port_manager = fake_port
    yield instance, fake_port
    instance.stop_listening()
    fake_port.cleanup()


def test_restart_with_saved_device_reconnects_same_port(service, monkeypatch):
    midi_service, fake_port = service
    clock = MonotonicClock()
    monkeypatch.setattr(usb_service.time, 'monotonic', clock)

    assert midi_service.start_listening('Digital Piano')
    assert midi_service.current_device == 'Digital Piano'
    initial_started = list(fake_port.started_with)

    assert midi_service.restart_with_saved_device('led.enabled')
    assert midi_service.current_device == 'Digital Piano'
    # restart should have produced an additional start attempt for the same device
    assert fake_port.started_with.count('Digital Piano') == initial_started.count('Digital Piano') + 1


def test_restart_obeys_cooldown_and_recovers_after_delay(service, monkeypatch):
    midi_service, fake_port = service
    clock = MonotonicClock()
    monkeypatch.setattr(usb_service.time, 'monotonic', clock)

    assert midi_service.start_listening('Digital Piano')

    assert midi_service.restart_with_saved_device('led.led_count')
    first_restart_calls = len(fake_port.started_with)

    # Attempting immediately should respect cooldown and skip restart
    assert not midi_service.restart_with_saved_device('led.led_count')
    assert len(fake_port.started_with) == first_restart_calls

    clock.advance(0.6)
    assert midi_service.restart_with_saved_device('led.led_count')
    assert len(fake_port.started_with) == first_restart_calls + 1


def test_restart_falls_back_to_auto_selection_when_saved_device_fails(service, monkeypatch):
    midi_service, fake_port = service
    clock = MonotonicClock()
    monkeypatch.setattr(usb_service.time, 'monotonic', clock)

    assert midi_service.start_listening('Digital Piano')
    fake_port.failures.add('Digital Piano')

    assert midi_service.restart_with_saved_device('led.led_count')
    # After failure the fallback should use auto-selection (None candidate)
    assert fake_port.started_with[-1] is None
    assert midi_service.current_device == 'AutoDevice'


def test_restart_when_not_listening_starts_saved_device(service, monkeypatch):
    midi_service, fake_port = service
    clock = MonotonicClock()
    monkeypatch.setattr(usb_service.time, 'monotonic', clock)

    assert midi_service.start_listening('Digital Piano')
    midi_service.stop_listening()
    assert not midi_service.is_listening

    # Ensure we have a remembered device
    midi_service._last_connected_device = 'Digital Piano'
    fake_port.started_with.clear()

    assert midi_service.restart_with_saved_device('led.led_count')
    assert midi_service.is_listening
    assert fake_port.started_with[-1] == 'Digital Piano'


def test_midi_input_manager_restart_delegates_to_usb_service(monkeypatch):
    class StubUSBService:
        def __init__(self):
            self.calls = []
            self._listening = True

        @property
        def is_listening(self):
            return self._listening

        def restart_with_saved_device(self, reason):
            self.calls.append(reason)
            return True

    manager = midi_manager.MIDIInputManager.__new__(midi_manager.MIDIInputManager)
    manager._usb_service = StubUSBService()
    manager._source_status = {
        midi_manager.MIDIInputSource.USB: {'listening': True},
        midi_manager.MIDIInputSource.RTPMIDI: {'listening': False},
    }
    manager._broadcast_status_update = lambda: None

    assert manager.restart_usb_service('led.led_count') is True
    assert manager._usb_service.calls == ['led.led_count']
    assert manager._source_status[midi_manager.MIDIInputSource.USB]['listening'] is True


class FakeSettingsService:
    def __init__(self):
        self.settings = {'led': {'enabled': False}}
        self.get_calls = []
        self.set_calls = []

    def get_setting(self, category, key, default=None):
        self.get_calls.append((category, key, default))
        return self.settings.get(category, {}).get(key, default)

    def set_setting(self, category, key, value):
        self.set_calls.append((category, key, value))
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value


def test_auto_enable_leds_on_usb_midi_connection(service, monkeypatch):
    """Test that LEDs are automatically enabled when a USB MIDI device connects."""
    midi_service, fake_port = service
    
    # Create a fake settings service
    fake_settings = FakeSettingsService()
    midi_service.settings_service = fake_settings
    
    # Initially LEDs should be disabled
    assert fake_settings.get_setting('led', 'enabled', False) is False
    
    # Start listening - this should auto-enable LEDs
    assert midi_service.start_listening('Test Device')
    
    # Verify that LEDs were enabled
    assert fake_settings.set_calls == [('led', 'enabled', True)]
    assert fake_settings.get_setting('led', 'enabled', False) is True


def test_auto_enable_leds_only_when_disabled(service, monkeypatch):
    """Test that LEDs are not re-enabled if already enabled."""
    midi_service, fake_port = service
    
    # Create a fake settings service with LEDs already enabled
    fake_settings = FakeSettingsService()
    fake_settings.settings['led']['enabled'] = True
    midi_service.settings_service = fake_settings
    
    # Start listening - this should NOT try to enable LEDs again
    assert midi_service.start_listening('Test Device')
    
    # Verify that no set_setting calls were made
    assert fake_settings.set_calls == []


def test_auto_enable_leds_handles_settings_service_error(service, monkeypatch):
    """Test that auto-enable gracefully handles settings service errors."""
    midi_service, fake_port = service
    
    # Create a fake settings service that raises an exception
    class ErrorSettingsService:
        def get_setting(self, category, key, default=None):
            raise Exception("Settings service error")
        
        def set_setting(self, category, key, value):
            raise Exception("Settings service error")
    
    midi_service.settings_service = ErrorSettingsService()
    
    # Start listening should still succeed despite settings error
    assert midi_service.start_listening('Test Device')
    assert midi_service.is_listening


def test_auto_enable_leds_skipped_when_no_settings_service(service, monkeypatch):
    """Test that auto-enable is skipped when no settings service is available."""
    midi_service, fake_port = service
    
    # Ensure no settings service
    midi_service.settings_service = None
    
    # Start listening should succeed without trying to enable LEDs
    assert midi_service.start_listening('Test Device')
    assert midi_service.is_listening
