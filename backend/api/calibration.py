#!/usr/bin/env python3
"""
Calibration API endpoints for LED-to-key alignment
Provides REST endpoints for managing global and per-key calibration offsets
"""

import logging
import time
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any
from datetime import datetime
from backend.logging_config import get_logger
from backend.config import (
    generate_auto_key_mapping,
    apply_calibration_offsets_to_mapping,
    validate_auto_mapping_config,
    get_piano_specs,
    calculate_physical_led_mapping
)

logger = get_logger(__name__)

# Import settings service - will be initialized in app.py
def get_settings_service():
    """Get the global settings service instance"""
    from backend.app import settings_service
    return settings_service

def get_socketio():
    """Get the global socketio instance"""
    from backend.app import socketio
    return socketio

def get_led_controller():
    """Get the global LED controller instance"""
    try:
        from flask import current_app
        
        # First try to get from current app config
        if current_app and hasattr(current_app, 'config'):
            led_ctrl = current_app.config.get('led_controller')
            if led_ctrl is not None:
                return led_ctrl
        
        # Fallback to direct import
        from backend.app import led_controller
        return led_controller
    except Exception as e:
        logger.error(f"Error getting LED controller: {e}", exc_info=True)
        return None

# Create the blueprint
calibration_bp = Blueprint('calibration_api', __name__, url_prefix='/api/calibration')


@calibration_bp.route('/health', methods=['GET'])
def led_health_check():
    """Check if LED controller is properly initialized and responsive"""
    try:
        led_controller = get_led_controller()
        
        # Build health status
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'led_controller_exists': led_controller is not None,
            'led_controller_type': type(led_controller).__name__ if led_controller else 'None',
        }
        
        if led_controller is None:
            logger.warning("LED controller is None")
            return jsonify({
                **health_status,
                'status': 'ERROR',
                'message': 'LED controller not available'
            }), 503
        
        # Check LED controller attributes
        try:
            health_status['num_pixels'] = getattr(led_controller, 'num_pixels', None)
            health_status['led_enabled'] = getattr(led_controller, 'led_enabled', None)
            health_status['pixels_initialized'] = bool(getattr(led_controller, 'pixels', None))
            health_status['brightness'] = getattr(led_controller, 'brightness', None)
            health_status['pin'] = getattr(led_controller, 'pin', None)
        except Exception as attr_error:
            logger.error(f"Error reading LED controller attributes: {attr_error}")
            return jsonify({
                **health_status,
                'status': 'ERROR',
                'message': f'LED controller has errors: {str(attr_error)}'
            }), 503
        
        # Check if LED controller can execute a safe operation
        try:
            # Just read a value, don't modify state
            if hasattr(led_controller, '_led_state'):
                health_status['led_state_length'] = len(led_controller._led_state)
        except Exception as e:
            logger.warning(f"Could not check LED state: {e}")
        
        # Determine overall health
        is_healthy = (
            led_controller is not None and
            health_status.get('num_pixels', 0) > 0 and
            health_status.get('led_enabled', False)
        )
        
        return jsonify({
            **health_status,
            'status': 'OK' if is_healthy else 'DEGRADED',
            'message': 'LED controller is responsive' if is_healthy else 'LED controller is in degraded state'
        }), (200 if is_healthy else 503)
        
    except Exception as e:
        logger.error(f"Error during LED health check: {e}", exc_info=True)
        return jsonify({
            'status': 'ERROR',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 503


@calibration_bp.route('/status', methods=['GET'])
def get_calibration_status():
    """Get current calibration status and settings"""
    try:
        settings_service = get_settings_service()
        
        status = {
            'enabled': settings_service.get_setting('calibration', 'calibration_enabled', False),
            'mode': settings_service.get_setting('calibration', 'calibration_mode', 'none'),
            'start_led': settings_service.get_setting('calibration', 'start_led', 0),
            'end_led': settings_service.get_setting('calibration', 'end_led', 245),
            'trim_left': settings_service.get_setting('calibration', 'trim_left', 0),
            'trim_right': settings_service.get_setting('calibration', 'trim_right', 0),
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


@calibration_bp.route('/start-led', methods=['PUT'])
def set_start_led():
    """Set the first LED index at the beginning of the piano"""
    try:
        data = request.get_json()
        if not data or 'start_led' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "start_led" field'
            }), 400
        
        start_led = data['start_led']
        
        # Validate start_led is an integer in acceptable range
        try:
            start_led = int(start_led)
            led_count = get_settings_service().get_setting('led', 'led_count', 246)
            if not (0 <= start_led < led_count):
                return jsonify({
                    'error': 'Validation Error',
                    'message': f'start_led must be between 0 and {led_count - 1}'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'start_led must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'start_led', start_led)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast start_led change
        socketio = get_socketio()
        socketio.emit('start_led_changed', {'start_led': start_led})
        
        logger.info(f"Start LED set to {start_led}")
        return jsonify({
            'message': 'Start LED updated',
            'start_led': start_led
        }), 200
    except Exception as e:
        logger.error(f"Error setting start LED: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to set start LED'
        }), 500


@calibration_bp.route('/end-led', methods=['PUT'])
def set_end_led():
    """Set the last LED index at the end of the piano"""
    try:
        data = request.get_json()
        if not data or 'end_led' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "end_led" field'
            }), 400
        
        end_led = data['end_led']
        
        # Validate end_led is an integer in acceptable range
        try:
            end_led = int(end_led)
            led_count = get_settings_service().get_setting('led', 'led_count', 246)
            if not (0 <= end_led < led_count):
                return jsonify({
                    'error': 'Validation Error',
                    'message': f'end_led must be between 0 and {led_count - 1}'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'end_led must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'end_led', end_led)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast end_led change
        socketio = get_socketio()
        socketio.emit('end_led_changed', {'end_led': end_led})
        
        logger.info(f"End LED set to {end_led}")
        return jsonify({
            'message': 'End LED updated',
            'end_led': end_led
        }), 200
    except Exception as e:
        logger.error(f"Error setting end LED: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to set end LED'
        }), 500


@calibration_bp.route('/trim-left', methods=['PUT'])
def set_trim_left():
    """Set the number of LEDs to trim from the left side"""
    try:
        data = request.get_json()
        if not data or 'trim_left' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "trim_left" field'
            }), 400
        
        trim_left = data['trim_left']
        
        # Validate trim_left is a non-negative integer
        try:
            trim_left = int(trim_left)
            if trim_left < 0 or trim_left > 100:
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'trim_left must be between 0 and 100'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'trim_left must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'trim_left', trim_left)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast trim_left change
        socketio = get_socketio()
        socketio.emit('trim_left_changed', {'trim_left': trim_left})
        
        logger.info(f"Trim left set to {trim_left}")
        return jsonify({
            'message': 'Trim left updated',
            'trim_left': trim_left
        }), 200
    except Exception as e:
        logger.error(f"Error setting trim left: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to set trim left'
        }), 500


@calibration_bp.route('/trim-right', methods=['PUT'])
def set_trim_right():
    """Set the number of LEDs to trim from the right side"""
    try:
        data = request.get_json()
        if not data or 'trim_right' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "trim_right" field'
            }), 400
        
        trim_right = data['trim_right']
        
        # Validate trim_right is a non-negative integer
        try:
            trim_right = int(trim_right)
            if trim_right < 0 or trim_right > 100:
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'trim_right must be between 0 and 100'
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'trim_right must be an integer'
            }), 400
        
        settings_service = get_settings_service()
        settings_service.set_setting('calibration', 'trim_right', trim_right)
        settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
        
        # Broadcast trim_right change
        socketio = get_socketio()
        socketio.emit('trim_right_changed', {'trim_right': trim_right})
        
        logger.info(f"Trim right set to {trim_right}")
        return jsonify({
            'message': 'Trim right updated',
            'trim_right': trim_right
        }), 200
    except Exception as e:
        logger.error(f"Error setting trim right: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to set trim right'
        }), 500
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


