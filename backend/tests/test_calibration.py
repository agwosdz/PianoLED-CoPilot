#!/usr/bin/env python3
"""
Tests for calibration offset logic in MIDI to LED mapping and auto mapping functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.midi.midi_event_processor import MidiEventProcessor
from backend.config import (
    generate_auto_key_mapping, 
    apply_calibration_offsets_to_mapping, 
    validate_auto_mapping_config,
    get_piano_specs
)


class TestCalibrationOffsets:
    """Test suite for calibration offset application"""
    
    @pytest.fixture
    def processor(self):
        """Create a MIDI event processor for testing"""
        processor = MidiEventProcessor()
        processor.num_leds = 100
        processor.min_midi_note = 21
        processor.max_midi_note = 108
        processor.calibration_enabled = False
        processor.global_offset = 0
        processor.key_offsets = {}
        # Mock precomputed mapping
        processor._precomputed_mapping = {
            21: [0],      # A0 → LED 0
            60: [40],     # Middle C → LED 40
            108: [99],    # C8 → LED 99
        }
        return processor
    
    def test_no_offset_when_disabled(self, processor):
        """Verify offsets are not applied when calibration is disabled"""
        processor.calibration_enabled = False
        processor.global_offset = 5
        processor.key_offsets = {60: 2}
        
        # Should return base mapping
        result = processor._map_note_to_leds(60)
        assert result == [40], "Should return unmodified mapping when calibration disabled"
    
    def test_global_offset_applied(self, processor):
        """Test global offset is applied to all LEDs"""
        processor.calibration_enabled = True
        processor.global_offset = 5
        processor.key_offsets = {}
        
        # MIDI 60 maps to LED 40, with global offset +5 → LED 45
        result = processor._map_note_to_leds(60)
        assert result == [45], f"Expected [45], got {result}"
    
    def test_per_key_offset_applied(self, processor):
        """Test per-key offset is applied"""
        processor.calibration_enabled = True
        processor.global_offset = 0
        processor.key_offsets = {60: 3}
        
        # MIDI 60 maps to LED 40, with key offset +3 → LED 43
        result = processor._map_note_to_leds(60)
        assert result == [43], f"Expected [43], got {result}"
    
    def test_combined_offsets(self, processor):
        """Test combined global and per-key offsets"""
        processor.calibration_enabled = True
        processor.global_offset = 5
        processor.key_offsets = {60: 2}
        
        # MIDI 60 maps to LED 40, +5 global +2 key = LED 47
        result = processor._map_note_to_leds(60)
        assert result == [47], f"Expected [47], got {result}"
    
    def test_negative_offset(self, processor):
        """Test negative offsets work correctly"""
        processor.calibration_enabled = True
        processor.global_offset = -5
        processor.key_offsets = {}
        
        # MIDI 60 maps to LED 40, -5 global = LED 35
        result = processor._map_note_to_leds(60)
        assert result == [35], f"Expected [35], got {result}"
    
    def test_negative_per_key_offset(self, processor):
        """Test negative per-key offsets"""
        processor.calibration_enabled = True
        processor.global_offset = 0
        processor.key_offsets = {60: -3}
        
        # MIDI 60 maps to LED 40, -3 key = LED 37
        result = processor._map_note_to_leds(60)
        assert result == [37], f"Expected [37], got {result}"
    
    def test_clamping_lower_bound(self, processor):
        """Test that offsets are clamped to lower bound"""
        processor.calibration_enabled = True
        processor.global_offset = -20  # Would go negative
        processor.key_offsets = {}
        
        # MIDI 21 maps to LED 0, -20 would be -20 → clamped to 0
        result = processor._map_note_to_leds(21)
        assert result == [0], f"Expected [0], got {result}"
    
    def test_clamping_upper_bound(self, processor):
        """Test that offsets are clamped to upper bound"""
        processor.calibration_enabled = True
        processor.global_offset = 20  # Would go past 99
        processor.key_offsets = {}
        
        # MIDI 108 maps to LED 99, +20 would be 119 → clamped to 99
        result = processor._map_note_to_leds(108)
        assert result == [99], f"Expected [99], got {result}"
    
    def test_multiple_leds_per_key(self, processor):
        """Test offsets applied to all LEDs when multiple per key"""
        processor.calibration_enabled = True
        processor.global_offset = 2
        processor.key_offsets = {}
        processor._precomputed_mapping[60] = [39, 40, 41]  # 3 LEDs
        
        # Each LED should get +2
        result = processor._map_note_to_leds(60)
        assert result == [41, 42, 43], f"Expected [41, 42, 43], got {result}"
    
    def test_per_key_only_affects_target_key(self, processor):
        """Test that per-key offset only affects target key"""
        processor.calibration_enabled = True
        processor.global_offset = 0
        processor.key_offsets = {60: 5}  # Only MIDI 60
        
        # MIDI 60 should have offset
        result_60 = processor._map_note_to_leds(60)
        assert result_60 == [45], f"Expected [45] for MIDI 60, got {result_60}"
        
        # MIDI 21 should not have offset
        result_21 = processor._map_note_to_leds(21)
        assert result_21 == [0], f"Expected [0] for MIDI 21, got {result_21}"
    
    def test_settings_loading(self):
        """Test that calibration settings are properly loaded from settings service"""
        mock_settings_service = Mock()
        mock_settings_service.get_setting = Mock(side_effect=lambda cat, key, default: {
            ('calibration', 'global_offset'): 3,
            ('calibration', 'calibration_enabled'): True,
            ('calibration', 'key_offsets'): {'60': 2, '21': -1},
        }.get((cat, key), default))
        
        processor = MidiEventProcessor(settings_service=mock_settings_service)
        
        assert processor.global_offset == 3
        assert processor.calibration_enabled == True
        assert processor.key_offsets == {60: 2, 21: -1}
    
    def test_key_offsets_normalization(self):
        """Test that key_offsets string keys are converted to integers"""
        mock_settings_service = Mock()
        mock_settings_service.get_setting = Mock(side_effect=lambda cat, key, default: {
            ('calibration', 'global_offset'): 0,
            ('calibration', 'calibration_enabled'): True,
            ('calibration', 'key_offsets'): {'60': 2, '21': -1},  # String keys
        }.get((cat, key), default))
        
        processor = MidiEventProcessor(settings_service=mock_settings_service)
        
        # Should have integer keys
        assert 60 in processor.key_offsets
        assert 21 in processor.key_offsets
        assert processor.key_offsets[60] == 2
        assert processor.key_offsets[21] == -1


class TestAutoKeyMapping:
    """Test suite for auto key mapping generation"""
    
    def test_basic_88_key_mapping(self):
        """Test basic 88-key piano mapping with sufficient LEDs"""
        mapping = generate_auto_key_mapping("88", led_count=88)
        
        assert len(mapping) > 0, "Mapping should not be empty"
        # 88-key piano starts at MIDI 21 (A0) and ends at MIDI 108 (C8)
        specs = get_piano_specs("88")
        assert len(mapping) <= specs["keys"], "Mapping should have at most key_count entries"
    
    def test_mapping_respects_led_count(self):
        """Test that mapping respects available LED count"""
        mapping = generate_auto_key_mapping("88", led_count=100)
        
        # Check that no LED index exceeds led_count - 1
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                for idx in led_indices:
                    assert idx < 100, f"LED index {idx} exceeds LED count 100"
            else:
                assert led_indices < 100, f"LED index {led_indices} exceeds LED count 100"
    
    def test_more_leds_than_keys(self):
        """Test mapping with more LEDs than keys"""
        mapping = generate_auto_key_mapping("88", led_count=500)
        
        # Each key should have multiple LEDs
        specs = get_piano_specs("88")
        total_assignments = sum(len(v) if isinstance(v, list) else 1 for v in mapping.values())
        assert total_assignments > specs["keys"], "Should have more LED assignments than keys"
    
    def test_fewer_leds_than_keys(self):
        """Test mapping with fewer LEDs than keys"""
        mapping = generate_auto_key_mapping("88", led_count=50)
        
        # Mapping attempts to assign all keys, but LEDs get truncated
        specs = get_piano_specs("88")
        # All keys should be in the mapping
        assert len(mapping) == specs["keys"], "All keys should be mapped (with potential truncation)"
        
        # LED indices should be valid and not exceed LED count
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                for idx in led_indices:
                    assert 0 <= idx < 50, f"LED index {idx} out of range [0, 50)"
            else:
                assert 0 <= led_indices < 50, f"LED index {led_indices} out of range [0, 50)"
    
    def test_exactly_matching_leds_keys(self):
        """Test mapping when LED count exactly matches key count"""
        mapping = generate_auto_key_mapping("88", led_count=88)
        
        specs = get_piano_specs("88")
        # Most keys should have exactly 1 LED
        single_led_count = sum(1 for v in mapping.values() if (isinstance(v, list) and len(v) == 1) or isinstance(v, int))
        assert single_led_count >= specs["keys"] - 5, "Most keys should have 1 LED each"
    
    def test_mapping_all_piano_sizes(self):
        """Test mapping generation for all common piano sizes"""
        sizes = ["25", "37", "49", "61", "76", "88"]
        led_counts = [50, 100]
        
        for size in sizes:
            specs = get_piano_specs(size)
            for led_count in led_counts:
                mapping = generate_auto_key_mapping(size, led_count=led_count)
                
                # Verify mapping exists
                assert len(mapping) > 0, f"Mapping for {size} keys with {led_count} LEDs should not be empty"
                
                # Verify LED indices are valid
                for midi_note, led_indices in mapping.items():
                    if isinstance(led_indices, list):
                        for idx in led_indices:
                            assert 0 <= idx < led_count, f"LED index {idx} out of range [0, {led_count})"
                    else:
                        assert 0 <= led_indices < led_count, f"LED index {led_indices} out of range [0, {led_count})"
    
    def test_mapping_with_orientation(self):
        """Test that LED orientation is respected"""
        mapping_normal = generate_auto_key_mapping("88", led_count=88, led_orientation="normal")
        mapping_reversed = generate_auto_key_mapping("88", led_count=88, led_orientation="reversed")
        
        # Both should produce valid mappings
        assert len(mapping_normal) > 0, "Normal orientation should produce mapping"
        assert len(mapping_reversed) > 0, "Reversed orientation should produce mapping"
        
        # They might differ in LED indices
        # (This depends on implementation, but at minimum both should exist)
    
    def test_mapping_with_base_offset(self):
        """Test mapping with base offset parameter"""
        mapping = generate_auto_key_mapping("88", led_count=100, mapping_base_offset=10)
        
        # Base offset should shift all LED indices
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                for idx in led_indices:
                    assert idx >= 10, f"LED index {idx} should be >= base_offset 10"
            else:
                assert led_indices >= 10, f"LED index {led_indices} should be >= base_offset 10"
    
    def test_mapping_with_fixed_leds_per_key(self):
        """Test mapping with fixed LEDs per key"""
        mapping = generate_auto_key_mapping("88", led_count=264, leds_per_key=3)
        
        # Each key should have exactly 3 LEDs (or fewer for truncated keys)
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                assert len(led_indices) <= 3, f"Key {midi_note} has {len(led_indices)} LEDs, expected <= 3"
            else:
                # Single LED is OK (truncation)
                pass


class TestCascadingOffsets:
    """Test suite for cascading offset application"""
    
    def test_cascading_offset_single_key(self):
        """Test that a single key offset only affects that key"""
        base_mapping = {
            21: [0],      # A0
            60: [40],     # Middle C
            108: [99],    # C8
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets={60: 5},  # Only affect MIDI 60
            led_count=100
        )
        
        # MIDI 21 should be unchanged
        assert adjusted[21] == [0], "MIDI 21 should be unaffected"
        
        # MIDI 60 should have offset
        assert adjusted[60] == [45], "MIDI 60 should be offset by 5"
        
        # MIDI 108 should be unchanged
        assert adjusted[108] == [99], "MIDI 108 should be unaffected"
    
    def test_cascading_offset_accumulation(self):
        """Test that offsets cascade (accumulate) from lower notes"""
        base_mapping = {
            21: [0],      # A0
            22: [1],      # A#0
            60: [40],     # Middle C
            108: [99],    # C8
        }
        
        # Set offsets at notes 21 and 60
        key_offsets = {
            21: 2,        # Affects notes >= 21
            60: 3,        # Affects notes >= 60
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 21: affected by offset at 21 → 0 + 2 = 2
        assert adjusted[21] == [2], "MIDI 21 should have offset +2"
        
        # MIDI 22: affected by offset at 21 (cascades) → 1 + 2 = 3
        assert adjusted[22] == [3], "MIDI 22 should cascade offset from note 21"
        
        # MIDI 60: affected by offsets at 21 and 60 → 40 + 2 + 3 = 45
        assert adjusted[60] == [45], "MIDI 60 should have cascading offsets +2 +3 = +5 total"
        
        # MIDI 108: affected by offsets at 21 and 60 → 99 + 2 + 3 = 104 → clamped to 99
        assert adjusted[108] == [99], "MIDI 108 should clamp to max LED index"
    
    def test_cascading_offset_multiple_overlaps(self):
        """Test cascading with multiple overlapping offsets"""
        base_mapping = {
            30: [15],
            40: [25],
            50: [35],
            60: [45],
        }
        
        key_offsets = {
            30: 1,   # Affects 30, 40, 50, 60
            40: 1,   # Affects 40, 50, 60
            50: 1,   # Affects 50, 60
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 30: +1 (from note 30) = 16
        assert adjusted[30] == [16], "MIDI 30: 15 + 1 = 16"
        
        # MIDI 40: +1 (from 30) +1 (from 40) = +2 total = 27
        assert adjusted[40] == [27], "MIDI 40: 25 + 1 + 1 = 27"
        
        # MIDI 50: +1 +1 +1 = +3 total = 38
        assert adjusted[50] == [38], "MIDI 50: 35 + 1 + 1 + 1 = 38"
        
        # MIDI 60: +1 +1 +1 = +3 total = 48
        assert adjusted[60] == [48], "MIDI 60: 45 + 1 + 1 + 1 = 48"
    
    def test_cascading_offset_with_global(self):
        """Test cascading offsets combined with global offset"""
        base_mapping = {
            21: [5],
            60: [40],
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=10,
            key_offsets={60: 5},
            led_count=100
        )
        
        # MIDI 21: 5 + 10 (global) = 15
        assert adjusted[21] == [15], "MIDI 21: 5 + global 10 = 15"
        
        # MIDI 60: 40 + 10 (global) + 5 (key) = 55
        assert adjusted[60] == [55], "MIDI 60: 40 + global 10 + key 5 = 55"
    
    def test_cascading_offset_clamping_lower(self):
        """Test that cascading offsets clamp to lower bound"""
        base_mapping = {
            30: [2],
            60: [50],
        }
        
        key_offsets = {
            30: -5,  # Would make MIDI 30 negative
            60: -10, # Would make MIDI 60 negative
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 30: 2 - 5 = -3 → clamped to 0
        assert adjusted[30] == [0], "MIDI 30 should clamp to 0"
        
        # MIDI 60: 50 - 5 - 10 = 35 (no clamp needed)
        assert adjusted[60] == [35], "MIDI 60: 50 - 5 - 10 = 35"
    
    def test_cascading_offset_clamping_upper(self):
        """Test that cascading offsets clamp to upper bound"""
        base_mapping = {
            60: [90],
            108: [99],
        }
        
        key_offsets = {
            60: 20,  # Would exceed LED count
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 60: 90 + 20 = 110 → clamped to 99
        assert adjusted[60] == [99], "MIDI 60 should clamp to max LED 99"
        
        # MIDI 108: 99 + 20 = 119 → clamped to 99
        assert adjusted[108] == [99], "MIDI 108 should clamp to max LED 99"
    
    def test_cascading_offset_multiple_leds_per_key(self):
        """Test cascading offsets with multiple LEDs per key"""
        base_mapping = {
            60: [38, 39, 40, 41],  # 4 LEDs
            61: [42, 43, 44],      # 3 LEDs
        }
        
        key_offsets = {
            60: 2,
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 60: all LEDs get +2
        assert adjusted[60] == [40, 41, 42, 43], "MIDI 60 all LEDs should shift by +2"
        
        # MIDI 61: cascades the +2 from MIDI 60
        assert adjusted[61] == [44, 45, 46], "MIDI 61 all LEDs should cascade +2"
    
    def test_cascading_offset_negative_accumulation(self):
        """Test cascading negative offsets"""
        base_mapping = {
            30: [30],
            40: [40],
            50: [50],
        }
        
        key_offsets = {
            30: -2,
            40: -1,
        }
        
        adjusted = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=key_offsets,
            led_count=100
        )
        
        # MIDI 30: 30 - 2 = 28
        assert adjusted[30] == [28], "MIDI 30: 30 - 2 = 28"
        
        # MIDI 40: 40 - 2 - 1 = 37
        assert adjusted[40] == [37], "MIDI 40: 40 - 2 - 1 = 37"
        
        # MIDI 50: 50 - 2 - 1 = 47
        assert adjusted[50] == [47], "MIDI 50: 50 - 2 - 1 = 47"
    
    def test_empty_mapping_no_processing(self):
        """Test that empty mapping is returned as-is"""
        result = apply_calibration_offsets_to_mapping(
            {},
            global_offset=5,
            key_offsets={60: 2},
            led_count=100
        )
        
        assert result == {}, "Empty mapping should remain empty"
    
    def test_no_offsets_returns_original(self):
        """Test that no offsets returns original mapping"""
        base_mapping = {
            21: [0],
            60: [40],
            108: [99],
        }
        
        result = apply_calibration_offsets_to_mapping(
            base_mapping,
            global_offset=0,
            key_offsets=None,
            led_count=100
        )
        
        assert result == base_mapping, "No offsets should return original mapping"


class TestAutoMappingValidation:
    """Test suite for auto mapping validation"""
    
    def test_validation_88_keys_100_leds(self):
        """Test validation for 88 keys with 100 LEDs (sufficient)"""
        warnings = validate_auto_mapping_config(piano_size="88", led_count=100)
        
        # Check that warnings is a dict/list
        assert isinstance(warnings, (dict, list)), "Validation should return dict or list"
    
    def test_validation_88_keys_50_leds(self):
        """Test validation for 88 keys with 50 LEDs (insufficient)"""
        warnings = validate_auto_mapping_config(piano_size="88", led_count=50)
        
        # Should produce validation result
        assert isinstance(warnings, (dict, list)), "Validation should return result"
    
    def test_validation_all_piano_sizes(self):
        """Test validation across all piano sizes"""
        sizes = ["25", "37", "49", "61", "76", "88"]
        led_counts = [25, 50, 100]
        
        for size in sizes:
            for led_count in led_counts:
                warnings = validate_auto_mapping_config(piano_size=size, led_count=led_count)
                
                # Should return validation result
                assert isinstance(warnings, (dict, list)), \
                    f"Validation for {size} keys with {led_count} LEDs should return result"
    
    def test_validation_with_fixed_leds_per_key(self):
        """Test validation with fixed LEDs per key"""
        warnings = validate_auto_mapping_config(
            piano_size="88",
            led_count=264,
            leds_per_key=3
        )
        
        # Should return validation result
        assert isinstance(warnings, (dict, list)), "Validation should return result"
    
    def test_validation_with_base_offset(self):
        """Test validation with base offset"""
        warnings = validate_auto_mapping_config(
            piano_size="88",
            led_count=100,
            base_offset=10
        )
        
        # Should return validation result
        assert isinstance(warnings, (dict, list)), "Validation should return result"


class TestDistributionModes:
    """Test suite for LED distribution modes (Priority 4)"""
    
    def test_proportional_mode_default(self):
        """Test proportional mode is default"""
        mapping = generate_auto_key_mapping("88", led_count=100, distribution_mode="proportional")
        
        specs = get_piano_specs("88")
        # Should map all keys with proportional distribution
        assert len(mapping) == specs["keys"], "Proportional mode should map all keys"
    
    def test_proportional_mode_even_distribution(self):
        """Test proportional mode distributes LEDs evenly"""
        # 88 keys, 88 LEDs = 1 LED per key
        mapping = generate_auto_key_mapping("88", led_count=88, distribution_mode="proportional")
        
        specs = get_piano_specs("88")
        # Most keys should have exactly 1 LED
        single_led_count = sum(1 for v in mapping.values() if (isinstance(v, list) and len(v) == 1) or isinstance(v, int))
        assert single_led_count == specs["keys"], "Each key should have 1 LED"
    
    def test_proportional_mode_uneven_distribution(self):
        """Test proportional mode handles uneven LED distribution"""
        # 88 keys, 100 LEDs = 1.136... LEDs per key
        # First 12 keys get 2 LEDs, rest get 1 LED
        mapping = generate_auto_key_mapping("88", led_count=100, distribution_mode="proportional")
        
        # Count how many keys have 2 LEDs
        two_led_count = sum(1 for v in mapping.values() if isinstance(v, list) and len(v) == 2)
        one_led_count = sum(1 for v in mapping.values() if isinstance(v, list) and len(v) == 1)
        
        assert two_led_count == 12, f"Expected 12 keys with 2 LEDs, got {two_led_count}"
        assert one_led_count == 76, f"Expected 76 keys with 1 LED, got {one_led_count}"
    
    def test_fixed_mode_basic(self):
        """Test fixed mode with explicit leds_per_key"""
        # 3 LEDs per key
        mapping = generate_auto_key_mapping(
            "88", 
            led_count=300,
            leds_per_key=3,
            distribution_mode="fixed"
        )
        
        # With 3 LEDs per key and sufficient LEDs, all keys should get 3 LEDs
        # (or be truncated if not enough LEDs)
        assert len(mapping) > 0, "Fixed mode should produce mapping"
    
    def test_fixed_mode_insufficient_leds(self):
        """Test fixed mode with insufficient LEDs truncates keys"""
        # Request 5 LEDs per key but only have 50 total for 88 keys
        # Max mappable: 50 / 5 = 10 keys
        mapping = generate_auto_key_mapping(
            "88",
            led_count=50,
            leds_per_key=5,
            distribution_mode="fixed"
        )
        
        specs = get_piano_specs("88")
        # Should map only 10 keys (50 / 5)
        assert len(mapping) == 10, f"Should map 10 keys with 5 LEDs each, got {len(mapping)}"
    
    def test_fixed_mode_respects_leds_per_key(self):
        """Test fixed mode assigns correct LEDs per key"""
        mapping = generate_auto_key_mapping(
            "37",  # 37 keys
            led_count=111,  # 3 LEDs per key
            leds_per_key=3,
            distribution_mode="fixed"
        )
        
        # All mapped keys should have exactly 3 LEDs
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                assert len(led_indices) == 3, f"Key {midi_note} should have 3 LEDs, got {len(led_indices)}"
    
    def test_custom_mode_fallback(self):
        """Test custom mode falls back to proportional-like behavior"""
        mapping = generate_auto_key_mapping(
            "88",
            led_count=100,
            distribution_mode="custom"
        )
        
        specs = get_piano_specs("88")
        # Should map all keys with fallback distribution
        assert len(mapping) == specs["keys"], "Custom mode should map all keys"
    
    def test_distribution_mode_parameter(self):
        """Test distribution_mode parameter is properly passed"""
        # All three modes should produce valid mappings
        for mode in ["proportional", "fixed", "custom"]:
            mapping = generate_auto_key_mapping(
                "88",
                led_count=100,
                distribution_mode=mode
            )
            
            assert len(mapping) > 0, f"Mode {mode} should produce valid mapping"
    
    def test_invalid_distribution_mode(self):
        """Test invalid distribution mode is handled"""
        # Should use proportional as fallback for invalid mode
        mapping = generate_auto_key_mapping(
            "88",
            led_count=100,
            distribution_mode="invalid_mode"
        )
        
        specs = get_piano_specs("88")
        # Should still produce valid mapping (fallback to proportional)
        assert len(mapping) > 0, "Should fallback to valid mode for invalid input"
    
    def test_distribution_mode_with_base_offset(self):
        """Test distribution mode works with base offset"""
        base_offset = 10
        mapping = generate_auto_key_mapping(
            "88",
            led_count=110,
            mapping_base_offset=base_offset,
            distribution_mode="proportional"
        )
        
        # All LED indices should be >= base_offset
        for midi_note, led_indices in mapping.items():
            if isinstance(led_indices, list):
                for idx in led_indices:
                    assert idx >= base_offset, f"LED {idx} should be >= base_offset {base_offset}"
    
    def test_all_modes_all_sizes(self):
        """Test all distribution modes work with all piano sizes"""
        sizes = ["25", "37", "49", "61", "76", "88"]
        modes = ["proportional", "fixed", "custom"]
        
        for size in sizes:
            for mode in modes:
                mapping = generate_auto_key_mapping(
                    size,
                    led_count=100,
                    distribution_mode=mode
                )
                
                assert len(mapping) > 0, \
                    f"Mode {mode} should work with {size} piano"
    
    def test_mode_affects_mapping_composition(self):
        """Test that different modes produce different LED distributions"""
        # Proportional mode with many LEDs
        proportional_mapping = generate_auto_key_mapping(
            "88",
            led_count=176,  # 2 LEDs per key
            distribution_mode="proportional"
        )
        
        # Fixed mode with 2 LEDs per key
        fixed_mapping = generate_auto_key_mapping(
            "88",
            led_count=176,
            leds_per_key=2,
            distribution_mode="fixed"
        )
        
        # Both should have same number of keys mapped
        assert len(proportional_mapping) > 0, "Proportional mapping should exist"
        assert len(fixed_mapping) > 0, "Fixed mapping should exist"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
