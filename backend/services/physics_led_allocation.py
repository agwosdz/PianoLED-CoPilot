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
            
            # Build initial mapping: each key gets all LEDs that overlap it
            # (without filtering yet)
            led_count = 255  # Total LEDs on strip
            initial_mapping = {}
            
            # Get physical geometry for all 88 keys
            key_geometries = self.analyzer.key_geometry.calculate_all_key_geometries()
            
            # Calculate LED placements
            usable_led_count = (end_led - start_led) + 1
            led_placements = self.analyzer.led_placement.calculate_led_placements(
                led_count=usable_led_count,
                strip_start_mm=0.0,
                start_led=0,  # Use relative indices
                end_led=usable_led_count - 1,
            )
            
            # For each key, find overlapping LEDs
            for key_idx in range(88):
                key_geom = key_geometries[key_idx]
                
                # Find all LEDs that have ANY overlap with this key
                overlapping_leds = []
                for rel_idx, led_placement in led_placements.items():
                    # Convert to absolute index for storage
                    abs_idx = rel_idx + start_led
                    
                    # Check for overlap between key exposed surface and LED
                    key_start = getattr(key_geom, '_exposed_start', key_geom.start_mm)
                    key_end = getattr(key_geom, '_exposed_end', key_geom.end_mm)
                    
                    led_start = led_placement.start_mm
                    led_end = led_placement.end_mm
                    
                    # Calculate overlap
                    overlap_start = max(key_start, led_start)
                    overlap_end = min(key_end, led_end)
                    overlap = max(0, overlap_end - overlap_start)
                    
                    # Include if there's any overlap
                    if overlap > 0:
                        overlapping_leds.append(abs_idx)
                
                initial_mapping[key_idx] = overlapping_leds
            
            # Now apply filtering based on overhang threshold
            # This uses the consolidated analyze_led_coverage function
            final_mapping = {}
            
            for key_idx in range(88):
                key_geom = key_geometries[key_idx]
                rel_indices = [idx - start_led for idx in initial_mapping[key_idx]]
                
                # Use the physics analyzer to get filtered LEDs
                coverage_result = self.analyzer.led_placement.analyze_led_coverage(
                    key_geom,
                    rel_indices,
                    led_placements,
                    overhang_threshold_mm=self.overhang_threshold_mm
                )
                
                # Convert filtered relative indices back to absolute
                filtered_abs = [idx + start_led for idx in coverage_result["filtered_leds"]]
                final_mapping[key_idx] = filtered_abs
            
            # Get complete analysis
            analysis = self.analyzer.analyze_mapping(
                final_mapping,
                led_count,
                start_led=start_led,
                end_led=end_led,
            )
            
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
