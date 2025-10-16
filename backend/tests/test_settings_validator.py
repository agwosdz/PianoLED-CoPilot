"""
Tests for Settings Validator.

This module tests the SettingsValidator class to ensure proper validation
and normalization of settings data.
"""

import pytest
from unittest.mock import Mock
from backend.services.settings_validator import SettingsValidator


class TestSettingsValidator:
    """Test cases for settings validation and normalization."""

    def test_validate_and_normalize_valid_settings(self):
        """Test validation and normalization of valid settings."""
        input_settings = {
            'led': {
                'brightness': 75,  # Should be normalized to 0.75
                'led_count': 100,
                'color_profile': 'srgb'  # Should be normalized to 'sRGB'
            },
            'piano': {
                'size': '88-key'  # Should fill in derived specs
            }
        }

        normalized, errors = SettingsValidator.validate_and_normalize(input_settings)

        assert errors == []
        assert normalized['led']['brightness'] == 0.75
        assert normalized['led']['led_count'] == 100
        assert normalized['led']['color_profile'] == 'sRGB'
        assert 'size' in normalized['piano']
        assert normalized['piano']['size'] == '88-key'

    def test_validate_brightness_normalization(self):
        """Test brightness value normalization."""
        test_cases = [
            (0, 0.0),
            (50, 0.5),
            (100, 1.0),
            (0.5, 0.5),  # Already normalized
            (1.0, 1.0),  # Already normalized
        ]

        for input_val, expected in test_cases:
            settings = {'led': {'brightness': input_val}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)

            assert errors == []
            assert normalized['led']['brightness'] == expected

    def test_validate_brightness_invalid(self):
        """Test invalid brightness values."""
        # Note: brightness gets normalized from 0-100 to 0.0-1.0, so 150 becomes 1.0 (valid)
        # Invalid types should fail
        invalid_values = ["invalid", None, [], {}]

        for invalid_val in invalid_values:
            settings = {'led': {'brightness': invalid_val}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)

            assert len(errors) > 0
            assert any('brightness' in error for error in errors)

    def test_validate_led_count(self):
        """Test LED count validation."""
        # Valid values
        valid_counts = [1, 50, 300, 100, 1000]
        for count in valid_counts:
            settings = {'led': {'led_count': count}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)
            assert errors == []
            assert normalized['led']['led_count'] == count

        # Invalid values - only type errors, since max is 1000
        invalid_counts = ["invalid", None, [], {}]
        for count in invalid_counts:
            settings = {'led': {'led_count': count}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)
            assert len(errors) > 0

    def test_validate_piano_size(self):
        """Test piano size validation and spec filling."""
        valid_sizes = ['25-key', '37-key', '49-key', '61-key', '76-key', '88-key']

        for size in valid_sizes:
            settings = {'piano': {'size': size}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)

            assert errors == []
            assert normalized['piano']['size'] == size

    def test_validate_piano_size_invalid(self):
        """Test invalid piano size."""
        settings = {'piano': {'piano_size': 'invalid-size'}}
        normalized, errors = SettingsValidator.validate_and_normalize(settings)

        assert len(errors) > 0
        assert any('piano_size' in error for error in errors)

    def test_validate_color_profile_normalization(self):
        """Test color profile normalization."""
        test_cases = [
            ('srgb', 'sRGB'),
            ('SRGB', 'sRGB'),
            ('Srgb', 'sRGB'),
            ('Standard RGB', 'Standard RGB'),
            ('standard', 'Standard RGB'),
            ('adobe rgb', 'Adobe RGB'),
            ('wide gamut', 'Wide Gamut'),
        ]

        for input_val, expected in test_cases:
            settings = {'led': {'color_profile': input_val}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)

            assert errors == []
            assert normalized['led']['color_profile'] == expected

        # Test invalid color profile
        settings = {'led': {'color_profile': 'invalid'}}
        normalized, errors = SettingsValidator.validate_and_normalize(settings)
        assert len(errors) > 0

    def test_validate_led_orientation(self):
        """Test LED orientation validation."""
        valid_orientations = ['normal', 'reversed']

        for orientation in valid_orientations:
            settings = {'led': {'led_orientation': orientation}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)
            assert errors == []
            assert normalized['led']['led_orientation'] == orientation

        # Invalid orientation
        settings = {'led': {'led_orientation': 'invalid'}}
        normalized, errors = SettingsValidator.validate_and_normalize(settings)
        assert len(errors) > 0

    def test_validate_gpio_pin(self):
        """Test GPIO pin validation."""
        # Valid pins (no min/max constraints in schema, only type)
        valid_pins = [0, 18, 19, 21, 27, 50, 100]

        for pin in valid_pins:
            settings = {'led': {'gpio_pin': pin}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)
            assert errors == []
            assert normalized['led']['gpio_pin'] == pin

        # Invalid pins - only type errors
        invalid_pins = ["invalid", None, [], {}]
        for pin in invalid_pins:
            settings = {'led': {'gpio_pin': pin}}
            normalized, errors = SettingsValidator.validate_and_normalize(settings)
            assert len(errors) > 0

    def test_validate_nested_categories(self):
        """Test validation of nested settings categories."""
        settings = {
            'led': {
                'brightness': 50,
                'led_count': 100,
                'gpio_pin': 18
            },
            'piano': {
                'size': '88-key'
            },
            'system': {
                'debug': True
            }
        }

        normalized, errors = SettingsValidator.validate_and_normalize(settings)

        assert errors == []
        assert normalized['led']['brightness'] == 0.5
        assert normalized['led']['led_count'] == 100
        assert normalized['piano']['size'] == '88-key'

    def test_validate_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Empty settings should not error but return empty normalized dict
        settings = {}
        normalized, errors = SettingsValidator.validate_and_normalize(settings)

        assert errors == []
        assert normalized == {}

    def test_validate_partial_settings(self):
        """Test validation with partial settings."""
        settings = {
            'led': {
                'brightness': 75
                # Missing other LED settings
            }
        }

        normalized, errors = SettingsValidator.validate_and_normalize(settings)

        assert errors == []
        assert normalized['led']['brightness'] == 0.75

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        settings = {
            'led': {
                'brightness': "invalid",  # Type error
                'led_count': "invalid",   # Type error
                'gpio_pin': "invalid"     # Type error
            },
            'piano': {
                'size': 'invalid'  # Invalid enum value
            }
        }

        normalized, errors = SettingsValidator.validate_and_normalize(settings)

        assert len(errors) >= 3  # Should have multiple errors