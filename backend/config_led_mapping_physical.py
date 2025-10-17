"""
Physical geometry-based LED mapping analysis for Piano LED Visualizer.

This module provides sophisticated LED placement analysis using physical geometry,
including key dimensions, LED physical properties, and symmetry scoring.

Extracted and adapted from the piano.py LED mapping script to integrate advanced
analysis with the main Piano LED Visualizer backend.
"""

import math
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum


class KeyType(Enum):
    """Enum for different key types on a piano keyboard."""
    WHITE = "white"
    BLACK = "black"


@dataclass
class KeyGeometry:
    """Physical geometry of a single piano key."""
    key_index: int
    key_type: KeyType
    # Position in millimeters from piano start
    start_mm: float
    end_mm: float
    center_mm: float
    width_mm: float
    height_mm: float
    # For black keys, offset from white key surface
    depth_mm: Optional[float] = None
    # Which white keys it sits between
    between_white_keys: Optional[Tuple[int, int]] = None


@dataclass
class LEDPlacement:
    """Placement of a single LED on the physical piano."""
    led_index: int
    start_mm: float
    end_mm: float
    center_mm: float
    width_mm: float


@dataclass
class KeyLEDAssignment:
    """LED assignment for a single key."""
    key_index: int
    key_type: KeyType
    led_indices: List[int]
    coverage_mm: float
    overhang_left_mm: float
    overhang_right_mm: float
    symmetry_score: float
    placement_quality: str


