#!/usr/bin/env python3
"""
Simple LED test script without threading
Bypasses the web service to directly test LED hardware
"""

import sys
import time
import logging
from logging_config import setup_logging, get_logger

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

def test_led_hardware():
    """Test LED hardware directly without threading"""
    try:
        # Import LED controller
        from led_controller import LEDController
        
        logger.info("Initializing LED controller...")
        controller = LEDController(
            pin=18,
            num_pixels=255,
            brightness=0.5
        )
        
        logger.info("Testing individual LED...")
        # Test first LED with red color
        controller.turn_on_led(0, (255, 0, 0))
        time.sleep(2)
        
        # Turn off LED
        controller.turn_off_led(0)
        logger.info("LED test completed successfully")
        
        # Test a few more LEDs
        logger.info("Testing multiple LEDs...")
        for i in range(5):
            controller.turn_on_led(i, (0, 255, 0))  # Green
            time.sleep(0.5)
            controller.turn_off_led(i)
        
        logger.info("Multi-LED test completed successfully")
        
        # Test all LEDs briefly
        logger.info("Testing all LEDs briefly...")
        for i in range(255):
            controller.turn_on_led(i, (0, 0, 255), auto_show=False)  # Blue
        controller.show()
        time.sleep(1)
        
        # Turn off all LEDs
        for i in range(255):
            controller.turn_off_led(i, auto_show=False)
        controller.show()
        
        logger.info("All LED test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"LED test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_led_hardware()
    sys.exit(0 if success else 1)