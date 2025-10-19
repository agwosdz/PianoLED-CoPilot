"""
LED Selection Override API endpoints

Provides REST API for managing per-LED selection overrides.
"""

import logging
from flask import Blueprint, request, jsonify
from backend.logging_config import get_logger
from backend.services.led_selection_service import LEDSelectionService

logger = get_logger(__name__)
led_selection_bp = Blueprint('led_selection', __name__, url_prefix='/api/led-selection')


def _get_selection_service(settings_service):
    """Create a configured LED selection service."""
    return LEDSelectionService(settings_service)


@led_selection_bp.route('/key/<int:midi_note>', methods=['GET'])
def get_key_selection(midi_note):
    """Get LED selection override for a specific key."""
    try:
        from backend.app import settings_service
        
        service = _get_selection_service(settings_service)
        result = service.get_key_led_selection(midi_note)
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error getting LED selection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@led_selection_bp.route('/key/<int:midi_note>', methods=['PUT'])
def set_key_selection(midi_note):
    """Override LED selection for a specific key."""
    try:
        from backend.app import settings_service, socketio
        
        data = request.get_json() or {}
        selected_leds = data.get('selected_leds', [])
        
        service = _get_selection_service(settings_service)
        result = service.set_key_led_selection(midi_note, selected_leds)
        
        if result.get('success'):
            # Broadcast update
            socketio.emit('led_selection_updated', {
                'midi_note': midi_note,
                'selected_leds': selected_leds
            })
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error setting LED selection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@led_selection_bp.route('/key/<int:midi_note>', methods=['DELETE'])
def clear_key_selection(midi_note):
    """Clear LED selection override for a specific key."""
    try:
        from backend.app import settings_service, socketio
        
        service = _get_selection_service(settings_service)
        result = service.clear_key_led_selection(midi_note)
        
        if result.get('success'):
            # Broadcast update
            socketio.emit('led_selection_cleared', {'midi_note': midi_note})
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error clearing LED selection: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@led_selection_bp.route('/key/<int:midi_note>/toggle/<int:led_index>', methods=['POST'])
def toggle_led(midi_note, led_index):
    """Toggle a single LED's selection for a key."""
    try:
        from backend.app import settings_service, socketio
        
        service = _get_selection_service(settings_service)
        result = service.toggle_led_selection(midi_note, led_index)
        
        if result.get('success'):
            # Broadcast update
            socketio.emit('led_toggled', {
                'midi_note': midi_note,
                'led_index': led_index,
                'action': result.get('action'),
                'selected_leds': result.get('selected_leds')
            })
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error toggling LED: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@led_selection_bp.route('/all', methods=['GET'])
def get_all_selections():
    """Get all LED selection overrides."""
    try:
        from backend.app import settings_service
        
        service = _get_selection_service(settings_service)
        overrides = service.get_all_overrides()
        
        # Convert to list format for frontend
        overrides_list = [
            {
                'midi_note': int(midi_note_str),
                'selected_leds': leds
            }
            for midi_note_str, leds in overrides.items()
        ]
        
        return jsonify({
            'success': True,
            'overrides': overrides_list,
            'count': len(overrides_list)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting all selections: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@led_selection_bp.route('/all', methods=['DELETE'])
def clear_all_selections():
    """Clear all LED selection overrides."""
    try:
        from backend.app import settings_service, socketio
        
        service = _get_selection_service(settings_service)
        result = service.clear_all_overrides()
        
        if result.get('success'):
            # Broadcast update
            socketio.emit('all_led_selections_cleared', {})
        
        return jsonify(result), 200 if result.get('success') else 400
    
    except Exception as e:
        logger.error(f"Error clearing all selections: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