class PhysicalKeyGeometry:
    """
    Calculates exact physical geometry of piano keys and LED placements.
    
    This implementation exactly mirrors piano.py's geometry calculations,
    including white key cuts (where black keys sit) and exposed top ranges.
    
    Uses standard piano dimensions:
    - White keys: 23.5mm wide
    - Black keys: 13.7mm wide, positioned between white keys
    - Key gap: 1.0mm spacing between white keys
    - White key cuts: Different amounts cut from each white key depending on black key position
    """

    # Standard piano dimensions (millimeters)
    WHITE_KEY_WIDTH = 23.5
    BLACK_KEY_WIDTH = 13.7
    WHITE_KEY_GAP = 1.0
    WHITE_KEY_HEIGHT = 107.0
    BLACK_KEY_HEIGHT = 60.0
    BLACK_KEY_DEPTH = 20.0
    
    # Cut amounts for white keys (where black keys sit)
    CUT_A = 2.2
    CUT_B = BLACK_KEY_WIDTH - CUT_A  # 11.5
    CUT_C = BLACK_KEY_WIDTH / 2  # 6.85
    
    # White key cut pattern by note name
    # Format: {'note': [left_cut_type, right_cut_type], ...}
    # None = no cut, 'A' = 2.2mm, 'B' = 11.5mm, 'C' = 6.85mm
    WHITE_KEY_CUTS = {
        'C': [None, 'B'],
        'D': ['A', 'A'],
        'E': ['B', None],
        'F': [None, 'B'],
        'G': ['A', 'C'],
        'A': ['C', 'A'],
        'B': ['B', None]
    }

    # Piano note sequence (repeating pattern)
    NOTE_NAMES = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    
    # KEY_MAP: type and note name for each of 88 keys
    KEY_MAP = [
        ('W', 'A'), ('B', 'A'), ('W', 'B'),
        ('W', 'C'), ('B', 'C'), ('W', 'D'), ('B', 'D'), ('W', 'E'), ('W', 'F'),
        ('B', 'F'), ('W', 'G'), ('B', 'G'),
        # This pattern repeats for octaves 1-7
    ]
    
    @staticmethod
    def _get_key_info(key_idx: int) -> Tuple[str, str]:
        """Get key type and note name for a key index (0-87)."""
        # This is the exact 88-key pattern from piano.py's KEY_MAP
        key_pattern = [
            ('W', 'A'), ('B', 'A'), ('W', 'B'),
            ('W', 'C'), ('B', 'C'), ('W', 'D'), ('B', 'D'), ('W', 'E'), ('W', 'F'),
            ('B', 'F'), ('W', 'G'), ('B', 'G'),
        ]
        # Pattern repeats for 7 octaves
        pattern_len = len(key_pattern)
        octave = key_idx // pattern_len
        pos_in_octave = key_idx % pattern_len
        
        # For the last octave (84-87), we only have A, B, C8
        if key_idx >= 84:
            final_keys = [
                (84, ('W', 'A')), (85, ('B', 'A')), (86, ('W', 'B')),
                (87, ('W', 'C')),
            ]
            for idx, info in final_keys:
                if key_idx == idx:
                    return info
        
        return key_pattern[pos_in_octave]

    @staticmethod
    def calculate_all_key_geometries(
        white_key_width: float = WHITE_KEY_WIDTH,
        black_key_width: float = BLACK_KEY_WIDTH,
        white_key_gap: float = WHITE_KEY_GAP,
    ) -> Dict[int, KeyGeometry]:
        """
        Calculate exact geometry for all 88 piano keys, including exposed top ranges.
        
        This exactly mirrors the piano.py algorithm which:
        1. Calculates base positions for all white keys
        2. Calculates exposed (visible) ranges accounting for black key cuts
        3. Calculates black key positions between white keys

        Args:
            white_key_width: Width of white keys in mm
            black_key_width: Width of black keys in mm
            white_key_gap: Gap between white keys in mm

        Returns:
            Dictionary mapping key_index to KeyGeometry with exposed ranges
        """
        geometries = {}
        
        # Step 1: Calculate BASE positions for all white keys
        white_key_positions = []  # List of {key_idx, base_start, base_end, note}
        current_pos = 0.0
        
        for key_idx in range(88):
            key_type, note_name = PhysicalKeyGeometry._get_key_info(key_idx)
            
            if key_type == 'W':
                base_start = current_pos
                base_end = current_pos + white_key_width
                white_key_positions.append({
                    'key_idx': key_idx,
                    'base_start': base_start,
                    'base_end': base_end,
                    'note': note_name
                })
                current_pos += white_key_width + white_key_gap
        
        # Step 2: Calculate EXPOSED ranges for white keys (accounting for black key cuts)
        for white_idx, white_pos in enumerate(white_key_positions):
            key_idx = white_pos['key_idx']
            base_start = white_pos['base_start']
            base_end = white_pos['base_end']
            note_name = white_pos['note']
            
            # Start with full base range
            exposed_start = base_start
            exposed_end = base_end
            
            # Get cut specifications for this note
            left_cut_type, right_cut_type = PhysicalKeyGeometry.WHITE_KEY_CUTS[note_name]
            
            # Apply LEFT cut if this note has a black key to its left AND this isn't the first key
            # (A0, the first key, has no black key to its left)
            if left_cut_type and white_idx > 0:
                cut_value = {
                    'A': PhysicalKeyGeometry.CUT_A,
                    'B': PhysicalKeyGeometry.CUT_B,
                    'C': PhysicalKeyGeometry.CUT_C
                }[left_cut_type]
                exposed_start = base_start + cut_value
            
            # Apply RIGHT cut if this note has a black key to its right AND this isn't the last key
            # (C8, the last key, has no black key to its right)
            if right_cut_type and white_idx < len(white_key_positions) - 1:
                cut_value = {
                    'A': PhysicalKeyGeometry.CUT_A,
                    'B': PhysicalKeyGeometry.CUT_B,
                    'C': PhysicalKeyGeometry.CUT_C
                }[right_cut_type]
                exposed_end = base_end - cut_value
            
            geometries[key_idx] = KeyGeometry(
                key_index=key_idx,
                key_type=KeyType.WHITE,
                start_mm=base_start,
                end_mm=base_end,
                center_mm=(base_start + base_end) / 2,
                width_mm=white_key_width,
                height_mm=PhysicalKeyGeometry.WHITE_KEY_HEIGHT,
                depth_mm=None
            )
            # Store exposed range in a way we can access later
            geometries[key_idx]._exposed_start = exposed_start
            geometries[key_idx]._exposed_end = exposed_end
            geometries[key_idx]._exposed_center = (exposed_start + exposed_end) / 2
        
        # Step 3: Calculate BLACK key positions (between white keys)
        # Black key start = exposed range end from previous white key + black gap (1.0mm)
        # Black key end = black key start + black key width
        white_key_idx = 0
        for key_idx in range(88):
            key_type, _ = PhysicalKeyGeometry._get_key_info(key_idx)
            
            if key_type == 'B':
                # Black key positioned between two white keys
                if white_key_idx < len(white_key_positions) and white_key_idx + 1 < len(white_key_positions):
                    prev_white_info = white_key_positions[white_key_idx]
                    prev_white_geo = geometries[prev_white_info['key_idx']]
                    
                    # Black key start = previous white key's exposed end + black gap (1.0mm)
                    black_start = prev_white_geo._exposed_end + 1.0
                    black_end = black_start + black_key_width
                    
                    geometries[key_idx] = KeyGeometry(
                        key_index=key_idx,
                        key_type=KeyType.BLACK,
                        start_mm=black_start,
                        end_mm=black_end,
                        center_mm=(black_start + black_end) / 2,
                        width_mm=black_key_width,
                        height_mm=PhysicalKeyGeometry.BLACK_KEY_HEIGHT,
                        depth_mm=PhysicalKeyGeometry.BLACK_KEY_DEPTH
                    )
                    # For black keys, physical and exposed ranges are the same
                    geometries[key_idx]._exposed_start = black_start
                    geometries[key_idx]._exposed_end = black_end
                    geometries[key_idx]._exposed_center = (black_start + black_end) / 2
            else:
                # Track white key index for black key calculations
                white_key_idx += 1
        
        return geometries


