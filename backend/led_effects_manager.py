#!/usr/bin/env python3
"""
LED Effects Manager - Thread-safe LED effects with proper cleanup
Prevents thread accumulation by managing effect threads properly
"""

import threading
import time
import logging
from typing import Optional, Dict, Any
from backend.logging_config import get_logger

logger = get_logger(__name__)

class LEDEffectsManager:
    """Manages LED effects with proper thread cleanup"""
    
    def __init__(self, led_controller, led_count: int = 88, settings_service=None):
        self.led_controller = led_controller
        self.led_count = led_count
        self.settings_service = settings_service
        self.start_led = 0
        self.end_led = led_count - 1
        
        # Load calibration range from settings
        if settings_service:
            self.start_led = settings_service.get_setting('calibration', 'start_led', 0)
            self.end_led = settings_service.get_setting('calibration', 'end_led', led_count - 1)
            logger.info(f"LEDEffectsManager initialized with calibration range: [{self.start_led}, {self.end_led}]")
        
        self.current_effect_thread: Optional[threading.Thread] = None
        self.stop_current_effect = threading.Event()
        self.lock = threading.Lock()

    def update_led_count(self, led_count: int) -> None:
        """Update the cached LED count used by effects."""
        with self.lock:
            self.led_count = led_count
        
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
        Play a fancy startup animation - Piano key cascade with musical color sweep
        Creates an elegant welcome effect with cascading keys and gradient waves
        This is a one-time effect that doesn't use the threading system
        Uses the FULL LED strip for the animation (not restricted to calibration range)
        """
        try:
            # Use full LED strip for startup animation (not calibration range)
            animation_start = 0
            animation_end = self.led_count - 1
            logger.info(f"Starting fancy startup animation (range: [{animation_start}, {animation_end}])")
            import math
            
            # Animation phases
            # Phase 1: Piano key cascade (0.8s) - keys light up sequentially
            # Phase 2: Musical gradient sweep (1.2s) - smooth color gradients flow through
            # Phase 3: Sparkle finale (0.8s) - random sparkling with fade
            
            phase1_duration = 0.8
            phase2_duration = 1.2
            phase3_duration = 0.7
            
            # Calculate visible LED range (full strip for startup)
            visible_led_count = animation_end - animation_start + 1
            
            # ========== PHASE 1: PIANO KEY CASCADE ==========
            logger.info("  Phase 1: Piano key cascade...")
            cascade_steps = 40
            cascade_delay = phase1_duration / cascade_steps
            
            for step in range(cascade_steps):
                # Clear all LEDs first (full strip)
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                
                # Create cascade effect - each key lights up in sequence within the visible range
                cascade_width = max(3, int(visible_led_count * 0.15))  # Width of the cascade wave
                cascade_pos = (step / cascade_steps) * (visible_led_count + cascade_width)
                
                for i in range(self.led_count):
                    distance_from_wave = abs((i - animation_start) - cascade_pos)
                    
                    # Only light LEDs within the animation range
                    if animation_start <= i <= animation_end and distance_from_wave < cascade_width:
                        # Bright cyan-to-blue gradient for the cascade
                        brightness = 1.0 - (distance_from_wave / cascade_width)
                        
                        # Gradient: Bright cyan -> blue
                        hue_factor = distance_from_wave / cascade_width
                        r = int(0 * brightness)
                        g = int(255 * brightness * (1 - hue_factor * 0.5))
                        b = int(255 * brightness)
                        
                        self.led_controller.turn_on_led(i, (r, g, b), auto_show=False)
                
                self.led_controller.show()
                time.sleep(cascade_delay)
            
            # ========== PHASE 2: MUSICAL GRADIENT SWEEP ==========
            logger.info("  Phase 2: Musical gradient sweep...")
            sweep_steps = 60
            sweep_delay = phase2_duration / sweep_steps
            
            for step in range(sweep_steps):
                # Clear all LEDs first (full strip)
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                
                # Create smooth gradient that sweeps through like a musical scale
                # Animate LEDs within the animation range (full strip for startup)
                for i in range(animation_start, animation_end + 1):
                    # Calculate position in the sweep cycle
                    wave_phase = ((i / self.led_count) + (step / sweep_steps)) * 2 * math.pi
                    
                    # Use sine waves to create smooth, musical gradient
                    r = int(127.5 + 127.5 * math.sin(wave_phase))
                    g = int(127.5 + 127.5 * math.sin(wave_phase + 2 * math.pi / 3))
                    b = int(127.5 + 127.5 * math.sin(wave_phase + 4 * math.pi / 3))
                    
                    self.led_controller.turn_on_led(i, (r, g, b), auto_show=False)
                
                self.led_controller.show()
                time.sleep(sweep_delay)
                
                self.led_controller.show()
                time.sleep(sweep_delay)
            
            # ========== PHASE 3: SPARKLE FINALE WITH FADE ==========
            logger.info("  Phase 3: Sparkle finale...")
            import random
            sparkle_steps = 50
            sparkle_delay = phase3_duration / sparkle_steps
            
            for step in range(sparkle_steps):
                brightness_scale = 1.0 - (step / sparkle_steps)
                
                # Clear full strip, then only illuminate within animation range (full strip for startup)
                for i in range(self.led_count):
                    if animation_start <= i <= animation_end:
                        # Mostly dim with occasional bright sparkles
                        if random.random() < 0.3 * brightness_scale:
                            # Gold/yellow sparkle
                            r = int(255 * brightness_scale)
                            g = int(200 * brightness_scale)
                            b = int(0)
                        else:
                            # Dim purple/magenta background
                            r = int(100 * brightness_scale)
                            g = int(30 * brightness_scale)
                            b = int(80 * brightness_scale)
                        
                        self.led_controller.turn_on_led(i, (r, g, b), auto_show=False)
                    else:
                        # Keep LEDs outside animation range off
                        self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                
                self.led_controller.show()
                time.sleep(sparkle_delay)
            
            # ========== COMPLETION: SMOOTH FADE TO BLACK ==========
            logger.info("  Fading out...")
            fade_steps = 15
            for fade_step in range(fade_steps):
                brightness = 1.0 - (fade_step / fade_steps)
                for i in range(self.led_count):
                    # Fade smoothly to black (all zeros)
                    r = int(0)
                    g = int(0)
                    b = int(0)
                    self.led_controller.turn_on_led(i, (r, g, b), auto_show=False)
                self.led_controller.show()
                time.sleep(0.08)
            
            # Turn off all LEDs
            for i in range(self.led_count):
                self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
            self.led_controller.show()
            
            logger.info("✨ Startup animation completed successfully!")
            
        except Exception as e:
            logger.error(f"Startup animation error: {e}")
            # Ensure LEDs are off even if animation fails
            try:
                for i in range(self.led_count):
                    self.led_controller.turn_on_led(i, (0, 0, 0), auto_show=False)
                self.led_controller.show()
            except:
                pass