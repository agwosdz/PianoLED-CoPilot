#!/usr/bin/env python3
"""
Configuration management for Piano LED Visualizer
Handles persistent storage of configuration values
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.logging_config import get_logger

# Configure logging
logger = get_logger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "led_count": 246,  # Default LED count
    "max_led_count": 300,  # Maximum allowed LED count
    "brightness": 0.5,  # Default brightness
    "pin": 19,  # Default GPIO pin (legacy)
    "piano_size": "88-key",  # Piano size: 25-key, 37-key, 49-key, 61-key, 76-key, 88-key, custom
    "gpio_pin": 19,  # GPIO pin for LED strip data
    "led_orientation": "normal",  # LED orientation: normal, reversed
    
    # Extended hardware configuration
    "led_type": "WS2812B",  # LED strip type: WS2812B, WS2813, WS2815, etc.
    "power_supply_voltage": 5.0,  # Power supply voltage (V)
    "power_supply_current": 10.0,  # Power supply max current (A)
    "gpio_power_pin": None,  # Optional GPIO pin for power control
    "gpio_ground_pin": None,  # Optional GPIO pin for ground reference
    "signal_level": 3.3,  # Signal voltage level (V)
    
    # Piano key mapping configuration
    "key_mapping": {},  # Custom key-to-LED mapping {midi_note: led_index or [led_indices]}
    "mapping_mode": "auto",  # Mapping mode: auto, manual, proportional, custom (legacy)
    "key_offset": 0,  # Offset for key mapping alignment
    "leds_per_key": 3,  # Number of LEDs to light up per key
    "mapping_base_offset": 0,  # Base offset for the entire mapping
    
    # Advanced timing and performance settings
    "led_frequency": 800000,  # LED strip frequency (Hz)
    "led_dma": 10,  # DMA channel for LED control
    "led_invert": False,  # Invert signal polarity
    "led_channel": 0,  # PWM channel
    "led_strip_type": "WS2811_STRIP_GRB",  # Strip color order
    
    # Color calibration settings
    "color_temperature": 6500,  # Color temperature (K)
    "gamma_correction": 2.2,  # Gamma correction value
    "color_balance": {"red": 1.0, "green": 1.0, "blue": 1.0},  # RGB balance
    
    # Hardware detection and validation
    "auto_detect_hardware": True,  # Enable automatic hardware detection
    "validate_gpio_pins": True,  # Validate GPIO pin availability
    "hardware_test_enabled": True,  # Enable hardware testing features
    
    # Enhanced LED configuration
    "led_strip_type": "WS2811_STRIP_GRB",  # LED strip color order
    "color_profile": "standard",  # Color profile: standard, warm_white, cool_white, music_viz
    "performance_mode": "balanced",  # Performance mode: quality, balanced, performance
    
    # Advanced settings for enhanced LED control
    "white_balance": {"r": 1.0, "g": 1.0, "b": 1.0},  # White balance RGB multipliers
    "dither_enabled": True,  # Enable dithering for smoother color transitions
    "update_rate": 60,  # LED update rate (Hz)
    "power_limiting_enabled": False,  # Enable power limiting
    "max_power_watts": 100,  # Maximum power consumption (W)
    "thermal_protection_enabled": True,  # Enable thermal protection
    "max_temperature_celsius": 85,  # Maximum operating temperature (°C)
    
    # Enhanced GPIO configuration
    "gpio_pull_up": [],  # GPIO pins to configure with pull-up resistors
    "gpio_pull_down": [],  # GPIO pins to configure with pull-down resistors
    "pwm_range": 4096,  # PWM range for precise control
    "spi_speed": 8000000,  # SPI speed for SPI-based LED strips (Hz)
    
    # Piano configuration enhancements
    "piano_keys": 88,  # Number of piano keys
    "piano_octaves": 7,  # Number of octaves
    "piano_start_note": "A0",  # Starting note
    "piano_end_note": "C8",  # Ending note
    "key_mapping_mode": "chromatic",  # Key mapping mode: chromatic, white-keys-only, custom
}

# Configuration file path
CONFIG_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    """Load configuration from file or create with defaults if not exists"""
    if not CONFIG_FILE.exists():
        # Create default configuration file
        save_config(DEFAULT_CONFIG)
        logger.info(f"Created default configuration file at {CONFIG_FILE}")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from {CONFIG_FILE}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        logger.info("Using default configuration")
        return DEFAULT_CONFIG


def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved configuration to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return False


def update_config(key, value):
    """Update a specific configuration value"""
    config = load_config()
    config[key] = value
    return save_config(config)


def get_config(key, default=None):
    """Get a specific configuration value"""
    config = load_config()
    return config.get(key, default)


def validate_config(config):
    """Validate configuration values"""
    errors = []
    
    # Validate LED count
    if "led_count" in config:
        if not isinstance(config["led_count"], int) or config["led_count"] <= 0:
            errors.append("led_count must be a positive integer")
        elif config["led_count"] > config.get("max_led_count", 300):
            errors.append(f"led_count cannot exceed {config.get('max_led_count', 300)}")
    
    # Validate GPIO pin
    if "gpio_pin" in config:
        if not isinstance(config["gpio_pin"], int) or not (0 <= config["gpio_pin"] <= 27):
            errors.append("gpio_pin must be an integer between 0 and 27")
    
    # Validate optional GPIO pins
    for pin_name in ["gpio_power_pin", "gpio_ground_pin"]:
        if pin_name in config and config[pin_name] is not None:
            if not isinstance(config[pin_name], int) or not (0 <= config[pin_name] <= 27):
                errors.append(f"{pin_name} must be an integer between 0 and 27 or None")
    
    # Validate piano size
    if "piano_size" in config:
        valid_sizes = ["25-key", "37-key", "49-key", "61-key", "76-key", "88-key", "custom"]
        if config["piano_size"] not in valid_sizes:
            errors.append(f"piano_size must be one of: {', '.join(valid_sizes)}")
    
    # Validate LED orientation
    if "led_orientation" in config:
        valid_orientations = ["normal", "reversed"]
        if config["led_orientation"] not in valid_orientations:
            errors.append(f"led_orientation must be one of: {', '.join(valid_orientations)}")
    
    # Validate brightness
    if "brightness" in config:
        if not isinstance(config["brightness"], (int, float)) or not (0.0 <= config["brightness"] <= 1.0):
            errors.append("brightness must be a number between 0.0 and 1.0")
    
    # Validate LED type
    if "led_type" in config:
        valid_led_types = ["WS2812B", "WS2811", "WS2813", "WS2815", "APA102", "SK6812"]
        if config["led_type"] not in valid_led_types:
            errors.append(f"led_type must be one of: {', '.join(valid_led_types)}")
    
    # Validate power supply settings
    if "power_supply_voltage" in config:
        voltage = config["power_supply_voltage"]
        if not isinstance(voltage, (int, float)) or not (3.0 <= voltage <= 12.0):
            errors.append("power_supply_voltage must be between 3.0V and 12.0V")
    
    if "power_supply_current" in config:
        current = config["power_supply_current"]
        if not isinstance(current, (int, float)) or not (0.5 <= current <= 50.0):
            errors.append("power_supply_current must be between 0.5A and 50.0A")
    
    # Validate signal level
    if "signal_level" in config:
        signal_level = config["signal_level"]
        if signal_level not in [3.3, 5.0]:
            errors.append("signal_level must be either 3.3V or 5.0V")
    
    # Validate mapping mode
    if "mapping_mode" in config:
        valid_mapping_modes = ["auto", "manual", "proportional", "custom"]
        if config["mapping_mode"] not in valid_mapping_modes:
            errors.append(f"mapping_mode must be one of: {', '.join(valid_mapping_modes)}")
    
    # Validate leds_per_key
    if "leds_per_key" in config:
        leds_per_key = config["leds_per_key"]
        if not isinstance(leds_per_key, int) or leds_per_key < 1:
            errors.append("leds_per_key must be a positive integer")
        elif leds_per_key > 10:
            errors.append("leds_per_key cannot exceed 10 for performance reasons")
    
    # Validate mapping_base_offset
    if "mapping_base_offset" in config:
        mapping_base_offset = config["mapping_base_offset"]
        if not isinstance(mapping_base_offset, int) or mapping_base_offset < 0:
            errors.append("mapping_base_offset must be a non-negative integer")
        elif mapping_base_offset >= config.get("led_count", 300):
            errors.append("mapping_base_offset must be less than led_count")
    
    # Validate LED frequency
    if "led_frequency" in config:
        frequency = config["led_frequency"]
        if frequency not in [400000, 800000]:
            errors.append("led_frequency must be either 400000Hz or 800000Hz")
    
    # Validate color temperature
    if "color_temperature" in config:
        color_temp = config["color_temperature"]
        if not isinstance(color_temp, (int, float)) or not (2700 <= color_temp <= 10000):
            errors.append("color_temperature must be between 2700K and 10000K")
    
    # Validate gamma correction
    if "gamma_correction" in config:
        gamma = config["gamma_correction"]
        if not isinstance(gamma, (int, float)) or not (1.0 <= gamma <= 3.0):
            errors.append("gamma_correction must be between 1.0 and 3.0")
    
    # Validate color balance
    if "color_balance" in config:
        color_balance = config["color_balance"]
        if not isinstance(color_balance, dict):
            errors.append("color_balance must be a dictionary")
        else:
            for color in ["red", "green", "blue"]:
                if color not in color_balance:
                    errors.append(f"color_balance must include {color} value")
                elif not isinstance(color_balance[color], (int, float)) or not (0.0 <= color_balance[color] <= 2.0):
                    errors.append(f"color_balance.{color} must be between 0.0 and 2.0")
    
    # Validate color profile
    if "color_profile" in config:
        valid_profiles = ["standard", "warm_white", "cool_white", "music_viz"]
        if config["color_profile"] not in valid_profiles:
            errors.append(f"color_profile must be one of: {', '.join(valid_profiles)}")
    
    # Validate performance mode
    if "performance_mode" in config:
        valid_modes = ["quality", "balanced", "performance"]
        if config["performance_mode"] not in valid_modes:
            errors.append(f"performance_mode must be one of: {', '.join(valid_modes)}")
    
    # Validate white balance
    if "white_balance" in config:
        white_balance = config["white_balance"]
        if not isinstance(white_balance, dict):
            errors.append("white_balance must be a dictionary")
        else:
            for color in ["r", "g", "b"]:
                if color not in white_balance:
                    errors.append(f"white_balance must include {color} value")
                elif not isinstance(white_balance[color], (int, float)) or not (0.0 <= white_balance[color] <= 2.0):
                    errors.append(f"white_balance.{color} must be between 0.0 and 2.0")
    
    # Validate update rate
    if "update_rate" in config:
        rate = config["update_rate"]
        if not isinstance(rate, (int, float)) or not (1 <= rate <= 120):
            errors.append("update_rate must be between 1 and 120 Hz")
    
    # Validate max power watts
    if "max_power_watts" in config:
        power = config["max_power_watts"]
        if not isinstance(power, (int, float)) or power <= 0:
            errors.append("max_power_watts must be a positive number")
    
    # Validate max temperature
    if "max_temperature_celsius" in config:
        temp = config["max_temperature_celsius"]
        if not isinstance(temp, (int, float)) or not (0 <= temp <= 150):
            errors.append("max_temperature_celsius must be between 0 and 150")
    
    # Validate GPIO pull resistor configurations
    for pull_key in ["gpio_pull_up", "gpio_pull_down"]:
        if pull_key in config:
            pins = config[pull_key]
            if not isinstance(pins, list):
                errors.append(f"{pull_key} must be a list")
            else:
                for pin in pins:
                    if not isinstance(pin, int) or not (0 <= pin <= 27):
                        errors.append(f"{pull_key} pin {pin} must be an integer between 0 and 27")
    
    # Validate PWM range
    if "pwm_range" in config:
        pwm_range = config["pwm_range"]
        if not isinstance(pwm_range, int) or not (256 <= pwm_range <= 65536):
            errors.append("pwm_range must be an integer between 256 and 65536")
    
    # Validate SPI speed
    if "spi_speed" in config:
        speed = config["spi_speed"]
        if not isinstance(speed, int) or not (1000000 <= speed <= 32000000):
            errors.append("spi_speed must be between 1MHz and 32MHz")
    
    # Validate piano configuration
    if "piano_keys" in config:
        keys = config["piano_keys"]
        if not isinstance(keys, int) or not (25 <= keys <= 128):
            errors.append("piano_keys must be between 25 and 128")
    
    if "piano_octaves" in config:
        octaves = config["piano_octaves"]
        if not isinstance(octaves, (int, float)) or not (2 <= octaves <= 10):
            errors.append("piano_octaves must be between 2 and 10")
    
    # Validate key mapping mode
    if "key_mapping_mode" in config:
        valid_modes = ["chromatic", "white-keys-only", "custom"]
        if config["key_mapping_mode"] not in valid_modes:
            errors.append(f"key_mapping_mode must be one of: {', '.join(valid_modes)}")
    
    # Validate boolean flags
    boolean_fields = [
        "dither_enabled", "power_limiting_enabled", "thermal_protection_enabled",
        "auto_detect_hardware", "validate_gpio_pins", "hardware_test_enabled",
        "led_invert"
    ]
    for field in boolean_fields:
        if field in config and not isinstance(config[field], bool):
            errors.append(f"{field} must be a boolean value")
    
    # Validate key mapping
    if "key_mapping" in config:
        key_mapping = config["key_mapping"]
        if not isinstance(key_mapping, dict):
            errors.append("key_mapping must be a dictionary")
        else:
            for midi_note, led_indices in key_mapping.items():
                try:
                    midi_note_int = int(midi_note)
                    if not (0 <= midi_note_int <= 127):
                        errors.append(f"MIDI note {midi_note} must be between 0 and 127")
                except ValueError:
                    errors.append(f"MIDI note {midi_note} must be a valid integer")
                
                # Accept both single LED index (int) and multiple LED indices (list[int])
                if isinstance(led_indices, int):
                    if led_indices < 0:
                        errors.append(f"LED index {led_indices} must be a non-negative integer")
                elif isinstance(led_indices, list):
                    if not led_indices:
                        errors.append(f"LED indices list for MIDI note {midi_note} cannot be empty")
                    for led_index in led_indices:
                        if not isinstance(led_index, int) or led_index < 0:
                            errors.append(f"LED index {led_index} must be a non-negative integer")
                else:
                    errors.append(f"LED indices for MIDI note {midi_note} must be an integer or list of integers")
    
    return errors


def validate_config_comprehensive(config):
    """Comprehensive configuration validation with cross-field checks"""
    # Normalize incoming configurations to support older/different shapes used by some callers/tests
    def _normalize_config_for_validation(input_config):
        normalized = dict(input_config) if isinstance(input_config, dict) else {}
        # Normalize brightness from 0-255 scale to 0.0-1.0 if needed
        b = normalized.get('brightness')
        if isinstance(b, (int, float)) and b > 1.0:
            try:
                if b <= 255:
                    normalized['brightness'] = round(float(b) / 255.0, 3)
            except Exception:
                pass
        # Normalize piano_size numeric to string form like "88-key"
        ps = normalized.get('piano_size')
        if isinstance(ps, int):
            normalized['piano_size'] = f"{ps}-key"
        # Map nested power_supply to flat keys
        if isinstance(normalized.get('power_supply'), dict):
            psup = normalized['power_supply']
            if 'voltage' in psup:
                normalized['power_supply_voltage'] = psup['voltage']
            if 'max_current' in psup:
                normalized['power_supply_current'] = psup['max_current']
        # Map nested gpio_pins to flat primary data pin
        if isinstance(normalized.get('gpio_pins'), dict):
            gp = normalized['gpio_pins']
            if gp.get('data_pin') is not None:
                normalized['gpio_pin'] = gp.get('data_pin')
        # Normalize orientation synonyms
        lo = normalized.get('led_orientation')
        if lo == 'bottom_up':
            normalized['led_orientation'] = 'reversed'
        elif lo == 'top_down':
            normalized['led_orientation'] = 'normal'
        # Normalize signal_level string like '3.3V' -> 3.3
        sl = normalized.get('signal_level')
        if isinstance(sl, str) and sl.strip().lower().endswith('v'):
            try:
                normalized['signal_level'] = float(sl.strip().lower().replace('v', ''))
            except Exception:
                pass
        # Map unknown mapping_mode values to supported ones
        mm = normalized.get('mapping_mode')
        if mm == 'linear':
            normalized['mapping_mode'] = 'auto'
        return normalized

    normalized = _normalize_config_for_validation(config)

    errors = validate_config(normalized)
    warnings = []
    
    # Cross-validation: Power consumption vs supply capacity
    if all(key in normalized for key in ["led_count", "brightness", "led_type", "power_supply_current", "power_supply_voltage"]):
        power_consumption = calculate_led_power_consumption(
            normalized["led_count"], 
            normalized["brightness"], 
            normalized["led_type"]
        )
        max_power = normalized["power_supply_voltage"] * normalized["power_supply_current"]
        
        if power_consumption.get("total_watts", 0) > max_power:
            errors.append(
                f"Power consumption ({power_consumption.get('total_watts', 0):.1f}W) exceeds "
                f"power supply capacity ({max_power:.1f}W)"
            )
        elif power_consumption.get("total_watts", 0) > max_power * 0.8:
            warnings.append(
                f"Power consumption ({power_consumption.get('total_watts', 0):.1f}W) is close to "
                f"power supply capacity ({max_power:.1f}W). Consider reducing brightness or LED count."
            )
    
    # Cross-validation: GPIO pin conflicts (support both flat and nested gpio_pins)
    gpio_pins_seen = []

    def _add_pin(pin_val):
        if pin_val is None:
            return
        if pin_val in gpio_pins_seen:
            errors.append(f"GPIO pin {pin_val} is used multiple times")
        gpio_pins_seen.append(pin_val)

    # Flat pins
    for pin_key in ["gpio_pin", "gpio_power_pin", "gpio_ground_pin"]:
        _add_pin(normalized.get(pin_key))

    # Nested pins
    gp = normalized.get('gpio_pins')
    if isinstance(gp, dict):
        for nested_key in ["data_pin", "clock_pin", "power_pin", "ground_pin"]:
            _add_pin(gp.get(nested_key))
    
    # Cross-validation: Piano size vs LED count consistency
    if "piano_size" in normalized and "led_count" in normalized and normalized["piano_size"] != "custom":
        piano_specs = get_piano_specs(normalized["piano_size"])
        recommended_leds = piano_specs["keys"] * 3  # Rough estimate
        
        if piano_specs["keys"] > 0 and abs(normalized["led_count"] - recommended_leds) > max(recommended_leds * 0.5, 1):
            warnings.append(
                f"LED count ({normalized['led_count']}) seems inconsistent with piano size "
                f"({normalized['piano_size']}). Recommended: ~{recommended_leds} LEDs"
            )
    
    return {
        "valid": len(errors) == 0,
        "is_valid": len(errors) == 0,  # alias for compatibility with some tests/clients
        "errors": errors,
        "warnings": warnings
    }


def backup_config():
    """Create a backup of the current configuration"""
    try:
        if CONFIG_FILE.exists():
            backup_file = CONFIG_FILE.with_suffix('.json.backup')
            import shutil
            shutil.copy2(CONFIG_FILE, backup_file)
            logger.info(f"Configuration backed up to {backup_file}")
            return True
    except Exception as e:
        logger.error(f"Failed to backup configuration: {e}")
        return False


def restore_config_from_backup():
    """Restore configuration from backup"""
    try:
        backup_file = CONFIG_FILE.with_suffix('.json.backup')
        if backup_file.exists():
            import shutil
            shutil.copy2(backup_file, CONFIG_FILE)
            logger.info(f"Configuration restored from {backup_file}")
            return True
        else:
            logger.warning("No backup file found")
            return False
    except Exception as e:
        logger.error(f"Failed to restore configuration: {e}")
        return False


def reset_config_to_defaults():
    """Reset configuration to default values"""
    try:
        backup_config()  # Backup current config first
        save_config(DEFAULT_CONFIG.copy())
        logger.info("Configuration reset to defaults")
        return True
    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}")
        return False


def export_config(export_path):
    """Export configuration to a specified file"""
    try:
        config = load_config()
        export_file = Path(export_path)
        
        with open(export_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration exported to {export_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to export configuration: {e}")
        return False


def import_config(import_path, validate_before_save=True):
    """Import configuration from a specified file"""
    try:
        import_file = Path(import_path)
        
        if not import_file.exists():
            logger.error(f"Import file {import_file} does not exist")
            return False
        
        with open(import_file, 'r') as f:
            imported_config = json.load(f)
        
        if validate_before_save:
            validation_result = validate_config_comprehensive(imported_config)
            if not validation_result["valid"]:
                logger.error(f"Imported configuration is invalid: {validation_result['errors']}")
                return False
        
        backup_config()  # Backup current config first
        save_config(imported_config)
        logger.info(f"Configuration imported from {import_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to import configuration: {e}")
        return False


def get_config_history():
    """Get configuration change history (if backup files exist)"""
    try:
        config_dir = CONFIG_FILE.parent
        backup_files = list(config_dir.glob("config.json.backup*"))
        
        history = []
        for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
            stat = backup_file.stat()
            history.append({
                "file": str(backup_file),
                "modified": stat.st_mtime,
                "size": stat.st_size
            })
        
        return history
    except Exception as e:
        logger.error(f"Failed to get configuration history: {e}")
        return []


def get_piano_specs(piano_size):
    """Get piano specifications based on size"""
    specs = {
        "25-key": {"keys": 25, "octaves": 2, "start_note": "C3", "end_note": "C5", "midi_start": 48, "midi_end": 72},
        "37-key": {"keys": 37, "octaves": 3, "start_note": "C2", "end_note": "C5", "midi_start": 36, "midi_end": 72},
        "49-key": {"keys": 49, "octaves": 4, "start_note": "C2", "end_note": "C6", "midi_start": 36, "midi_end": 84},
        "61-key": {"keys": 61, "octaves": 5, "start_note": "C2", "end_note": "C7", "midi_start": 36, "midi_end": 96},
        "76-key": {"keys": 76, "octaves": 6.25, "start_note": "E1", "end_note": "G7", "midi_start": 28, "midi_end": 103},
        "88-key": {"keys": 88, "octaves": 7.25, "start_note": "A0", "end_note": "C8", "midi_start": 21, "midi_end": 108},
        "custom": {"keys": 0, "octaves": 0, "start_note": "", "end_note": "", "midi_start": 0, "midi_end": 127}
    }
    return specs.get(piano_size, specs["88-key"])


def calculate_led_power_consumption(led_count, brightness=1.0, led_type="WS2812B"):
    """Calculate estimated power consumption for LED strip with enhanced analysis"""
    # Power consumption per LED at full brightness (mA)
    led_power_specs = {
        "WS2812B": {"current_ma": 60, "voltage": 5.0, "max_temp": 85},
        "WS2813": {"current_ma": 60, "voltage": 5.0, "max_temp": 85},
        "WS2815": {"current_ma": 60, "voltage": 12.0, "max_temp": 85},
        "APA102": {"current_ma": 60, "voltage": 5.0, "max_temp": 85},
        "SK6812": {"current_ma": 60, "voltage": 5.0, "max_temp": 85}
    }
    
    led_spec = led_power_specs.get(led_type, led_power_specs["WS2812B"])
    power_per_led = led_spec["current_ma"]
    voltage = led_spec["voltage"]
    
    # Calculate power consumption
    total_current_ma = led_count * power_per_led * brightness
    total_current_amps = total_current_ma / 1000
    total_watts = round(total_current_amps * voltage, 2)
    
    # Calculate thermal considerations
    heat_dissipation_per_led = 0.2  # Watts per LED at full brightness
    total_heat = round(led_count * heat_dissipation_per_led * brightness, 2)
    
    # Power efficiency calculations
    efficiency = 0.85  # Typical LED strip efficiency
    actual_power_draw = round(total_watts / efficiency, 2)
    
    # Safety margins
    recommended_supply_amps = round(total_current_amps * 1.2, 2)  # 20% safety margin
    recommended_supply_watts = round(actual_power_draw * 1.3, 2)  # 30% safety margin
    
    return {
        "led_count": led_count,
        "brightness": brightness,
        "led_type": led_type,
        "voltage": voltage,
        "current_amps": round(total_current_amps, 3),
        "current_ma": round(total_current_ma),
        "power_watts": total_watts,
        "total_watts": total_watts,  # alias for compatibility
        "power_5v_watts": total_watts if voltage == 5.0 else round(total_current_amps * 5.0, 2),
        "actual_power_draw": actual_power_draw,
        "heat_dissipation_watts": total_heat,
        "efficiency": efficiency,
        "recommended_supply_amps": recommended_supply_amps,
        "recommended_supply_watts": recommended_supply_watts,
        "max_operating_temp": led_spec["max_temp"],
        "power_per_led_ma": power_per_led,
        "power_density": round(total_watts / max(led_count, 1), 3)  # Watts per LED
    }


def generate_auto_key_mapping(piano_size, led_count, led_orientation="normal", leds_per_key=None, mapping_base_offset=None, distribution_mode="proportional"):
    """Generate automatic key-to-LED mapping based on piano size and LED count
    
    Uses calibration range (start_led to end_led) to compute LED-per-key distribution dynamically.
    This ensures that the usable LED range is utilized optimally without waste.
    
    Args:
        piano_size: Piano size (e.g., "88-key")
        led_count: Total number of LEDs available (or usable range size if mapping_base_offset used)
        led_orientation: LED orientation ("normal" or "reversed") - NOT applied here, 
                        physical reversal happens in LEDController._map_led_index()
        leds_per_key: Number of LEDs per key (overrides calculation if provided)
        mapping_base_offset: Base offset (start_led) for the entire mapping (default: 0).
                           This represents the calibration range start point.
        distribution_mode: LED distribution mode ("proportional", "fixed", or "custom") - default: "proportional"
    
    Returns:
        dict: Mapping of MIDI note to list of LED indices (logical, not physical)
    """
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
    
    specs = get_piano_specs(piano_size)
    key_count = specs["keys"]
    
    if key_count == 0:  # Custom piano size
        logger.warning(f"Piano size '{piano_size}' has 0 keys, returning empty mapping")
        return {}
    
    # Use provided values or calculate defaults
    if mapping_base_offset is None:
        mapping_base_offset = 0
    
    # Calculate available LED count:
    # - If mapping_base_offset > 0, then led_count is the usable range size (end_led - start_led)
    # - Otherwise, available_leds = led_count - mapping_base_offset
    available_leds = led_count if mapping_base_offset > 0 else (led_count - mapping_base_offset)
    
    logger.info(f"Generating auto mapping for {piano_size} ({key_count} keys) "
               f"with {led_count} total LEDs, base_offset={mapping_base_offset}, "
               f"available={available_leds}, distribution_mode={distribution_mode}")
    
    if available_leds <= 0:
        logger.error(f"Invalid LED count: total={led_count}, base_offset={mapping_base_offset}, "
                    f"available={available_leds}. Mapping cannot be generated.")
        return {}
    
    # Validate and apply distribution mode
    valid_modes = ["proportional", "fixed", "custom"]
    if distribution_mode not in valid_modes:
        logger.warning(f"Invalid distribution_mode '{distribution_mode}', using 'proportional'")
        distribution_mode = "proportional"
    
    logger.info(f"Distribution mode: {distribution_mode} "
               f"{'(will use provided leds_per_key)' if leds_per_key else '(auto-calculate)'}")
    
    # Calculate LEDs per key based on distribution mode
    was_leds_per_key_auto_calculated = False
    original_key_count = key_count
    remaining_leds = 0  # Initialize to handle all paths
    
    if leds_per_key is None:
        if distribution_mode == "proportional":
            # Proportional: distribute LEDs evenly across all keys
            leds_per_key = available_leds // key_count
            remaining_leds = available_leds % key_count
            was_leds_per_key_auto_calculated = True
            logger.info(f"Proportional mode: Auto-calculated {leds_per_key} LEDs/key "
                       f"with {remaining_leds} remaining LEDs")
            if remaining_leds > 0:
                logger.info(f"Distribution: First {remaining_leds} keys will get +1 LED "
                           f"({remaining_leds} keys × {leds_per_key + 1} LEDs, "
                           f"{key_count - remaining_leds} keys × {leds_per_key} LEDs)")
        
        elif distribution_mode == "fixed":
            # Fixed: use a fixed number of LEDs per key (from settings or default)
            # Default to 3 LEDs per key if not specified elsewhere
            leds_per_key = 1  # Will be overridden by settings or explicit parameter
            remaining_leds = 0  # Fixed mode doesn't use remaining LEDs distribution
            logger.info(f"Fixed mode: Will use fixed leds_per_key (to be specified)")
        
        elif distribution_mode == "custom":
            # Custom: allow for special distributions (advanced users)
            logger.info(f"Custom mode: Using custom distribution configuration")
            leds_per_key = available_leds // key_count  # Fallback to proportional
            remaining_leds = available_leds % key_count
            logger.info(f"Custom mode fallback: {leds_per_key} LEDs/key "
                       f"with {remaining_leds} remaining LEDs")
    else:
        # When leds_per_key is specified, calculate how many keys we can map
        max_mappable_keys = available_leds // leds_per_key
        if max_mappable_keys < key_count:
            logger.warning(f"Specified {leds_per_key} LEDs/key, but only {max_mappable_keys}/{key_count} "
                          f"keys can be mapped. Keys {specs['midi_start'] + max_mappable_keys} to "
                          f"{specs['midi_end']} will be UNMAPPED.")
            key_count = max_mappable_keys
        else:
            logger.info(f"Specified {leds_per_key} LEDs/key: will map {max_mappable_keys}/{original_key_count} keys")
        
        remaining_leds = available_leds - (key_count * leds_per_key)
        if remaining_leds > 0:
            logger.info(f"Unused LEDs with fixed leds_per_key: {remaining_leds}")
        else:
            remaining_leds = 0  # Ensure non-negative
    
    mapping = {}
    led_index = mapping_base_offset
    
    for key_num in range(key_count):
        midi_note = specs["midi_start"] + key_num
        
        # Distribute remaining LEDs among first keys (only when leds_per_key is calculated)
        if leds_per_key is None or remaining_leds > 0:
            key_led_count = leds_per_key + (1 if key_num < remaining_leds else 0)
        else:
            key_led_count = leds_per_key
        
        # Create LED range for this key (logical indices only)
        led_range = list(range(led_index, led_index + key_led_count))
        mapping[midi_note] = led_range
        led_index += key_led_count
    
    logger.info(f"Mapping complete: {len(mapping)} keys mapped, "
               f"LED range {mapping_base_offset} to {led_index - 1}, "
               f"total LEDs used={led_index - mapping_base_offset}, "
               f"distribution_mode={distribution_mode}")
    
    if original_key_count > key_count:
        unmapped_count = original_key_count - key_count
        logger.warning(f"Result: {key_count}/{original_key_count} keys mapped, "
                      f"{unmapped_count} keys UNMAPPED (insufficient LEDs)")
    
    return mapping


def apply_calibration_offsets_to_mapping(mapping, start_led=0, end_led=None, key_offsets=None, key_led_trims=None, led_count=None, weld_offsets=None):
    """Apply calibration offsets and LED trims to a pre-computed key mapping with cascading individual offsets and weld compensations
    
    Args:
        mapping: Base key-to-LED mapping dict
        start_led: First LED index at the beginning of the piano (clamp min)
        end_led: Last LED index at the end of the piano (clamp max)
        key_offsets: Per-key offset dict {midi_note: offset}
                     Individual offsets cascade: an offset at note N affects all notes >= N
        key_led_trims: Per-key LED trim dict {midi_note: {left_trim: N, right_trim: M}}
                       Trims are applied AFTER offsets to the adjusted LED indices
        led_count: Total LED count for bounds checking (optional, no bounds if None)
        weld_offsets: Weld offset dict {led_index: offset_mm} for LED strip welds/joints
                      Offsets after a weld are adjusted by the cumulative weld offset to account for
                      density discontinuities at solder points
    
    Returns:
        dict: Adjusted mapping with LED range clamped to [start_led, end_led], cascading key offsets applied,
              trims applied, and weld compensations factored in
    """
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
    
    if end_led is None:
        end_led = (led_count - 1) if led_count else 245
    
    if not mapping or (start_led == 0 and end_led == (led_count - 1 if led_count else 245) and not key_offsets and not key_led_trims and not weld_offsets):
        logger.debug(f"Skipping offset application: mapping_empty={not mapping}, "
                    f"start_led={start_led}, end_led={end_led}, key_offsets_empty={not key_offsets}, "
                    f"key_led_trims_empty={not key_led_trims}, weld_offsets_empty={not weld_offsets}")
        return mapping
    
    if key_offsets is None:
        key_offsets = {}
    if key_led_trims is None:
        key_led_trims = {}
    if weld_offsets is None:
        weld_offsets = {}
    
    logger.info(f"Applying calibration offsets to mapping with {len(mapping)} entries. "
               f"start_led={start_led}, end_led={end_led}, key_offsets_count={len(key_offsets)}, "
               f"key_led_trims_count={len(key_led_trims)}, weld_offsets_count={len(weld_offsets)}, "
               f"led_count={led_count}")
    
    # Normalize and sort weld offsets by LED index for efficient processing
    normalized_weld_offsets = {}
    invalid_weld_count = 0
    for led_idx_str, offset_val in weld_offsets.items():
        try:
            led_idx = int(led_idx_str) if isinstance(led_idx_str, str) else led_idx_str
            offset_mm = float(offset_val) if isinstance(offset_val, (str, int)) else offset_val
            normalized_weld_offsets[led_idx] = offset_mm
        except (ValueError, TypeError):
            invalid_weld_count += 1
            continue
    
    if invalid_weld_count > 0:
        logger.warning(f"Skipped {invalid_weld_count} invalid weld offset entries during normalization")
    
    if normalized_weld_offsets:
        logger.debug(f"Normalized {len(normalized_weld_offsets)} weld offsets. "
                    f"LED indices: {sorted(normalized_weld_offsets.keys())}, "
                    f"Offsets (mm): {[normalized_weld_offsets[i] for i in sorted(normalized_weld_offsets.keys())]}")
    
    # Normalize key_led_trims to ensure all keys are integers and trim values are valid
    normalized_key_led_trims = {}
    invalid_trims_count = 0
    for key, trim_value in key_led_trims.items():
        try:
            note_num = int(key) if isinstance(key, str) else key
            if isinstance(trim_value, dict):
                left_trim = int(trim_value.get('left_trim', 0))
                right_trim = int(trim_value.get('right_trim', 0))
                normalized_key_led_trims[note_num] = {
                    'left_trim': left_trim,
                    'right_trim': right_trim
                }
            else:
                invalid_trims_count += 1
        except (ValueError, TypeError):
            invalid_trims_count += 1
            continue  # Skip invalid entries
    
    if invalid_trims_count > 0:
        logger.warning(f"Skipped {invalid_trims_count} invalid trim entries during normalization")
    
    if normalized_key_led_trims:
        logger.debug(f"Normalized {len(normalized_key_led_trims)} key LED trims. "
                    f"Notes with trims: {sorted(normalized_key_led_trims.keys())}")
    
    adjusted = {}
    
    # Normalize key_offsets to ensure all keys and values are integers
    normalized_key_offsets = {}
    invalid_offsets_count = 0
    for key, value in key_offsets.items():
        try:
            note_num = int(key) if isinstance(key, str) else key
            offset_val = int(value) if isinstance(value, str) else value
            if isinstance(offset_val, float):
                offset_val = int(offset_val)
            normalized_key_offsets[note_num] = offset_val
        except (ValueError, TypeError):
            invalid_offsets_count += 1
            continue  # Skip invalid entries
    
    if invalid_offsets_count > 0:
        logger.warning(f"Skipped {invalid_offsets_count} invalid offset entries during normalization")
    
    if normalized_key_offsets:
        logger.debug(f"Normalized {len(normalized_key_offsets)} key offsets. "
                    f"Notes: {sorted(normalized_key_offsets.keys())}, "
                    f"Offsets: {[normalized_key_offsets[n] for n in sorted(normalized_key_offsets.keys())]}")

    
    clamped_count = 0
    invalid_entries_count = 0
    trimmed_count = 0
    
    # First pass: Apply offsets and collect trims for redistribution
    trim_redistributions = {}  # {midi_note: {'left': [leds], 'right': [leds]}}
    
    for midi_note, led_indices in mapping.items():
        adjusted_indices = []
        
        # Normalize midi_note to int for comparison
        try:
            midi_note_int = int(midi_note) if isinstance(midi_note, str) else midi_note
        except (ValueError, TypeError):
            invalid_entries_count += 1
            continue  # Skip invalid entries
        
        # Calculate cascading offset: sum of all key offsets for notes <= current note
        cascading_offset = 0
        contributing_offsets = []
        
        if normalized_key_offsets:
            for offset_note, offset_value in sorted(normalized_key_offsets.items()):
                if offset_note <= midi_note_int:
                    cascading_offset += offset_value
                    contributing_offsets.append((offset_note, offset_value, 'led'))
                else:
                    break  # No more offsets apply to this note
        
        if isinstance(led_indices, list):
            for idx in led_indices:
                # Apply cascading key offsets
                adjusted_idx = idx + cascading_offset
                
                # Apply weld compensation: sum of all weld offsets for LEDs < current LED
                # Each weld at or before this LED index adds its offset to account for density discontinuity
                weld_compensation = 0
                if normalized_weld_offsets:
                    for weld_idx, weld_offset_mm in sorted(normalized_weld_offsets.items()):
                        if weld_idx < adjusted_idx:
                            # Convert mm offset to LED count (rough estimate: 1 LED ≈ 3.5-4mm spacing)
                            # For precise values, this should be calculated from leds_per_meter
                            # As default: 1mm ≈ 0.29 LEDs (3.5mm per LED at 200 LEDs/meter)
                            weld_led_offset = round(weld_offset_mm / 3.5)
                            weld_compensation += weld_led_offset
                
                adjusted_idx = adjusted_idx + weld_compensation
                
                # Clamp to the start_led and end_led range
                was_clamped = False
                if adjusted_idx < start_led or adjusted_idx > end_led:
                    was_clamped = True
                    clamped_count += 1
                adjusted_idx = max(start_led, min(adjusted_idx, end_led))
                
                adjusted_indices.append(adjusted_idx)
                
                if cascading_offset != 0 or weld_compensation != 0:
                    logger.debug(f"Note {midi_note_int}: LED {idx} → {adjusted_idx} "
                                f"(led_offset={cascading_offset}, "
                                f"weld_compensation={weld_compensation} LEDs, "
                                f"contributing_offsets={contributing_offsets}, clamped={was_clamped})")
        elif isinstance(led_indices, int):
            # Apply cascading key offsets
            adjusted_idx = led_indices + cascading_offset
            
            # Apply weld compensation
            weld_compensation = 0
            if normalized_weld_offsets:
                for weld_idx, weld_offset_mm in sorted(normalized_weld_offsets.items()):
                    if weld_idx < adjusted_idx:
                        weld_led_offset = round(weld_offset_mm / 3.5)
                        weld_compensation += weld_led_offset
            
            adjusted_idx = adjusted_idx + weld_compensation
            
            # Clamp to the start_led and end_led range
            was_clamped = False
            if adjusted_idx < start_led or adjusted_idx > end_led:
                was_clamped = True
                clamped_count += 1
            adjusted_idx = max(start_led, min(adjusted_idx, end_led))
            
            adjusted_indices = [adjusted_idx]
            
            if cascading_offset != 0 or weld_compensation != 0:
                logger.debug(f"Note {midi_note_int}: LED {led_indices} → {adjusted_idx} "
                            f"(led_offset={cascading_offset}, "
                            f"weld_compensation={weld_compensation} LEDs, "
                            f"contributing_offsets={contributing_offsets}, clamped={was_clamped})")
        
        # Apply LED trims AFTER offsets: collect trimmed LEDs for redistribution
        if adjusted_indices and midi_note_int in normalized_key_led_trims:
            trim_spec = normalized_key_led_trims[midi_note_int]
            left_trim = trim_spec.get('left_trim', 0)
            right_trim = trim_spec.get('right_trim', 0)
            
            if left_trim > 0 or right_trim > 0:
                original_len = len(adjusted_indices)
                trimmed_left = []
                trimmed_right = []
                
                # Collect left-trimmed LEDs (will go to previous key)
                if left_trim > 0:
                    trimmed_left = adjusted_indices[:left_trim]
                
                # Collect right-trimmed LEDs (will go to next key)
                if right_trim > 0:
                    trimmed_right = adjusted_indices[-right_trim:]
                
                # Apply trim by slicing
                if right_trim > 0:
                    trimmed_indices = adjusted_indices[left_trim:-right_trim]
                else:
                    trimmed_indices = adjusted_indices[left_trim:]
                
                if trimmed_indices:  # Only apply if result is non-empty
                    adjusted_indices = trimmed_indices
                    trimmed_count += 1
                    logger.info(f"Note {midi_note_int}: Applied trim L{left_trim}/R{right_trim} "
                                f"→ {original_len} LEDs became {len(adjusted_indices)} LEDs. "
                                f"Redistributing: {len(trimmed_left)} left to prev, {len(trimmed_right)} right to next")
                    
                    # Store trimmed LEDs for redistribution pass
                    if trimmed_left or trimmed_right:
                        trim_redistributions[midi_note_int] = {
                            'left': trimmed_left,
                            'right': trimmed_right
                        }
                else:
                    # Trim result is empty - log warning but keep original
                    logger.warning(f"Note {midi_note_int}: Trim L{left_trim}/R{right_trim} would eliminate all LEDs, "
                                  f"keeping original {len(adjusted_indices)} LEDs")
        
        if adjusted_indices:
            adjusted[midi_note] = adjusted_indices
    
    # Second pass: Redistribute trimmed LEDs to adjacent keys
    if trim_redistributions:
        logger.info(f"Second pass: Redistributing trimmed LEDs from {len(trim_redistributions)} keys")
        
        for midi_note_with_trim, trims in trim_redistributions.items():
            left_trimmed = trims['left']
            right_trimmed = trims['right']
            
            # Redistribute left-trimmed LEDs to previous key
            if left_trimmed and midi_note_with_trim > 0:
                prev_note = midi_note_with_trim - 1
                
                # Find the actual previous note in the adjusted mapping
                # (might not be exactly midi_note_with_trim - 1 if some notes were missing)
                prev_notes = sorted([n for n in adjusted.keys() if (isinstance(n, int) or isinstance(n, str) and n.isdigit()) and int(n) < midi_note_with_trim])
                
                if prev_notes:
                    actual_prev_note = max(prev_notes)
                    if actual_prev_note in adjusted:
                        # Add left-trimmed LEDs to the END of previous key's list
                        adjusted[actual_prev_note].extend(left_trimmed)
                        logger.info(f"Redistributed {len(left_trimmed)} left-trimmed LEDs from MIDI {midi_note_with_trim} "
                                  f"to MIDI {actual_prev_note} (now has {len(adjusted[actual_prev_note])} LEDs)")
            
            # Redistribute right-trimmed LEDs to next key
            if right_trimmed and midi_note_with_trim < 127:
                # Find the actual next note in the adjusted mapping
                next_notes = sorted([n for n in adjusted.keys() if (isinstance(n, int) or isinstance(n, str) and n.isdigit()) and int(n) > midi_note_with_trim])
                
                if next_notes:
                    actual_next_note = min(next_notes)
                    if actual_next_note in adjusted:
                        # Add right-trimmed LEDs to the BEGINNING of next key's list
                        adjusted[actual_next_note] = right_trimmed + adjusted[actual_next_note]
                        logger.info(f"Redistributed {len(right_trimmed)} right-trimmed LEDs from MIDI {midi_note_with_trim} "
                                  f"to MIDI {actual_next_note} (now has {len(adjusted[actual_next_note])} LEDs)")
    
    if invalid_entries_count > 0:
        logger.warning(f"Skipped {invalid_entries_count} invalid mapping entries (non-integer MIDI notes)")
    
    logger.info(f"Offset and trim application complete. Adjusted {len(adjusted)} notes. "
               f"Clamped {clamped_count} LED indices (bounds: {start_led}-{end_led}). "
               f"Applied {len(normalized_key_offsets)} LED offsets, "
               f"{trimmed_count} LED trims (with redistribution), "
               f"and {len(normalized_weld_offsets)} weld compensations. "
               f"Adjusted mapping now has {sum(len(v) if isinstance(v, list) else 1 for v in adjusted.values())} total LED assignments")
    
    return adjusted



def validate_gpio_pin_availability(pin, exclude_pins=None):
    """Validate if a GPIO pin is available for use"""
    if exclude_pins is None:
        exclude_pins = []
    
    # Reserved pins that should not be used
    reserved_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 30, 31]
    
    # Power and ground pins
    power_ground_pins = [1, 2, 4, 6, 9, 14, 17, 20, 25, 30, 34, 39]
    
    if pin in reserved_pins:
        return False, "Pin is reserved for system use"
    
    if pin in power_ground_pins:
        return False, "Pin is a power or ground pin"
    
    if pin in exclude_pins:
        return False, "Pin is already in use"
    
    if not 0 <= pin <= 40:
        return False, "Pin number out of valid range (0-40)"
    
    return True, "Pin is available"


def get_color_profile_settings(profile_name):
    """Get predefined color profile settings"""
    profiles = {
        "standard": {
            "color_temperature": 6500,
            "gamma_correction": 2.2,
            "white_balance": {"r": 1.0, "g": 1.0, "b": 1.0},
            "color_balance": {"red": 1.0, "green": 1.0, "blue": 1.0}
        },
        "warm_white": {
            "color_temperature": 3000,
            "gamma_correction": 2.0,
            "white_balance": {"r": 1.0, "g": 0.9, "b": 0.7},
            "color_balance": {"red": 1.0, "green": 0.9, "blue": 0.7}
        },
        "cool_white": {
            "color_temperature": 8000,
            "gamma_correction": 2.4,
            "white_balance": {"r": 0.9, "g": 1.0, "b": 1.0},
            "color_balance": {"red": 0.9, "green": 1.0, "blue": 1.0}
        },
        "music_viz": {
            "color_temperature": 6500,
            "gamma_correction": 1.8,
            "white_balance": {"r": 1.0, "g": 1.0, "b": 1.0},
            "color_balance": {"red": 1.2, "green": 1.0, "blue": 1.1}
        }
    }
    return profiles.get(profile_name, profiles["standard"])


def get_performance_mode_settings(mode_name):
    """Get predefined performance mode settings"""
    modes = {
        "quality": {
            "update_rate": 60,
            "dither_enabled": True,
            "led_frequency": 800000,
            "pwm_range": 4096
        },
        "balanced": {
            "update_rate": 30,
            "dither_enabled": True,
            "led_frequency": 800000,
            "pwm_range": 2048
        },
        "performance": {
            "update_rate": 120,
            "dither_enabled": False,
            "led_frequency": 400000,
            "pwm_range": 1024
        }
    }
    return modes.get(mode_name, modes["balanced"])


def save_configuration_profile(profile_name, config):
    """Save a configuration as a named profile"""
    try:
        profiles_dir = CONFIG_DIR / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        
        profile_file = profiles_dir / f"{profile_name}.json"
        
        # Validate configuration before saving
        validation_result = validate_config_comprehensive(config)
        if not validation_result["valid"]:
            logger.error(f"Cannot save invalid configuration profile: {validation_result['errors']}")
            return False, validation_result["errors"]
        
        with open(profile_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration profile '{profile_name}' saved")
        return True, []
    except Exception as e:
        logger.error(f"Failed to save configuration profile: {e}")
        return False, [str(e)]


def load_configuration_profile(profile_name):
    """Load a named configuration profile"""
    try:
        profiles_dir = CONFIG_DIR / "profiles"
        profile_file = profiles_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            logger.error(f"Configuration profile '{profile_name}' not found")
            return None, ["Profile not found"]
        
        with open(profile_file, 'r') as f:
            config = json.load(f)
        
        # Validate loaded configuration
        validation_result = validate_config_comprehensive(config)
        if not validation_result["valid"]:
            logger.warning(f"Loaded profile has validation issues: {validation_result['warnings']}")
        
        logger.info(f"Configuration profile '{profile_name}' loaded")
        return config, validation_result.get("warnings", [])
    except Exception as e:
        logger.error(f"Failed to load configuration profile: {e}")
        return None, [str(e)]


def list_configuration_profiles():
    """List all available configuration profiles"""
    try:
        profiles_dir = CONFIG_DIR / "profiles"
        if not profiles_dir.exists():
            return []
        
        profiles = []
        for profile_file in profiles_dir.glob("*.json"):
            profile_name = profile_file.stem
            stat = profile_file.stat()
            profiles.append({
                "name": profile_name,
                "file": str(profile_file),
                "modified": stat.st_mtime,
                "size": stat.st_size
            })
        
        return sorted(profiles, key=lambda x: x["modified"], reverse=True)
    except Exception as e:
        logger.error(f"Failed to list configuration profiles: {e}")
        return []


def delete_configuration_profile(profile_name):
    """Delete a named configuration profile"""
    try:
        profiles_dir = CONFIG_DIR / "profiles"
        profile_file = profiles_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            logger.error(f"Configuration profile '{profile_name}' not found")
            return False, "Profile not found"
        
        profile_file.unlink()
        logger.info(f"Configuration profile '{profile_name}' deleted")
        return True, "Profile deleted successfully"
    except Exception as e:
        logger.error(f"Failed to delete configuration profile: {e}")
        return False, str(e)


def detect_hardware_capabilities():
    """Detect available hardware capabilities"""
    capabilities = {
        "gpio_available": False,
        "spi_available": False,
        "i2c_available": False,
        "pwm_available": False,
        "available_pins": [],
        "led_strips_detected": [],
        "power_supplies_detected": [],
        "system_info": {}
    }
    
    try:
        # Try to detect GPIO availability
        try:
            import RPi.GPIO as GPIO
            capabilities["gpio_available"] = True
            
            # Get available GPIO pins (excluding reserved ones)
            reserved_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 30, 31]
            power_ground_pins = [1, 2, 4, 6, 9, 14, 17, 20, 25, 30, 34, 39]
            all_reserved = set(reserved_pins + power_ground_pins)
            
            capabilities["available_pins"] = [pin for pin in range(2, 28) if pin not in all_reserved]
            
        except ImportError:
            logger.warning("RPi.GPIO not available - running on non-Raspberry Pi system")
        except Exception as e:
            logger.warning(f"GPIO detection failed: {e}")
        
        # Try to detect SPI availability
        try:
            import spidev
            capabilities["spi_available"] = True
        except ImportError:
            pass
        
        # Try to detect I2C availability
        try:
            import smbus
            capabilities["i2c_available"] = True
        except ImportError:
            pass
        
        # Try to detect PWM availability
        try:
            import pigpio
            capabilities["pwm_available"] = True
        except ImportError:
            pass
        
        # Get system information
        try:
            import platform
            import psutil
            
            capabilities["system_info"] = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture()[0],
                "python_version": platform.python_version(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None
            }
        except ImportError:
            pass
        
        logger.info("Hardware detection completed")
        return capabilities
        
    except Exception as e:
        logger.error(f"Hardware detection failed: {e}")
        return capabilities


def apply_color_profile(config, profile_name):
    """Apply a color profile to the configuration"""
    profile_settings = get_color_profile_settings(profile_name)
    config.update(profile_settings)
    config["color_profile"] = profile_name
    return config


def apply_performance_mode(config, mode_name):
    """Apply a performance mode to the configuration"""
    mode_settings = get_performance_mode_settings(mode_name)
    config.update(mode_settings)
    config["performance_mode"] = mode_name
    return config


# ============================================================================
# Piano Geometry & Physical-Distance-Based LED Mapping
# ============================================================================

# Physical constants for piano measurements (in mm)
WHITE_KEY_WIDTH_MM = 23.5  # Standard acoustic piano white key width
BLACK_KEY_WIDTH_MM = 13.5  # Standard acoustic piano black key width
KEY_GAP_MM = 1.0           # Gap between keys at the base

# Pre-calculated white key counts for each piano size
WHITE_KEY_COUNTS = {
    "25-key": 18,   # C3-C5
    "37-key": 27,   # C2-C5
    "49-key": 35,   # C2-C6
    "61-key": 44,   # C2-C7
    "76-key": 54,   # E1-G7
    "88-key": 52,   # A0-C8
}

# Pre-calculated total piano widths (mm) including gaps
PIANO_WIDTHS_MM = {
    "25-key": 18 * WHITE_KEY_WIDTH_MM + 17 * KEY_GAP_MM,
    "37-key": 27 * WHITE_KEY_WIDTH_MM + 26 * KEY_GAP_MM,
    "49-key": 35 * WHITE_KEY_WIDTH_MM + 34 * KEY_GAP_MM,
    "61-key": 44 * WHITE_KEY_WIDTH_MM + 43 * KEY_GAP_MM,
    "76-key": 54 * WHITE_KEY_WIDTH_MM + 53 * KEY_GAP_MM,
    "88-key": 1225.0,  # 88 keys × 13.92mm per key (total piano width)
}


def count_white_keys_for_piano(piano_size: str) -> int:
    """
    Get the number of white keys for a given piano size.
    
    Args:
        piano_size: Piano size (e.g., "88-key")
    
    Returns:
        Number of white keys, or 0 for unknown sizes
    """
    return WHITE_KEY_COUNTS.get(piano_size, 0)


def get_piano_width_mm(piano_size: str) -> float:
    """
    Get the physical width of the piano in millimeters (white keys + gaps).
    
    Args:
        piano_size: Piano size (e.g., "88-key")
    
    Returns:
        Width in mm, or 0 for unknown sizes
    """
    return PIANO_WIDTHS_MM.get(piano_size, 0)


def calculate_physical_led_mapping(
    leds_per_meter: int,
    start_led: int,
    end_led: int,
    piano_size: str,
    distribution_mode: str = "proportional"
) -> Dict[str, Any]:
    """
    Calculate LED-to-key mapping parameters based on physical geometry.
    
    This algorithm maps physical distances:
    - LED strip position (based on leds_per_meter and physical LED indices)
    - Piano key positions (based on standard white key widths and gaps)
    
    By correlating these physical distances, we determine:
    - Which LEDs should light up for which keys
    - How many LEDs per key makes physical sense
    - Quality metrics and warnings about the configuration
    
    Args:
        leds_per_meter: LED strip density (60, 72, 100, 120, 144, 160, 180, 200)
        start_led: Physical LED index where piano starts
        end_led: Physical LED index where piano ends
        piano_size: Piano size (e.g., "88-key")
        distribution_mode: "proportional", "fixed", or "custom"
    
    Returns:
        dict with:
            - first_led: Logical offset for mapping (= start_led)
            - led_count_usable: Number of LEDs in the range
            - leds_per_key: Calculated LEDs per white key (float)
            - leds_per_key_int: Integer LEDs per key (for fixed mode)
            - white_key_count: Number of white keys on this piano
            - piano_width_mm: Physical width of piano in mm
            - led_spacing_mm: Distance between LEDs in mm
            - led_coverage_mm: Total distance covered by LED range
            - quality_score: 0-100 rating of the configuration
            - quality_level: "poor", "ok", "good", "excellent"
            - warnings: List of warning messages
            - recommendations: List of suggestions
            - metadata: Detailed metrics
    """
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
    
    result = {
        "error": None,
        "first_led": start_led,
        "led_count_usable": 0,
        "leds_per_key": 0.0,
        "leds_per_key_int": 0,
        "white_key_count": 0,
        "piano_width_mm": 0,
        "led_spacing_mm": 0,
        "led_coverage_mm": 0,
        "quality_score": 0,
        "quality_level": "unknown",
        "warnings": [],
        "recommendations": [],
        "metadata": {}
    }
    
    # Step 1: Validate inputs
    if leds_per_meter not in [60, 72, 100, 120, 144, 160, 180, 200]:
        result["error"] = f"Invalid leds_per_meter: {leds_per_meter}. Must be one of [60, 72, 100, 120, 144, 160, 180, 200]"
        result["warnings"].append(result["error"])
        return result
    
    if start_led < 0 or end_led < 0:
        result["error"] = "start_led and end_led must be non-negative"
        result["warnings"].append(result["error"])
        return result
    
    if end_led < start_led:
        result["error"] = f"end_led ({end_led}) must be >= start_led ({start_led})"
        result["warnings"].append(result["error"])
        return result
    
    # Step 2: Get piano specs
    white_key_count = count_white_keys_for_piano(piano_size)
    piano_width_mm = get_piano_width_mm(piano_size)
    
    if white_key_count == 0:
        result["error"] = f"Unknown piano size: {piano_size}"
        result["warnings"].append(result["error"])
        return result
    
    # Step 3: Calculate physical LED range and spacing
    physical_led_range = end_led - start_led + 1
    led_spacing_mm = 1000.0 / leds_per_meter  # mm between LEDs
    led_coverage_mm = (physical_led_range - 1) * led_spacing_mm if physical_led_range > 1 else 0
    
    # Step 4: Calculate distance per white key
    distance_per_white_key = piano_width_mm / white_key_count
    
    # Step 5: Calculate LEDs per white key (physical geometry based)
    if led_spacing_mm > 0:
        leds_per_white_key_physical = distance_per_white_key / led_spacing_mm
    else:
        leds_per_white_key_physical = 0
    
    # Also calculate proportional distribution (simpler)
    leds_per_white_key_proportional = physical_led_range / white_key_count if white_key_count > 0 else 0
    
    # Use proportional as the primary metric (consistent with existing code)
    leds_per_white_key = leds_per_white_key_proportional
    leds_per_white_key_int = max(1, int(leds_per_white_key))
    
    # Step 6: Calculate quality score
    quality_score = _calculate_led_mapping_quality(
        leds_per_white_key,
        physical_led_range,
        white_key_count,
        piano_width_mm,
        led_coverage_mm
    )
    
    # Step 7: Determine quality level and warnings
    if quality_score >= 90:
        quality_level = "excellent"
    elif quality_score >= 70:
        quality_level = "good"
    elif quality_score >= 50:
        quality_level = "ok"
    else:
        quality_level = "poor"
    
    # Generate warnings and recommendations
    warnings = []
    recommendations = []
    
    if leds_per_white_key < 1.0:
        warnings.append(f"Undersaturated: Only {leds_per_white_key:.2f} LEDs per white key ({white_key_count} keys, {physical_led_range} LEDs)")
        recommendations.append(f"Try using more LEDs from the strip or a denser LED strip (increase leds_per_meter)")
        recommendations.append(f"Or reduce the piano size to map fewer keys")
    elif leds_per_white_key < 2.0:
        warnings.append(f"Low coverage: {leds_per_white_key:.2f} LEDs per white key - effects may appear sparse")
    elif leds_per_white_key > 5.0:
        warnings.append(f"Oversaturated: {leds_per_white_key:.2f} LEDs per white key - many unused LEDs")
        recommendations.append(f"Consider using a less dense LED strip (lower leds_per_meter) or a larger piano")
    
    # Coverage ratio analysis
    coverage_ratio = led_coverage_mm / piano_width_mm if piano_width_mm > 0 else 0
    if coverage_ratio < 0.9:
        warnings.append(f"LED strip coverage ({led_coverage_mm:.1f}mm) is less than piano width ({piano_width_mm:.1f}mm). Coverage ratio: {coverage_ratio:.2f}")
        recommendations.append(f"Extend the calibration range to use more LEDs")
    elif coverage_ratio > 1.5:
        warnings.append(f"LED strip coverage ({led_coverage_mm:.1f}mm) significantly exceeds piano width ({piano_width_mm:.1f}mm). Coverage ratio: {coverage_ratio:.2f}")
    
    # Step 8: Build result
    result = {
        "error": None,
        "first_led": start_led,
        "led_count_usable": physical_led_range,
        "leds_per_key": leds_per_white_key,
        "leds_per_key_int": leds_per_white_key_int,
        "white_key_count": white_key_count,
        "piano_width_mm": piano_width_mm,
        "led_spacing_mm": led_spacing_mm,
        "led_coverage_mm": led_coverage_mm,
        "quality_score": quality_score,
        "quality_level": quality_level,
        "warnings": warnings,
        "recommendations": recommendations,
        "metadata": {
            "leds_per_meter": leds_per_meter,
            "start_led": start_led,
            "end_led": end_led,
            "piano_size": piano_size,
            "distribution_mode": distribution_mode,
            "physical_led_range": physical_led_range,
            "leds_per_white_key_physical": leds_per_white_key_physical,
            "leds_per_white_key_proportional": leds_per_white_key_proportional,
            "distance_per_white_key_mm": distance_per_white_key,
            "coverage_ratio": coverage_ratio,
            "piano_width_m": piano_width_mm / 1000.0,
            "led_coverage_m": led_coverage_mm / 1000.0,
        }
    }
    
    logger.info(f"Physical LED mapping calculated: {piano_size} with {leds_per_meter} LEDs/m, "
               f"LEDs {start_led}-{end_led} ({physical_led_range} total), "
               f"{leds_per_white_key:.2f} LEDs/key, quality={quality_level} ({quality_score}/100)")
    
    return result


def _calculate_led_mapping_quality(
    leds_per_key: float,
    physical_led_range: int,
    white_key_count: int,
    piano_width_mm: float,
    led_coverage_mm: float
) -> int:
    """
    Calculate a quality score (0-100) for the LED mapping configuration.
    
    Considers:
    - Adequacy of LEDs per key
    - Coverage of the piano width
    - Utilization efficiency
    """
    score = 100
    
    # Factor 1: LEDs per key adequacy (target: 2-4 LEDs per key)
    if leds_per_key < 1.0:
        score -= 50  # Critically low
    elif leds_per_key < 2.0:
        score -= 20  # Low
    elif leds_per_key <= 4.0:
        score -= 0   # Ideal range
    elif leds_per_key <= 6.0:
        score -= 5   # Slightly high
    else:
        score -= 15  # Very high
    
    # Factor 2: Coverage ratio (target: 0.95-1.05)
    coverage_ratio = led_coverage_mm / piano_width_mm if piano_width_mm > 0 else 0
    if coverage_ratio < 0.8:
        score -= 25
    elif coverage_ratio < 0.95:
        score -= 10
    elif coverage_ratio <= 1.05:
        score -= 0   # Perfect
    elif coverage_ratio <= 1.2:
        score -= 5
    else:
        score -= 15
    
    # Factor 3: Efficiency (how many keys can be mapped with available LEDs)
    mappable_keys = physical_led_range / leds_per_key if leds_per_key > 0 else 0
    efficiency = mappable_keys / white_key_count if white_key_count > 0 else 0
    if efficiency < 0.5:
        score -= 30
    elif efficiency < 1.0:
        score -= 10
    elif efficiency <= 1.1:
        score -= 0   # Good
    else:
        score -= 5
    
    return max(0, min(100, score))


def validate_auto_mapping_config(piano_size, led_count, leds_per_key=None, base_offset=0):
    """
    Validate mapping configuration and return warnings/recommendations.
    
    Args:
        piano_size: Piano size (e.g., "88-key")
        led_count: Total LEDs available
        leds_per_key: Optional fixed LEDs per key
        base_offset: LED offset (default 0)
    
    Returns:
        dict with keys:
            - valid (bool): Whether configuration is valid
            - warnings (list): Warning messages
            - recommendations (list): Suggestion messages
            - stats (dict): Configuration statistics
    """
    specs = get_piano_specs(piano_size)
    key_count = specs['keys']
    available_leds = led_count - base_offset
    
    warnings = []
    recommendations = []
    stats = {
        'key_count': key_count,
        'available_leds': available_leds,
        'leds_per_key_calc': 0.0,
        'remaining_leds': 0,
        'mappable_keys': key_count
    }
    
    # Check 1: Negative available LEDs
    if available_leds <= 0:
        return {
            'valid': False,
            'warnings': [f'No available LEDs: {led_count} total - {base_offset} offset = {available_leds}'],
            'recommendations': ['Reduce mapping_base_offset or increase led_count'],
            'stats': stats
        }
    
    # Check 2: LEDs per key calculation
    calc_leds_per_key = available_leds / key_count
    stats['leds_per_key_calc'] = calc_leds_per_key
    stats['remaining_leds'] = available_leds % key_count
    
    if calc_leds_per_key < 1:
        warnings.append(
            f'Not enough LEDs: {available_leds} / {key_count} = {calc_leds_per_key:.2f} LEDs/key'
        )
        recommendations.append('Increase led_count or use smaller piano size')
        return {
            'valid': False,
            'warnings': warnings,
            'recommendations': recommendations,
            'stats': stats
        }
    
    # Check 3: Uneven distribution
    if calc_leds_per_key != int(calc_leds_per_key):
        remainder = available_leds % key_count
        base_per_key = int(calc_leds_per_key)
        warnings.append(
            f'Uneven distribution: {remainder} keys get {base_per_key + 1} LEDs, '
            f'{key_count - remainder} keys get {base_per_key} LEDs'
        )
        recommendations.append(
            f'For even distribution, use a multiple of {key_count} LEDs '
            f'(e.g., {base_per_key * key_count} or {(base_per_key + 1) * key_count})'
        )
    
    # Check 4: Specified leds_per_key vs available
    if leds_per_key:
        mappable_keys = available_leds // leds_per_key
        stats['mappable_keys'] = mappable_keys
        
        if mappable_keys < key_count:
            warnings.append(
                f'With {leds_per_key} LEDs/key, only {mappable_keys}/{key_count} keys can be mapped'
            )
            unmapped_keys = key_count - mappable_keys
            start_midi = specs['midi_start']
            end_midi = specs['midi_end']
            first_unmapped = start_midi + mappable_keys
            recommendations.append(
                f'Keys MIDI {first_unmapped} to {end_midi} ({unmapped_keys} keys) will be unmapped'
            )
    
    # Check 5: Very low LED allocation
    if calc_leds_per_key < 2:
        warnings.append('Very low LED count per key - visualization may be subtle')
        recommendations.append('Consider increasing led_count for brighter visualization')
    
    return {
        'valid': True,
        'warnings': warnings,
        'recommendations': recommendations,
        'stats': stats
    }


def get_canonical_led_mapping(settings_service=None):
    """
    Get the canonical LED-to-key mapping respecting all current settings.
    
    This function generates the authoritative mapping that should be used by:
    - USB MIDI input processor
    - rtpMIDI input processor
    - LED playback service
    - Any other component that needs MIDI-to-LED mapping
    
    Uses the same logic as /key-led-mapping endpoint to ensure consistency.
    
    Args:
        settings_service: Optional SettingsService instance. If None, uses default settings.
    
    Returns:
        dict: {
            'success': bool,
            'mapping': {key_index: [led_indices]},  # key_index 0-87, MIDI notes 21-108
            'error': str or None
        }
    """
    try:
        # Get settings service if not provided
        if settings_service is None:
            from backend.services.settings_service import SettingsService
            settings_service = SettingsService()
        
        # Read all required settings
        piano_size = settings_service.get_setting('piano', 'size', '88-key')
        led_count = settings_service.get_setting('led', 'led_count', 300)
        start_led = settings_service.get_setting('calibration', 'start_led', 4)
        end_led = settings_service.get_setting('calibration', 'end_led', 249)
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
        key_led_trims = settings_service.get_setting('calibration', 'key_led_trims', {})
        weld_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        distribution_mode = settings_service.get_setting('calibration', 'distribution_mode', 'Piano Based (with overlap)')
        allow_led_sharing = settings_service.get_setting('calibration', 'allow_led_sharing', True)
        leds_per_meter = settings_service.get_setting('led', 'leds_per_meter', 200)
        
        # Choose allocation algorithm based on distribution mode
        if distribution_mode == 'Physics-Based LED Detection':
            # Use physics-based allocation
            from backend.services.physics_led_allocation import PhysicsBasedAllocationService
            
            led_physical_width = settings_service.get_setting('calibration', 'led_physical_width', 3.5)
            led_strip_offset = settings_service.get_setting('calibration', 'led_strip_offset', None)
            overhang_threshold = settings_service.get_setting('calibration', 'led_overhang_threshold', 1.5)
            white_key_width = settings_service.get_setting('calibration', 'white_key_width', 22.0)
            black_key_width = settings_service.get_setting('calibration', 'black_key_width', 12.0)
            white_key_gap = settings_service.get_setting('calibration', 'white_key_gap', 1.0)
            
            service = PhysicsBasedAllocationService(
                led_density=leds_per_meter,
                led_physical_width=led_physical_width,
                led_strip_offset=led_strip_offset,
                overhang_threshold_mm=overhang_threshold
            )
            
            service.analyzer.white_key_width = white_key_width
            service.analyzer.black_key_width = black_key_width
            service.analyzer.white_key_gap = white_key_gap
            
            allocation_result = service.allocate_leds(
                start_led=start_led,
                end_led=end_led
            )
        else:
            # Use traditional Piano-Based allocation
            from backend.config_led_mapping_advanced import calculate_per_key_led_allocation
            allocation_result = calculate_per_key_led_allocation(
                leds_per_meter=leds_per_meter,
                start_led=start_led,
                end_led=end_led,
                piano_size=piano_size,
                allow_led_sharing=allow_led_sharing
            )
        
        if not allocation_result.get('success'):
            return {
                'success': False,
                'mapping': {},
                'error': allocation_result.get('message', 'Unknown error')
            }
        
        base_mapping = allocation_result.get('key_led_mapping', {})
        
        # Convert offset keys from MIDI notes (21-108) to key indices (0-87)
        converted_offsets = {}
        if key_offsets:
            for midi_note_str, offset_value in key_offsets.items():
                try:
                    midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
                    key_index = midi_note - 21
                    if 0 <= key_index < 88:
                        converted_offsets[key_index] = offset_value
                except (ValueError, TypeError):
                    pass
        
        # Convert trim keys from MIDI notes to key indices (for consistency with offsets)
        converted_trims = {}
        if key_led_trims:
            for midi_note_str, trim_value in key_led_trims.items():
                try:
                    midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
                    key_index = midi_note - 21
                    if 0 <= key_index < 88:
                        converted_trims[key_index] = trim_value
                except (ValueError, TypeError):
                    pass
        
        # Apply calibration offsets, trims, and weld compensations
        final_mapping = apply_calibration_offsets_to_mapping(
            mapping=base_mapping,
            start_led=start_led,
            end_led=end_led,
            key_offsets=converted_offsets,
            key_led_trims=converted_trims,
            led_count=led_count,
            weld_offsets=weld_offsets
        )
        
        # Apply LED selection overrides (per-LED customization)
        from backend.services.led_selection_service import LEDSelectionService
        selection_service = LEDSelectionService(settings_service)
        final_mapping = selection_service.apply_overrides_to_mapping(
            final_mapping,
            start_led=start_led,
            end_led=end_led
        )
        
        return {
            'success': True,
            'mapping': final_mapping,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error generating canonical LED mapping: {e}", exc_info=True)
        return {
            'success': False,
            'mapping': {},
            'error': str(e)
        }