class LEDPhysicalPlacement:
    """
    Calculates LED strip placements and detects physical overlaps.
    """

    def __init__(
        self,
        led_density: float = 200.0,  # LEDs per meter
        led_physical_width: float = 3.5,  # mm
        led_strip_offset: Optional[float] = None,  # mm (defaults to led_physical_width / 2)
    ):
        """
        Initialize LED physical placement calculator.

        Args:
            led_density: Number of LEDs per meter
            led_physical_width: Physical width of each LED in mm
            led_strip_offset: Physical offset of LED center from strip edge in mm
                            (defaults to led_physical_width / 2)
        """
        self.led_density = led_density
        self.led_spacing_mm = 1000.0 / led_density
        self.led_physical_width = led_physical_width
        # Default offset is half the LED width (center of LED)
        self.led_strip_offset = led_strip_offset if led_strip_offset is not None else (led_physical_width / 2)

    def calculate_led_placements(
        self,
        led_count: int,
        strip_start_mm: float = 0.0,
        start_led: int = 0,
        end_led: Optional[int] = None,
    ) -> Dict[int, LEDPlacement]:
        """
        Calculate physical placement of LEDs in a usable range.

        Uses relative indices (0 to range_size-1) for positioning calculation,
        then maps back to actual LED indices for the dictionary keys.

        Args:
            led_count: Total number of LEDs on strip (for validation)
            strip_start_mm: Physical start position of LED strip in mm
            start_led: First LED index in usable range (default 0)
            end_led: Last LED index in usable range (default led_count-1)

        Returns:
            Dictionary mapping actual led_index to LEDPlacement
        """
        if end_led is None:
            end_led = led_count - 1

        placements = {}

        # Calculate placements for usable range using relative indices
        for relative_idx in range(start_led, end_led + 1):
            # Position of LED center using relative index for spacing
            # This ensures LEDs 0 to range_size-1 have correct spacing
            led_center = strip_start_mm + (relative_idx * self.led_spacing_mm) + self.led_strip_offset
            led_start = led_center - (self.led_physical_width / 2)
            led_end = led_center + (self.led_physical_width / 2)

            placements[relative_idx] = LEDPlacement(
                led_index=relative_idx,
                start_mm=led_start,
                end_mm=led_end,
                center_mm=led_center,
                width_mm=self.led_physical_width,
            )

        return placements

    def find_overlapping_leds(
        self,
        key_geometry: KeyGeometry,
        led_placements: Dict[int, LEDPlacement],
        overhang_threshold_mm: float = 1.5,
    ) -> List[int]:
        """
        Find all LEDs that physically overlap with a key.

        Uses configurable overhang threshold to determine significant overlap.

        Args:
            key_geometry: Geometry of the key
            led_placements: Dictionary of all LED placements
            overhang_threshold_mm: Minimum overhang to count LED as assigned

        Returns:
            List of LED indices that overlap with the key
        """
        overlapping = []

        for led_idx, led_placement in led_placements.items():
            # Calculate overlap between key and LED
            overlap_start = max(key_geometry.start_mm, led_placement.start_mm)
            overlap_end = min(key_geometry.end_mm, led_placement.end_mm)
            overlap_amount = max(0, overlap_end - overlap_start)

            # Check if overlap meets threshold
            if overlap_amount >= overhang_threshold_mm:
                overlapping.append(led_idx)

        return overlapping

    def calculate_overhang(
        self,
        key_geometry: KeyGeometry,
        led_indices: List[int],
        led_placements: Dict[int, LEDPlacement],
    ) -> Tuple[float, float]:
        """
        Calculate how much LED coverage overhangs beyond key exposed edges.
        
        Uses exposed_start and exposed_end (the visible playing surface)
        rather than the full key range which includes cuts for black keys.

        Args:
            key_geometry: Geometry of the key
            led_indices: List of LED indices assigned to this key
            led_placements: Dictionary of all LED placements

        Returns:
            Tuple of (left_overhang_mm, right_overhang_mm)
        """
        if not led_indices:
            return 0.0, 0.0

        # Get exposed range from key geometry
        exposed_start = getattr(key_geometry, '_exposed_start', key_geometry.start_mm)
        exposed_end = getattr(key_geometry, '_exposed_end', key_geometry.end_mm)

        # Get min and max LED positions
        led_start = min(led_placements[idx].start_mm for idx in led_indices)
        led_end = max(led_placements[idx].end_mm for idx in led_indices)

        left_overhang = max(0, exposed_start - led_start)
        right_overhang = max(0, led_end - exposed_end)

        return left_overhang, right_overhang

    def calculate_coverage_amount(
        self,
        key_geometry: KeyGeometry,
        led_indices: List[int],
        led_placements: Dict[int, LEDPlacement],
    ) -> float:
        """
        Calculate how much of the key exposed surface is covered by LEDs (in mm).
        
        Uses exposed_start and exposed_end (the visible playing surface)
        rather than the full key range which includes cuts for black keys.
        """
        if not led_indices:
            return 0.0

        # Get exposed range from key geometry
        exposed_start = getattr(key_geometry, '_exposed_start', key_geometry.start_mm)
        exposed_end = getattr(key_geometry, '_exposed_end', key_geometry.end_mm)

        total_coverage = 0.0
        for led_idx in led_indices:
            led = led_placements[led_idx]
            overlap_start = max(exposed_start, led.start_mm)
            overlap_end = min(exposed_end, led.end_mm)
            total_coverage += max(0, overlap_end - overlap_start)

        return total_coverage


