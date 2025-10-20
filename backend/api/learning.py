"""Learning mode API endpoints for the Piano LED Visualizer."""

import re
import logging
from flask import Blueprint, request, jsonify
from backend.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

# Create blueprint for learning routes
learning_bp = Blueprint('learning', __name__)

# Global reference to settings service (set by app.py)
_settings_service: SettingsService = None

def set_settings_service(settings_service: SettingsService):
    """Set the global settings service reference."""
    global _settings_service
    _settings_service = settings_service


@learning_bp.route('/learning/options', methods=['GET'])
def get_learning_options():
    """Get current learning mode settings.
    
    Returns:
        JSON with per-hand learning mode settings
    """
    try:
        if not _settings_service:
            return jsonify({'error': 'Settings service not available'}), 503
        
        options = {
            'success': True,
            'left_hand': {
                'wait_for_notes': _settings_service.get_setting('learning_mode', 'left_hand_wait_for_notes', False),
                'white_color': _settings_service.get_setting('learning_mode', 'left_hand_white_color', '#ff6b6b'),
                'black_color': _settings_service.get_setting('learning_mode', 'left_hand_black_color', '#c92a2a')
            },
            'right_hand': {
                'wait_for_notes': _settings_service.get_setting('learning_mode', 'right_hand_wait_for_notes', False),
                'white_color': _settings_service.get_setting('learning_mode', 'right_hand_white_color', '#006496'),
                'black_color': _settings_service.get_setting('learning_mode', 'right_hand_black_color', '#960064')
            },
            'timing_window_ms': _settings_service.get_setting('learning_mode', 'timing_window_ms', 500)
        }
        return jsonify(options)
    except Exception as e:
        logger.error(f"Error getting learning options: {e}")
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/learning/options', methods=['POST'])
def update_learning_options():
    """Update learning mode settings.
    
    Request body:
        JSON object with:
        - left_hand (object): { wait_for_notes, white_color, black_color }
        - right_hand (object): { wait_for_notes, white_color, black_color }
        - timing_window_ms (number, 100-2000)
    
    Returns:
        JSON with success status
    """
    try:
        if not _settings_service:
            return jsonify({'error': 'Settings service not available'}), 503
        
        data = request.get_json()
        
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid request format'}), 400
        
        # Handle left hand settings
        if 'left_hand' in data:
            left_hand = data['left_hand']
            if isinstance(left_hand, dict):
                if 'wait_for_notes' in left_hand:
                    value = left_hand['wait_for_notes']
                    if not isinstance(value, bool):
                        return jsonify({'error': 'left_hand.wait_for_notes must be a boolean'}), 400
                    _settings_service.set_setting('learning_mode', 'left_hand_wait_for_notes', value)
                
                if 'white_color' in left_hand:
                    color = left_hand['white_color']
                    if not isinstance(color, str) or not re.match(r'^#[0-9a-fA-F]{6}$', color):
                        return jsonify({'error': 'left_hand.white_color must be valid hex color (e.g., #ff0000)'}), 400
                    _settings_service.set_setting('learning_mode', 'left_hand_white_color', color)
                
                if 'black_color' in left_hand:
                    color = left_hand['black_color']
                    if not isinstance(color, str) or not re.match(r'^#[0-9a-fA-F]{6}$', color):
                        return jsonify({'error': 'left_hand.black_color must be valid hex color (e.g., #ff0000)'}), 400
                    _settings_service.set_setting('learning_mode', 'left_hand_black_color', color)
        
        # Handle right hand settings
        if 'right_hand' in data:
            right_hand = data['right_hand']
            if isinstance(right_hand, dict):
                if 'wait_for_notes' in right_hand:
                    value = right_hand['wait_for_notes']
                    if not isinstance(value, bool):
                        return jsonify({'error': 'right_hand.wait_for_notes must be a boolean'}), 400
                    _settings_service.set_setting('learning_mode', 'right_hand_wait_for_notes', value)
                
                if 'white_color' in right_hand:
                    color = right_hand['white_color']
                    if not isinstance(color, str) or not re.match(r'^#[0-9a-fA-F]{6}$', color):
                        return jsonify({'error': 'right_hand.white_color must be valid hex color (e.g., #ff0000)'}), 400
                    _settings_service.set_setting('learning_mode', 'right_hand_white_color', color)
                
                if 'black_color' in right_hand:
                    color = right_hand['black_color']
                    if not isinstance(color, str) or not re.match(r'^#[0-9a-fA-F]{6}$', color):
                        return jsonify({'error': 'right_hand.black_color must be valid hex color (e.g., #ff0000)'}), 400
                    _settings_service.set_setting('learning_mode', 'right_hand_black_color', color)
        
        # Handle timing window
        if 'timing_window_ms' in data:
            timing = data['timing_window_ms']
            if not isinstance(timing, (int, float)):
                return jsonify({'error': 'timing_window_ms must be a number'}), 400
            if timing < 100 or timing > 2000:
                return jsonify({'error': 'timing_window_ms must be between 100 and 2000'}), 400
            _settings_service.set_setting('learning_mode', 'timing_window_ms', int(timing))
        
        logger.info("Learning options updated successfully")
        return jsonify({'success': True, 'message': 'Learning options saved'})
    
    except Exception as e:
        logger.error(f"Error updating learning options: {e}")
        return jsonify({'error': str(e)}), 500
