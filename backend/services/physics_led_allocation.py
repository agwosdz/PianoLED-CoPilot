"""
Physics-based LED allocation service.

Uses physical geometry to dynamically determine LED assignments based on
actual physical overlap and quality metrics, rather than fixed ratios.
"""

import logging
from typing import Dict, List, Optional
from backend.config_led_mapping_physical import PhysicalMappingAnalyzer

logger = logging.getLogger(__name__)


class PhysicsBasedAllocationService:
    """
    Allocates LEDs to piano keys using physics-based detection.
    
    Instead of fixed LED-per-key ratios, this analyzes the physical
    geometry of the piano keyboard and LED strip to determine which
    LEDs should be assigned to each key based on:
    - Physical overlap between LED and key exposed surface
    - Overhang threshold (how much LED can extend beyond key edges)
    - Symmetry and coverage quality metrics
    """
    
    def __init__(
        self,
        led_density: float = 200.0,
        led_physical_width: float = 2.0,
        led_strip_offset: Optional[float] = None,
        overhang_threshold_mm: float = 1.5,
    ):
        """
        Initialize physics-based allocation service.
        
        Args:
            led_density: LEDs per meter (default 200 for WS2812B)
            led_physical_width: Physical width of each LED in mm (default 2.0)
            led_strip_offset: Offset of LED center from strip edge in mm
                            (default is led_physical_width / 2)
            overhang_threshold_mm: Maximum allowed overhang in mm (default 1.5)
        """
        self.led_density = led_density
        self.led_physical_width = led_physical_width
        self.led_strip_offset = led_strip_offset or (led_physical_width / 2)
        self.overhang_threshold_mm = overhang_threshold_mm
        
        self.analyzer = PhysicalMappingAnalyzer(
            led_density=led_density,
            led_physical_width=led_physical_width,
            led_strip_offset=self.led_strip_offset,
            overhang_threshold_mm=overhang_threshold_mm,
        )
    
    def allocate_leds(
        self,
        start_led: int = 4,
        end_led: int = 249,
    ) -> Dict:
        """
        Allocate LEDs to piano keys using physics-based detection.
        
        This function:
        1. Calculates physical geometry of all 88 piano keys
        2. Calculates physical placements of all LEDs in the range
        3. For each key, determines which LEDs physically overlap it
        4. Filters LEDs based on overhang threshold to ensure quality
        5. Returns complete allocation with quality metrics
        
        Args:
            start_led: First usable LED index (default 4)
            end_led: Last usable LED index (default 249)
        
        Returns:
            Dictionary with:
            - success: bool indicating if allocation succeeded
            - key_led_mapping: Dict[key_idx] -> List[led_idx]
            - led_allocation_stats: Statistics about the allocation
            - per_key_analysis: Detailed analysis from PhysicalMappingAnalyzer
            - quality_metrics: Overall quality metrics
            - parameters_used: Parameters used for allocation
        """
        try:
            logger.info(f"Starting physics-based LED allocation (LEDs {start_led}-{end_led}, "
                       f"threshold={self.overhang_threshold_mm}mm)")
            
            led_count = 255  # Total LEDs on strip
            key_geometries = self.analyzer.key_geometry.calculate_all_key_geometries()
            
            # STEP 1: Generate initial mapping to detect coverage gap
            logger.info("STEP 1: Generating initial mapping to calculate coverage...")
            initial_mapping, initial_max_led = self._generate_mapping(
                key_geometries, start_led, end_led
            )
            
            # STEP 2: Calculate pitch adjustment based on detected coverage gap
            logger.info("STEP 2: Analyzing coverage gap and calculating pitch adjustment...")
            coverage_gap = end_led - initial_max_led
            logger.info(f"Coverage gap: max_led={initial_max_led}, end_led={end_led}, gap={coverage_gap}")
            
            from backend.services.led_pitch_auto_calibration import auto_calibrate_pitch
            
            piano_start_mm = key_geometries[0].start_mm
            piano_end_mm = key_geometries[87].end_mm
            theoretical_pitch = self.analyzer.led_placement.led_spacing_mm
            
            calibrated_pitch, was_adjusted, pitch_info = auto_calibrate_pitch(
                theoretical_pitch_mm=theoretical_pitch,
                piano_start_mm=piano_start_mm,
                piano_end_mm=piano_end_mm,
                start_led=start_led,
                actual_end_led=end_led,
            )
            
            logger.info(f"Pitch calibration result: was_adjusted={was_adjusted}, "
                       f"theoretical={theoretical_pitch:.6f}mm, calibrated={calibrated_pitch:.6f}mm, "
                       f"diff={abs(calibrated_pitch - theoretical_pitch):.6f}mm")
            
            # Store the pitch info from STEP 2 to use later (before analyzer recalculates)
            initial_pitch_info = pitch_info.copy()
            
            # STEP 3: If pitch was adjusted, regenerate mapping with new pitch
            if was_adjusted:
                logger.info(f"Pitch adjusted: {theoretical_pitch:.4f}mm → {calibrated_pitch:.4f}mm "
                           f"({pitch_info.get('reason', 'coverage')})")
                
                # Update analyzer with calibrated pitch
                self.analyzer.led_placement.led_spacing_mm = calibrated_pitch
                
                # Regenerate mapping with adjusted pitch
                logger.info("STEP 3: Regenerating mapping with adjusted pitch...")
                final_mapping, final_max_led = self._generate_mapping(
                    key_geometries, start_led, end_led
                )
                logger.info(f"New mapping coverage: max_led={final_max_led}")
            else:
                logger.info("No pitch adjustment needed, using initial mapping")
                final_mapping = initial_mapping
            
            # Get complete analysis
            analysis = self.analyzer.analyze_mapping(
                final_mapping,
                led_count,
                start_led=start_led,
                end_led=end_led,
            )
            
            # IMPORTANT: Use the pitch_info from STEP 2, not the recalculated one from analyze_mapping
            # because analyze_mapping recalculates with the updated pitch, losing the "was_adjusted" info
            if was_adjusted:
                # Override with the actual adjustment that happened
                analysis['pitch_calibration'] = initial_pitch_info
                logger.info(f"OVERRIDE: Using pitch calibration from STEP 2: was_adjusted={initial_pitch_info.get('was_adjusted')}, "
                           f"theoretical={initial_pitch_info.get('theoretical_pitch_mm')}, "
                           f"calibrated={initial_pitch_info.get('calibrated_pitch_mm')}")
            else:
                logger.info(f"NO OVERRIDE: was_adjusted={was_adjusted}, keeping analysis pitch_calibration")
            
            # Calculate allocation statistics
            led_allocation_stats = self._calculate_stats(final_mapping, start_led, end_led)
            
            logger.info(f"Physics-based allocation complete: "
                       f"{led_allocation_stats['total_key_count']} keys, "
                       f"{led_allocation_stats['total_led_count']} LEDs used, "
                       f"avg {led_allocation_stats['avg_leds_per_key']:.2f} LEDs/key")
            
            return {
                'success': True,
                'key_led_mapping': final_mapping,
                'led_allocation_stats': led_allocation_stats,
                'per_key_analysis': analysis['per_key_analysis'],
                'quality_metrics': analysis['quality_metrics'],
                'overall_quality': analysis['overall_quality'],
                'pitch_calibration': analysis['pitch_calibration'],
                'parameters_used': {
                    'allocation_method': 'Physics-Based LED Detection',
                    'led_density': self.led_density,
                    'led_physical_width': self.led_physical_width,
                    'led_strip_offset': self.led_strip_offset,
                    'overhang_threshold_mm': self.overhang_threshold_mm,
                    'start_led': start_led,
                    'end_led': end_led,
                },
            }
        
        except Exception as e:
            logger.error(f"Physics-based allocation failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to allocate LEDs using physics-based detection',
            }
    
    def _generate_mapping(self, key_geometries: Dict, start_led: int, end_led: int) -> tuple:
        """
        Generate LED mapping and detect maximum LED coverage.
        
        Returns:
            Tuple of (mapping_dict, max_led_assigned)
        """
        # Calculate LED placements with current pitch
        usable_led_count = (end_led - start_led) + 1
        led_placements = self.analyzer.led_placement.calculate_led_placements(
            led_count=usable_led_count,
            strip_start_mm=0.0,
            start_led=0,
            end_led=usable_led_count - 1,
        )
        
        # Build initial mapping: find overlapping LEDs for each key
        initial_mapping = {}
        for key_idx in range(88):
            key_geom = key_geometries[key_idx]
            overlapping_leds = []
            
            for rel_idx, led_placement in led_placements.items():
                abs_idx = rel_idx + start_led
                
                # Check overlap between key and LED
                key_start = getattr(key_geom, '_exposed_start', key_geom.start_mm)
                key_end = getattr(key_geom, '_exposed_end', key_geom.end_mm)
                
                led_start = led_placement.start_mm
                led_end = led_placement.end_mm
                
                overlap_start = max(key_start, led_start)
                overlap_end = min(key_end, led_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > 0:
                    overlapping_leds.append(abs_idx)
            
            initial_mapping[key_idx] = overlapping_leds
        
        # Apply overhang filtering
        final_mapping = {}
        for key_idx in range(88):
            key_geom = key_geometries[key_idx]
            rel_indices = [idx - start_led for idx in initial_mapping[key_idx]]
            
            coverage_result = self.analyzer.led_placement.analyze_led_coverage(
                key_geom,
                rel_indices,
                led_placements,
                overhang_threshold_mm=self.overhang_threshold_mm
            )
            
            filtered_abs = [idx + start_led for idx in coverage_result["filtered_leds"]]
            final_mapping[key_idx] = filtered_abs
        
        # Ensure full LED range coverage by extending last key
        max_led_assigned = 0
        for leds in final_mapping.values():
            if leds:
                max_led_assigned = max(max_led_assigned, max(leds))
        
        if max_led_assigned < end_led:
            # Find last key with LEDs and extend it
            for key_idx in range(87, -1, -1):
                if final_mapping[key_idx]:
                    current_leds = final_mapping[key_idx]
                    max_current = max(current_leds) if current_leds else start_led
                    
                    if max_current < end_led:
                        extended_leds = list(current_leds) + list(range(max_current + 1, end_led + 1))
                        final_mapping[key_idx] = extended_leds
                        max_led_assigned = end_led
                        logger.debug(f"Extended key {key_idx} to reach end_led {end_led}")
                    break
        
        return final_mapping, max_led_assigned
    
    @staticmethod
    def _calculate_stats(mapping: Dict[int, List[int]], start_led: int, end_led: int) -> Dict:
        """Calculate allocation statistics."""
        total_keys = len(mapping)
        total_leds_used = len(set(led for leds in mapping.values() for led in leds))
        
        leds_per_key = [len(leds) for leds in mapping.values() if len(leds) > 0]
        avg_leds_per_key = sum(leds_per_key) / len(leds_per_key) if leds_per_key else 0
        
        # Count distribution
        distribution = {}
        for count in leds_per_key:
            distribution[str(count)] = distribution.get(str(count), 0) + 1
        
        return {
            'total_key_count': total_keys,
            'total_led_count': total_leds_used,
            'mapped_key_count': len([leds for leds in mapping.values() if leds]),
            'unmapped_key_count': len([leds for leds in mapping.values() if not leds]),
            'avg_leds_per_key': round(avg_leds_per_key, 2),
            'min_leds_per_key': min(leds_per_key) if leds_per_key else 0,
            'max_leds_per_key': max(leds_per_key) if leds_per_key else 0,
            'leds_per_key_distribution': distribution,
            'led_range': f"{start_led}-{end_led}",
            'total_led_range_available': (end_led - start_led) + 1,
        }