class SymmetryAnalysis:
    """
    Analyzes symmetry and alignment quality of LED placement on keys.
    """

    @staticmethod
    def calculate_symmetry_score(
        key_geometry: KeyGeometry,
        led_indices: List[int],
        led_placements: Dict[int, LEDPlacement],
    ) -> float:
        """
        Calculate symmetry score for LED placement on a key (0.0 to 1.0).

        1.0 = perfectly centered relative to exposed surface
        0.0 = completely off-center
        
        Uses exposed center and width for comparison, not the full key range.

        Args:
            key_geometry: Geometry of the key
            led_indices: List of LED indices assigned to this key
            led_placements: Dictionary of all LED placements

        Returns:
            Symmetry score from 0.0 to 1.0
        """
        if not led_indices:
            return 0.0

        # Get exposed range (visible playing surface)
        exposed_start = getattr(key_geometry, '_exposed_start', key_geometry.start_mm)
        exposed_end = getattr(key_geometry, '_exposed_end', key_geometry.end_mm)
        exposed_center = (exposed_start + exposed_end) / 2
        exposed_width = exposed_end - exposed_start

        # Calculate center of LED assignment
        led_positions = [led_placements[idx].center_mm for idx in led_indices]
        led_center = sum(led_positions) / len(led_positions)

        # Calculate deviation from exposed center
        deviation = abs(led_center - exposed_center)
        exposed_half_width = exposed_width / 2

        # Normalize to 0-1 score
        # 0 deviation = 1.0, full width deviation = 0.0
        if deviation >= exposed_half_width:
            symmetry = 0.0
        else:
            symmetry = 1.0 - (deviation / exposed_half_width)

        return round(symmetry, 4)

    @staticmethod
    def get_symmetry_label(score: float) -> str:
        """Get human-readable label for symmetry score."""
        if score >= 0.95:
            return "Excellent Center Alignment"
        elif score >= 0.85:
            return "Good Center Alignment"
        elif score >= 0.70:
            return "Acceptable Alignment"
        elif score >= 0.50:
            return "Off-Center Alignment"
        else:
            return "Poor Alignment"

    @staticmethod
    def analyze_coverage_consistency(
        key_geometry: KeyGeometry,
        led_indices: List[int],
        led_placements: Dict[int, LEDPlacement],
    ) -> Tuple[float, str]:
        """
        Analyze coverage consistency (how evenly LEDs are distributed on key).

        Returns:
            Tuple of (consistency_score, description)
        """
        if not led_indices or len(led_indices) <= 1:
            return 1.0, "Single LED or no coverage"

        # Calculate gaps between consecutive LEDs
        led_positions = sorted([led_placements[idx].center_mm for idx in led_indices])
        gaps = [led_positions[i + 1] - led_positions[i] for i in range(len(led_positions) - 1)]

        if not gaps:
            return 1.0, "No gaps"

        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)

        # Score based on variance
        # Low variance = consistent gaps = high score
        if variance < 0.5:
            consistency = 1.0
            description = "Perfectly even distribution"
        elif variance < 1.5:
            consistency = 0.85
            description = "Very consistent distribution"
        elif variance < 3.0:
            consistency = 0.70
            description = "Reasonably consistent"
        else:
            consistency = 0.50
            description = "Uneven distribution"

        return round(consistency, 4), description