@calibration_bp.route('/key-offset/<int:midi_note>', methods=['DELETE'])
def delete_key_offset(midi_note):
    """Delete the offset for a specific key"""
    try:
        if not (0 <= midi_note <= 127):
            return jsonify({
                'error': 'Bad Request',
                'message': 'MIDI note must be between 0 and 127'
            }), 400
        
        settings_service = get_settings_service()
        
        # Get current offsets
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {}) or {}
        
        # Remove offset for this key if it exists
        if str(midi_note) in key_offsets:
            del key_offsets[str(midi_note)]
            
            # Save updated offsets
            settings_service.set_setting('calibration', 'key_offsets', key_offsets)
            settings_service.set_setting('calibration', 'last_calibration', datetime.now().isoformat())
            
            # Broadcast offset change
            socketio = get_socketio()
            socketio.emit('key_offset_changed', {
                'midi_note': midi_note,
                'offset': 0
            })
            
            logger.info(f"Key offset for MIDI note {midi_note} deleted")
        
        return jsonify({
            'message': 'Key offset deleted',
            'midi_note': midi_note
        }), 200
    except Exception as e:
        logger.error(f"Error deleting key offset: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to delete offset for MIDI note {midi_note}'
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
        led_count = settings_service.get_setting('led', 'led_count', 246)
        
        settings_service.set_setting('calibration', 'start_led', 0)
        settings_service.set_setting('calibration', 'end_led', led_count - 1)
        settings_service.set_setting('calibration', 'key_offsets', {})
        settings_service.set_setting('calibration', 'calibration_enabled', False)
        settings_service.set_setting('calibration', 'calibration_mode', 'none')
        
        # Broadcast reset
        socketio = get_socketio()
        socketio.emit('calibration_reset', {
            'start_led': 0,
            'end_led': led_count - 1,
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


@calibration_bp.route('/key-led-mapping', methods=['GET'])
def get_key_led_mapping():
    """Get the key-to-LED mapping with calibration offsets applied, respecting distribution mode"""
    logger.info("GET /key-led-mapping endpoint called")
    
    try:
        settings_service = get_settings_service()
        
        # Get piano settings
        piano_size = settings_service.get_setting('piano', 'size', '88-key')
        led_count = settings_service.get_setting('led', 'led_count', 300)
        
        # Get calibration settings (LED range)
        start_led = settings_service.get_setting('calibration', 'start_led', 4)
        end_led = settings_service.get_setting('calibration', 'end_led', 249)
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
        
        # Get distribution mode settings
        leds_per_meter = settings_service.get_setting('led', 'leds_per_meter', 200)
        allow_led_sharing = settings_service.get_setting('calibration', 'allow_led_sharing', True)
        distribution_mode = settings_service.get_setting('calibration', 'distribution_mode', 'Piano Based (with overlap)')
        
        logger.info(f"Generating mapping with distribution mode '{distribution_mode}' (allow_led_sharing={allow_led_sharing}), "
                   f"LEDs: {start_led}-{end_led}, piano_size={piano_size}")
        
        # Choose allocation algorithm based on distribution mode
        if distribution_mode == 'Physics-Based LED Detection':
            # Use physics-based allocation
            from backend.services.physics_led_allocation import PhysicsBasedAllocationService
            
            # Read ALL physics parameters from settings
            led_density = settings_service.get_setting('led', 'leds_per_meter', 200)
            led_physical_width = settings_service.get_setting('calibration', 'led_physical_width', 3.5)
            led_strip_offset = settings_service.get_setting('calibration', 'led_strip_offset', None)
            overhang_threshold = settings_service.get_setting('calibration', 'led_overhang_threshold', 1.5)
            white_key_width = settings_service.get_setting('calibration', 'white_key_width', 22.0)
            black_key_width = settings_service.get_setting('calibration', 'black_key_width', 12.0)
            white_key_gap = settings_service.get_setting('calibration', 'white_key_gap', 1.0)
            
            logger.info(f"Physics-based allocation parameters: "
                       f"density={led_density} LEDs/m, led_width={led_physical_width}mm, "
                       f"overhang={overhang_threshold}mm, "
                       f"white_key={white_key_width}mm, black_key={black_key_width}mm, gap={white_key_gap}mm")
            
            service = PhysicsBasedAllocationService(
                led_density=led_density,
                led_physical_width=led_physical_width,
                led_strip_offset=led_strip_offset,
                overhang_threshold_mm=overhang_threshold
            )
            
            # Apply geometry parameters to analyzer to ensure they're used for calculations
            service.analyzer.white_key_width = white_key_width
            service.analyzer.black_key_width = black_key_width
            service.analyzer.white_key_gap = white_key_gap
            
            allocation_result = service.allocate_leds(
                start_led=start_led,
                end_led=end_led
            )
        else:
            # Use traditional Piano-Based allocation
            from backend.config_led_mapping_advanced import calculate_per_key_led_allocation
            
            allocation_result = calculate_per_key_led_allocation(
                leds_per_meter=leds_per_meter,
                start_led=start_led,
                end_led=end_led,
                piano_size=piano_size,
                allow_led_sharing=allow_led_sharing
            )
        
        if not allocation_result.get('success'):
            logger.warning(f"LED allocation returned success=false: {allocation_result}")
            return jsonify({
                'error': 'Mapping generation failed',
                'message': allocation_result.get('message', 'Unknown error')
            }), 400
        
        # Extract the base mapping (without offsets yet)
        base_mapping = allocation_result.get('key_led_mapping', {})
        logger.info(f"Base mapping generated with {len(base_mapping)} keys")
        
        # Convert offset keys from MIDI notes (21-108) to key indices (0-87)
        # The base mapping uses key indices, but offsets are stored as MIDI notes
        converted_offsets = {}
        if key_offsets:
            for midi_note_str, offset_value in key_offsets.items():
                try:
                    midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
                    key_index = midi_note - 21  # Convert MIDI to index (MIDI 21 = index 0, MIDI 42 = index 21)
                    if 0 <= key_index < 88:
                        converted_offsets[key_index] = offset_value
                        logger.debug(f"Converted offset: MIDI {midi_note} → index {key_index}, offset={offset_value}")
                    else:
                        logger.warning(f"Offset MIDI note {midi_note} out of range, skipped")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert offset key {midi_note_str}: {e}")
        
        logger.info(f"Converted {len(converted_offsets)} offsets from MIDI notes to key indices")
        
        logger.info(f"Converted {len(converted_offsets)} offsets from MIDI notes to key indices")
        
        # Apply calibration key offsets to the mapping (now with matching key indices)
        final_mapping = apply_calibration_offsets_to_mapping(
            mapping=base_mapping,
            start_led=start_led,
            end_led=end_led,
            key_offsets=converted_offsets,
            led_count=led_count
        )
        
        logger.info(f"Successfully generated mapping with {len(final_mapping)} keys (distribution_mode='{distribution_mode}')")
        
        return jsonify({
            'mapping': final_mapping,
            'piano_size': piano_size,
            'led_count': led_count,
            'start_led': start_led,
            'end_led': end_led,
            'key_offsets_count': len(key_offsets),
            'distribution_mode': distribution_mode,
            'allow_led_sharing': allow_led_sharing,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating key-LED mapping: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to generate mapping: {str(e)}'
        }), 500


@calibration_bp.route('/mapping-validate', methods=['POST'])
def validate_mapping():
    """Validate a proposed mapping configuration before applying it"""
    logger.info("POST /mapping-validate endpoint called")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include JSON body'
            }), 400
        
        piano_size = data.get('piano_size', '88-key')
        led_count = data.get('led_count', 300)
        leds_per_key = data.get('leds_per_key')
        base_offset = data.get('mapping_base_offset', 0)
        
        # Validate inputs
        try:
            led_count = int(led_count)
            base_offset = int(base_offset)
            if leds_per_key is not None:
                leds_per_key = int(leds_per_key)
        except (TypeError, ValueError):
            return jsonify({
                'error': 'Bad Request',
                'message': 'led_count, leds_per_key, and mapping_base_offset must be integers'
            }), 400
        
        # Validate configuration
        validation = validate_auto_mapping_config(
            piano_size=piano_size,
            led_count=led_count,
            leds_per_key=leds_per_key,
            base_offset=base_offset
        )
        
        logger.info(f"Mapping validation result: valid={validation['valid']}, "
                   f"warnings={len(validation['warnings'])}")
        
        return jsonify(validation), 200
        
    except Exception as e:
        logger.error(f"Error validating mapping: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to validate mapping: {str(e)}'
        }), 500


