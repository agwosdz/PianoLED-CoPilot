#!/usr/bin/env python3
"""
Calibration API endpoints for LED-to-key alignment
Provides REST endpoints for managing global and per-key calibration offsets
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from datetime import datetime
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Import settings service - will be initialized in app.py
def get_settings_service():
    """Get the global settings service instance"""
    from app import settings_service
    return settings_service

def get_socketio():
    """Get the global socketio instance"""
    from app import socketio
    return socketio

# Create the blueprint
calibration_bp = Blueprint('calibration_api', __name__, url_prefix='/api/calibration')


@calibration_bp.route('/status', methods=['GET'])
def get_calibration_status():
    """Get current calibration status and settings"""
    try:
        settings_service = get_settings_service()
        
        status = {
            'enabled': settings_service.get_setting('calibration', 'calibration_enabled', False),
            'mode': settings_service.get_setting('calibration', 'calibration_mode', 'none'),
            'global_offset': settings_service.get_setting('calibration', 'global_offset', 0),
            'key_offsets': settings_service.get_setting('calibration', 'key_offsets', {}),
            'last_calibration': settings_service.get_setting('calibration', 'last_calibration', ''),
            'mapping_base_offset': settings_service.get_setting('led', 'mapping_base_offset', 0),
            'leds_per_key': settings_service.get_setting('led', 'leds_per_key', 3),
        }
        
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to retrieve calibration status'
        }), 500


@calibration_bp.route('/enable', methods=['POST'])
def enable_calibration():
    """Enable calibration mode"""
    try:
        settings_service = get_settings_service()
        
        settings_service.set_setting('calibration', 'calibration_enabled', True)
        settings_service.set_setting('calibration', 'calibration_mode', 'manual')
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast calibration state change
        socketio = get_socketio()
        socketio.emit('calibration_enabled', {'enabled': True})
        
        logger.info("Calibration mode enabled")
        return jsonify({'message': 'Calibration mode enabled'}), 200
    except Exception as e:
        logger.error(f"Error enabling calibration: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to enable calibration mode'
        }), 500


@calibration_bp.route('/disable', methods=['POST'])
def disable_calibration():
    """Disable calibration mode"""
    try:
        settings_service = get_settings_service()
        
        settings_service.set_setting('calibration', 'calibration_enabled', False)
        settings_service.set_setting('calibration', 'calibration_mode', 'none')
        
        # Broadcast calibration state change
        socketio = get_socketio()
        socketio.emit('calibration_disabled', {'enabled': False})
        
        logger.info("Calibration mode disabled")
        return jsonify({'message': 'Calibration mode disabled'}), 200
    except Exception as e:
        logger.error(f"Error disabling calibration: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to disable calibration mode'
        }), 500


@calibration_bp.route('/global-offset', methods=['GET'])
def get_global_offset():
    """Get the global LED offset"""
    try:
        settings_service = get_settings_service()
        offset = settings_service.get_setting('calibration', 'global_offset', 0)
        
        return jsonify({'global_offset': offset}), 200
    except Exception as e:
        logger.error(f"Error getting global offset: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to retrieve global offset'
        }), 500


@calibration_bp.route('/global-offset', methods=['PUT'])
def set_global_offset():
    """Set the global LED offset"""
    try:
        data = request.get_json()
        if not data or 'global_offset' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "global_offset" field'
            }), 400
        
        offset = data['global_offset']
        
        # Validate offset is an integer in acceptable range
        try:
            offset = int(offset)
            if not (-100 <= offset <= 100):
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'global_offset must be between -100 and 100'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'global_offset must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'global_offset', offset)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast offset change
        socketio = get_socketio()
        socketio.emit('global_offset_changed', {'global_offset': offset})
        
        logger.info(f"Global offset set to {offset}")
        return jsonify({
            'message': 'Global offset updated',
            'global_offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error setting global offset: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to set global offset'
        }), 500


@calibration_bp.route('/key-offset/<int:midi_note>', methods=['GET'])
def get_key_offset(midi_note):
    """Get the offset for a specific key"""
    try:
        if not (0 <= midi_note <= 127):
            return jsonify({
                'error': 'Bad Request',
                'message': 'MIDI note must be between 0 and 127'
            }), 400
        
        settings_service = get_settings_service()
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {}) or {}
        offset = key_offsets.get(str(midi_note), 0)
        
        return jsonify({
            'midi_note': midi_note,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error getting key offset: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to retrieve offset for MIDI note {midi_note}'
        }), 500


@calibration_bp.route('/key-offset/<int:midi_note>', methods=['PUT'])
def set_key_offset(midi_note):
    """Set the offset for a specific key"""
    try:
        if not (0 <= midi_note <= 127):
            return jsonify({
                'error': 'Bad Request',
                'message': 'MIDI note must be between 0 and 127'
            }), 400
        
        data = request.get_json()
        if not data or 'offset' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "offset" field'
            }), 400
        
        offset = data['offset']
        
        # Validate offset is an integer
        try:
            offset = int(offset)
            if not (-100 <= offset <= 100):
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'offset must be between -100 and 100'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'offset must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        
        # Get current offsets
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {}) or {}
        
        # Update offset for this key
        if offset == 0 and str(midi_note) in key_offsets:
            # Remove offset if it's 0 (default)
            del key_offsets[str(midi_note)]
        else:
            key_offsets[str(midi_note)] = offset
        
        # Save updated offsets
        settings_service.set_setting('calibration', 'key_offsets', key_offsets)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast offset change
        socketio = get_socketio()
        socketio.emit('key_offset_changed', {
            'midi_note': midi_note,
            'offset': offset
        })
        
        logger.info(f"Key offset for MIDI note {midi_note} set to {offset}")
        return jsonify({
            'message': 'Key offset updated',
            'midi_note': midi_note,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error setting key offset: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to set offset for MIDI note {midi_note}'
        }), 500


@calibration_bp.route('/key-offsets', methods=['GET'])
def get_all_key_offsets():
    """Get all key offsets"""
    try:
        settings_service = get_settings_service()
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {}) or {}
        
        return jsonify({
            'key_offsets': key_offsets
        }), 200
    except Exception as e:
        logger.error(f"Error getting all key offsets: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to retrieve key offsets'
        }), 500


@calibration_bp.route('/key-offsets', methods=['PUT'])
def set_all_key_offsets():
    """Set multiple key offsets at once"""
    try:
        data = request.get_json()
        if not data or 'key_offsets' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "key_offsets" field'
            }), 400
        
        key_offsets_input = data['key_offsets']
        if not isinstance(key_offsets_input, dict):
            return jsonify({
                'error': 'Validation Error',
                'message': 'key_offsets must be a dictionary'
            }), 400
        
        # Validate all offsets
        validated_offsets = {}
        for note_key, offset in key_offsets_input.items():
            try:
                midi_note = int(note_key)
                if not (0 <= midi_note <= 127):
                    return jsonify({
                        'error': 'Validation Error',
                        'message': f'MIDI note {midi_note} must be between 0 and 127'
                    }), 400
                
                offset_val = int(offset)
                if not (-100 <= offset_val <= 100):
                    return jsonify({
                        'error': 'Validation Error',
                        'message': f'Offset for note {midi_note} must be between -100 and 100'
                    }), 400
                
                # Only include non-zero offsets
                if offset_val != 0:
                    validated_offsets[str(midi_note)] = offset_val
            except (TypeError, ValueError):
                return jsonify({
                    'error': 'Validation Error',
                    'message': f'Invalid MIDI note or offset: {note_key}={offset}'
                }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'key_offsets', validated_offsets)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast offset change
        socketio = get_socketio()
        socketio.emit('key_offsets_changed', {
            'key_offsets': validated_offsets
        })
        
        logger.info(f"Updated {len(validated_offsets)} key offsets")
        return jsonify({
            'message': 'Key offsets updated',
            'count': len(validated_offsets)
        }), 200
    except Exception as e:
        logger.error(f"Error setting key offsets: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to update key offsets'
        }), 500


@calibration_bp.route('/reset', methods=['POST'])
def reset_calibration():
    """Reset all calibration offsets to defaults"""
    try:
        settings_service = get_settings_service()
        
        settings_service.set_setting('calibration', 'global_offset', 0)
        settings_service.set_setting('calibration', 'key_offsets', {})
        settings_service.set_setting('calibration', 'calibration_enabled', False)
        settings_service.set_setting('calibration', 'calibration_mode', 'none')
        
        # Broadcast reset
        socketio = get_socketio()
        socketio.emit('calibration_reset', {
            'global_offset': 0,
            'key_offsets': {},
            'enabled': False
        })
        
        logger.info("Calibration reset to defaults")
        return jsonify({'message': 'Calibration reset to defaults'}), 200
    except Exception as e:
        logger.error(f"Error resetting calibration: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reset calibration'
        }), 500


@calibration_bp.route('/export', methods=['GET'])
def export_calibration():
    """Export calibration data"""
    try:
        settings_service = get_settings_service()
        
        calibration_data = {
            'enabled': settings_service.get_setting('calibration', 'calibration_enabled', False),
            'mode': settings_service.get_setting('calibration', 'calibration_mode', 'none'),
            'global_offset': settings_service.get_setting('calibration', 'global_offset', 0),
            'key_offsets': settings_service.get_setting('calibration', 'key_offsets', {}),
            'last_calibration': settings_service.get_setting('calibration', 'last_calibration', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(calibration_data), 200
    except Exception as e:
        logger.error(f"Error exporting calibration: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to export calibration data'
        }), 500


@calibration_bp.route('/import', methods=['POST'])
def import_calibration():
    """Import calibration data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'No calibration data provided'
            }), 400
        
        settings_service = get_settings_service()
        
        # Import global_offset if present
        if 'global_offset' in data:
            try:
                offset = int(data['global_offset'])
                if -100 <= offset <= 100:
                    settings_service.set_setting('calibration', 'global_offset', offset)
            except (TypeError, ValueError):
                pass
        
        # Import key_offsets if present
        if 'key_offsets' in data and isinstance(data['key_offsets'], dict):
            key_offsets = {}
            for note_key, offset in data['key_offsets'].items():
                try:
                    midi_note = int(note_key)
                    offset_val = int(offset)
                    if 0 <= midi_note <= 127 and -100 <= offset_val <= 100 and offset_val != 0:
                        key_offsets[str(midi_note)] = offset_val
                except (TypeError, ValueError):
                    continue
            
            settings_service.set_setting('calibration', 'key_offsets', key_offsets)
        
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        logger.info("Calibration data imported")
        return jsonify({
            'message': 'Calibration data imported successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error importing calibration: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to import calibration data'
        }), 500
