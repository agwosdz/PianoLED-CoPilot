#!/usr/bin/env python3
"""
Tests for calibration offset logic in MIDI to LED mapping
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.midi.midi_event_processor import MidiEventProcessor


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