@calibration_bp.route('/mapping-info', methods=['GET'])
def get_mapping_info():
    """Get detailed information about current LED mapping"""
    logger.info("GET /mapping-info endpoint called")
    
    try:
        settings_service = get_settings_service()
        
        # Get current settings
        piano_size = settings_service.get_setting('piano', 'size', '88-key')
        led_count = settings_service.get_setting('led', 'led_count', 300)
        base_offset = settings_service.get_setting('led', 'mapping_base_offset', 0)
        leds_per_key = settings_service.get_setting('led', 'leds_per_key', None)
        
        # Get calibration settings (LED range) - MUST use actual available range
        start_led = settings_service.get_setting('calibration', 'start_led', 0)
        end_led = settings_service.get_setting('calibration', 'end_led', led_count - 1)
        
        # Calculate available LED count based on the configured range
        available_led_range = end_led - start_led + 1
        
        logger.info(f"Generating mapping info for {piano_size} with calibration range [{start_led}, {end_led}] "
                   f"(total_leds={led_count}, available={available_led_range})")
        
        # Generate mapping using ONLY the available LED range
        mapping = generate_auto_key_mapping(
            piano_size=piano_size,
            led_count=available_led_range,  # Use only available range, not total LEDs
            leds_per_key=leds_per_key,
            mapping_base_offset=base_offset
        )
        
        # Analyze distribution
        led_counts = {}
        total_leds_used = 0
        for midi_note, led_indices in mapping.items():
            count = len(led_indices)
            total_leds_used += count
            if count not in led_counts:
                led_counts[count] = 0
            led_counts[count] += 1
        
        specs = get_piano_specs(piano_size)
        
        # Calculate statistics
        avg_leds_per_key = total_leds_used / len(mapping) if mapping else 0
        
        info = {
            'piano_size': piano_size,
            'piano_specs': {
                'keys': specs['keys'],
                'midi_start': specs['midi_start'],
                'midi_end': specs['midi_end'],
                'octaves': specs['octaves'],
                'start_note': specs['start_note'],
                'end_note': specs['end_note']
            },
            'led_configuration': {
                'total_leds': led_count,
                'calibration_start_led': start_led,
                'calibration_end_led': end_led,
                'calibration_range': f"[{start_led}, {end_led}]",
                'available_leds': available_led_range,
                'mapping_base_offset': base_offset,
                'leds_per_key_setting': leds_per_key
            },
            'mapping_statistics': {
                'total_keys': specs['keys'],
                'mapped_keys': len(mapping),
                'unmapped_keys': specs['keys'] - len(mapping),
                'leds_used': total_leds_used,
                'leds_unused': available_led_range - total_leds_used,
                'min_leds_per_key': min(led_counts.keys()) if led_counts else 0,
                'max_leds_per_key': max(led_counts.keys()) if led_counts else 0,
                'avg_leds_per_key': round(avg_leds_per_key, 2)
            },
            'distribution': {
                f'{count}_leds_per_key': count_keys 
                for count, count_keys in sorted(led_counts.items())
            },
            'first_unmapped_key': (
                specs['midi_start'] + len(mapping) 
                if len(mapping) < specs['keys'] else None
            ),
            'validation': validate_auto_mapping_config(
                piano_size=piano_size,
                led_count=led_count,
                leds_per_key=leds_per_key,
                base_offset=base_offset
            ),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Mapping info generated: {len(mapping)} keys mapped, "
                   f"{total_leds_used} LEDs used")
        
        return jsonify(info), 200
        
    except Exception as e:
        logger.error(f"Error getting mapping info: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to get mapping info: {str(e)}'
        }), 500


@calibration_bp.route('/test-led/<int:led_index>', methods=['POST'])
def test_led(led_index: int):
    """Light up a specific LED for calibration testing (3 seconds)"""
    logger.info(f"Test LED endpoint called for LED {led_index}")
    
    try:
        led_controller = get_led_controller()
        logger.info(f"LED controller retrieved: {led_controller is not None}")
        
        if not led_controller:
            logger.warning("LED controller is not available")
            return jsonify({
                'message': f'LED {led_index} test requested (LED controller not available)',
                'led_index': led_index,
                'status': 'unavailable'
            }), 200
        
        # Validate LED index
        try:
            led_count = led_controller.num_pixels
            logger.info(f"LED count: {led_count}")
        except AttributeError as attr_error:
            logger.error(f"LED controller has no num_pixels attribute: {attr_error}")
            return jsonify({
                'message': f'LED {led_index} test requested (LED controller error)',
                'led_index': led_index,
                'status': 'error'
            }), 200
        
        if led_index < 0 or led_index >= led_count:
            logger.warning(f"LED index {led_index} out of range (0-{led_count-1})")
            return jsonify({
                'error': 'Bad Request',
                'message': f'LED index must be between 0 and {led_count - 1}'
            }), 400
        
        # Light up the LED with a bright color (cyan)
        logger.info(f"Lighting up LED {led_index}")
        success, error = led_controller.turn_on_led(led_index, (0, 255, 255), auto_show=True)
        logger.info(f"LED turn_on_led returned: success={success}, error={error}")
        
        if not success:
            logger.error(f"Failed to turn on LED: {error}")
        
        # Schedule turning off after 3 seconds
        try:
            socketio = get_socketio()
            logger.info("Starting background task to turn off LED")
            socketio.start_background_task(_turn_off_led_after_delay, led_index, 3)
        except Exception as task_error:
            logger.error(f"Failed to start background task: {task_error}", exc_info=True)
        
        logger.info(f"Test LED {led_index} completed")
        return jsonify({
            'message': f'LED {led_index} lit for 3 seconds',
            'led_index': led_index
        }), 200
    except Exception as e:
        logger.error(f"Error testing LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'message': f'LED {led_index} test requested',
            'led_index': led_index,
            'error': str(e)
        }), 200


