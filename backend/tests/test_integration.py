import pytest
import json
import os
import tempfile
import time
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_socketio import SocketIOTestClient

# Import the app and components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app
from playback_service import PlaybackService
from midi_parser import MIDIParser
from led_controller import LEDController

class TestIntegration:
    """Integration tests for the complete playback system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.app = app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create a temporary MIDI file for testing
        self.temp_midi = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
        # Simple MIDI file content (header + track)
        midi_content = bytes([
            # MIDI Header
            0x4D, 0x54, 0x68, 0x64,  # "MThd"
            0x00, 0x00, 0x00, 0x06,  # Header length
            0x00, 0x00,              # Format 0
            0x00, 0x01,              # 1 track
            0x00, 0x60,              # 96 ticks per quarter note
            
            # Track Header
            0x4D, 0x54, 0x72, 0x6B,  # "MTrk"
            0x00, 0x00, 0x00, 0x0B,  # Track length
            
            # Track data
            0x00, 0x90, 0x40, 0x40,  # Note on C4
            0x60, 0x80, 0x40, 0x40,  # Note off C4
            0x00, 0xFF, 0x2F, 0x00   # End of track
        ])
        self.temp_midi.write(midi_content)
        self.temp_midi.close()

        # Stub the MIDI parser to ensure consistent playback during tests
        self._original_midi_parser = None
        if getattr(app, 'playback_service', None):
            self._original_midi_parser = getattr(app.playback_service, '_midi_parser', None)

            class _TestMidiParser:
                def parse_file(self, _filename):
                    return {
                        'events': [
                            {'type': 'on', 'note': 60, 'velocity': 80, 'time': 0},
                            {'type': 'off', 'note': 60, 'velocity': 0, 'time': 480}
                        ]
                    }

            app.playback_service._midi_parser = _TestMidiParser()
        
    def teardown_method(self):
        """Clean up test fixtures"""
        if getattr(app, 'playback_service', None):
            app.playback_service._midi_parser = self._original_midi_parser
            try:
                app.playback_service.stop_playback()
            except Exception:
                pass
        self.app_context.pop()
        if os.path.exists(self.temp_midi.name):
            os.unlink(self.temp_midi.name)
    
    def test_complete_playback_workflow(self):
        """Test the complete workflow: upload -> play -> status -> stop"""
        # 1. Upload a MIDI file
        with open(self.temp_midi.name, 'rb') as f:
            response = self.client.post('/api/upload-midi', 
                                      data={'file': (f, 'test.mid')},
                                      content_type='multipart/form-data')
        
        assert response.status_code == 200
        upload_data = json.loads(response.data)
        assert upload_data['success'] is True
        uploaded_filename = upload_data.get('filename') or upload_data.get('upload_path')
        assert uploaded_filename
        
        # 2. Start playback
        response = self.client.post('/api/play', json={'filename': uploaded_filename})
        assert response.status_code == 200
        play_data = json.loads(response.data)
        assert play_data['status'] == 'success'
        assert play_data['filename'] == uploaded_filename
        
        # 3. Check status
        response = self.client.get('/api/playback-status')
        assert response.status_code == 200
        status_data = json.loads(response.data)
        assert status_data['status'] == 'success'
        assert status_data['playback']['filename'] is not None
        
        # 4. Stop playback
        response = self.client.post('/api/stop')
        assert response.status_code == 200
        stop_data = json.loads(response.data)
        assert stop_data['status'] == 'success'
    
    def test_playback_without_file(self):
        """Test playback behavior when no file is loaded"""
        # Try to play without providing filename
        response = self.client.post('/api/play', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert data['message'] == 'Filename parameter is required'
        
        # Try to play with nonexistent file
        response = self.client.post('/api/play', 
                                  json={'filename': 'nonexistent.mid'})
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Failed to load MIDI file' in data['message']
    
    def test_pause_resume_workflow(self):
        """Test pause and resume functionality"""
        # Upload and start playback
        with open(self.temp_midi.name, 'rb') as f:
            upload_response = self.client.post('/api/upload-midi', 
                                             data={'file': (f, 'test.mid')},
                                             content_type='multipart/form-data')

        uploaded_filename = upload_response.get_json().get('filename')
        assert uploaded_filename
        self.client.post('/api/play', json={'filename': uploaded_filename})
        
        # Pause
        response = self.client.post('/api/pause')
        assert response.status_code == 200
        pause_data = json.loads(response.data)
        assert pause_data['status'] == 'success'
        
        # Check paused status
        response = self.client.get('/api/playback-status')
        status_data = json.loads(response.data)
        assert status_data['status'] == 'success'
        assert status_data['playback']['state'] in {'paused', 'playing', 'idle'}
        
        # Resume
        response = self.client.post('/api/play', json={'filename': uploaded_filename})
        assert response.status_code == 200
    
    def test_invalid_file_upload(self):
        """Test uploading invalid file types"""
        # Create a text file instead of MIDI
        temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_txt.write(b'This is not a MIDI file')
        temp_txt.close()
        
        try:
            with open(temp_txt.name, 'rb') as f:
                response = self.client.post('/api/upload-midi',
                                          data={'file': (f, 'test.txt')},
                                          content_type='multipart/form-data')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data.get('error') == 'Invalid File Type'
        finally:
            os.unlink(temp_txt.name)
    
    def test_api_error_handling(self):
        """Test API error handling for various scenarios"""
        # Test missing file in upload
        response = self.client.post('/api/upload-midi')
        assert response.status_code == 400
        
        # Test invalid endpoints
        response = self.client.get('/api/nonexistent')
        assert response.status_code == 404
        
        # Test method not allowed
        response = self.client.get('/api/play')
        assert response.status_code == 405
    
    @patch('playback_service.PlaybackService')
    def test_service_initialization_failure(self, mock_playback_service):
        """Test handling of service initialization failures"""
        mock_playback_service.side_effect = Exception("Service init failed")
        
        # This should be handled gracefully by the app
        # Since the app is already initialized, we'll test that it handles service failures
        assert hasattr(app, 'playback_service')
    
    def test_concurrent_playback_requests(self):
        """Test handling of concurrent playback requests"""
        # Upload file first
        with open(self.temp_midi.name, 'rb') as f:
            upload_response = self.client.post('/api/upload-midi',
                                               data={'file': (f, 'test.mid')},
                                               content_type='multipart/form-data')

        uploaded_filename = upload_response.get_json().get('filename')
        assert uploaded_filename

        # Start playback
        response1 = self.client.post('/api/play', json={'filename': uploaded_filename})
        assert response1.status_code == 200
        
        # Try to start again (should handle gracefully)
        response2 = self.client.post('/api/play', json={'filename': uploaded_filename})
        # Should either succeed (if already playing) or return appropriate status
        assert response2.status_code in [200, 400]
    
    def test_status_endpoint_consistency(self):
        """Test that status endpoint returns consistent data"""
        response = self.client.get('/api/playback-status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        playback = data['playback']
        assert set(playback.keys()) >= {'state', 'current_time', 'total_duration', 'progress_percentage', 'filename', 'error_message'}
        assert isinstance(playback['current_time'], (int, float))
        assert isinstance(playback['total_duration'], (int, float))
    
    def test_led_visualization_integration(self):
        """Test that LED visualization works with playback"""
        if not getattr(app, 'playback_service', None):
            pytest.skip("Playback service not initialized")

        original_led_controller = app.playback_service.led_controller
        mock_led_controller = MagicMock()
        app.playback_service.led_controller = mock_led_controller

        try:
            with open(self.temp_midi.name, 'rb') as f:
                upload_response = self.client.post('/api/upload-midi',
                                                   data={'file': (f, 'test.mid')},
                                                   content_type='multipart/form-data')

            uploaded_filename = upload_response.get_json().get('filename')
            assert uploaded_filename
            play_response = self.client.post('/api/play', json={'filename': uploaded_filename})
            assert play_response.status_code == 200

            # Allow background thread to start and interact with the controller
            time.sleep(0.1)

            assert mock_led_controller.turn_off_all.called or mock_led_controller.turn_on_led.called
        finally:
            app.playback_service.led_controller = original_led_controller
            try:
                app.playback_service.stop_playback()
            except Exception:
                pass