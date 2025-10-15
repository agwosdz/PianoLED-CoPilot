import pytest
from unittest.mock import Mock, patch, MagicMock
from usb_midi_service import USBMIDIInputService
from midi_parser import MIDIParser
from playback_service import PlaybackService


class TestMIDIMappingConfiguration:
    """Test cases for MIDI mapping with different piano configurations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_led_controller = Mock()
        self.mock_websocket_callback = Mock()
        self.mock_settings_service = Mock()
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_usb_midi_service_88_key_normal(self, mock_get_specs, mock_get_config):
        """Test USB MIDI service with 88-key piano, normal orientation"""
        # Mock configuration
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '88-key',
            'led_orientation': 'normal'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 88,
            'midi_start': 21,
            'midi_end': 108
        }
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '88-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Verify configuration was loaded correctly
        assert service.num_leds == 246  # Now uses settings service default
        assert service.min_midi_note == 21
        assert service.max_midi_note == 108
        assert service.led_orientation == 'normal'
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_usb_midi_service_61_key_reversed(self, mock_get_specs, mock_get_config):
        """Test USB MIDI service with 61-key piano, reversed orientation"""
        # Mock configuration
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '61-key',
            'led_orientation': 'reversed'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 61,
            'midi_start': 36,
            'midi_end': 96
        }
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '61-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'reversed',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Verify configuration was loaded correctly
        assert service.num_leds == 246  # Now uses settings service default
        assert service.min_midi_note == 36
        assert service.max_midi_note == 96
        assert service.led_orientation == 'reversed'
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_midi_note_to_led_mapping_normal_orientation(self, mock_get_specs, mock_get_config):
        """Test MIDI note to LED mapping with normal orientation"""
        # Mock configuration for 88-key piano
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '88-key',
            'led_orientation': 'normal'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 88,
            'midi_start': 21,
            'midi_end': 108
        }
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '88-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Test mapping for different MIDI notes (with 246 LEDs)
        test_cases = [
            (21, 0),    # Lowest note (A0) -> LED 0
            (65, 123),  # Middle range -> LED 123
            (108, 245), # Highest note (C8) -> LED 245
        ]
        
        for midi_note, expected_led in test_cases:
            led_index = service._map_note_to_led(midi_note)
            assert led_index == expected_led, f"MIDI note {midi_note} should map to LED {expected_led}, got {led_index}"
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_midi_note_to_led_mapping_reversed_orientation(self, mock_get_specs, mock_get_config):
        """Test MIDI note to LED mapping with reversed orientation"""
        # Mock configuration for 88-key piano with reversed orientation
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '88-key',
            'led_orientation': 'reversed'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 88,
            'midi_start': 21,
            'midi_end': 108
        }
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '88-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'reversed',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Test mapping for different MIDI notes (returns logical indices; controller applies orientation)
        test_cases = [
            (21, 0),    # Lowest note (A0) -> logical LED 0
            (65, 123),  # Middle range -> logical LED 123
            (108, 245), # Highest note (C8) -> logical LED 245
        ]
        
        for midi_note, expected_led in test_cases:
            led_index = service._map_note_to_led(midi_note)
            assert led_index == expected_led, f"MIDI note {midi_note} should map to LED {expected_led}, got {led_index}"
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_midi_note_out_of_range(self, mock_get_specs, mock_get_config):
        """Test MIDI note mapping for notes outside piano range"""
        # Mock configuration for 61-key piano
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '61-key',
            'led_orientation': 'normal'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 61,
            'midi_start': 36,
            'midi_end': 96
        }
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '61-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Test notes outside range
        test_cases = [
            (20, None),  # Below minimum
            (35, None),  # Below minimum
            (97, None),  # Above maximum
            (127, None), # Above maximum
        ]
        
        for midi_note, expected_result in test_cases:
            led_index = service._map_note_to_led(midi_note)
            assert led_index == expected_result, f"MIDI note {midi_note} outside range should return None, got {led_index}"

    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_usb_midi_mapping_respects_mapping_led_subset(self, mock_get_specs, mock_get_config):
        """Ensure mapping count can shrink without altering controller capacity."""
        mock_get_specs.return_value = {
            'keys': 88,
            'midi_start': 21,
            'midi_end': 108
        }

        settings_values = {
            ('piano', 'piano_size'): '88-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }

        def get_setting(category, key, default=None):
            return settings_values.get((category, key), default)

        # Maintain controller capacity larger than mapping
        self.mock_led_controller.num_pixels = 300
        self.mock_led_controller.led_orientation = 'normal'

        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '88-key',
            'led_orientation': 'normal'
        }.get(key, default)

        self.mock_settings_service.get_setting.side_effect = get_setting

        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)

        assert service.num_leds == 246
        assert service._controller_led_capacity == 300

        # Shrink mapping count and ensure it updates without changing controller capacity
        settings_values[('led', 'led_count')] = 120
        service.refresh_runtime_settings()
        assert service.num_leds == 120
        assert service._controller_led_capacity == 300
        top_leds = service._map_note_to_leds(service.max_midi_note)
        assert top_leds and max(top_leds) < 120

        # Request more LEDs than hardware supports -> expect clamp to controller capacity
        settings_values[('led', 'led_count')] = 512
        service.refresh_runtime_settings()
        assert service.num_leds == 300
        assert service._controller_led_capacity == 300
        top_leds = service._map_note_to_leds(service.max_midi_note)
        assert top_leds and max(top_leds) == 299
    
    @patch('midi_parser.get_piano_specs')
    def test_midi_parser_configuration(self, mock_get_specs):
        """Test MIDI parser uses correct piano configuration"""
        mock_get_specs.return_value = {
            'keys': 76,
            'midi_start': 28,
            'midi_end': 103
        }
        
        # Mock settings service for MIDI parser
        mock_settings = Mock()
        mock_settings.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'size'): '76-key',
            ('led', 'led_count'): 246
        }.get((category, key), default)
        
        with patch('midi_parser.get_config', return_value='76-key'):
            parser = MIDIParser(settings_service=mock_settings)
            
            # Verify parser loaded correct configuration
            assert parser.led_count == 246  # Now uses settings service
            # When settings_service is provided, it uses internal _get_piano_specs, not the global one
            mock_get_specs.assert_not_called()
    
    @patch('playback_service.get_config')
    @patch('playback_service.get_piano_specs')
    def test_playback_service_configuration(self, mock_get_specs, mock_get_config):
        """Test playback service uses correct piano configuration"""
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '49-key',
            'led_orientation': 'reversed'
        }.get(key, default)
        
        mock_get_specs.return_value = {
            'keys': 49,
            'midi_start': 36,
            'midi_end': 84
        }
        
        # Mock settings service for playback service
        mock_settings = Mock()
        mock_settings.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'size'): '49-key',  # Note: using 'size' not 'piano_size'
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'reversed'
        }.get((category, key), default)
        
        service = PlaybackService(self.mock_led_controller, settings_service=mock_settings)
        
        # Verify service loaded correct configuration
        assert service.num_leds == 246  # Now uses settings service
        assert service.min_midi_note == 36
        assert service.max_midi_note == 84
        assert service.led_orientation == 'reversed'


class TestPianoSizeVariations:
    """Test cases for different piano size configurations"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_led_controller = Mock()
        self.mock_websocket_callback = Mock()
        self.mock_settings_service = Mock()
    
    @pytest.mark.parametrize("piano_size,expected_specs", [
        ("25-key", {"keys": 25, "midi_start": 60, "midi_end": 84}),
        ("37-key", {"keys": 37, "midi_start": 48, "midi_end": 84}),
        ("49-key", {"keys": 49, "midi_start": 36, "midi_end": 84}),
        ("61-key", {"keys": 61, "midi_start": 36, "midi_end": 96}),
        ("76-key", {"keys": 76, "midi_start": 28, "midi_end": 103}),
        ("88-key", {"keys": 88, "midi_start": 21, "midi_end": 108}),
    ])
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_all_piano_sizes(self, mock_get_specs, mock_get_config, piano_size, expected_specs):
        """Test USB MIDI service with all supported piano sizes"""
        # Mock configuration
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': piano_size,
            'led_orientation': 'normal'
        }.get(key, default)
        
        mock_get_specs.return_value = expected_specs
        
        # Mock settings service
        self.mock_settings_service.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): piano_size,
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        service = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, self.mock_settings_service)
        
        # Verify configuration was loaded correctly
        assert service.num_leds == 246  # Now uses settings service default
        assert service.min_midi_note == expected_specs['midi_start']
        assert service.max_midi_note == expected_specs['midi_end']
        
        # Test that first and last notes map correctly (with 246 LEDs)
        first_led = service._map_note_to_led(expected_specs['midi_start'])
        last_led = service._map_note_to_led(expected_specs['midi_end'])
        
        assert first_led == 0
        assert last_led == 245  # 246 - 1


