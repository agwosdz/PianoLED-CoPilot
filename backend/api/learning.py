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
        JSON with all learning mode settings
    """
    try:
        if not _settings_service:
            return jsonify({'error': 'Settings service not available'}), 503
        
        options = {
            'success': True,
            'wait_for_notes_enabled': _settings_service.get_setting('learning_mode', 'wait_for_notes_enabled', False),
            'timing_window_ms': _settings_service.get_setting('learning_mode', 'timing_window_ms', 500),
            'left_hand_white': _settings_service.get_setting('learning_mode', 'left_hand_white', '#ff6b6b'),
            'left_hand_black': _settings_service.get_setting('learning_mode', 'left_hand_black', '#ff9999'),
            'right_hand_white': _settings_service.get_setting('learning_mode', 'right_hand_white', '#4dabf7'),
            'right_hand_black': _settings_service.get_setting('learning_mode', 'right_hand_black', '#74c0fc')
        }
        return jsonify(options)
    except Exception as e:
        logger.error(f"Error getting learning options: {e}")
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/learning/options', methods=['POST'])
def update_learning_options():
    """Update learning mode settings.
    
    Request body:
        JSON object with any of these fields:
        - wait_for_notes_enabled (boolean)
        - timing_window_ms (number, 100-2000)
        - left_hand_white (hex color string)
        - left_hand_black (hex color string)
        - right_hand_white (hex color string)
        - right_hand_black (hex color string)
    
    Returns:
        JSON with success status
    """
    try:
        if not _settings_service:
            return jsonify({'error': 'Settings service not available'}), 503
        
        data = request.get_json()
        
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid request format'}), 400
        
        # Handle wait_for_notes_enabled
        if 'wait_for_notes_enabled' in data:
            value = data['wait_for_notes_enabled']
            if not isinstance(value, bool):
                return jsonify({'error': 'wait_for_notes_enabled must be a boolean'}), 400
            _settings_service.set_setting('learning_mode', 'wait_for_notes_enabled', value)
        
        # Handle timing_window_ms
        if 'timing_window_ms' in data:
            timing = data['timing_window_ms']
            if not isinstance(timing, (int, float)):
                return jsonify({'error': 'timing_window_ms must be a number'}), 400
            if timing < 100 or timing > 2000:
                return jsonify({'error': 'timing_window_ms must be between 100 and 2000'}), 400
            _settings_service.set_setting('learning_mode', 'timing_window_ms', int(timing))
        
        # Validate and save colors
        color_keys = ['left_hand_white', 'left_hand_black', 'right_hand_white', 'right_hand_black']
        for color_key in color_keys:
            if color_key in data:
                color_value = data[color_key]
                
                # Validate hex color format
                if not isinstance(color_value, str):
                    return jsonify({'error': f'{color_key} must be a string'}), 400
                
                # Check hex format (#RRGGBB)
                if not re.match(r'^#[0-9a-fA-F]{6}$', color_value):
                    return jsonify({'error': f'{color_key} must be valid hex color (e.g., #ff0000)'}), 400
                
                _settings_service.set_setting('learning_mode', color_key, color_value)
        
        logger.info("Learning options updated successfully")
        return jsonify({'success': True, 'message': 'Learning options saved'})
    
    except Exception as e:
        logger.error(f"Error updating learning options: {e}")
        return jsonify({'error': str(e)}), 500