@calibration_bp.route('/led-on/<int:led_index>', methods=['POST'])
def turn_on_led_persistent(led_index: int):
    """Light up a specific LED persistently (stays on until turned off)
    
    Query parameters (optional):
    - r: red component (0-255, default 255)
    - g: green component (0-255, default 255)
    - b: blue component (0-255, default 255)
    """
    logger.info(f"Persistent LED on endpoint called for LED {led_index}")
    
    try:
        # Parse color from query parameters
        try:
            r = int(request.args.get('r', 255))
            g = int(request.args.get('g', 255))
            b = int(request.args.get('b', 255))
            
            # Validate color values
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            color = (r, g, b)
            logger.info(f"Using color RGB{color}")
        except (ValueError, TypeError):
            logger.warning("Invalid color parameters, using default white")
            color = (255, 255, 255)
        
        led_controller = get_led_controller()
        
        if not led_controller:
            logger.warning("LED controller is not available")
            return jsonify({
                'message': f'LED {led_index} on requested (LED controller not available)',
                'led_index': led_index,
                'status': 'unavailable'
            }), 200
        
        # Validate LED index
        try:
            led_count = led_controller.num_pixels
            logger.info(f"LED count: {led_count}")
        except AttributeError as attr_error:
            logger.error(f"LED controller has no num_pixels attribute: {attr_error}")
            return jsonify({
                'message': f'LED {led_index} on requested (LED controller error)',
                'led_index': led_index,
                'status': 'error'
            }), 200
        
        if led_index < 0 or led_index >= led_count:
            logger.warning(f"LED index {led_index} out of range (0-{led_count-1})")
            return jsonify({
                'error': 'Bad Request',
                'message': f'LED index must be between 0 and {led_count - 1}'
            }), 400
        
        # Light up the LED with specified color (persistent)
        logger.info(f"Lighting up LED {led_index} persistently with color RGB{color}")
        success, error = led_controller.turn_on_led(led_index, color, auto_show=True)
        logger.info(f"LED turn_on_led returned: success={success}, error={error}")
        
        if not success:
            logger.error(f"Failed to turn on LED: {error}")
        
        logger.info(f"LED {led_index} turned on persistently")
        return jsonify({
            'message': f'LED {led_index} turned on (persistent)',
            'led_index': led_index,
            'color': color
        }), 200
        
    except Exception as e:
        logger.error(f"Error turning on LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'message': f'LED {led_index} on requested',
            'led_index': led_index,
            'error': str(e)
        }), 200


def _turn_off_led_after_delay(led_index: int, delay_seconds: int):
    """Turn off LED after specified delay"""
    try:
        time.sleep(delay_seconds)
        led_controller = get_led_controller()
        if led_controller:
            led_controller.turn_off_led(led_index)
            logger.info(f"Test LED {led_index} turned off after {delay_seconds}s")
    except Exception as e:
        logger.error(f"Error turning off LED: {e}", exc_info=True)


@calibration_bp.route('/leds-on', methods=['POST'])
def turn_on_leds_batch():
    """Light up multiple LEDs with specified colors (batch operation)
    
    Request body (JSON):
    {
        "leds": [
            {"index": 0, "r": 150, "g": 0, "b": 100},
            {"index": 1, "r": 0, "g": 100, "b": 150},
            ...
        ]
    }
    
    Or simple array of indices (uses white as default):
    {
        "leds": [0, 1, 2, 3]
    }
    """
    logger.info("Batch LED on endpoint called")
    
    try:
        led_controller = get_led_controller()
        
        if not led_controller:
            logger.warning("LED controller is not available")
            return jsonify({
                'message': 'LED controller not available',
                'status': 'unavailable',
                'leds_turned_on': 0
            }), 200
        
        # Get LED count for validation
        try:
            led_count = led_controller.num_pixels
            logger.info(f"LED count: {led_count}")
        except AttributeError as attr_error:
            logger.error(f"LED controller has no num_pixels attribute: {attr_error}")
            return jsonify({
                'message': 'LED controller error',
                'status': 'error',
                'leds_turned_on': 0
            }), 200
        
        # Parse request body
        data = request.get_json()
        if not data or 'leds' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "leds" array'
            }), 400
        
        leds_data = data['leds']
        if not isinstance(leds_data, list):
            return jsonify({
                'error': 'Bad Request',
                'message': '"leds" must be an array'
            }), 400
        
        if len(leds_data) == 0:
            return jsonify({
                'message': 'No LEDs to turn on',
                'leds_turned_on': 0
            }), 200
        
        leds_turned_on = 0
        errors = []
        
        # Process each LED
        for led_item in leds_data:
            try:
                # Handle both simple index format and object format
                if isinstance(led_item, int):
                    led_index = led_item
                    color = (255, 255, 255)  # Default white
                elif isinstance(led_item, dict):
                    if 'index' not in led_item:
                        errors.append(f"LED object missing 'index' field")
                        continue
                    
                    led_index = int(led_item['index'])
                    r = int(led_item.get('r', 255))
                    g = int(led_item.get('g', 255))
                    b = int(led_item.get('b', 255))
                    
                    # Validate and clamp color values
                    r = max(0, min(255, r))
                    g = max(0, min(255, g))
                    b = max(0, min(255, b))
                    
                    color = (r, g, b)
                else:
                    errors.append(f"Invalid LED item format: {led_item}")
                    continue
                
                # Validate LED index
                if led_index < 0 or led_index >= led_count:
                    errors.append(f"LED index {led_index} out of range (0-{led_count-1})")
                    continue
                
                # Turn on the LED
                logger.debug(f"Turning on LED {led_index} with color RGB{color}")
                success, error = led_controller.turn_on_led(led_index, color, auto_show=False)
                
                if success:
                    leds_turned_on += 1
                else:
                    errors.append(f"LED {led_index}: {error}")
                
            except (ValueError, TypeError) as e:
                errors.append(f"Error processing LED item {led_item}: {str(e)}")
                continue
        
        # Call show once at the end to update all LEDs
        try:
            if leds_turned_on > 0:
                led_controller.show()
                logger.info(f"Batch operation complete: {leds_turned_on} LEDs turned on")
        except Exception as e:
            logger.error(f"Error calling show: {e}")
            errors.append(f"Error updating display: {str(e)}")
        
        response = {
            'message': f'Batch operation complete',
            'leds_turned_on': leds_turned_on,
            'total_requested': len(leds_data)
        }

        if errors:
            response['errors'] = errors

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in batch LED operation: {e}", exc_info=True)
        return jsonify({
            'message': 'Batch operation failed',
            'error': str(e),
            'leds_turned_on': 0
        }), 200


