"""
LED Selection Override Service

Manages per-key LED selection overrides, allowing users to:
- Override the number of LEDs assigned to a key
- Select/deselect individual LEDs
- Reallocate excluded LEDs to adjacent keys
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from backend.logging_config import get_logger

logger = get_logger(__name__)


class LEDSelectionService:
    """
    Manages LED selection overrides for fine-grained control over LED allocation.
    
    When a user selects/deselects LEDs for a key:
    1. Store the override in settings
    2. Reallocate deselected LEDs to adjacent keys (left/right neighbors)
    3. Ensure no LED is assigned to multiple keys
    4. Preserve the override in the final mapping
    """
    
    def __init__(self, settings_service=None):
        """Initialize the LED selection service."""
        self.settings_service = settings_service
    
    def _get_led_range(self) -> Tuple[int, int]:
        """
        Get the valid LED range from settings.
        
        Returns:
            (start_led, end_led) tuple
        """
        if not self.settings_service:
            return (0, 249)
        
        start_led = self.settings_service.get_setting('calibration', 'start_led', 4)
        end_led = self.settings_service.get_setting('calibration', 'end_led', 249)
        return (start_led, end_led)
    
    def set_key_led_selection(
        self,
        midi_note: int,
        selected_leds: List[int]
    ) -> Dict:
        """
        Override LED selection for a specific key.
        
        Args:
            midi_note: MIDI note number (21-108)
            selected_leds: List of LED indices to assign to this key
        
        Returns:
            dict with success status and any conflicts/reallocations
        """
        if not self.settings_service:
            return {'success': False, 'error': 'Settings service not available'}
        
        if not (21 <= midi_note <= 108):
            return {'success': False, 'error': f'Invalid MIDI note: {midi_note}'}
        
        if not isinstance(selected_leds, list):
            return {'success': False, 'error': 'selected_leds must be a list'}
        
        # Validate LED indices and warn about out-of-range LEDs
        start_led, end_led = self._get_led_range()
        out_of_range_leds = []
        
        for led_idx in selected_leds:
            if not isinstance(led_idx, int) or led_idx < 0:
                return {'success': False, 'error': f'Invalid LED index: {led_idx}'}
            if led_idx < start_led or led_idx > end_led:
                out_of_range_leds.append(led_idx)
        
        try:
            # Get current overrides
            overrides = self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
            
            # Update with new selection
            overrides[str(midi_note)] = selected_leds
            
            # Save back to settings
            self.settings_service.set_setting('calibration', 'led_selection_overrides', overrides)
            
            logger.info(f"Set LED selection for MIDI {midi_note}: {selected_leds}")
            
            response = {
                'success': True,
                'midi_note': midi_note,
                'selected_leds': selected_leds,
                'message': f'Updated LED selection for MIDI {midi_note}',
                'out_of_range_warning': None
            }
            
            if out_of_range_leds:
                warning = f'Warning: LEDs {out_of_range_leds} are outside valid range [{start_led}, {end_led}]'
                logger.warning(warning)
                response['out_of_range_warning'] = warning
            
            return response
        except Exception as e:
            logger.error(f"Failed to set LED selection: {e}")
            return {'success': False, 'error': str(e)}
    
    def clear_key_led_selection(self, midi_note: int) -> Dict:
        """
        Clear LED selection override for a specific key (revert to auto-allocation).
        
        Args:
            midi_note: MIDI note number (21-108)
        
        Returns:
            dict with success status
        """
        if not self.settings_service:
            return {'success': False, 'error': 'Settings service not available'}
        
        if not (21 <= midi_note <= 108):
            return {'success': False, 'error': f'Invalid MIDI note: {midi_note}'}
        
        try:
            overrides = self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
            
            if str(midi_note) in overrides:
                del overrides[str(midi_note)]
                self.settings_service.set_setting('calibration', 'led_selection_overrides', overrides)
                logger.info(f"Cleared LED selection override for MIDI {midi_note}")
            
            return {
                'success': True,
                'midi_note': midi_note,
                'message': f'Cleared LED selection override for MIDI {midi_note}'
            }
        except Exception as e:
            logger.error(f"Failed to clear LED selection: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_key_led_selection(self, midi_note: int) -> Dict:
        """
        Get the LED selection override for a specific key.
        
        Args:
            midi_note: MIDI note number (21-108)
        
        Returns:
            dict with selected LEDs or empty list if no override
        """
        if not self.settings_service:
            return {'success': False, 'error': 'Settings service not available'}
        
        if not (21 <= midi_note <= 108):
            return {'success': False, 'error': f'Invalid MIDI note: {midi_note}'}
        
        try:
            overrides = self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
            selected = overrides.get(str(midi_note), [])
            
            return {
                'success': True,
                'midi_note': midi_note,
                'selected_leds': selected,
                'has_override': len(selected) > 0
            }
        except Exception as e:
            logger.error(f"Failed to get LED selection: {e}")
            return {'success': False, 'error': str(e)}
    
    def toggle_led_selection(self, midi_note: int, led_index: int) -> Dict:
        """
        Toggle a single LED's selection for a key (add or remove).
        
        Args:
            midi_note: MIDI note number (21-108)
            led_index: LED index to toggle
        
        Returns:
            dict with updated selection and success status
        """
        if not self.settings_service:
            return {'success': False, 'error': 'Settings service not available'}
        
        if not (21 <= midi_note <= 108):
            return {'success': False, 'error': f'Invalid MIDI note: {midi_note}'}
        
        if not isinstance(led_index, int) or led_index < 0:
            return {'success': False, 'error': f'Invalid LED index: {led_index}'}
        
        try:
            overrides = self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
            selected = list(overrides.get(str(midi_note), []))
            
            if led_index in selected:
                selected.remove(led_index)
                action = 'removed'
            else:
                selected.append(led_index)
                selected.sort()
                action = 'added'
            
            overrides[str(midi_note)] = selected
            self.settings_service.set_setting('calibration', 'led_selection_overrides', overrides)
            
            logger.info(f"LED {led_index} {action} for MIDI {midi_note}. New selection: {selected}")
            
            return {
                'success': True,
                'midi_note': midi_note,
                'led_index': led_index,
                'action': action,
                'selected_leds': selected
            }
        except Exception as e:
            logger.error(f"Failed to toggle LED selection: {e}")
            return {'success': False, 'error': str(e)}
    
    def apply_overrides_to_mapping(
        self,
        base_mapping: Dict[int, List[int]],
        start_led: int = 0,
        end_led: int = 249
    ) -> Dict[int, List[int]]:
        """
        Apply LED selection overrides to the base mapping.
        
        Reallocates excluded LEDs to adjacent keys to ensure full coverage.
        
        Args:
            base_mapping: Base mapping from allocation algorithm (key_index -> [led_indices])
            start_led: First available LED
            end_led: Last available LED
        
        Returns:
            Modified mapping with overrides applied
        """
        if not self.settings_service:
            return base_mapping
        
        try:
            overrides = self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
            
            if not overrides:
                return base_mapping  # No overrides, return original
            
            # Create a working copy
            adjusted_mapping = {k: list(v) for k, v in base_mapping.items()}
            
            # Track removed LEDs that need reallocation
            removed_leds_queue: List[tuple] = []  # [(led_index, source_key_index), ...]
            
            # First pass: Apply overrides and collect removed LEDs
            for midi_note_str, selected_leds in overrides.items():
                try:
                    midi_note = int(midi_note_str)
                    key_index = midi_note - 21
                    
                    if not (0 <= key_index < 88):
                        continue
                    
                    selected_leds = list(selected_leds) if selected_leds else []
                    
                    # Get the original LEDs for this key
                    original_leds = base_mapping.get(key_index, [])
                    
                    # Find LEDs that were removed
                    removed_leds = set(original_leds) - set(selected_leds)
                    
                    # Update the mapping for this key
                    adjusted_mapping[key_index] = sorted(selected_leds)
                    
                    # Queue removed LEDs for reallocation
                    for removed_led in sorted(removed_leds):
                        removed_leds_queue.append((removed_led, key_index))
                    
                except (ValueError, TypeError):
                    continue
            
            # Second pass: Reassign removed LEDs to neighbors
            for removed_led, source_key in removed_leds_queue:
                target_key = self._find_best_neighbor(
                    source_key, removed_led, adjusted_mapping, start_led, end_led
                )
                
                if target_key is not None and 0 <= target_key < 88:
                    if removed_led not in adjusted_mapping[target_key]:
                        adjusted_mapping[target_key].append(removed_led)
                        adjusted_mapping[target_key].sort()
                        logger.debug(f"Reassigned LED {removed_led} from key {source_key} to key {target_key}")
            
            return adjusted_mapping
        
        except Exception as e:
            logger.error(f"Error applying LED selection overrides: {e}")
            return base_mapping
    
    def _find_best_neighbor(
        self,
        key_index: int,
        led_index: int,
        mapping: Dict[int, List[int]],
        start_led: int,
        end_led: int
    ) -> Optional[int]:
        """
        Find the best neighboring key to assign a removed LED.
        
        Strategy:
        1. Prefer the neighbor whose LED range is closest to the removed LED
        2. If equidistant, prefer the neighbor in the direction of the LED
        3. Fallback to any available neighbor
        """
        candidates = []
        
        # Check left neighbor
        if key_index > 0:
            left_key_leds = mapping.get(key_index - 1, [])
            if left_key_leds:
                left_max = max(left_key_leds)
                left_min = min(left_key_leds)
                # Distance to the closest edge of left neighbor's range
                distance = min(abs(led_index - left_max), abs(led_index - left_min))
                candidates.append((distance, key_index - 1, 'left'))
        
        # Check right neighbor
        if key_index < 87:
            right_key_leds = mapping.get(key_index + 1, [])
            if right_key_leds:
                right_min = min(right_key_leds)
                right_max = max(right_key_leds)
                # Distance to the closest edge of right neighbor's range
                distance = min(abs(led_index - right_min), abs(led_index - right_max))
                candidates.append((distance, key_index + 1, 'right'))
        
        if not candidates:
            return None
        
        # Sort by distance (prefer closest neighbor)
        candidates.sort(key=lambda x: x[0])
        
        # If there's a clear winner (significantly closer), use it
        if len(candidates) > 1 and candidates[0][0] < candidates[1][0]:
            return candidates[0][1]
        
        # If distances are similar, prefer right (LEDs typically progress left->right)
        # but check if LED is more on left side - then prefer left
        if len(candidates) > 1:
            left_candidate = next((c for c in candidates if c[2] == 'left'), None)
            right_candidate = next((c for c in candidates if c[2] == 'right'), None)
            
            if left_candidate and right_candidate:
                # Check which neighbor's range the LED is closer to (directionally)
                if left_candidate[0] <= right_candidate[0]:
                    return left_candidate[1]
                else:
                    return right_candidate[1]
        
        # Default to the first (closest) candidate
        return candidates[0][1]
    
    def get_all_overrides(self) -> Dict:
        """
        Get all current LED selection overrides.
        
        Returns:
            dict with all overrides
        """
        if not self.settings_service:
            return {}
        
        try:
            return self.settings_service.get_setting('calibration', 'led_selection_overrides', {}) or {}
        except Exception as e:
            logger.error(f"Failed to get all overrides: {e}")
            return {}
    
    def clear_all_overrides(self) -> Dict:
        """
        Clear all LED selection overrides (revert to auto-allocation for all keys).
        
        Returns:
            dict with success status
        """
        if not self.settings_service:
            return {'success': False, 'error': 'Settings service not available'}
        
        try:
            self.settings_service.set_setting('calibration', 'led_selection_overrides', {})
            logger.info("Cleared all LED selection overrides")
            return {'success': True, 'message': 'All overrides cleared'}
        except Exception as e:
            logger.error(f"Failed to clear all overrides: {e}")
            return {'success': False, 'error': str(e)}
