"""
Pytest configuration and common fixtures for PianoLED-CoPilot backend tests.

This module provides shared fixtures and mocking utilities to handle hardware-optional
dependencies and ensure tests run consistently across different environments.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional

# Add backend directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def mock_hardware_dependencies():
    """
    Mock hardware dependencies that may not be available in test environments.

    This fixture patches imports for:
    - rpi_ws281x (LED strip control)
    - RPi.GPIO (GPIO control)
    - mido (MIDI library)
    - eventlet (async server)
    """
    hardware_mocks = {}

    # Mock rpi_ws281x
    try:
        with patch.dict('sys.modules', {'rpi_ws281x': Mock()}):
            mock_rpi_ws281x = Mock()
            mock_rpi_ws281x.PixelStrip = Mock()
            mock_rpi_ws281x.Color = Mock()
            hardware_mocks['rpi_ws281x'] = mock_rpi_ws281x
    except ImportError:
        pass

    # Mock RPi.GPIO
    try:
        with patch.dict('sys.modules', {'RPi.GPIO': Mock()}):
            mock_gpio = Mock()
            hardware_mocks['RPi.GPIO'] = mock_gpio
    except ImportError:
        pass

    # Mock mido and related MIDI libraries
    midi_mocks = {}
    for module in ['mido', 'mido.ports', 'rtpmidi', 'pymidi']:
        try:
            with patch.dict('sys.modules', {module: Mock()}):
                mock_module = Mock()
                midi_mocks[module] = mock_module
        except ImportError:
            pass

    # Mock eventlet
    try:
        with patch.dict('sys.modules', {'eventlet': Mock()}):
            mock_eventlet = Mock()
            hardware_mocks['eventlet'] = mock_eventlet
    except ImportError:
        pass

    return hardware_mocks


@pytest.fixture
def mock_settings_service():
    """Create a mock settings service for testing."""
    mock_service = Mock()

    # Default settings
    default_settings = {
        'led': {
            'enabled': True,
            'led_count': 88,
            'brightness': 0.5,
            'gpio_pin': 18,
            'led_orientation': 'normal',
            'mapping_mode': 'auto',
            'leds_per_key': 3,
            'mapping_base_offset': 0,
            'key_mapping': {},
            'led_channel': 0,
            'led_type': 'WS2812B',
            'led_frequency': 800000,
            'led_dma': 10,
            'led_invert': False
        },
        'piano': {
            'piano_size': '88-key'
        },
        'midi': {
            'enabled': True
        }
    }

    def mock_get_setting(category, key, default=None):
        return default_settings.get(category, {}).get(key, default)

    def mock_set_setting(category, key, value):
        if category not in default_settings:
            default_settings[category] = {}
        default_settings[category][key] = value
        return True

    mock_service.get_setting = mock_get_setting
    mock_service.set_setting = mock_set_setting
    mock_service.get_all_settings = Mock(return_value=default_settings)

    return mock_service


@pytest.fixture
def mock_led_controller(mock_settings_service):
    """Create a mock LED controller for testing."""
    with patch('led_controller.HARDWARE_AVAILABLE', False):
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        # Mock the methods to return success tuples
        controller.turn_on_led = Mock(return_value=(True, None))
        controller.turn_off_led = Mock(return_value=(True, None))
        controller.show = Mock(return_value=(True, None))
        controller.turn_off_all = Mock(return_value=(True, None))
        controller.set_multiple_leds = Mock(return_value=(True, None))

        return controller


@pytest.fixture
def mock_websocket_callback():
    """Create a mock WebSocket callback for testing."""
    return Mock()


@pytest.fixture
def mock_midi_input():
    """Create mock MIDI input data for testing."""
    return {
        'note': 60,  # Middle C
        'velocity': 100,
        'channel': 0,
        'event_type': 'note_on',
        'timestamp': 1234567890.0
    }


@pytest.fixture
def mock_midi_file():
    """Create a mock MIDI file content for testing."""
    # Simple MIDI file header + track
    return bytes([
        # MIDI Header
        0x4D, 0x54, 0x68, 0x64,  # "MThd"
        0x00, 0x00, 0x00, 0x06,  # Header length
        0x00, 0x00,              # Format 0
        0x00, 0x01,              # 1 track
        0x00, 0x60,              # 96 ticks per quarter note

        # Track Header
        0x4D, 0x54, 0x72, 0x6B,  # "MTrk"
        0x00, 0x00, 0x00, 0x0B,  # Track length

        # Track data
        0x00, 0x90, 0x40, 0x40,  # Note on C4
        0x60, 0x80, 0x40, 0x40,  # Note off C4
        0x00, 0xFF, 0x2F, 0x00   # End of track
    ])


@pytest.fixture(autouse=True)
def mock_hardware_imports():
    """
    Automatically mock hardware imports for all tests.

    This ensures tests run consistently regardless of hardware availability.
    """
    mocks = {}

    # Hardware libraries
    hardware_modules = [
        'rpi_ws281x',
        'RPi.GPIO',
        'mido',
        'mido.ports',
        'rtpmidi',
        'pymidi',
        'python-rtmidi',
        'eventlet',
        'eventlet.wsgi'
    ]

    for module in hardware_modules:
        if module not in sys.modules:
            mock = Mock()
            mocks[module] = mock
            sys.modules[module] = mock

    yield

    # Clean up mocks after test
    for module in mocks:
        if module in sys.modules and sys.modules[module] is mocks[module]:
            del sys.modules[module]


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory for testing file uploads."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return str(upload_dir)


@pytest.fixture
def sample_midi_data():
    """Provide sample MIDI data for testing."""
    return {
        'notes': [
            {'note': 60, 'velocity': 100, 'time': 0.0, 'duration': 1.0},
            {'note': 64, 'velocity': 100, 'time': 1.0, 'duration': 1.0},
            {'note': 67, 'velocity': 100, 'time': 2.0, 'duration': 1.0},
        ],
        'tempo': 120,
        'time_signature': (4, 4),
        'duration': 3.0
    }


# Coverage configuration
def pytest_configure(config):
    """Configure pytest with custom markers and coverage settings."""
    config.addinivalue_line(
        "markers", "hardware: marks tests that require hardware (deselect with '-m \"not hardware\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests that are slow to run"
    )