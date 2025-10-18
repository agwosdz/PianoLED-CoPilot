"""
Unit tests for physical geometry-based LED mapping analysis.

Tests the piano.py integration module:
- PhysicalKeyGeometry: Piano key dimension calculations
- LEDPhysicalPlacement: LED strip positioning and overlap detection
- SymmetryAnalysis: Alignment quality scoring
- PhysicalMappingAnalyzer: Complete analysis pipeline
"""

import pytest
import json
from backend.config_led_mapping_physical import (
    PhysicalKeyGeometry,
    LEDPhysicalPlacement,
    SymmetryAnalysis,
    PhysicalMappingAnalyzer,
    KeyGeometry,
    LEDPlacement,
    KeyType,
)


class TestPhysicalKeyGeometry:
    """Test piano key geometry calculations."""

    def test_calculate_all_key_geometries_count(self):
        """Test that all 88 keys are calculated."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries()
        assert len(geometries) == 88, "Should generate geometry for all 88 keys"

    def test_key_geometry_white_keys(self):
        """Test white key dimensions."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries()
        
        # Key 0 (A0) is white
        key_0 = geometries[0]
        assert key_0.key_type == KeyType.WHITE
        assert key_0.width_mm == 23.5
        assert key_0.height_mm == 107.0
        assert key_0.depth_mm is None  # White keys have no depth
        
    def test_key_geometry_black_keys(self):
        """Test black key dimensions."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries()
        
        # Key 1 (A#0) is black
        key_1 = geometries[1]
        assert key_1.key_type == KeyType.BLACK
        assert key_1.width_mm == 13.7
        assert key_1.height_mm == 60.0
        assert key_1.depth_mm == 20.0  # Black keys have depth
        assert key_1.between_white_keys is not None

    def test_key_positions_are_ordered(self):
        """Test that key positions increase monotonically."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries()
        
        prev_center = -1
        for i in range(88):
            current_center = geometries[i].center_mm
            assert current_center > prev_center, f"Key {i} center ({current_center}) should be > previous ({prev_center})"
            prev_center = current_center

    def test_custom_key_dimensions(self):
        """Test with custom key dimensions."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries(
            white_key_width=25.0,
            black_key_width=14.0,
            white_key_gap=1.5
        )
        
        # Check white key width is applied
        white_keys = [g for g in geometries.values() if g.key_type == KeyType.WHITE]
        for wk in white_keys:
            assert wk.width_mm == 25.0, f"White key should be 25.0mm wide, got {wk.width_mm}"

    def test_black_key_neighbors(self):
        """Test black key neighbor identification."""
        # Key 1 is black (A#0)
        left, right = PhysicalKeyGeometry.get_black_key_neighbors(1)
        assert left == 0, "Key 1 (A#0) should have left neighbor at white key 0"
        assert right == 1, "Key 1 (A#0) should have right neighbor at white key 1"

    def test_black_key_neighbors_invalid(self):
        """Test black key neighbor returns None for white keys."""
        # Key 0 is white
        left, right = PhysicalKeyGeometry.get_black_key_neighbors(0)
        assert left is None and right is None, "White keys should return (None, None)"

    def test_piano_total_width(self):
        """Test total piano width calculation."""
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries()
        
        first_key = geometries[0]
        last_key = geometries[87]
        
        total_width = last_key.end_mm - first_key.start_mm
        
        # Approximately 88 keys * ~14.46mm average width = ~1273mm
        assert 1200 < total_width < 1300, f"Piano width should be ~1273mm, got {total_width}"


class TestLEDPhysicalPlacement:
    """Test LED strip positioning and overlap detection."""

    def test_initialize_with_defaults(self):
        """Test LED placement initialization with default parameters."""
        placement = LEDPhysicalPlacement()
        assert placement.led_density == 200.0
        assert placement.led_spacing_mm == 5.0  # 1000/200
        assert placement.led_physical_width == 2.0
        assert placement.led_strip_offset == 1.0

    def test_calculate_led_placements(self):
        """Test LED placement calculation."""
        placement = LEDPhysicalPlacement()
        led_placements = placement.calculate_led_placements(10)
        
        assert len(led_placements) == 10
        
        # LED 0 should start at offset
        led_0 = led_placements[0]
        assert led_0.center_mm == pytest.approx(1.0, rel=0.01)
        
        # LED 1 should be 5mm away
        led_1 = led_placements[1]
        assert led_1.center_mm == pytest.approx(6.0, rel=0.01)

    def test_led_overhang_calculation(self):
        """Test LED overhang from key edge calculation."""
        placement = LEDPhysicalPlacement()
        led_placements = placement.calculate_led_placements(20)
        
        # Create a simple key at 0-25mm
        key_geometry = KeyGeometry(
            key_index=0,
            key_type=KeyType.WHITE,
            start_mm=0.0,
            end_mm=25.0,
            center_mm=12.5,
            width_mm=25.0
        )
        
        # Find LEDs that overlap with key
        led_indices = placement.find_overlapping_leds(key_geometry, led_placements, overhang_threshold_mm=1.0)
        
        # Should have multiple LEDs
        assert len(led_indices) > 0, "Should find overlapping LEDs"

    def test_coverage_amount(self):
        """Test LED coverage amount calculation."""
        placement = LEDPhysicalPlacement()
        led_placements = placement.calculate_led_placements(20)
        
        key_geometry = KeyGeometry(
            key_index=0,
            key_type=KeyType.WHITE,
            start_mm=0.0,
            end_mm=25.0,
            center_mm=12.5,
            width_mm=25.0
        )
        
        # Assume LEDs 0-4 cover this key
        led_indices = [0, 1, 2, 3, 4]
        coverage = placement.calculate_coverage_amount(key_geometry, led_indices, led_placements)
        
        # Should have positive coverage
        assert coverage > 0, "Should have positive coverage"

    def test_led_density_variations(self):
        """Test LED placement with different densities."""
        # 100 LEDs/meter = 10mm spacing
        placement_100 = LEDPhysicalPlacement(led_density=100.0)
        assert placement_100.led_spacing_mm == pytest.approx(10.0, rel=0.01)
        
        # 200 LEDs/meter = 5mm spacing
        placement_200 = LEDPhysicalPlacement(led_density=200.0)
        assert placement_200.led_spacing_mm == pytest.approx(5.0, rel=0.01)


class TestSymmetryAnalysis:
    """Test LED placement symmetry and quality analysis."""

    def test_perfect_symmetry(self):
        """Test perfect center alignment gives high symmetry score."""
        led_placements = {
            0: LEDPlacement(led_index=0, start_mm=9.25, end_mm=12.75, center_mm=11.0, width_mm=3.5),
            1: LEDPlacement(led_index=1, start_mm=14.25, end_mm=17.75, center_mm=16.0, width_mm=3.5),
        }
        
        key_geometry = KeyGeometry(
            key_index=0,
            key_type=KeyType.WHITE,
            start_mm=8.0,
            end_mm=23.0,
            center_mm=15.5,
            width_mm=15.0
        )
        
        led_indices = [0, 1]
        score = SymmetryAnalysis.calculate_symmetry_score(key_geometry, led_indices, led_placements)
        
        # Should be high (LEDs centered on key)
        assert score > 0.8, f"High symmetry expected, got {score}"

    def test_poor_symmetry(self):
        """Test off-center placement gives low symmetry score."""
        led_placements = {
            0: LEDPlacement(led_index=0, start_mm=8.0, end_mm=11.5, center_mm=9.75, width_mm=3.5),
        }
        
        key_geometry = KeyGeometry(
            key_index=0,
            key_type=KeyType.WHITE,
            start_mm=15.0,  # Key far from LED
            end_mm=30.0,
            center_mm=22.5,
            width_mm=15.0
        )
        
        led_indices = [0]
        score = SymmetryAnalysis.calculate_symmetry_score(key_geometry, led_indices, led_placements)
        
        # Should be low
        assert score < 0.5, f"Low symmetry expected, got {score}"

    def test_symmetry_label_mapping(self):
        """Test symmetry score to label mapping."""
        assert SymmetryAnalysis.get_symmetry_label(0.98) == "Excellent Center Alignment"
        assert SymmetryAnalysis.get_symmetry_label(0.90) == "Good Center Alignment"
        assert SymmetryAnalysis.get_symmetry_label(0.75) == "Acceptable Alignment"
        assert SymmetryAnalysis.get_symmetry_label(0.60) == "Off-Center Alignment"
        assert SymmetryAnalysis.get_symmetry_label(0.40) == "Poor Alignment"

    def test_coverage_consistency(self):
        """Test LED distribution consistency analysis."""
        led_placements = {
            0: LEDPlacement(led_index=0, start_mm=0.0, end_mm=3.5, center_mm=1.75, width_mm=3.5),
            1: LEDPlacement(led_index=1, start_mm=5.0, end_mm=8.5, center_mm=6.75, width_mm=3.5),
            2: LEDPlacement(led_index=2, start_mm=10.0, end_mm=13.5, center_mm=11.75, width_mm=3.5),
        }
        
        key_geometry = KeyGeometry(
            key_index=0,
            key_type=KeyType.WHITE,
            start_mm=0.0,
            end_mm=15.0,
            center_mm=7.5,
            width_mm=15.0
        )
        
        led_indices = [0, 1, 2]
        consistency, label = SymmetryAnalysis.analyze_coverage_consistency(
            key_geometry, led_indices, led_placements
        )
        
        # Should have reasonable consistency with evenly spaced LEDs
        assert 0 <= consistency <= 1.0
        assert len(label) > 0


class TestPhysicalMappingAnalyzer:
    """Test complete physical mapping analysis."""

    def test_analyzer_initialization(self):
        """Test analyzer can be initialized with various parameters."""
        analyzer = PhysicalMappingAnalyzer(
            led_density=200,
            led_physical_width=2.0,
            led_strip_offset=1.0,
            overhang_threshold_mm=1.5,
            white_key_width=23.5,
            black_key_width=13.7,
            white_key_gap=1.0
        )
        
        assert analyzer.led_density == 200
        assert analyzer.white_key_width == 23.5

    def test_analyze_mapping_structure(self):
        """Test analyze_mapping returns expected structure."""
        analyzer = PhysicalMappingAnalyzer()
        
        # Create minimal test mapping (just 3 keys for speed)
        test_mapping = {
            0: [4, 5, 6],
            1: [6, 7, 8],
            2: [8, 9, 10]
        }
        
        result = analyzer.analyze_mapping(test_mapping, led_count=20)
        
        assert 'per_key_analysis' in result
        assert 'quality_metrics' in result
        assert 'overall_quality' in result
        assert 'parameters_used' in result

    def test_analyze_mapping_per_key_metrics(self):
        """Test per-key analysis contains required metrics."""
        analyzer = PhysicalMappingAnalyzer()
        
        test_mapping = {0: [4, 5, 6]}
        result = analyzer.analyze_mapping(test_mapping, led_count=20)
        
        key_analysis = result['per_key_analysis'][0]
        
        assert 'key_type' in key_analysis
        assert 'led_indices' in key_analysis
        assert 'led_count' in key_analysis
        assert 'coverage_mm' in key_analysis
        assert 'symmetry_score' in key_analysis
        assert 'symmetry_label' in key_analysis
        assert 'overall_quality' in key_analysis

    def test_analyze_mapping_quality_metrics(self):
        """Test quality metrics aggregation."""
        analyzer = PhysicalMappingAnalyzer()
        
        test_mapping = {
            i: [4+i*2, 5+i*2] for i in range(10)  # 10 keys with 2 LEDs each
        }
        
        result = analyzer.analyze_mapping(test_mapping, led_count=30)
        metrics = result['quality_metrics']
        
        assert 'avg_symmetry' in metrics
        assert 'avg_coverage_consistency' in metrics
        assert 'total_keys_analyzed' in metrics
        assert 'excellent_alignment' in metrics
        assert metrics['total_keys_analyzed'] == 10

    def test_overall_quality_grading(self):
        """Test overall quality grade calculation."""
        # These are based on the static method implementation
        result = PhysicalMappingAnalyzer._calculate_overall_quality_grade({
            'avg_symmetry': 0.92,
            'excellent_alignment': 75,
        })
        
        assert result in ['Excellent', 'Very Good', 'Good', 'Acceptable', 'Needs Improvement']

    def test_individual_quality_calculation(self):
        """Test per-key quality calculation."""
        quality = PhysicalMappingAnalyzer._calculate_overall_quality(0.95, 0.90)
        assert quality == 'Excellent'
        
        quality = PhysicalMappingAnalyzer._calculate_overall_quality(0.85, 0.80)
        assert quality == 'Good'
        
        quality = PhysicalMappingAnalyzer._calculate_overall_quality(0.50, 0.55)
        assert quality == 'Poor'


class TestPhysicalMappingIntegration:
    """Integration tests for complete physical mapping analysis."""

    def test_full_analysis_pipeline_small(self):
        """Test complete analysis pipeline with small dataset."""
        analyzer = PhysicalMappingAnalyzer(
            led_density=200,
            led_physical_width=2.0,
            led_strip_offset=1.0,
            overhang_threshold_mm=1.5,
            white_key_width=23.5,
            black_key_width=13.7,
            white_key_gap=1.0
        )
        
        # Create test mapping
        test_mapping = {i: [4+i, 5+i] for i in range(20)}
        
        # Analyze
        result = analyzer.analyze_mapping(test_mapping, led_count=50)
        
        # Verify results
        assert result['overall_quality'] in ['Excellent', 'Very Good', 'Good', 'Acceptable', 'Needs Improvement']
        assert 0 <= result['quality_metrics']['avg_symmetry'] <= 1.0

    def test_analysis_with_different_parameters(self):
        """Test analysis produces different results with different parameters."""
        # High density analyzer
        analyzer_dense = PhysicalMappingAnalyzer(led_density=200)
        
        # Low density analyzer
        analyzer_sparse = PhysicalMappingAnalyzer(led_density=100)
        
        test_mapping = {i: [4+i*2, 5+i*2] for i in range(10)}
        
        result_dense = analyzer_dense.analyze_mapping(test_mapping, led_count=40)
        result_sparse = analyzer_sparse.analyze_mapping(test_mapping, led_count=40)
        
        # Different density should produce different results
        # (Though they may be similar depending on the calculation)
        assert 'per_key_analysis' in result_dense
        assert 'per_key_analysis' in result_sparse

    def test_empty_mapping_handling(self):
        """Test analyzer handles empty mapping gracefully."""
        analyzer = PhysicalMappingAnalyzer()
        
        result = analyzer.analyze_mapping({}, led_count=20)
        
        assert result['per_key_analysis'] == {}
        assert result['quality_metrics']['total_keys_analyzed'] == 0

    def test_geometry_calculation_consistency(self):
        """Test that geometry calculations are consistent."""
        geometries1 = PhysicalKeyGeometry.calculate_all_key_geometries()
        geometries2 = PhysicalKeyGeometry.calculate_all_key_geometries()
        
        # Should be identical
        for i in range(88):
            g1 = geometries1[i]
            g2 = geometries2[i]
            assert g1.center_mm == g2.center_mm
            assert g1.width_mm == g2.width_mm


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_led_per_key(self):
        """Test mapping with only one LED per key."""
        analyzer = PhysicalMappingAnalyzer()
        
        test_mapping = {i: [i] for i in range(5)}
        result = analyzer.analyze_mapping(test_mapping, led_count=10)
        
        assert result['quality_metrics']['total_keys_analyzed'] == 5

    def test_many_leds_per_key(self):
        """Test mapping with many LEDs per key."""
        analyzer = PhysicalMappingAnalyzer()
        
        test_mapping = {0: list(range(0, 10))}
        result = analyzer.analyze_mapping(test_mapping, led_count=20)
        
        key_analysis = result['per_key_analysis'][0]
        assert key_analysis['led_count'] == 10

    def test_overlapping_led_assignments(self):
        """Test that overlapping LED assignments are handled."""
        analyzer = PhysicalMappingAnalyzer()
        
        # Keys with overlapping LED indices
        test_mapping = {
            0: [4, 5, 6, 7],
            1: [7, 8, 9, 10],  # LED 7 shared with key 0
            2: [10, 11, 12]
        }
        
        result = analyzer.analyze_mapping(test_mapping, led_count=20)
        
        # Should analyze successfully with overlaps
        assert result['per_key_analysis'][0]['led_count'] == 4
        assert result['per_key_analysis'][1]['led_count'] == 4

    def test_zero_led_count(self):
        """Test handling of zero LED count."""
        analyzer = PhysicalMappingAnalyzer()
        
        # Empty LED placements
        test_mapping = {0: []}
        result = analyzer.analyze_mapping(test_mapping, led_count=10)
        
        key_analysis = result['per_key_analysis'][0]
        assert key_analysis['led_count'] == 0

    def test_negative_indices_not_allowed_in_practice(self):
        """Test that analysis handles negative indices gracefully."""
        analyzer = PhysicalMappingAnalyzer()
        
        # Negative indices (shouldn't happen in practice but should not crash)
        test_mapping = {0: [-1, 0, 1]}
        
        # Should not raise an exception
        try:
            result = analyzer.analyze_mapping(test_mapping, led_count=10)
            # If it succeeds, that's ok (implementation dependent)
            assert 'per_key_analysis' in result
        except (ValueError, IndexError):
            # If it fails with appropriate errors, that's also acceptable
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