@calibration_bp.route('/distribution-mode', methods=['GET', 'POST'])
def distribution_mode():
    """Get or set LED distribution mode for piano-based key mapping
    
    GET: Returns current distribution mode and available modes
    POST: Sets new distribution mode and optionally applies new mapping
    
    Available modes:
    - "Piano Based (with overlap)": Allow LED sharing at boundaries (5-6 LEDs/key, smooth transitions)
    - "Piano Based (no overlap)": Tight allocation without LED sharing (3-4 LEDs/key, individual control)
    - "Physics-Based LED Detection": Uses physical geometry to detect LED-to-key overlap (adaptive, threshold-based)
    - "Custom": Reserved for future custom distribution patterns
    """
    try:
        settings_service = get_settings_service()
        
        if request.method == 'GET':
            # Return current distribution mode and options
            current_mode = settings_service.get_setting('calibration', 'distribution_mode', 'Piano Based (with overlap)')
            allow_led_sharing = settings_service.get_setting('calibration', 'allow_led_sharing', True)
            overhang_threshold = settings_service.get_setting('calibration', 'overhang_threshold_mm', 1.5)
            
            return jsonify({
                'current_mode': current_mode,
                'available_modes': [
                    'Piano Based (with overlap)',
                    'Piano Based (no overlap)',
                    'Physics-Based LED Detection',
                    'Custom'
                ],
                'mode_descriptions': {
                    'Piano Based (with overlap)': 'LEDs at key boundaries are shared for smooth transitions (5-6 LEDs per key)',
                    'Piano Based (no overlap)': 'Tight allocation without LED sharing (3-4 LEDs per key)',
                    'Physics-Based LED Detection': 'Uses physical geometry and overhang thresholds for adaptive allocation (best accuracy)',
                    'Custom': 'Use custom distribution configuration'
                },
                'allow_led_sharing': allow_led_sharing,
                'overhang_threshold_mm': overhang_threshold,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        
        elif request.method == 'POST':
            # Set new distribution mode
            data = request.get_json() or {}
            new_mode = data.get('mode', '').strip()
            apply_mapping = data.get('apply_mapping', False)
            overhang_threshold = data.get('overhang_threshold_mm', 1.5)
            
            # Validate mode
            valid_modes = ['Piano Based (with overlap)', 'Piano Based (no overlap)', 'Physics-Based LED Detection', 'Custom']
            if new_mode not in valid_modes:
                return jsonify({
                    'error': f"Invalid distribution mode '{new_mode}'",
                    'valid_modes': valid_modes,
                    'message': 'Distribution mode not changed'
                }), 400
            
            # Map mode to parameters
            if new_mode == 'Piano Based (with overlap)':
                allow_led_sharing = True
                use_physics_based = False
            elif new_mode == 'Piano Based (no overlap)':
                allow_led_sharing = False
                use_physics_based = False
            elif new_mode == 'Physics-Based LED Detection':
                allow_led_sharing = False  # Physics-based doesn't share
                use_physics_based = True
            else:  # Custom
                allow_led_sharing = True  # Default to with overlap for custom
                use_physics_based = False
            
            # Save distribution mode and settings
            settings_service.set_setting('calibration', 'distribution_mode', new_mode)
            settings_service.set_setting('calibration', 'allow_led_sharing', allow_led_sharing)
            if new_mode == 'Physics-Based LED Detection':
                settings_service.set_setting('calibration', 'overhang_threshold_mm', overhang_threshold)
            logger.info(f"Distribution mode changed to: {new_mode} (allow_led_sharing={allow_led_sharing}, "
                       f"physics_based={use_physics_based}, threshold={overhang_threshold}mm)")
            
            response = {
                'message': f'Distribution mode changed to: {new_mode}',
                'distribution_mode': new_mode,
                'allow_led_sharing': allow_led_sharing,
                'overhang_threshold_mm': overhang_threshold if use_physics_based else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # If apply_mapping is true, regenerate the mapping with new mode
            if apply_mapping:
                try:
                    if use_physics_based:
                        # Use physics-based allocation
                        from backend.services.physics_led_allocation import PhysicsBasedAllocationService
                        
                        start_led = settings_service.get_setting('calibration', 'start_led', 4)
                        end_led = settings_service.get_setting('calibration', 'end_led', 249)
                        led_density = settings_service.get_setting('led', 'leds_per_meter', 200)
                        led_width = settings_service.get_setting('led', 'physical_width_mm', 3.5)
                        
                        service = PhysicsBasedAllocationService(
                            led_density=led_density,
                            led_physical_width=led_width,
                            overhang_threshold_mm=overhang_threshold
                        )
                        
                        allocation_result = service.allocate_leds(
                            start_led=start_led,
                            end_led=end_led
                        )
                    else:
                        # Use traditional Piano Based algorithm
                        from backend.config_led_mapping_advanced import calculate_per_key_led_allocation
                        
                        piano_size = settings_service.get_setting('piano', 'size', '88-key')
                        start_led = settings_service.get_setting('calibration', 'start_led', 4)
                        end_led = settings_service.get_setting('calibration', 'end_led', 249)
                        leds_per_meter = settings_service.get_setting('led', 'leds_per_meter', 200)
                        
                        allocation_result = calculate_per_key_led_allocation(
                            leds_per_meter=leds_per_meter,
                            start_led=start_led,
                            end_led=end_led,
                            piano_size=piano_size,
                            allow_led_sharing=allow_led_sharing
                        )
                    
                    if allocation_result.get('success'):
                        stats = allocation_result.get('led_allocation_stats', {})
                        logger.info(f"New mapping generated with {stats.get('total_key_count', 0)} keys using {new_mode} mode")
                        
                        response['mapping_regenerated'] = True
                        response['mapping_stats'] = {
                            'total_keys_mapped': stats.get('total_key_count', 0),
                            'total_leds_used': stats.get('total_led_count', 0),
                            'avg_leds_per_key': stats.get('avg_leds_per_key', 0),
                            'distribution': stats.get('leds_per_key_distribution', {}),
                            'distribution_mode': new_mode,
                            'allow_led_sharing': allow_led_sharing
                        }
                        
                        # Add physics-specific stats if applicable
                        if use_physics_based and 'quality_metrics' in allocation_result:
                            response['mapping_stats']['quality_metrics'] = allocation_result['quality_metrics']
                            response['mapping_stats']['overall_quality'] = allocation_result['overall_quality']
                    else:
                        logger.warning(f"Mapping generation returned success=false")
                        response['warning'] = f"Mapping generation: {allocation_result.get('message', 'unknown issue')}"
                    
                except Exception as e:
                    logger.error(f"Error regenerating mapping: {e}", exc_info=True)
                    response['warning'] = f"Mapping regeneration failed: {str(e)}"
            
            return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error in distribution_mode endpoint: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Distribution mode operation failed'
        }), 500


@calibration_bp.route('/mapping-quality', methods=['GET', 'POST'])
def get_mapping_quality_recommendations():
    """
    Get detailed LED mapping quality analysis and recommendations.
    
    Provides real-time feedback about mapping quality during calibration setup.
    Uses the physical LED mapping algorithm to calculate actual coverage metrics.
    
    GET: Returns quality analysis for current settings
    POST: Analyzes proposed settings without applying them
    
    GET/POST parameters:
    - leds_per_meter (optional): LED strip density (60-200, default from settings)
    - start_led (optional): First LED index (default from settings)
    - end_led (optional): Last LED index (default from settings)
    - piano_size (optional): Piano size (default from settings)
    
    Returns:
        {
            'quality_analysis': {
                'quality_score': 0-100,
                'quality_level': 'poor'/'ok'/'good'/'excellent',
                'leds_per_key': float,
                'coverage_ratio': float,
                'warnings': [list of warnings],
                'recommendations': [list of suggestions]
            },
            'hardware_info': {
                'total_leds': int,
                'usable_leds': int,
                'start_led': int,
                'end_led': int,
                'led_spacing_mm': float
            },
            'piano_info': {
                'piano_size': str,
                'white_keys': int,
                'piano_width_mm': float
            },
            'physical_analysis': {
                'piano_coverage_ratio': float,
                'oversaturation': bool,
                'undersaturation': bool,
                'ideal_leds': int
            },
            'timestamp': ISO timestamp
        }
    """
    logger.info("Mapping quality recommendation endpoint called")
    
    try:
        settings_service = get_settings_service()
        
        # Get current or proposed settings
        if request.method == 'POST':
            data = request.get_json() or {}
            leds_per_meter = data.get('leds_per_meter')
            start_led = data.get('start_led')
            end_led = data.get('end_led')
            piano_size = data.get('piano_size')
        else:
            leds_per_meter = request.args.get('leds_per_meter')
            start_led = request.args.get('start_led')
            end_led = request.args.get('end_led')
            piano_size = request.args.get('piano_size')
        
        # Fall back to current settings if not provided
        if leds_per_meter is None:
            leds_per_meter = settings_service.get_setting('led', 'leds_per_meter', 60)
        else:
            leds_per_meter = int(leds_per_meter)
        
        if start_led is None:
            start_led = settings_service.get_setting('calibration', 'start_led', 0)
        else:
            start_led = int(start_led)
        
        if end_led is None:
            total_led_count = settings_service.get_setting('led', 'led_count', 300)
            end_led = settings_service.get_setting('calibration', 'end_led', total_led_count - 1)
        else:
            end_led = int(end_led)
        
        if piano_size is None:
            piano_size = settings_service.get_setting('piano', 'size', '88-key')
        
        logger.info(f"Analyzing mapping quality: "
                   f"leds_per_meter={leds_per_meter}, "
                   f"range=[{start_led},{end_led}], "
                   f"piano_size={piano_size}")
        
        # Call the physical LED mapping algorithm
        mapping_result = calculate_physical_led_mapping(
            leds_per_meter=leds_per_meter,
            start_led=start_led,
            end_led=end_led,
            piano_size=piano_size
        )
        
        if mapping_result.get('error'):
            logger.error(f"Mapping calculation error: {mapping_result['error']}")
            return jsonify({
                'error': 'Calculation Error',
                'message': mapping_result['error'],
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Extract quality information
        quality_analysis = {
            'quality_score': mapping_result.get('quality_score', 0),
            'quality_level': mapping_result.get('quality_level', 'unknown'),
            'leds_per_key': round(mapping_result.get('leds_per_key', 0), 2),
            'coverage_ratio': round(mapping_result.get('coverage_ratio', 0), 2),
            'warnings': mapping_result.get('warnings', []),
            'recommendations': mapping_result.get('recommendations', [])
        }
        
        hardware_info = {
            'total_leds': mapping_result.get('total_led_count', 0),
            'usable_leds': mapping_result.get('led_count_usable', 0),
            'start_led': mapping_result.get('first_led', start_led),
            'end_led': end_led,
            'led_spacing_mm': round(mapping_result.get('led_spacing_mm', 0), 2)
        }
        
        piano_info = {
            'piano_size': piano_size,
            'white_keys': mapping_result.get('white_key_count', 0),
            'piano_width_mm': round(mapping_result.get('piano_width_mm', 0), 2)
        }
        
        physical_analysis = {
            'piano_coverage_ratio': round(mapping_result.get('coverage_ratio', 0), 2),
            'oversaturation': mapping_result.get('coverage_ratio', 0) > 1.5,
            'undersaturation': mapping_result.get('coverage_ratio', 0) < 0.5,
            'ideal_leds': mapping_result.get('white_key_count', 0) * 3  # Approximate ideal
        }
        
        response = {
            'quality_analysis': quality_analysis,
            'hardware_info': hardware_info,
            'piano_info': piano_info,
            'physical_analysis': physical_analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add detailed metadata if available
        if 'metadata' in mapping_result:
            response['metadata'] = mapping_result['metadata']
        
        logger.info(f"Quality analysis complete: "
                   f"score={quality_analysis['quality_score']}, "
                   f"level={quality_analysis['quality_level']}, "
                   f"warnings={len(quality_analysis['warnings'])}")
        
        return jsonify(response), 200
        
    except ValueError as e:
        logger.error(f"Invalid parameter value: {e}")
        return jsonify({
            'error': 'Bad Request',
            'message': f'Invalid parameter: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 400
    except Exception as e:
        logger.error(f"Error calculating mapping quality: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to calculate mapping quality: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@calibration_bp.route('/advanced-mapping', methods=['GET', 'POST'])
def get_advanced_mapping_allocation():
    """
    Get per-key LED allocation based on physical positioning.
    
    This endpoint supports TWO MODES:
    1. WITH LED SHARING (default): Smooth transitions, 5-6 LEDs per key
    2. WITHOUT LED SHARING: Tight allocation, 3-4 LEDs per key
    
    Query parameters (GET) or JSON body (POST):
        - leds_per_meter: LED strip density (60, 72, 100, 120, 144, 160, 180, 200)
        - start_led: First LED index (default from settings)
        - end_led: Last LED index (default from settings)
        - piano_size: Piano size (default "88-key")
        - allow_led_sharing: bool, true for smooth transitions, false for tight allocation (default true)
    
    Returns:
        {
            "success": bool,
            "error": None or error message,
            "key_led_mapping": {
                0: [4, 5, 6, 7],      # Key 0 (A0) gets LEDs
                1: [7, 8, 9, 10],     # Key 1 (A#0) gets LEDs (with sharing: LED 7 shared with Key 0)
                ...
            },
            "led_allocation_stats": {
                "avg_leds_per_key": 3.78,
                "min_leds_per_key": 3,
                "max_leds_per_key": 4,
                "total_key_count": 88,
                "total_led_count": 246,
                "leds_per_key_distribution": {
                    3: 19,    # 19 keys get 3 LEDs
                    4: 69     # 69 keys get 4 LEDs
                }
            },
            "allow_led_sharing": bool (which mode was used),
            "warnings": [...],
            "improvements": [...],
            "timestamp": "2025-10-17T..."
        }
    """
    try:
        settings_service = get_settings_service()
        
        # Get parameters
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        # Extract parameters with defaults
        leds_per_meter = int(data.get('leds_per_meter', 
                                     settings_service.get_setting('led', 'leds_per_meter', 200)))
        start_led = int(data.get('start_led',
                                settings_service.get_setting('led', 'start_led', 4)))
        end_led = int(data.get('end_led',
                              settings_service.get_setting('led', 'end_led', 249)))
        piano_size = data.get('piano_size', '88-key')
        allow_led_sharing = data.get('allow_led_sharing', 'true').lower() == 'true'
        
        # Validate inputs
        if not isinstance(leds_per_meter, int) or leds_per_meter <= 0:
            return jsonify({
                'error': 'Bad Request',
                'message': 'leds_per_meter must be a positive integer',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if not isinstance(start_led, int) or not isinstance(end_led, int):
            return jsonify({
                'error': 'Bad Request',
                'message': 'start_led and end_led must be integers',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Import the advanced mapping function
        from backend.config_led_mapping_advanced import calculate_per_key_led_allocation
        
        # Calculate per-key allocation
        allocation_result = calculate_per_key_led_allocation(
            leds_per_meter=leds_per_meter,
            start_led=start_led,
            end_led=end_led,
            piano_size=piano_size,
            allow_led_sharing=allow_led_sharing
        )
        
        if not allocation_result['success']:
            logger.warning(f"Advanced mapping failed: {allocation_result.get('error', 'Unknown error')}")
            return jsonify({
                'error': 'Mapping Failed',
                'message': allocation_result.get('error', 'Could not create advanced LED allocation'),
                'warnings': allocation_result.get('warnings', []),
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Build response
        response = {
            'success': True,
            'error': None,
            'key_led_mapping': allocation_result['key_led_mapping'],
            'led_allocation_stats': allocation_result['led_allocation_stats'],
            'warnings': allocation_result.get('warnings', []),
            'improvements': allocation_result.get('improvements', []),
            'parameters': {
                'leds_per_meter': leds_per_meter,
                'start_led': start_led,
                'end_led': end_led,
                'piano_size': piano_size,
                'led_count': end_led - start_led + 1
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Advanced mapping calculated: "
                   f"leds_per_meter={leds_per_meter}, "
                   f"avg_leds_per_key={allocation_result['led_allocation_stats']['avg_leds_per_key']:.2f}, "
                   f"min={allocation_result['led_allocation_stats']['min_leds_per_key']}, "
                   f"max={allocation_result['led_allocation_stats']['max_leds_per_key']}")
        
        return jsonify(response), 200
        
    except ImportError as e:
        logger.error(f"Failed to import advanced mapping module: {e}")
        return jsonify({
            'error': 'Not Implemented',
            'message': 'Advanced mapping module not available',
            'timestamp': datetime.now().isoformat()
        }), 501
    except ValueError as e:
        logger.error(f"Invalid parameter value: {e}")
        return jsonify({
            'error': 'Bad Request',
            'message': f'Invalid parameter: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 400
    except Exception as e:
        logger.error(f"Error calculating advanced mapping: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to calculate advanced mapping: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@calibration_bp.route('/physical-analysis', methods=['GET', 'POST'])
def get_physical_analysis():
    """
    Get detailed physical geometry analysis of LED placement on piano keys.
    
    Uses sophisticated geometry calculations to analyze:
    - Per-key LED alignment symmetry (0.0-1.0 score)
    - LED coverage consistency across keys
    - Physical overhang amounts (left/right)
    - Overall placement quality per key
    - System-wide quality metrics
    
    GET: Analyzes current settings
    POST: Analyzes proposed settings without applying them
    
    Query parameters (GET) or JSON body (POST):
        - leds_per_meter: LED strip density (default from settings, 200)
        - led_physical_width: Physical width of each LED in mm (default 3.5)
        - led_strip_offset: Offset of LED center from strip edge in mm (default 1.75)
        - overhang_threshold: Minimum overhang to count LED (mm, default 1.5)
        - white_key_width: Piano white key width in mm (default 23.5)
        - black_key_width: Piano black key width in mm (default 13.7)
        - white_key_gap: Gap between white keys in mm (default 1.0)
        - start_led: First LED index (default from settings)
        - end_led: Last LED index (default from settings)
        - piano_size: Piano size (default "88-key")
    
    Returns comprehensive physical analysis object with per-key quality metrics.
    """
    logger.info("Physical analysis endpoint called")
    
    try:
        settings_service = get_settings_service()
        
        # Get parameters
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        # Extract parameters with defaults from settings or physical defaults
        leds_per_meter = int(float(data.get('leds_per_meter',
                                            settings_service.get_setting('led', 'leds_per_meter') or 200)))
        led_physical_width = float(data.get('led_physical_width',
                                           settings_service.get_setting('calibration', 'led_physical_width') or 3.5))
        # LED strip offset: only use explicit value if provided, otherwise let it default to led_physical_width/2
        led_strip_offset = None
        if 'led_strip_offset' in data:
            led_strip_offset = float(data['led_strip_offset'])
        elif settings_service.get_setting('calibration', 'led_strip_offset'):
            led_strip_offset = float(settings_service.get_setting('calibration', 'led_strip_offset'))
        # If still None, it will default to led_physical_width/2 in LEDPlacementCalculator
        
        overhang_threshold = float(data.get('overhang_threshold',
                                           settings_service.get_setting('calibration', 'led_overhang_threshold') or 1.5))
        white_key_width = float(data.get('white_key_width',
                                        settings_service.get_setting('calibration', 'white_key_width') or 22.0))
        black_key_width = float(data.get('black_key_width',
                                        settings_service.get_setting('calibration', 'black_key_width') or 12.0))
        white_key_gap = float(data.get('white_key_gap',
                                      settings_service.get_setting('calibration', 'white_key_gap') or 1.0))
        
        start_led = int(data.get('start_led',
                                settings_service.get_setting('calibration', 'start_led') or 4))
        end_led = int(data.get('end_led',
                              settings_service.get_setting('calibration', 'end_led') or 249))
        piano_size = data.get('piano_size', '88-key')
        
        logger.info(f"Physical analysis parameters: "
                   f"leds_per_meter={leds_per_meter}, "
                   f"led_physical_width={led_physical_width}, "
                   f"range=[{start_led},{end_led}], "
                   f"piano_size={piano_size}")
        
        # Get total LED count (physical strip size, not just usable range)
        total_led_count = settings_service.get_setting('led', 'led_count', 255)
        
        # Get current distribution mode AND allow_led_sharing setting
        distribution_mode = settings_service.get_setting('calibration', 'distribution_mode', 'Piano Based (with overlap)')
        allow_led_sharing = settings_service.get_setting('calibration', 'allow_led_sharing', True)
        
        logger.info(f"Physical analysis will use distribution_mode='{distribution_mode}', allow_led_sharing={allow_led_sharing}")
        
        # Generate LED mapping based on distribution mode (MATCHING /key-led-mapping logic)
        if distribution_mode == 'Physics-Based LED Detection':
            logger.info("Physical analysis using Physics-Based LED Detection mode")
            from backend.services.physics_led_allocation import PhysicsBasedAllocationService
            
            service = PhysicsBasedAllocationService(
                led_density=leds_per_meter,
                led_physical_width=led_physical_width,
                led_strip_offset=led_strip_offset,
                overhang_threshold_mm=overhang_threshold
            )
            
            # Apply geometry parameters
            service.analyzer.white_key_width = white_key_width
            service.analyzer.black_key_width = black_key_width
            service.analyzer.white_key_gap = white_key_gap
            
            allocation_result = service.allocate_leds(
                start_led=start_led,
                end_led=end_led
            )
        else:
            # Use traditional Piano-Based allocation with setting-respecting allow_led_sharing
            logger.info(f"Physical analysis using Piano-Based mode with allow_led_sharing={allow_led_sharing}")
            from backend.config_led_mapping_advanced import calculate_per_key_led_allocation
            
            allocation_result = calculate_per_key_led_allocation(
                leds_per_meter=leds_per_meter,
                start_led=start_led,
                end_led=end_led,
                piano_size=piano_size,
                allow_led_sharing=allow_led_sharing
            )
        
        if not allocation_result.get('success'):
            logger.error(f"Failed to generate mapping for analysis: {allocation_result.get('error')}")
            return jsonify({
                'error': 'Mapping Failed',
                'message': 'Could not generate LED mapping for physical analysis',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        key_led_mapping = allocation_result.get('key_led_mapping', {})

        
        # Import physical analysis module
        from backend.config_led_mapping_physical import PhysicalMappingAnalyzer
        
        # Create analyzer with the requested parameters
        analyzer = PhysicalMappingAnalyzer(
            led_density=leds_per_meter,
            led_physical_width=led_physical_width,
            led_strip_offset=led_strip_offset,
            overhang_threshold_mm=overhang_threshold,
            white_key_width=white_key_width,
            black_key_width=black_key_width,
            white_key_gap=white_key_gap
        )
        
        # Perform analysis (pass total LED count AND usable range)
        analysis_result = analyzer.analyze_mapping(
            key_led_mapping, 
            total_led_count,
            start_led=start_led,
            end_led=end_led
        )
        
        # For alignment with /key-led-mapping, also apply calibration offsets to the mapping
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
        converted_offsets = {}
        if key_offsets:
            for midi_note_str, offset_value in key_offsets.items():
                try:
                    midi_note = int(midi_note_str) if isinstance(midi_note_str, str) else midi_note_str
                    key_index = midi_note - 21
                    if 0 <= key_index < 88:
                        converted_offsets[key_index] = offset_value
                except (ValueError, TypeError):
                    pass
        
        # Apply calibration offsets to match /key-led-mapping behavior
        final_mapping = apply_calibration_offsets_to_mapping(
            mapping=key_led_mapping,
            start_led=start_led,
            end_led=end_led,
            key_offsets=converted_offsets,
            led_count=total_led_count
        )
        
        response = {
            'mapping': final_mapping,  # Include the actual key-led mapping with offsets applied
            'per_key_analysis': analysis_result['per_key_analysis'],
            'quality_metrics': analysis_result['quality_metrics'],
            'overall_quality': analysis_result['overall_quality'],
            'parameters_used': analysis_result['parameters_used'],
            'led_range': analysis_result['led_range'],
            'mapping_info': {
                'piano_size': piano_size,
                'start_led': start_led,
                'end_led': end_led,
                'total_keys': 88,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        logger.info(f"Physical analysis complete: "
                   f"overall_quality={analysis_result['overall_quality']}, "
                   f"avg_symmetry={analysis_result['quality_metrics']['avg_symmetry']:.4f}")
        
        return jsonify(response), 200
        
    except ImportError as e:
        logger.error(f"Failed to import physical analysis module: {e}")
        return jsonify({
            'error': 'Not Implemented',
            'message': 'Physical analysis module not available',
            'timestamp': datetime.now().isoformat()
        }), 501
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({
            'error': 'Bad Request',
            'message': f'Invalid parameter: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 400
    except Exception as e:
        logger.error(f"Error during physical analysis: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to perform physical analysis: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


@calibration_bp.route('/physics-parameters', methods=['GET', 'POST'])
def get_set_physics_parameters():
    """
    Get or set advanced physics-based parameters for LED allocation.
    
    GET: Returns current physics parameter values
    POST: Updates physics parameters and regenerates mapping if requested
    
    Parameters (all in millimeters):
    - white_key_width: Width of white piano keys (default 23.5mm)
    - black_key_width: Width of black piano keys (default 13.7mm)
    - white_key_gap: Gap between white keys (default 1.0mm)
    - led_physical_width: Physical width of each LED (default 3.5mm)
    - overhang_threshold_mm: Overhang threshold for LED detection (default 1.5mm)
    """
    try:
        settings_service = get_settings_service()
        
        if request.method == 'GET':
            # Return current physics parameters
            settings_service = get_settings_service()
            pitch_calibration_info = None
            
            # Try to get cached pitch calibration info from last successful allocation
            try:
                cached_pitch_json = settings_service.get_setting('calibration', 'last_pitch_calibration_info', None)
                if cached_pitch_json:
                    import json
                    pitch_calibration_info = json.loads(cached_pitch_json)
                    logger.info(f"[Pitch Debug] Retrieved cached pitch calibration info: {pitch_calibration_info}")
                else:
                    logger.info(f"[Pitch Debug] No cached pitch calibration info found")
            except Exception as e:
                logger.warning(f"[Pitch Debug] Could not retrieve cached pitch calibration: {e}")
            
            
            return jsonify({
                'physics_parameters': {
                    'white_key_width': settings_service.get_setting('calibration', 'white_key_width', 22.0),
                    'black_key_width': settings_service.get_setting('calibration', 'black_key_width', 12.0),
                    'white_key_gap': settings_service.get_setting('calibration', 'white_key_gap', 1.0),
                    'led_physical_width': settings_service.get_setting('calibration', 'led_physical_width', 3.5),
                    'overhang_threshold_mm': settings_service.get_setting('calibration', 'led_overhang_threshold', 1.5),
                },
                'parameter_ranges': {
                    'white_key_width': {'min': 18.5, 'max': 28.5, 'default': 22.0},
                    'black_key_width': {'min': 10.0, 'max': 20.0, 'default': 12.0},
                    'white_key_gap': {'min': 0.0, 'max': 3.0, 'default': 1.0},
                    'led_physical_width': {'min': 1.0, 'max': 10.0, 'default': 3.5},
                    'overhang_threshold_mm': {'min': 0.5, 'max': 5.0, 'default': 1.5},
                },
                'pitch_calibration_info': pitch_calibration_info,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        
        elif request.method == 'POST':
            # Update physics parameters
            data = request.get_json() or {}
            apply_mapping = data.get('apply_mapping', False)
            
            # Validate and save parameters
            params_to_save = {}
            for param_name in ['white_key_width', 'black_key_width', 'white_key_gap', 'led_physical_width']:
                if param_name in data:
                    try:
                        value = float(data[param_name])
                        params_to_save[param_name] = value
                    except (ValueError, TypeError):
                        return jsonify({
                            'error': f'Invalid value for {param_name}',
                            'message': f'Parameter must be a number'
                        }), 400
            
            # Handle overhang threshold (stored as led_overhang_threshold)
            if 'overhang_threshold_mm' in data:
                try:
                    value = float(data['overhang_threshold_mm'])
                    params_to_save['led_overhang_threshold'] = value
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid value for overhang_threshold_mm',
                        'message': 'Parameter must be a number'
                    }), 400
            
            # Save all parameters
            for param_name, value in params_to_save.items():
                logger.info(f"Setting physics parameter: {param_name} = {value}")
                settings_service.set_setting('calibration', param_name, value)
            
            response = {
                'message': f'Updated {len(params_to_save)} physics parameters',
                'parameters_updated': params_to_save,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Optionally regenerate mapping with new parameters
            if apply_mapping:
                try:
                    distribution_mode = settings_service.get_setting('calibration', 'distribution_mode', 'Piano Based (with overlap)')
                    
                    if distribution_mode == 'Physics-Based LED Detection':
                        # Regenerate physics-based mapping with new parameters
                        from backend.services.physics_led_allocation import PhysicsBasedAllocationService
                        
                        start_led = settings_service.get_setting('calibration', 'start_led', 4)
                        end_led = settings_service.get_setting('calibration', 'end_led', 249)
                        led_density = settings_service.get_setting('led', 'leds_per_meter', 200)
                        led_width = params_to_save.get('led_physical_width', settings_service.get_setting('calibration', 'led_physical_width', 3.5))
                        overhang_threshold = params_to_save.get('led_overhang_threshold', settings_service.get_setting('calibration', 'led_overhang_threshold', 1.5))
                        white_key_width = params_to_save.get('white_key_width', settings_service.get_setting('calibration', 'white_key_width', 22.0))
                        black_key_width = params_to_save.get('black_key_width', settings_service.get_setting('calibration', 'black_key_width', 12.0))
                        white_key_gap = params_to_save.get('white_key_gap', settings_service.get_setting('calibration', 'white_key_gap', 1.0))
                        
                        service = PhysicsBasedAllocationService(
                            led_density=led_density,
                            led_physical_width=led_width,
                            overhang_threshold_mm=overhang_threshold
                        )
                        
                        # Override geometry parameters in analyzer
                        service.analyzer.white_key_width = white_key_width
                        service.analyzer.black_key_width = black_key_width
                        service.analyzer.white_key_gap = white_key_gap
                        
                        allocation_result = service.allocate_leds(
                            start_led=start_led,
                            end_led=end_led
                        )
                        
                        if allocation_result.get('success'):
                            stats = allocation_result.get('led_allocation_stats', {})
                            response['mapping_regenerated'] = True
                            response['mapping_stats'] = {
                                'total_keys_mapped': stats.get('total_key_count', 0),
                                'total_leds_used': stats.get('total_led_count', 0),
                                'avg_leds_per_key': stats.get('avg_leds_per_key', 0),
                            }
                            
                            # Extract pitch calibration info directly from allocation result
                            # No need to re-analyze - allocate_leds already includes it
                            if 'pitch_calibration' in allocation_result:
                                response['pitch_calibration_info'] = allocation_result['pitch_calibration']
                                # Also cache it in settings for GET requests
                                import json
                                settings_service.set_setting('calibration', 'last_pitch_calibration_info', json.dumps(allocation_result['pitch_calibration']))
                                logger.info(f"Pitch calibration info included: was_adjusted={allocation_result['pitch_calibration'].get('was_adjusted', False)}")
                            
                            logger.info(f"Mapping regenerated with new physics parameters")
                        else:
                            response['warning'] = 'Mapping regeneration failed'
                    else:
                        logger.info(f"Skipping mapping regeneration: not using Physics-Based mode (current: {distribution_mode})")
                
                except Exception as e:
                    logger.error(f"Error regenerating mapping: {e}", exc_info=True)
                    response['warning'] = f'Mapping regeneration failed: {str(e)}'
            
            return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error in physics parameters endpoint: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Physics parameters operation failed'
        }), 500