class PhysicalMappingAnalyzer:
    """
    Complete physical mapping analysis combining geometry, placement, and symmetry.
    """

    def __init__(
        self,
        led_density: float = 200.0,
        led_physical_width: float = 3.5,
        led_strip_offset: Optional[float] = None,
        overhang_threshold_mm: float = 1.5,
        white_key_width: float = 23.5,
        black_key_width: float = 13.7,
        white_key_gap: float = 1.0,
    ):
        """Initialize the complete analyzer with all parameters."""
        self.led_density = led_density
        self.led_physical_width = led_physical_width
        # Use the provided offset or let LEDPhysicalPlacement calculate default
        self.led_strip_offset = led_strip_offset if led_strip_offset is not None else (led_physical_width / 2)
        self.overhang_threshold_mm = overhang_threshold_mm
        self.white_key_width = white_key_width
        self.black_key_width = black_key_width
        self.white_key_gap = white_key_gap

        self.key_geometry = PhysicalKeyGeometry()
        self.led_placement = LEDPhysicalPlacement(
            led_density=led_density,
            led_physical_width=led_physical_width,
            led_strip_offset=led_strip_offset,  # Pass None to use default
        )
        self.symmetry = SymmetryAnalysis()

    def analyze_mapping(
        self,
        key_led_mapping: Dict[int, List[int]],
        led_count: int,
        start_led: int = 0,
        end_led: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Perform complete physical analysis on a key-to-LED mapping.

        Args:
            key_led_mapping: Dictionary mapping key_index to list of LED indices
            led_count: Total number of LEDs on the strip
            start_led: First LED index in usable range (default 0)
            end_led: Last LED index in usable range (default led_count-1)

        Returns:
            Complete analysis result with detailed metrics per key
        """
        if end_led is None:
            end_led = led_count - 1

        # Calculate geometries
        key_geometries = self.key_geometry.calculate_all_key_geometries(
            white_key_width=self.white_key_width,
            black_key_width=self.black_key_width,
            white_key_gap=self.white_key_gap,
        )

        # Calculate LED placements for usable range only
        # Using relative indices (0 to range_size-1) ensures correct spacing formula
        # We calculate with indices starting at 0 for proper spacing calculation
        usable_led_count = (end_led - start_led) + 1
        led_placements = self.led_placement.calculate_led_placements(
            led_count=usable_led_count,  # Number of LEDs in usable range
            strip_start_mm=0.0,
            start_led=0,  # Start from relative 0
            end_led=usable_led_count - 1,  # End at relative count-1
        )

        # Analyze each key
        per_key_analysis = {}
        quality_metrics = {
            "avg_symmetry": 0.0,
            "avg_coverage_consistency": 0.0,
            "avg_overhang_left": 0.0,
            "avg_overhang_right": 0.0,
            "total_keys_analyzed": 0,
            "excellent_alignment": 0,
            "good_alignment": 0,
            "acceptable_alignment": 0,
            "poor_alignment": 0,
        }

        total_symmetry = 0.0
        total_consistency = 0.0
        total_overhang_left = 0.0
        total_overhang_right = 0.0
        for key_idx in range(88):
            key_geom = key_geometries[key_idx]
            # Get absolute LED indices from mapping
            abs_led_indices = key_led_mapping.get(key_idx, [])
            # Convert to relative indices for calculations
            rel_led_indices = [idx - start_led for idx in abs_led_indices if start_led <= idx <= end_led]

            # Calculate metrics using relative indices
            symmetry_score = self.symmetry.calculate_symmetry_score(
                key_geom, rel_led_indices, led_placements
            )
            symmetry_label = self.symmetry.get_symmetry_label(symmetry_score)

            consistency_score, consistency_label = (
                self.symmetry.analyze_coverage_consistency(key_geom, rel_led_indices, led_placements)
            )

            left_overhang, right_overhang = self.led_placement.calculate_overhang(
                key_geom, rel_led_indices, led_placements
            )

            coverage_amount = self.led_placement.calculate_coverage_amount(
                key_geom, rel_led_indices, led_placements
            )

            # Calculate LED gaps and detail information (matching piano.py output)
            # Use absolute indices for output detail
            led_details = []
            if abs_led_indices:
                for i, abs_idx in enumerate(abs_led_indices):
                    # Convert to relative for lookup
                    rel_idx = abs_idx - start_led
                    if rel_idx in led_placements:
                        led_placement = led_placements[rel_idx]
                        led_detail = {
                            "led_index": abs_idx,  # Output absolute index
                            "center_mm": round(led_placement.center_mm, 2),
                            "start_mm": round(led_placement.start_mm, 2),
                            "end_mm": round(led_placement.end_mm, 2),
                        }
                        # Add gap info from previous LED
                        if i > 0:
                            prev_abs_idx = abs_led_indices[i-1]
                            prev_rel_idx = prev_abs_idx - start_led
                            if prev_rel_idx in led_placements:
                                prev_led = led_placements[prev_rel_idx]
                                gap = led_placement.start_mm - prev_led.end_mm
                                led_detail["gap_from_previous_mm"] = round(gap, 2)
                        led_details.append(led_detail)

            # Neighbor analysis
            neighbor_prev = None
            neighbor_next = None
            
            # Analyze with previous key
            if key_idx > 0:
                prev_abs_indices = set(key_led_mapping.get(key_idx - 1, []))
                curr_abs_indices = set(abs_led_indices)
                shared = prev_abs_indices.intersection(curr_abs_indices)
                neighbor_prev = {
                    "key_index": key_idx - 1,
                    "shared_leds": sorted(list(shared)),
                    "consecutive": False
                }
                # Check if consecutive
                if prev_abs_indices and curr_abs_indices:
                    if max(prev_abs_indices) + 1 == min(curr_abs_indices):
                        neighbor_prev["consecutive"] = True

            # Analyze with next key
            if key_idx < 87:
                curr_abs_indices = set(abs_led_indices)
                next_abs_indices = set(key_led_mapping.get(key_idx + 1, []))
                shared = curr_abs_indices.intersection(next_abs_indices)
                neighbor_next = {
                    "key_index": key_idx + 1,
                    "shared_leds": sorted(list(shared)),
                    "consecutive": False
                }
                # Check if consecutive
                if curr_abs_indices and next_abs_indices:
                    if max(curr_abs_indices) + 1 == min(next_abs_indices):
                        neighbor_next["consecutive"] = True

            # Build analysis record
            per_key_analysis[key_idx] = {
                "key_number": key_idx + 1,
                "key_type": key_geom.key_type.value,
                "physical_front_range_mm": {
                    "start": round(key_geom.start_mm, 2),
                    "end": round(key_geom.end_mm, 2),
                    "center": round(key_geom.center_mm, 2)
                },
                "exposed_top_range_mm": {
                    "start": round(getattr(key_geom, '_exposed_start', key_geom.start_mm), 2),
                    "end": round(getattr(key_geom, '_exposed_end', key_geom.end_mm), 2),
                    "center": round(getattr(key_geom, '_exposed_center', key_geom.center_mm), 2)
                },
                "led_indices": abs_led_indices,  # Output absolute indices
                "led_count": len(abs_led_indices),
                "led_details": led_details,
                "coverage_mm": round(coverage_amount, 2),
                "key_width_mm": round(key_geom.width_mm, 2),
                "overhang_left_mm": round(left_overhang, 2),
                "overhang_right_mm": round(right_overhang, 2),
                "symmetry_score": round(symmetry_score, 4),
                "symmetry_label": symmetry_label,
                "consistency_score": round(consistency_score, 4),
                "consistency_label": consistency_label,
                "overall_quality": self._calculate_overall_quality(
                    symmetry_score, consistency_score
                ),
                "neighbor_prev": neighbor_prev,
                "neighbor_next": neighbor_next,
            }

            # Accumulate for averages
            total_symmetry += symmetry_score
            total_consistency += consistency_score
            total_overhang_left += left_overhang
            total_overhang_right += right_overhang

            # Count quality tiers
            if symmetry_score >= 0.95:
                quality_metrics["excellent_alignment"] += 1
            elif symmetry_score >= 0.85:
                quality_metrics["good_alignment"] += 1
            elif symmetry_score >= 0.70:
                quality_metrics["acceptable_alignment"] += 1
            else:
                quality_metrics["poor_alignment"] += 1

        # Calculate averages
        quality_metrics["total_keys_analyzed"] = 88
        quality_metrics["avg_symmetry"] = round(total_symmetry / 88, 4)
        quality_metrics["avg_coverage_consistency"] = round(total_consistency / 88, 4)
        quality_metrics["avg_overhang_left"] = round(total_overhang_left / 88, 4)
        quality_metrics["avg_overhang_right"] = round(total_overhang_right / 88, 4)

        # Calculate overall quality grade
        overall_quality = self._calculate_overall_quality_grade(quality_metrics)

        return {
            "per_key_analysis": per_key_analysis,
            "quality_metrics": quality_metrics,
            "overall_quality": overall_quality,
            "parameters_used": {
                "led_density": self.led_density,
                "led_physical_width": self.led_physical_width,
                "led_strip_offset": self.led_strip_offset,
                "overhang_threshold_mm": self.overhang_threshold_mm,
                "white_key_width": self.white_key_width,
                "black_key_width": self.black_key_width,
                "white_key_gap": self.white_key_gap,
            },
            "led_range": {
                "start_led": start_led,
                "end_led": end_led,
                "total_leds_analyzed": end_led - start_led + 1
            },
        }

    @staticmethod
    def _calculate_overall_quality(symmetry: float, consistency: float) -> str:
        """Determine overall quality for a single key."""
        combined = (symmetry + consistency) / 2
        if combined >= 0.90:
            return "Excellent"
        elif combined >= 0.75:
            return "Good"
        elif combined >= 0.60:
            return "Acceptable"
        else:
            return "Poor"

    @staticmethod
    def _calculate_overall_quality_grade(metrics: Dict) -> str:
        """Determine overall quality grade for entire mapping."""
        avg_symmetry = metrics["avg_symmetry"]
        excellent_pct = (metrics["excellent_alignment"] / 88) * 100

        if avg_symmetry >= 0.90 and excellent_pct >= 70:
            return "Excellent"
        elif avg_symmetry >= 0.80 and excellent_pct >= 50:
            return "Very Good"
        elif avg_symmetry >= 0.70 and excellent_pct >= 30:
            return "Good"
        elif avg_symmetry >= 0.60:
            return "Acceptable"
        else:
            return "Needs Improvement"
