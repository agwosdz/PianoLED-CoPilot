#!/usr/bin/env python3
"""
LED Effects Manager - Thread-safe LED effects with proper cleanup
Prevents thread accumulation by managing effect threads properly
"""

import threading
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LEDEffectsManager:
    """Manages LED effects with proper thread cleanup"""
    
    def __init__(self, led_controller, led_count: int = 88):
        self.led_controller = led_controller
        self.led_count = led_count
        self.current_effect_thread: Optional[threading.Thread] = None
        self.stop_current_effect = threading.Event()
        self.lock = threading.Lock()
        
    def stop_current(self):
        """Stop the currently running effect"""
        with self.lock:
            if self.current_effect_thread and self.current_effect_thread.is_alive():
                logger.info("Stopping current LED effect")
                self.stop_current_effect.set()
                # Give the thread a moment to stop gracefully
                self.current_effect_thread.join(timeout=1.0)
                if self.current_effect_thread.is_alive():
                    logger.warning("Effect thread did not stop gracefully")
            self.stop_current_effect.clear()
            
    def start_effect(self, pattern: str, base_color: tuple = (255, 255, 255), **kwargs):
        """Start a new LED effect, stopping any current effect first"""
        # Stop any current effect
        self.stop_current()
        
        with self.lock:
            if pattern == 'pulse':
                self.current_effect_thread = threading.Thread(
                    target=self._pulse_effect, 
                    args=(base_color,), 
                    daemon=True
                )
            elif pattern == 'chase':
                self.current_effect_thread = threading.Thread(
                    target=self._chase_effect, 
                    args=(base_color,), 
                    daemon=True
                )
            elif pattern == 'strobe':
                self.current_effect_thread = threading.Thread(
                    target=self._strobe_effect, 
                    args=(base_color,), 
                    daemon=True
                )
            elif pattern == 'fade':
                self.current_effect_thread = threading.Thread(
                    target=self._fade_effect, 
                    args=(base_color,), 
                    daemon=True
                )
            elif pattern in ['solid', 'red', 'green', 'blue', 'white']:
                # Static patterns don't need threads
                self._static_pattern(pattern, base_color)
                return
            else:
                logger.warning(f"Unknown LED pattern: {pattern}")
                return
                
            self.current_effect_thread.start()
            logger.info(f"Started LED effect: {pattern}")
            
    def _static_pattern(self, pattern: str, base_color: tuple):
        """Handle static LED patterns"""
        try:
            if pattern == 'solid':
                color = base_color
            elif pattern == 'red':
                color = (255, 0, 0)
            elif pattern == 'green':
                color = (0, 255, 0)
            elif pattern == 'blue':
                color = (0, 0, 255)
            elif pattern == 'white':
                color = (255, 255, 255)
            else:
                logger.warning(f"Unknown static pattern: {pattern}")
                return
                
            for i in range(self.led_count):
                self.led_controller.turn_on_led(i, color, auto_show=False)
            self.led_controller.show()
        except Exception as e:
            logger.error(f"Static pattern error: {e}")
            
    def _pulse_effect(self, base_color: tuple):
        """Pulse effect with stop check"""
        try:
            while not self.stop_current_effect.is_set():
                # Fade in
                for brightness in range(0, 256, 8):
                    if self.stop_current_effect.is_set():
                        return
                    factor = brightness / 255.0
                    pulse_color = (
                        int(base_color[0] * factor), 
                        int(base_color[1] * factor), 
                        int(base_color[2] * factor)
                    )
                    for i in range(self.led_count):
                        self.led_controller.turn_on_led(i, pulse_color, auto_show=False)
                    self.led_controller.show()
                    time.sleep(0.02)
                    
                # Fade out
                for brightness in range(255, -1, -8):
                    if self.stop_current_effect.is_set():
                        return
                    factor = brightness / 255.0
                    pulse_color = (
                        int(base_color[0] * factor), 
                        int(base_color[1] * factor), 
                        int(base_color[2] * factor)
                    )
                    for i in range(self.led_count):
                        self.led_controller.turn_on_led(i, pulse_color, auto_show=False)
                    self.led_controller.show()
                    time.sleep(0.02)
        except Exception as e:
            logger.error(f"Pulse effect error: {e}")
            
    def _chase_effect(self, base_color: tuple):
        """Chase effect with stop check"""
        try:
            chase_length = 5
            while not self.stop_current_effect.is_set():
                for offset in range(self.led_count + chase_length):
                    if self.stop_current_effect.is_set():
                        return
                        
                    # Clear all LEDs
                    for i in range(self.led_count):
                        self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                        
                    # Set chase LEDs
                    for i in range(chase_length):
                        led_pos = (offset - i) % self.led_count
                        if 0 <= led_pos < self.led_count:
                            brightness = 1.0 - (i / chase_length)
                            chase_color = (
                                int(base_color[0] * brightness), 
                                int(base_color[1] * brightness), 
                                int(base_color[2] * brightness)
                            )
                            self.led_controller.turn_on_led(led_pos, chase_color, auto_show=False)
                    self.led_controller.show()
                    time.sleep(0.05)
        except Exception as e:
            logger.error(f"Chase effect error: {e}")
            
    def _strobe_effect(self, base_color: tuple):
        """Strobe effect with stop check"""
        try:
            flash_count = 0
            while not self.stop_current_effect.is_set() and flash_count < 20:
                # Flash on
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, base_color, auto_show=False)
                self.led_controller.show()
                time.sleep(0.05)
                
                if self.stop_current_effect.is_set():
                    return
                    
                # Flash off
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                self.led_controller.show()
                time.sleep(0.05)
                flash_count += 1
        except Exception as e:
            logger.error(f"Strobe effect error: {e}")
            
    def _fade_effect(self, base_color: tuple):
        """Fade effect with stop check"""
        try:
            while not self.stop_current_effect.is_set():
                # Fade in
                for brightness in range(0, 256, 4):
                    if self.stop_current_effect.is_set():
                        return
                    factor = brightness / 255.0
                    fade_color = (
                        int(base_color[0] * factor), 
                        int(base_color[1] * factor), 
                        int(base_color[2] * factor)
                    )
                    for i in range(self.led_count):
                        self.led_controller.turn_on_led(i, fade_color, auto_show=False)
                    self.led_controller.show()
                    time.sleep(0.03)
                    
                time.sleep(1)  # Hold at full brightness
                
                # Fade out
                for brightness in range(255, -1, -4):
                    if self.stop_current_effect.is_set():
                        return
                    factor = brightness / 255.0
                    fade_color = (
                        int(base_color[0] * factor), 
                        int(base_color[1] * factor), 
                        int(base_color[2] * factor)
                    )
                    for i in range(self.led_count):
                        self.led_controller.turn_on_led(i, fade_color, auto_show=False)
                    self.led_controller.show()
                    time.sleep(0.03)
        except Exception as e:
            logger.error(f"Fade effect error: {e}")
            
    def cleanup(self):
        """Clean up all effects and threads"""
        self.stop_current()
        logger.info("LED effects manager cleaned up")
        
    def startup_animation(self, duration: float = 3.0):
        """
        Play a startup animation - rainbow wave effect
        This is a one-time effect that doesn't use the threading system
        """
        try:
            logger.info("Starting startup animation")
            import math
            
            # Rainbow wave parameters
            wave_length = 10  # Number of LEDs in one wave cycle
            speed = 0.02  # Animation speed
            steps = int(duration / speed)
            
            for step in range(steps):
                # Clear all LEDs first
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                
                # Create rainbow wave
                for i in range(self.led_count):
                    # Calculate wave position
                    wave_pos = (i + step * 2) % (wave_length * 6)  # 6 colors in rainbow
                    
                    # Generate rainbow colors based on position
                    if wave_pos < wave_length:
                        # Red to Orange
                        r = 255
                        g = int(255 * (wave_pos / wave_length))
                        b = 0
                    elif wave_pos < wave_length * 2:
                        # Orange to Yellow
                        r = 255
                        g = 255
                        b = 0
                    elif wave_pos < wave_length * 3:
                        # Yellow to Green
                        r = int(255 * (1 - (wave_pos - wave_length * 2) / wave_length))
                        g = 255
                        b = 0
                    elif wave_pos < wave_length * 4:
                        # Green to Cyan
                        r = 0
                        g = 255
                        b = int(255 * ((wave_pos - wave_length * 3) / wave_length))
                    elif wave_pos < wave_length * 5:
                        # Cyan to Blue
                        r = 0
                        g = int(255 * (1 - (wave_pos - wave_length * 4) / wave_length))
                        b = 255
                    else:
                        # Blue to Purple
                        r = int(255 * ((wave_pos - wave_length * 5) / wave_length))
                        g = 0
                        b = 255
                    
                    # Apply brightness fade based on distance from wave center
                    brightness = max(0.1, 1.0 - abs((wave_pos % wave_length) - wave_length/2) / (wave_length/2))
                    
                    color = (int(r * brightness), int(g * brightness), int(b * brightness))
                    self.led_controller.turn_on_led(i, color, auto_show=False)
                
                self.led_controller.show()
                time.sleep(speed)
            
            # Fade out to complete the animation
            for fade_step in range(20):
                brightness = 1.0 - (fade_step / 20.0)
                for i in range(self.led_count):
                    # Get current color and fade it
                    current_color = self.led_controller._led_state[i] if hasattr(self.led_controller, '_led_state') else (0, 0, 0)
                    faded_color = (
                        int(current_color[0] * brightness),
                        int(current_color[1] * brightness),
                        int(current_color[2] * brightness)
                    )
                    self.led_controller.turn_on_led(i, faded_color, auto_show=False)
                self.led_controller.show()
                time.sleep(0.05)
            
            # Turn off all LEDs
            for i in range(self.led_count):
                self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
            self.led_controller.show()
            
            logger.info("Startup animation completed")
            
        except Exception as e:
            logger.error(f"Startup animation error: {e}")
            # Ensure LEDs are off even if animation fails
            try:
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                self.led_controller.show()
            except:
                pass