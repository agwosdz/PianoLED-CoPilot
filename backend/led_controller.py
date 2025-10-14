import logging
from typing import Any, Dict, Optional, Tuple
from logging_config import get_logger

logger = get_logger(__name__)

try:
    from rpi_ws281x import PixelStrip, ws, Color
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
    logger.info("rpi_ws281x library loaded successfully")
except ModuleNotFoundError as e:
    logger.warning(f"rpi_ws281x library not available: {e}")
    HARDWARE_AVAILABLE = False
    PixelStrip = None
    ws = None
    Color = None
    GPIO = None
except ImportError as e:
    logger.warning(f"rpi_ws281x library not available: {e}")
    HARDWARE_AVAILABLE = False
    PixelStrip = None
    ws = None
    Color = None
    GPIO = None

# Fallback to config.py if settings service is not available
try:
    from backend.config import get_config
except ImportError:
    try:
        from config import get_config
    except ImportError:
        logger.warning("Config module not available, using defaults")
        def get_config(key, default):
            return default

class LEDController:
    """Controller for WS2812B LED strip using rpi_ws281x library."""

    def __init__(self, pin=None, num_pixels=None, brightness=None, settings_service=None):
        self.settings_service = settings_service

        # Runtime hardware handles
        self.pixels = None
        self._led_state = []

        # Configuration defaults
        self.led_enabled = True
        self.pin = 18
        self.num_pixels = 0
        self.brightness = 0.3
        self.led_orientation = 'normal'
        self.led_channel = 0
        self.led_frequency = 800000
        self.led_dma = 10
        self.led_invert = False
        self.led_type = 'WS2812B'
        self.led_strip_type = 'WS2811_STRIP_GRB'
        self.gamma_factor = 2.2

        self._load_configuration(pin, num_pixels, brightness)
        self._initialize_strip()

    @staticmethod
    def _normalize_brightness(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.3
        if numeric > 1.0:
            numeric = numeric / 100.0
        return max(0.0, min(1.0, numeric))

    def _load_configuration(self, pin_override, num_pixels_override, brightness_override) -> None:
        if self.settings_service:
            get_setting = self.settings_service.get_setting
            self.led_enabled = bool(get_setting('led', 'enabled', True))
            pin_value = pin_override if pin_override is not None else get_setting('led', 'gpio_pin', 19)
            self.pin = int(pin_value)
            count_value = num_pixels_override if num_pixels_override is not None else get_setting('led', 'led_count', 30)
            self.num_pixels = max(1, int(count_value))
            brightness_value = brightness_override if brightness_override is not None else get_setting('led', 'brightness', 0.3)
            self.brightness = self._normalize_brightness(brightness_value)
            self.led_orientation = get_setting('led', 'led_orientation', 'normal')
            default_channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
            self.led_channel = int(get_setting('led', 'led_channel', default_channel))
            self.led_type = get_setting('led', 'led_type', 'WS2812B')
            self.led_strip_type = get_setting('led', 'led_strip_type', 'WS2811_STRIP_GRB')
            self.led_frequency = int(get_setting('led', 'led_frequency', 800000))
            self.led_dma = int(get_setting('led', 'led_dma', 10))
            self.led_invert = bool(get_setting('led', 'led_invert', False))
            self.gamma_factor = float(get_setting('led', 'gamma_correction', 2.2))
        else:
            self.led_enabled = bool(get_config('led_enabled', True))
            pin_value = pin_override if pin_override is not None else get_config('gpio_pin', 19)
            self.pin = int(pin_value)
            count_value = num_pixels_override if num_pixels_override is not None else get_config('led_count', 30)
            self.num_pixels = max(1, int(count_value))
            brightness_value = brightness_override if brightness_override is not None else get_config('brightness', 0.3)
            self.brightness = self._normalize_brightness(brightness_value)
            self.led_orientation = get_config('led_orientation', 'normal')
            default_channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
            self.led_channel = int(get_config('led_channel', default_channel))
            self.led_type = get_config('led_type', 'WS2812B')
            self.led_strip_type = get_config('led_strip_type', 'WS2811_STRIP_GRB')
            self.led_frequency = int(get_config('led_frequency', 800000))
            self.led_dma = int(get_config('led_dma', 10))
            self.led_invert = bool(get_config('led_invert', False))
            self.gamma_factor = float(get_config('gamma_correction', 2.2))

    def _resolve_strip_type(self, strip_type_name: Optional[str]) -> int:
        if not ws:
            return 0
        if strip_type_name and hasattr(ws, strip_type_name):
            return getattr(ws, strip_type_name)
        return getattr(ws, 'WS2811_STRIP_GRB', 0)

    def _apply_gamma(self) -> None:
        if not HARDWARE_AVAILABLE or not ws or not self.pixels:
            return
        try:
            ws.ws2811_set_custom_gamma_factor(self.pixels._leds, float(self.gamma_factor))
        except Exception as exc:
            logger.debug(f"Failed to apply gamma factor {self.gamma_factor}: {exc}")

    def _cleanup_strip(self) -> None:
        if not self.pixels or not HARDWARE_AVAILABLE:
            self.pixels = None
            return

        try:
            for index in range(len(self._led_state)):
                self.pixels.setPixelColor(index, Color(0, 0, 0))
            self.pixels.show()
        except Exception as exc:
            logger.debug(f"Error while clearing LEDs during cleanup: {exc}")

        if ws and hasattr(self.pixels, '_leds') and getattr(self.pixels, '_leds', None):
            try:
                ws.delete_ws2811_t(self.pixels._leds)
            except Exception as exc:
                logger.debug(f"Failed to release ws2811_t structure: {exc}")

        self.pixels = None

    def _initialize_strip(self) -> None:
        self._cleanup_strip()
        self._led_state = [(0, 0, 0)] * self.num_pixels

        if not self.led_enabled:
            logger.info("LEDs are disabled in settings - running in simulation mode")
            return

        if not HARDWARE_AVAILABLE or PixelStrip is None:
            logger.warning("Hardware not available - running in simulation mode")
            return

        try:
            strip_type = self._resolve_strip_type(self.led_strip_type)
            brightness_255 = int(self.brightness * 255)
            self.pixels = PixelStrip(
                self.num_pixels,
                self.pin,
                self.led_frequency,
                self.led_dma,
                self.led_invert,
                brightness_255,
                self.led_channel,
                strip_type
            )
            self.pixels.begin()
            if hasattr(self.pixels, 'releaseGIL'):
                self.pixels.releaseGIL()
            self._apply_gamma()
            self.turn_off_all()
            logger.info(
                "LED controller initialized with %s pixels on pin %s (freq=%s, dma=%s, channel=%s)",
                self.num_pixels,
                self.pin,
                self.led_frequency,
                self.led_dma,
                self.led_channel
            )
        except Exception as exc:
            logger.error(f"Failed to initialize LED controller: {exc}")
            self.pixels = None
            raise

    def change_gamma(self, value: Any) -> bool:
        try:
            gamma_value = float(value)
        except (TypeError, ValueError):
            return False

        if abs(gamma_value - self.gamma_factor) <= 1e-6:
            return False

        self.gamma_factor = gamma_value
        self._apply_gamma()
        logger.debug("LED controller gamma updated to %.3f", self.gamma_factor)
        return True

    def change_brightness(self, value: Any, is_percent: bool = False) -> bool:
        normalized = self._normalize_brightness((float(value) / 100.0) if is_percent else value)
        if abs(normalized - self.brightness) <= 1e-6:
            return False

        self.brightness = normalized
        if HARDWARE_AVAILABLE and self.pixels:
            try:
                self.pixels.setBrightness(int(self.brightness * 255))
                self.show()
            except Exception as exc:
                logger.warning(f"Failed to update LED brightness: {exc}")
        logger.debug("LED controller brightness updated to %.4f", self.brightness)
        return True

    def change_led_count(self, value: Any, fixed_number: bool = True) -> bool:
        try:
            requested = int(value)
        except (TypeError, ValueError):
            return False

        new_count = requested if fixed_number else (self.num_pixels + requested)
        new_count = max(1, new_count)
        if new_count == self.num_pixels:
            return False

        self.num_pixels = new_count
        self._initialize_strip()
        logger.info("LED count changed to %s", self.num_pixels)
        return True

    def change_orientation(self, orientation: str) -> bool:
        if orientation not in {'normal', 'reversed'}:
            return False
        if orientation == self.led_orientation:
            return False

        self.led_orientation = orientation
        try:
            self.turn_off_all()
        except Exception as exc:
            logger.warning(f"Failed to clear LEDs during orientation update: {exc}")
        logger.debug("LED controller orientation updated to %s", self.led_orientation)
        return True

    def apply_runtime_settings(self, led_config: Dict[str, Any]) -> Dict[str, bool]:
        """Apply runtime LED settings that may require reinitialization."""
        changes = {
            'led_count_changed': False,
            'orientation_changed': False,
            'brightness_changed': False,
            'gamma_changed': False,
        }

        if not isinstance(led_config, dict):
            return changes

        if 'enabled' in led_config:
            enabled_value = bool(led_config['enabled'])
            if enabled_value != self.led_enabled:
                self.led_enabled = enabled_value
                if enabled_value:
                    self._initialize_strip()
                else:
                    try:
                        self.turn_off_all()
                    except Exception as exc:
                        logger.debug(f"Failed to clear LEDs while disabling controller: {exc}")
                    self._cleanup_strip()
                changes['led_count_changed'] = True

        if 'led_count' in led_config and self.change_led_count(led_config['led_count'], fixed_number=True):
            changes['led_count_changed'] = True

        orientation = led_config.get('orientation')
        if orientation and self.change_orientation(orientation):
            changes['orientation_changed'] = True

        brightness = led_config.get('brightness')
        if brightness is not None and self.change_brightness(brightness):
            changes['brightness_changed'] = True

        gamma = led_config.get('gamma_correction')
        if gamma is not None and self.change_gamma(gamma):
            changes['gamma_changed'] = True

        return changes
    
    def _map_led_index(self, index: int) -> int:
        """
        Map logical LED index to physical LED index based on orientation.
        
        Args:
            index: Logical LED index (0-based)
            
        Returns:
            int: Physical LED index
        """
        if self.led_orientation == 'reversed':
            return self.num_pixels - 1 - index
        return index
    
    def turn_on_led(self, index: int, color: tuple = (255, 255, 255), brightness: Optional[float] = None, auto_show: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Turn on a specific LED.
        
        Args:
            index: Logical LED index (0-based)
            color: RGB color tuple (default: white)
            brightness: Optional per-call brightness multiplier (0.0-1.0). If provided, scales the color.
            auto_show: Whether to immediately update the LED strip (default: True)
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            if not 0 <= index < self.num_pixels:
                return False, f"LED index {index} out of range (0-{self.num_pixels-1})"
            
            # Normalize color to tuple
            r, g, b = tuple(color)
            
            # Apply brightness scaling if provided
            if brightness is not None:
                try:
                    brightness = max(0.0, min(1.0, float(brightness)))
                except Exception:
                    brightness = None
                if brightness is not None:
                    r = int(r * brightness)
                    g = int(g * brightness)
                    b = int(b * brightness)
            
            # Map logical index to physical index based on orientation
            physical_index = self._map_led_index(index)
            
            # Check if color actually changed to avoid unnecessary updates
            if self._led_state[index] == (r, g, b):
                return True, None
                
            self._led_state[index] = (r, g, b)
            
            if not HARDWARE_AVAILABLE:
                logger.debug(f"[SIMULATION] LED {index} (physical: {physical_index}) set to color {(r, g, b)}")
                return True, None
                
            if not self.pixels:
                return False, "LED controller not initialized"
            
            # Set the pixel color using rpi_ws281x Color function
            self.pixels.setPixelColor(physical_index, Color(r, g, b))
            
            if auto_show:
                success, error = self.show()
                if not success:
                    return False, error
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to turn on LED {index}: {e}")
            return False, str(e)
    
    def turn_off_led(self, index: int, auto_show: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Turn off a specific LED.
        
        Args:
            index: LED index (0-based)
            auto_show: Whether to immediately update the LED strip (default: True)
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        return self.turn_on_led(index, (0, 0, 0), brightness=None, auto_show=auto_show)
    
    def show(self) -> Tuple[bool, Optional[str]]:
        """
        Update the LED strip with pending changes.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            if not HARDWARE_AVAILABLE:
                return True, None
                
            if not self.pixels:
                return False, "LED controller not initialized"
            
            # Update the LED strip
            self.pixels.show()
                
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to update LED strip: {e}")
            return False, str(e)
    

    
    def turn_off_all(self) -> Tuple[bool, Optional[str]]:
        """
        Turn off all LEDs.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Update state tracking
            self._led_state = [(0, 0, 0)] * self.num_pixels
            
            if not HARDWARE_AVAILABLE:
                logger.debug("[SIMULATION] All LEDs turned off")
                return True, None

            if not self.pixels:
                return False, "LED controller not initialized"

            for i in range(self.num_pixels):
                self.pixels.setPixelColor(i, Color(0, 0, 0))
            success, error = self.show()
            if not success:
                return False, error
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to turn off all LEDs: {e}")
            return False, str(e)
    
    def set_multiple_leds(self, led_data: dict, auto_show: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Set multiple LEDs at once for better performance.
        
        Args:
            led_data: Dictionary mapping LED index to color tuple
            auto_show: Whether to immediately update the LED strip (default: True)
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            success = True
            error_messages = []
            for index, color in led_data.items():
                led_success, led_error = self.turn_on_led(index, color, auto_show=False)
                if not led_success:
                    success = False
                    error_messages.append(f"LED {index}: {led_error}")
            
            if auto_show and success:
                show_success, show_error = self.show()
                if not show_success:
                    return False, show_error
            
            if not success:
                return False, "; ".join(error_messages)
                
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to set multiple LEDs: {e}")
            return False, str(e)
    
    def cleanup(self):
        """
        Clean up GPIO resources.
        """
        try:
            if not HARDWARE_AVAILABLE:
                logger.info("[SIMULATION] LED controller cleaned up successfully")
                return

            self._cleanup_strip()
            logger.info("LED controller cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()