class TestLEDOrientationMapping:
    """Test cases for LED orientation mapping"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_led_controller = Mock()
        self.mock_websocket_callback = Mock()
        self.mock_settings_service = Mock()
    
    @patch('usb_midi_service.get_config')
    @patch('usb_midi_service.get_piano_specs')
    def test_orientation_mapping_consistency(self, mock_get_specs, mock_get_config):
        """Test that orientation mapping is consistent across the range"""
        # Test with 61-key piano
        mock_get_specs.return_value = {
            'keys': 61,
            'midi_start': 36,
            'midi_end': 96
        }
        
        # Mock settings service for normal orientation
        mock_settings_normal = Mock()
        mock_settings_normal.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '61-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'normal',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        # Test normal orientation
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '61-key',
            'led_orientation': 'normal'
        }.get(key, default)
        
        service_normal = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, mock_settings_normal)
        
        # Mock settings service for reversed orientation
        mock_settings_reversed = Mock()
        mock_settings_reversed.get_setting.side_effect = lambda category, key, default=None: {
            ('piano', 'piano_size'): '61-key',
            ('led', 'led_count'): 246,
            ('led', 'led_orientation'): 'reversed',
            ('led', 'mapping_mode'): 'auto',
            ('led', 'leds_per_key'): 3,
            ('led', 'mapping_base_offset'): 0,
            ('led', 'key_mapping'): {}
        }.get((category, key), default)
        
        # Test reversed orientation
        mock_get_config.side_effect = lambda key, default=None: {
            'piano_size': '61-key',
            'led_orientation': 'reversed'
        }.get(key, default)
        
        service_reversed = USBMIDIInputService(self.mock_led_controller, self.mock_websocket_callback, mock_settings_reversed)
        
        # Test that mappings are exact opposites
        for midi_note in range(36, 97):  # All notes in range
            normal_led = service_normal._map_note_to_led(midi_note)
            reversed_led = service_reversed._map_note_to_led(midi_note)
            
            if normal_led is not None and reversed_led is not None:
                # Mapping returns logical indices regardless of orientation; hardware layer handles inversion
                assert normal_led == reversed_led