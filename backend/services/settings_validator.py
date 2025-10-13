#!/usr/bin/env python3
"""
Settings Validator for Piano LED Visualizer
Centralized validation and normalization logic for all settings
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from backend.config import get_piano_specs
from logging_config import get_logger

logger = get_logger(__name__)

class SettingsValidator:
    """
    Centralized settings validation and normalization
    Combines logic from config.py, schemas/settings_schema.py, and api normalization
    """

    @staticmethod
    def validate_and_normalize(settings_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate and normalize settings dictionary.

        Args:
            settings_dict: Raw settings dictionary

        Returns:
            Tuple of (normalized_settings, error_messages)
        """
        if not isinstance(settings_dict, dict):
            return {}, ["Settings must be a dictionary"]

        normalized = {}
        errors = []

        # Process each category
        for category, category_settings in settings_dict.items():
            if not isinstance(category_settings, dict):
                errors.append(f"Category '{category}' must be a dictionary")
                continue

            normalized_category, category_errors = SettingsValidator._validate_and_normalize_category(category, category_settings)
            if category_errors:
                errors.extend([f"{category}.{key}: {error}" for key, error in category_errors.items()])
            else:
                normalized[category] = normalized_category

        return normalized, errors

    @staticmethod
    def _validate_and_normalize_category(category: str, settings: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Validate and normalize a single category of settings.

        Args:
            category: Settings category name
            settings: Category settings dictionary

        Returns:
            Tuple of (normalized_settings, error_dict)
        """
        normalized = {}
        errors = {}

        # Get schema for this category
        schema = SettingsValidator._get_category_schema(category)
        if not schema:
            errors['__category__'] = f"Unknown category '{category}'"
            return normalized, errors

        # Process each setting in the category
        for key, value in settings.items():
            if key not in schema:
                errors[key] = f"Unknown setting '{key}' in category '{category}'"
                continue

            setting_config = schema[key]
            
            # Normalize first, then validate
            normalized_value = SettingsValidator._normalize_setting_value(category, key, value)
            validation_errors = SettingsValidator._validate_setting_value(category, key, normalized_value, setting_config)
            
            if validation_errors:
                errors[key] = validation_errors[0]  # Take first error
            else:
                normalized[key] = normalized_value

        return normalized, errors

    @staticmethod
    def _validate_and_normalize_setting(category: str, key: str, value: Any, config: Dict[str, Any]) -> Tuple[Any, List[str]]:
        """
        Validate and normalize a single setting.

        Args:
            category: Settings category
            key: Setting key
            value: Setting value
            config: Setting configuration from schema

        Returns:
            Tuple of (normalized_value, error_messages)
        """
        errors = []

        # Type validation
        expected_type = config.get('type')
        if not SettingsValidator._validate_type(value, expected_type):
            errors.append(f"Expected type {expected_type}, got {type(value).__name__}")
            return value, errors

        # Range validation for numbers
        if expected_type == 'number':
            if 'min' in config and value < config['min']:
                errors.append(f"Value {value} below minimum {config['min']}")
            if 'max' in config and value > config['max']:
                errors.append(f"Value {value} above maximum {config['max']}")

        # Enum validation
        if 'enum' in config and value not in config['enum']:
            errors.append(f"Value {value} not in allowed values {config['enum']}")

        # Special normalization for specific settings
        normalized_value = SettingsValidator._normalize_setting_value(category, key, value)

        return normalized_value, errors

    @staticmethod
    def _validate_setting_value(category: str, key: str, value: Any, config: Dict[str, Any]) -> List[str]:
        """
        Validate a single setting value.

        Args:
            category: Settings category
            key: Setting key
            value: Setting value
            config: Setting configuration from schema

        Returns:
            List of error messages
        """
        errors = []

        # Type validation
        expected_type = config.get('type')
        if not SettingsValidator._validate_type(value, expected_type):
            errors.append(f"Expected type {expected_type}, got {type(value).__name__}")
            return errors

        # Range validation for numbers
        if expected_type == 'number':
            if 'min' in config and value < config['min']:
                errors.append(f"Value {value} below minimum {config['min']}")
            if 'max' in config and value > config['max']:
                errors.append(f"Value {value} above maximum {config['max']}")

        # Enum validation
        if 'enum' in config and value not in config['enum']:
            errors.append(f"Value {value} not in allowed values {config['enum']}")

        return errors

    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            'string': str,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }

        if expected_type not in type_map:
            return True  # Unknown type, allow it

        expected_python_type = type_map[expected_type]
        return isinstance(value, expected_python_type)

    @staticmethod
    def _normalize_setting_value(category: str, key: str, value: Any) -> Any:
        """Apply special normalization rules for specific settings."""
        # LED brightness normalization (0-100 to 0.0-1.0)
        if category == 'led' and key == 'brightness':
            try:
                if isinstance(value, (int, float)) and value > 1.0:
                    return max(0.0, min(1.0, float(value) / 100.0))
                return max(0.0, min(1.0, float(value)))
            except (ValueError, TypeError):
                return value  # Return as-is if conversion fails, validation will catch it

        # Piano size normalization
        if category == 'piano' and key == 'size':
            if isinstance(value, int):
                return f"{value}-key"

        # Piano specs filling
        if category == 'piano' and key == 'size':
            # This would be handled at category level, but we can normalize here too
            pass

        # GPIO pin normalization
        if category == 'led' and key in ['gpio_pin', 'data_pin']:
            try:
                if isinstance(value, (int, float)):
                    return int(value)
            except (ValueError, TypeError):
                return value

        # Color profile canonicalization
        if category == 'led' and key == 'color_profile':
            if isinstance(value, str):
                cp = value.strip().lower()
                if cp in ['standard', 'standard rgb']:
                    return 'Standard RGB'
                elif cp in ['srgb']:
                    return 'sRGB'
                elif cp in ['adobe rgb', 'adobe']:
                    return 'Adobe RGB'
                elif cp in ['wide gamut', 'wide']:
                    return 'Wide Gamut'

        # Performance mode canonicalization
        if category == 'led' and key == 'performance_mode':
            if isinstance(value, str):
                pm = value.strip().lower()
                mapping = {
                    'power saving': 'Power Saving',
                    'balanced': 'Balanced',
                    'performance': 'Performance',
                    'maximum': 'Maximum'
                }
                if pm in mapping:
                    return mapping[pm]

        return value

    @staticmethod
    def _get_category_schema(category: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get the schema for a settings category."""
        schemas = {
            'audio': {
                'enabled': {'type': 'boolean', 'default': False},
                'volume': {'type': 'number', 'default': 50, 'min': 0, 'max': 100},
                'input_device': {'type': 'string', 'default': 'default'},
                'gain': {'type': 'number', 'default': 1.0, 'min': 0, 'max': 2.0},
                'latency': {'type': 'number', 'default': 50, 'min': 0, 'max': 500},
                'sample_rate': {'type': 'number', 'default': 44100},
                'buffer_size': {'type': 'number', 'default': 1024}
            },
            'piano': {
                'enabled': {'type': 'boolean', 'default': False},
                'octave': {'type': 'number', 'default': 4, 'min': 0, 'max': 8},
                'velocity_sensitivity': {'type': 'number', 'default': 64, 'min': 0, 'max': 127},
                'channel': {'type': 'number', 'default': 1, 'min': 1, 'max': 16},
                'size': {'type': 'string', 'default': '88-key'},
                'keys': {'type': 'number', 'default': 88, 'min': 0, 'max': 128},
                'octaves': {'type': 'number', 'default': 7.25, 'min': 0, 'max': 10},
                'start_note': {'type': 'string', 'default': 'A0'},
                'end_note': {'type': 'string', 'default': 'C8'},
                'key_mapping_mode': {'type': 'string', 'default': 'chromatic'},
                'key_mapping': {'type': 'object', 'default': {}}
            },
            'gpio': {
                'enabled': {'type': 'boolean', 'default': False},
                'pins': {'type': 'array', 'default': []},
                'debounce_time': {'type': 'number', 'default': 50, 'min': 0, 'max': 1000}
            },
            'led': {
                'enabled': {'type': 'boolean', 'default': False},
                'led_count': {'type': 'number', 'default': 246, 'min': 1, 'max': 1000},
                'max_led_count': {'type': 'number', 'default': 1000, 'min': 1, 'max': 1000},
                'brightness': {'type': 'number', 'default': 0.5, 'min': 0, 'max': 1},
                'led_type': {'type': 'string', 'default': 'WS2812B', 'enum': ['WS2812B', 'WS2811', 'WS2813', 'WS2815', 'APA102', 'SK6812']},
                'led_orientation': {'type': 'string', 'default': 'normal', 'enum': ['normal', 'reversed']},
                'led_strip_type': {'type': 'string', 'default': 'WS2811_STRIP_GRB', 'enum': ['WS2811_STRIP_GRB', 'WS2811_STRIP_RGB', 'WS2811_STRIP_BRG', 'WS2811_STRIP_BGR']},
                'power_supply_voltage': {'type': 'number', 'default': 5.0, 'min': 3.0, 'max': 24.0},
                'power_supply_current': {'type': 'number', 'default': 10.0, 'min': 0.1, 'max': 100.0},
                'color_profile': {'type': 'string', 'default': 'Standard RGB', 'enum': ['Standard RGB', 'sRGB', 'Adobe RGB', 'Wide Gamut']},
                'performance_mode': {'type': 'string', 'default': 'Balanced', 'enum': ['Power Saving', 'Balanced', 'Performance', 'Maximum']},
                'gamma_correction': {'type': 'number', 'default': 2.2, 'min': 1.0, 'max': 3.0},
                'white_balance': {'type': 'object', 'default': {'r': 1.0, 'g': 1.0, 'b': 1.0}},
                'color_temperature': {'type': 'number', 'default': 6500, 'min': 2000, 'max': 10000},
                'dither_enabled': {'type': 'boolean', 'default': False},
                'update_rate': {'type': 'number', 'default': 60, 'min': 1, 'max': 120},
                'power_limiting_enabled': {'type': 'boolean', 'default': False},
                'max_power_watts': {'type': 'number', 'default': 100, 'min': 1, 'max': 1000},
                'thermal_protection_enabled': {'type': 'boolean', 'default': False},
                'max_temperature_celsius': {'type': 'number', 'default': 80, 'min': 40, 'max': 100},
                'data_pin': {'type': 'number', 'default': 18, 'min': 1, 'max': 40},
                'clock_pin': {'type': 'number', 'default': 19, 'min': 1, 'max': 40},
                'reverse_order': {'type': 'boolean', 'default': False},
                'color_mode': {'type': 'string', 'default': 'velocity', 'enum': ['rainbow', 'velocity', 'note', 'custom']},
                'color_scheme': {'type': 'string', 'default': 'rainbow'},
                'animation_speed': {'type': 'number', 'default': 1.0, 'min': 0.1, 'max': 3.0},
                'gpio_pin': {'type': 'number', 'default': 19}
            },
            'hardware': {
                'auto_detect_midi': {'type': 'boolean', 'default': True},
                'auto_detect_gpio': {'type': 'boolean', 'default': True},
                'auto_detect_led': {'type': 'boolean', 'default': True},
                'midi_device_id': {'type': 'string', 'default': ''},
                'rtpmidi_enabled': {'type': 'boolean', 'default': False},
                'rtpmidi_port': {'type': 'number', 'default': 5004, 'min': 1024, 'max': 65535}
            },
            'system': {
                'theme': {'type': 'string', 'default': 'auto', 'enum': ['light', 'dark', 'auto']},
                'debug': {'type': 'boolean', 'default': False},
                'log_level': {'type': 'string', 'default': 'info', 'enum': ['debug', 'info', 'warn', 'error']},
                'auto_save': {'type': 'boolean', 'default': True},
                'backup_settings': {'type': 'boolean', 'default': True},
                'performance_mode': {'type': 'string', 'default': 'balanced', 'enum': ['power_save', 'balanced', 'performance']}
            },
            'user': {
                'name': {'type': 'string', 'default': 'User'},
                'email': {'type': 'string', 'default': ''},
                'preferences': {'type': 'object', 'default': {}},
                'favorite_schemes': {'type': 'array', 'default': []},
                'recent_configs': {'type': 'array', 'default': []},
                'last_used_device': {'type': 'string', 'default': ''},
                'navigation_collapsed': {'type': 'boolean', 'default': False}
            },
            'upload': {
                'auto_upload': {'type': 'boolean', 'default': False},
                'remember_last_directory': {'type': 'boolean', 'default': True},
                'show_file_preview': {'type': 'boolean', 'default': True},
                'confirm_before_reset': {'type': 'boolean', 'default': True},
                'last_uploaded_file': {'type': 'string', 'default': ''}
            },
            'ui': {
                'theme': {'type': 'string', 'default': 'auto', 'enum': ['light', 'dark', 'auto']},
                'reduced_motion': {'type': 'boolean', 'default': False},
                'show_tooltips': {'type': 'boolean', 'default': True},
                'tooltip_delay': {'type': 'number', 'default': 300, 'min': 0, 'max': 2000},
                'animation_speed': {'type': 'string', 'default': 'normal', 'enum': ['slow', 'normal', 'fast']}
            },
            'a11y': {
                'highContrast': {'type': 'boolean', 'default': False},
                'largeText': {'type': 'boolean', 'default': False},
                'keyboardNavigation': {'type': 'boolean', 'default': True},
                'screenReaderOptimized': {'type': 'boolean', 'default': False}
            },
            'help': {
                'showOnboarding': {'type': 'boolean', 'default': True},
                'showHints': {'type': 'boolean', 'default': True},
                'completedTours': {'type': 'array', 'default': []},
                'skippedTours': {'type': 'array', 'default': []},
                'tourCompleted': {'type': 'boolean', 'default': False}
            },
            'history': {
                'maxHistorySize': {'type': 'number', 'default': 50, 'min': 10, 'max': 200},
                'autosaveInterval': {'type': 'number', 'default': 30000, 'min': 5000, 'max': 300000},
                'persistHistory': {'type': 'boolean', 'default': True}
            }
        }

        return schemas.get(category)

    @staticmethod
    def normalize_piano_settings(piano_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Special normalization for piano settings that depend on each other.

        Args:
            piano_settings: Piano category settings

        Returns:
            Normalized piano settings
        """
        normalized = dict(piano_settings)

        # If size is provided, fill in derived specs
        if 'size' in normalized:
            try:
                specs = get_piano_specs(str(normalized.get('size')))
                # Fill missing fields from specs
                if 'keys' not in normalized or normalized.get('keys') is None:
                    normalized['keys'] = specs.get('keys')
                if 'octaves' not in normalized or normalized.get('octaves') is None:
                    normalized['octaves'] = specs.get('octaves')
                if 'start_note' not in normalized or not normalized.get('start_note'):
                    normalized['start_note'] = specs.get('start_note')
                if 'end_note' not in normalized or not normalized.get('end_note'):
                    normalized['end_note'] = specs.get('end_note')
            except Exception as e:
                logger.warning(f"Error normalizing piano specs: {e}")

        # Ensure mode and mapping types
        if 'key_mapping_mode' not in normalized or not isinstance(normalized.get('key_mapping_mode'), str):
            normalized['key_mapping_mode'] = 'chromatic'
        km = normalized.get('key_mapping')
        if not isinstance(km, dict):
            normalized['key_mapping'] = {}

        return normalized