import logging
from typing import Any, Dict, Optional, Tuple
from logging_config import get_logger

logger = get_logger(__name__)

try:
    from rpi_ws281x import PixelStrip, Color
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
    logger.info("rpi_ws281x library loaded successfully")
except ImportError as e:
    logger.warning(f"rpi_ws281x library not available: {e}")
    HARDWARE_AVAILABLE = False
    PixelStrip = None
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
        """
        Initialize LED controller.

        Args:
            pin: GPIO pin for LED strip (uses settings if None)
            num_pixels: Number of LEDs in strip (uses settings if None)
            brightness: LED brightness 0.0-1.0 (uses settings if None)
            settings_service: Settings service instance for retrieving configuration
        """
        self.settings_service = settings_service
        
        # Load configuration values if not provided
        if settings_service:
            # Check if LEDs are enabled first
            self.led_enabled = settings_service.get_setting('led', 'enabled', True)
            
            # Use settings service to get LED configuration
            self.pin = pin if pin is not None else settings_service.get_setting('led', 'gpio_pin', 19)
            self.num_pixels = num_pixels if num_pixels is not None else settings_service.get_setting('led', 'led_count', 30)
            self.brightness = brightness if brightness is not None else settings_service.get_setting('led', 'brightness', 0.3)
            self.led_orientation = settings_service.get_setting('led', 'led_orientation', 'normal')
            
            # Determine proper PWM channel based on GPIO pin when not explicitly set
            default_channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
            self.led_channel = settings_service.get_setting('led', 'led_channel', default_channel)
            
            # Get additional LED settings from the settings service
            self.led_type = settings_service.get_setting('led', 'led_type', 'WS2812B')
            self.led_frequency = settings_service.get_setting('led', 'led_frequency', 800000)
            self.led_dma = settings_service.get_setting('led', 'led_dma', 10)
            self.led_invert = settings_service.get_setting('led', 'led_invert', False)
        else:
            # Fallback to config.py
            self.led_enabled = get_config('led_enabled', True)
            self.pin = pin if pin is not None else get_config('gpio_pin', 19)
            self.num_pixels = num_pixels if num_pixels is not None else get_config('led_count', 30)
            self.brightness = brightness if brightness is not None else get_config('brightness', 0.3)
            self.led_orientation = get_config('led_orientation', 'normal')
            
            # Determine proper PWM channel default from pin
            default_channel = 1 if self.pin in [13, 19, 41, 45, 53] else 0
            self.led_channel = get_config('led_channel', default_channel)
            
            # Fallback LED settings
            self.led_type = get_config('led_type', 'WS2812B')
            self.led_frequency = get_config('led_frequency', 800000)
            self.led_dma = get_config('led_dma', 10)
            self.led_invert = get_config('led_invert', False)
        
        # If LEDs are disabled, run in simulation mode
        if not self.led_enabled:
            logger.info("LEDs are disabled in settings - running in simulation mode")
            self.pixels = None
            self._led_state = [(0, 0, 0)] * self.num_pixels  # Track LED state for simulation
            return
        
        if not HARDWARE_AVAILABLE:
            logger.warning("Hardware not available - running in simulation mode")
            self.pixels = None
            self._led_state = [(0, 0, 0)] * self.num_pixels  # Track LED state for simulation
            return
            
        self._led_state = [(0, 0, 0)] * self.num_pixels  # Track current LED state
        
        try:
            # Use settings from the settings service or fallback to hardcoded values
            LED_FREQ_HZ = self.led_frequency
            LED_DMA = self.led_dma
            LED_INVERT = self.led_invert
            LED_CHANNEL = self.led_channel

            # Initialize rpi_ws281x strip
            self.pixels = PixelStrip(
                self.num_pixels,
                self.pin,
                LED_FREQ_HZ,
                LED_DMA,
                LED_INVERT,
                int(self.brightness * 255),  # Convert brightness to 0-255 range
                LED_CHANNEL
            )

            # Initialize the library (must be called once before other functions)
            self.pixels.begin()

            logger.info(f"LED controller initialized with {self.num_pixels} pixels on pin {self.pin} using rpi_ws281x")
            logger.info(f"LED settings: type={self.led_type}, freq={LED_FREQ_HZ}, dma={LED_DMA}, channel={LED_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to initialize LED controller: {e}")
            raise

    def apply_runtime_settings(self, led_config: Dict[str, Any]) -> Dict[str, bool]:
        """Apply runtime LED settings that do not require full reinitialization."""
        changes = {
            'orientation_changed': False,
            'brightness_changed': False,
        }

        if not isinstance(led_config, dict):
            return changes

        orientation = led_config.get('orientation')
        if orientation and orientation != self.led_orientation:
            changes['orientation_changed'] = True
            try:
                self.turn_off_all()
            except Exception as exc:
                logger.warning(f"Failed to clear LEDs during orientation update: {exc}")
            self.led_orientation = orientation

        brightness = led_config.get('brightness')
        if brightness is not None:
            try:
                normalized = max(0.0, min(1.0, float(brightness)))
            except (TypeError, ValueError):
                normalized = self.brightness

            if abs(normalized - float(self.brightness)) > 1e-6:
                self.brightness = normalized
                changes['brightness_changed'] = True

                if HARDWARE_AVAILABLE and self.pixels:
                    try:
                        self.pixels.setBrightness(int(normalized * 255))
                        self.show()
                    except Exception as exc:
                        logger.warning(f"Failed to update LED brightness: {exc}")

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
            
            # Turn off all pixels using rpi_ws281x
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
                
            if self.pixels:
                # Turn off all LEDs before cleanup
                self._led_state = [(0, 0, 0)] * self.num_pixels
                for i in range(self.num_pixels):
                    self.pixels.setPixelColor(i, Color(0, 0, 0))
                self.pixels.show()
                
                # Clean up rpi_ws281x resources
                # Note: rpi_ws281x doesn't have explicit cleanup, but we set to None
                self.pixels = None
                logger.info("LED controller cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()