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
    
    Uses standard piano dimensions:
    - White keys: 23.5mm wide
    - Black keys: 13.7mm wide, positioned between white keys
    - Key gap: 1.0mm spacing between white keys
    """

    # Standard piano dimensions (millimeters)
    WHITE_KEY_WIDTH = 23.5
    BLACK_KEY_WIDTH = 13.7
    WHITE_KEY_GAP = 1.0
    WHITE_KEY_HEIGHT = 107.0
    BLACK_KEY_HEIGHT = 60.0
    BLACK_KEY_DEPTH = 20.0  # Offset from white key surface

    # Total 88 keys: 52 white, 36 black
    # Black keys at positions: 1,2,4,5,6,8,9,11,12,13, ... (repeating pattern except first/last)
    BLACK_KEY_INDICES = [
        1, 2, 4, 5, 6, 8, 9, 11, 12, 13,
        15, 16, 18, 19, 20, 22, 23, 25, 26, 27,
        29, 30, 32, 33, 34, 36, 37, 39, 40, 41,
        43, 44, 46, 47, 48, 50, 51, 53, 54, 55,
        57, 58, 60, 61, 62, 64, 65, 67, 68, 69,
        71, 72, 74, 75, 76, 78, 79, 81, 82, 83,
        85, 86
    ]

    @staticmethod
    def calculate_all_key_geometries(
        white_key_width: float = WHITE_KEY_WIDTH,
        black_key_width: float = BLACK_KEY_WIDTH,
        white_key_gap: float = WHITE_KEY_GAP,
    ) -> Dict[int, KeyGeometry]:
        """
        Calculate exact geometry for all 88 piano keys.

        Args:
            white_key_width: Width of white keys in mm
            black_key_width: Width of black keys in mm
            white_key_gap: Gap between white keys in mm

        Returns:
            Dictionary mapping key_index to KeyGeometry
        """
        geometries = {}
        current_pos = 0.0  # Position in mm from piano start

        white_key_count = 0
        for key_idx in range(88):
            is_black = key_idx in PhysicalKeyGeometry.BLACK_KEY_INDICES

            if is_black:
                # Black key is positioned between two white keys
                # Center it at a specific offset relative to the gap
                white_idx = white_key_count if key_idx > 0 else 0

                # Position of left white key boundary
                left_white_start = white_idx * (white_key_width + white_key_gap)
                left_white_end = left_white_start + white_key_width

                # Position of right white key boundary
                right_white_start = (white_idx + 1) * (white_key_width + white_key_gap)

                # Black key center is between the white keys
                black_center = (left_white_end + right_white_start) / 2
                black_start = black_center - (black_key_width / 2)
                black_end = black_center + (black_key_width / 2)

                geometries[key_idx] = KeyGeometry(
                    key_index=key_idx,
                    key_type=KeyType.BLACK,
                    start_mm=black_start,
                    end_mm=black_end,
                    center_mm=black_center,
                    width_mm=black_key_width,
                    height_mm=PhysicalKeyGeometry.BLACK_KEY_HEIGHT,
                    depth_mm=PhysicalKeyGeometry.BLACK_KEY_DEPTH,
                    between_white_keys=(white_idx, white_idx + 1)
                )
            else:
                # White key
                white_start = white_key_count * (white_key_width + white_key_gap)
                white_end = white_start + white_key_width
                white_center = (white_start + white_end) / 2

                geometries[key_idx] = KeyGeometry(
                    key_index=key_idx,
                    key_type=KeyType.WHITE,
                    start_mm=white_start,
                    end_mm=white_end,
                    center_mm=white_center,
                    width_mm=white_key_width,
                    height_mm=PhysicalKeyGeometry.WHITE_KEY_HEIGHT,
                    depth_mm=None,
                    between_white_keys=None
                )
                white_key_count += 1

        return geometries

    @staticmethod
    def get_black_key_neighbors(key_idx: int) -> Tuple[Optional[int], Optional[int]]:
        """Get the white keys neighboring a black key."""
        if key_idx not in PhysicalKeyGeometry.BLACK_KEY_INDICES:
            return None, None

        # Count how many white keys come before this key
        white_count = 0
        for idx in range(key_idx):
            if idx not in PhysicalKeyGeometry.BLACK_KEY_INDICES:
                white_count += 1

        return white_count, white_count + 1


class LEDPhysicalPlacement:
    """
    Calculates LED strip placements and detects physical overlaps.
    """

    def __init__(
        self,
        led_density: float = 200.0,  # LEDs per meter
        led_physical_width: float = 3.5,  # mm
        led_strip_offset: float = 1.75,  # mm (half width, offset from start)
    ):
        """
        Initialize LED physical placement calculator.

        Args:
            led_density: Number of LEDs per meter
            led_physical_width: Physical width of each LED in mm
            led_strip_offset: Physical offset of LED center from strip edge in mm
        """
        self.led_density = led_density
        self.led_spacing_mm = 1000.0 / led_density
        self.led_physical_width = led_physical_width
        self.led_strip_offset = led_strip_offset

    def calculate_led_placements(
        self,
        led_count: int,
        strip_start_mm: float = 0.0,
    ) -> Dict[int, LEDPlacement]:
        """
        Calculate physical placement of all LEDs on the strip.

        Args:
            led_count: Total number of LEDs on strip
            strip_start_mm: Physical start position of LED strip in mm

        Returns:
            Dictionary mapping led_index to LEDPlacement
        """
        placements = {}

        for led_idx in range(led_count):
            # Position of LED center
            led_center = strip_start_mm + (led_idx * self.led_spacing_mm) + self.led_strip_offset
            led_start = led_center - (self.led_physical_width / 2)
            led_end = led_center + (self.led_physical_width / 2)

            placements[led_idx] = LEDPlacement(
                led_index=led_idx,
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
        Calculate how much LED coverage overhangs beyond key edges.

        Args:
            key_geometry: Geometry of the key
            led_indices: List of LED indices assigned to this key
            led_placements: Dictionary of all LED placements

        Returns:
            Tuple of (left_overhang_mm, right_overhang_mm)
        """
        if not led_indices:
            return 0.0, 0.0

        # Get min and max LED positions
        led_start = min(led_placements[idx].start_mm for idx in led_indices)
        led_end = max(led_placements[idx].end_mm for idx in led_indices)

        left_overhang = max(0, key_geometry.start_mm - led_start)
        right_overhang = max(0, led_end - key_geometry.end_mm)

        return left_overhang, right_overhang

    def calculate_coverage_amount(
        self,
        key_geometry: KeyGeometry,
        led_indices: List[int],
        led_placements: Dict[int, LEDPlacement],
    ) -> float:
        """Calculate how much of the key is covered by LEDs (in mm)."""
        if not led_indices:
            return 0.0

        total_coverage = 0.0
        for led_idx in led_indices:
            led = led_placements[led_idx]
            overlap_start = max(key_geometry.start_mm, led.start_mm)
            overlap_end = min(key_geometry.end_mm, led.end_mm)
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

        1.0 = perfectly centered
        0.0 = completely off-center

        Args:
            key_geometry: Geometry of the key
            led_indices: List of LED indices assigned to this key
            led_placements: Dictionary of all LED placements

        Returns:
            Symmetry score from 0.0 to 1.0
        """
        if not led_indices:
            return 0.0

        # Calculate center of LED assignment
        led_positions = [led_placements[idx].center_mm for idx in led_indices]
        led_center = sum(led_positions) / len(led_positions)

        # Calculate deviation from key center
        deviation = abs(led_center - key_geometry.center_mm)
        key_half_width = key_geometry.width_mm / 2

        # Normalize to 0-1 score
        # 0 deviation = 1.0, full width deviation = 0.0
        if deviation >= key_half_width:
            symmetry = 0.0
        else:
            symmetry = 1.0 - (deviation / key_half_width)

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
        led_strip_offset: float = 1.75,
        overhang_threshold_mm: float = 1.5,
        white_key_width: float = 23.5,
        black_key_width: float = 13.7,
        white_key_gap: float = 1.0,
    ):
        """Initialize the complete analyzer with all parameters."""
        self.led_density = led_density
        self.led_physical_width = led_physical_width
        self.led_strip_offset = led_strip_offset
        self.overhang_threshold_mm = overhang_threshold_mm
        self.white_key_width = white_key_width
        self.black_key_width = black_key_width
        self.white_key_gap = white_key_gap

        self.key_geometry = PhysicalKeyGeometry()
        self.led_placement = LEDPhysicalPlacement(
            led_density=led_density,
            led_physical_width=led_physical_width,
            led_strip_offset=led_strip_offset,
        )
        self.symmetry = SymmetryAnalysis()

    def analyze_mapping(
        self,
        key_led_mapping: Dict[int, List[int]],
        led_count: int,
    ) -> Dict[str, Any]:
        """
        Perform complete physical analysis on a key-to-LED mapping.

        Args:
            key_led_mapping: Dictionary mapping key_index to list of LED indices
            led_count: Total number of LEDs on the strip

        Returns:
            Complete analysis result with detailed metrics per key
        """
        # Calculate geometries
        key_geometries = self.key_geometry.calculate_all_key_geometries(
            white_key_width=self.white_key_width,
            black_key_width=self.black_key_width,
            white_key_gap=self.white_key_gap,
        )

        # Calculate LED placements
        led_placements = self.led_placement.calculate_led_placements(led_count)

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
            led_indices = key_led_mapping.get(key_idx, [])

            # Calculate metrics
            symmetry_score = self.symmetry.calculate_symmetry_score(
                key_geom, led_indices, led_placements
            )
            symmetry_label = self.symmetry.get_symmetry_label(symmetry_score)

            consistency_score, consistency_label = (
                self.symmetry.analyze_coverage_consistency(key_geom, led_indices, led_placements)
            )

            left_overhang, right_overhang = self.led_placement.calculate_overhang(
                key_geom, led_indices, led_placements
            )

            coverage_amount = self.led_placement.calculate_coverage_amount(
                key_geom, led_indices, led_placements
            )

            # Build analysis record
            per_key_analysis[key_idx] = {
                "key_type": key_geom.key_type.value,
                "led_indices": led_indices,
                "led_count": len(led_indices),
                "coverage_mm": round(coverage_amount, 2),
                "key_width_mm": round(key_geom.width_mm, 2),
                "overhang_left_mm": round(left_overhang, 2),
                "overhang_right_mm": round(right_overhang, 2),
                "symmetry_score": symmetry_score,
                "symmetry_label": symmetry_label,
                "consistency_score": consistency_score,
                "consistency_label": consistency_label,
                "overall_quality": self._calculate_overall_quality(
                    symmetry_score, consistency_score
                ),
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
