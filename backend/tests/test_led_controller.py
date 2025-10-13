"""
Tests for LED Controller with comprehensive hardware mocking.

This module tests the LEDController class with proper mocking of hardware dependencies
to ensure tests run consistently across different environments.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Tuple


class TestLEDController:
    """Test cases for LED controller functionality."""

    def test_led_controller_init_simulation_mode(self, mock_settings_service):
        """Test LED controller initialization in simulation mode."""
        with patch('led_controller.HARDWARE_AVAILABLE', False):
            from led_controller import LEDController

            controller = LEDController(settings_service=mock_settings_service)

            assert controller.num_pixels == 88
            assert controller.pin == 18
            assert controller.brightness == 0.5
            assert controller.led_orientation == 'normal'
            assert controller.pixels is None  # Simulation mode
            assert len(controller._led_state) == 88

    def test_led_controller_init_hardware_disabled(self, mock_settings_service):
        """Test LED controller when LEDs are disabled in settings."""
        mock_settings_service.get_setting = Mock(side_effect=lambda cat, key, default: {
            ('led', 'enabled'): False,
            ('led', 'led_count'): 50,
            ('led', 'gpio_pin'): 19,
            ('led', 'brightness'): 0.3
        }.get((cat, key), default))

        with patch('led_controller.HARDWARE_AVAILABLE', True):
            from led_controller import LEDController

            controller = LEDController(settings_service=mock_settings_service)

            assert controller.led_enabled is False
            assert controller.num_pixels == 50
            assert controller.pixels is None  # Disabled mode

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_turn_on_led_simulation(self, mock_settings_service):
        """Test turning on LED in simulation mode."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        success, error = controller.turn_on_led(10, (255, 0, 0))

        assert success is True
        assert error is None
        assert controller._led_state[10] == (255, 0, 0)

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_turn_on_led_invalid_index(self, mock_settings_service):
        """Test turning on LED with invalid index."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        success, error = controller.turn_on_led(100, (255, 0, 0))  # Index out of range

        assert success is False
        assert "out of range" in error

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_turn_off_led_simulation(self, mock_settings_service):
        """Test turning off LED in simulation mode."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        # First turn on LED
        controller.turn_on_led(5, (0, 255, 0))
        assert controller._led_state[5] == (0, 255, 0)

        # Then turn off
        success, error = controller.turn_off_led(5)

        assert success is True
        assert error is None
        assert controller._led_state[5] == (0, 0, 0)

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_turn_off_all_simulation(self, mock_settings_service):
        """Test turning off all LEDs in simulation mode."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        # Turn on some LEDs
        controller.turn_on_led(0, (255, 0, 0))
        controller.turn_on_led(10, (0, 255, 0))
        controller.turn_on_led(20, (0, 0, 255))

        # Turn off all
        success, error = controller.turn_off_all()

        assert success is True
        assert error is None
        assert all(color == (0, 0, 0) for color in controller._led_state)

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_set_multiple_leds_simulation(self, mock_settings_service):
        """Test setting multiple LEDs at once in simulation mode."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        led_data = {
            0: (255, 0, 0),
            5: (0, 255, 0),
            10: (0, 0, 255)
        }

        success, error = controller.set_multiple_leds(led_data)

        assert success is True
        assert error is None
        assert controller._led_state[0] == (255, 0, 0)
        assert controller._led_state[5] == (0, 255, 0)
        assert controller._led_state[10] == (0, 0, 255)

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_led_orientation_normal(self, mock_settings_service):
        """Test LED orientation mapping with normal orientation."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)
        controller.led_orientation = 'normal'

        # Test mapping
        assert controller._map_led_index(0) == 0
        assert controller._map_led_index(10) == 10
        assert controller._map_led_index(87) == 87

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_led_orientation_reversed(self, mock_settings_service):
        """Test LED orientation mapping with reversed orientation."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)
        controller.led_orientation = 'reversed'
        controller.num_pixels = 88

        # Test mapping
        assert controller._map_led_index(0) == 87  # First becomes last
        assert controller._map_led_index(10) == 77
        assert controller._map_led_index(87) == 0  # Last becomes first

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_brightness_scaling(self, mock_settings_service):
        """Test brightness scaling in LED color setting."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        # Test with brightness parameter
        success, error = controller.turn_on_led(0, (255, 128, 64), brightness=0.5)

        assert success is True
        assert error is None
        assert controller._led_state[0] == (127, 64, 32)  # Half brightness

    @patch('led_controller.HARDWARE_AVAILABLE', False)
    def test_show_simulation(self, mock_settings_service):
        """Test show method in simulation mode."""
        from led_controller import LEDController

        controller = LEDController(settings_service=mock_settings_service)

        success, error = controller.show()

        assert success is True
        assert error is None

    @patch('led_controller.HARDWARE_AVAILABLE', True)
    @patch('led_controller.PixelStrip')
    def test_hardware_mode_initialization(self, mock_pixel_strip, mock_settings_service):
        """Test LED controller initialization in hardware mode."""
        from led_controller import LEDController

        # Mock the PixelStrip instance
        mock_strip_instance = Mock()
        mock_pixel_strip.return_value = mock_strip_instance

        controller = LEDController(settings_service=mock_settings_service)

        assert controller.pixels is mock_strip_instance
        mock_pixel_strip.assert_called_once()
        mock_strip_instance.begin.assert_called_once()

    @patch('led_controller.HARDWARE_AVAILABLE', True)
    @patch('led_controller.PixelStrip')
    def test_hardware_mode_turn_on_led(self, mock_pixel_strip, mock_settings_service):
        """Test turning on LED in hardware mode."""
        from led_controller import LEDController

        # Mock the PixelStrip instance
        mock_strip_instance = Mock()
        mock_pixel_strip.return_value = mock_strip_instance

        controller = LEDController(settings_service=mock_settings_service)

        # Mock Color function
        with patch('led_controller.Color') as mock_color:
            mock_color.return_value = Mock()

            success, error = controller.turn_on_led(5, (255, 100, 50))

            assert success is True
            assert error is None
            mock_strip_instance.setPixelColor.assert_called_once_with(5, mock_color.return_value)
            mock_strip_instance.show.assert_called_once()

    @patch('led_controller.HARDWARE_AVAILABLE', True)
    @patch('led_controller.PixelStrip')
    @patch('led_controller.Color')
    def test_hardware_mode_error_handling(self, mock_color, mock_pixel_strip, mock_settings_service):
        """Test error handling in hardware mode."""
        from led_controller import LEDController

        # Mock the PixelStrip to raise an exception
        mock_strip_instance = Mock()
        mock_pixel_strip.return_value = mock_strip_instance
        mock_strip_instance.setPixelColor.side_effect = Exception("Hardware error")
        mock_color.return_value = Mock()

        controller = LEDController(settings_service=mock_settings_service)

        success, error = controller.turn_on_led(0, (255, 0, 0))

        assert success is False
        assert "Hardware error" in error

    def test_context_manager(self, mock_settings_service):
        """Test LED controller context manager."""
        with patch('led_controller.HARDWARE_AVAILABLE', False):
            from led_controller import LEDController

            with LEDController(settings_service=mock_settings_service) as controller:
                assert controller.num_pixels == 88
                # Context manager should work without errors

    def test_cleanup_simulation(self, mock_settings_service):
        """Test cleanup in simulation mode."""
        with patch('led_controller.HARDWARE_AVAILABLE', False):
            from led_controller import LEDController

            controller = LEDController(settings_service=mock_settings_service)
            controller.cleanup()  # Should not raise any errors

    @patch('led_controller.HARDWARE_AVAILABLE', True)
    @patch('led_controller.PixelStrip')
    @patch('led_controller.Color')
    def test_cleanup_hardware(self, mock_color, mock_pixel_strip, mock_settings_service):
        """Test cleanup in hardware mode."""
        from led_controller import LEDController

        mock_strip_instance = Mock()
        mock_pixel_strip.return_value = mock_strip_instance

        controller = LEDController(settings_service=mock_settings_service)
        controller.cleanup()

        # Should turn off all LEDs and clean up
        assert mock_strip_instance.setPixelColor.call_count == 88  # Once for each LED
        mock_strip_instance.show.assert_called_once()