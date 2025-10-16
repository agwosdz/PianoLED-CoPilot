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
    get_piano_specs
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
        from backend.app import led_controller
        return led_controller
    except (ImportError, AttributeError):
        return None

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
            'start_led': settings_service.get_setting('calibration', 'start_led', 0),
            'end_led': settings_service.get_setting('calibration', 'end_led', 245),
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
    """Get the key-to-LED mapping with calibration offsets applied"""
    logger.info("GET /key-led-mapping endpoint called")
    
    try:
        settings_service = get_settings_service()
        
        # Get piano settings
        piano_size = settings_service.get_setting('piano', 'size', 88)
        led_count = settings_service.get_setting('led', 'led_count', 300)
        led_orientation = settings_service.get_setting('led', 'led_orientation', 'normal')
        mapping_base_offset = settings_service.get_setting('led', 'mapping_base_offset', 0)
        leds_per_key = settings_service.get_setting('led', 'leds_per_key', None)
        
        logger.info(f"Generated mapping with piano_size={piano_size}, led_count={led_count}, "
                   f"orientation={led_orientation}, mapping_base_offset={mapping_base_offset}")
        
        # Generate the base auto key-to-LED mapping
        auto_mapping = generate_auto_key_mapping(
            piano_size=piano_size,
            led_count=led_count,
            led_orientation=led_orientation,
            leds_per_key=leds_per_key,
            mapping_base_offset=mapping_base_offset
        )
        
        # Get calibration offsets
        global_offset = settings_service.get_setting('calibration', 'global_offset', 0)
        key_offsets = settings_service.get_setting('calibration', 'key_offsets', {})
        
        logger.info(f"Applying offsets: global_offset={global_offset}, key_offsets count={len(key_offsets)}")
        
        # Apply calibration offsets to the mapping (with bounds checking)
        final_mapping = apply_calibration_offsets_to_mapping(
            mapping=auto_mapping,
            global_offset=global_offset,
            key_offsets=key_offsets,
            led_count=led_count  # Pass led_count for bounds validation
        )
        
        logger.info(f"Successfully generated mapping with {len(final_mapping)} keys")
        
        return jsonify({
            'mapping': final_mapping,
            'piano_size': piano_size,
            'led_count': led_count,
            'global_offset': global_offset,
            'key_offsets_count': len(key_offsets),
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
        
        logger.info(f"Generating mapping info for {piano_size} with {led_count} LEDs")
        
        # Generate mapping
        mapping = generate_auto_key_mapping(
            piano_size=piano_size,
            led_count=led_count,
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
                'mapping_base_offset': base_offset,
                'available_leds': led_count - base_offset,
                'leds_per_key_setting': leds_per_key
            },
            'mapping_statistics': {
                'total_keys': specs['keys'],
                'mapped_keys': len(mapping),
                'unmapped_keys': specs['keys'] - len(mapping),
                'leds_used': total_leds_used,
                'leds_unused': led_count - total_leds_used,
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
    """Get or set LED distribution mode for auto mapping
    
    GET: Returns current distribution mode and available modes
    POST: Sets new distribution mode (and optionally applies new mapping)
    """
    try:
        settings_service = get_settings_service()
        
        if request.method == 'GET':
            # Return current distribution mode and options
            current_mode = settings_service.get_setting('calibration', 'distribution_mode', 'proportional')
            fixed_leds = settings_service.get_setting('calibration', 'fixed_leds_per_key', 3)
            
            return jsonify({
                'current_mode': current_mode,
                'available_modes': ['proportional', 'fixed', 'custom'],
                'mode_descriptions': {
                    'proportional': 'Distribute LEDs evenly across all keys (default)',
                    'fixed': 'Assign fixed number of LEDs per key',
                    'custom': 'Use custom distribution configuration'
                },
                'fixed_leds_per_key': fixed_leds,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        
        elif request.method == 'POST':
            # Set new distribution mode
            data = request.get_json() or {}
            new_mode = data.get('mode', '').lower()
            fixed_leds = data.get('fixed_leds_per_key')
            apply_mapping = data.get('apply_mapping', False)
            
            # Validate mode
            valid_modes = ['proportional', 'fixed', 'custom']
            if new_mode not in valid_modes:
                return jsonify({
                    'error': f"Invalid distribution mode '{new_mode}'",
                    'valid_modes': valid_modes,
                    'message': 'Distribution mode not changed'
                }), 400
            
            # Save distribution mode
            settings_service.set_setting('calibration', 'distribution_mode', new_mode)
            logger.info(f"Distribution mode changed to: {new_mode}")
            
            # Handle fixed mode settings
            if new_mode == 'fixed' and fixed_leds is not None:
                try:
                    fixed_leds = int(fixed_leds)
                    if fixed_leds < 1 or fixed_leds > 10:
                        return jsonify({
                            'error': f"fixed_leds_per_key must be between 1 and 10, got {fixed_leds}",
                            'message': 'Setting not applied'
                        }), 400
                    
                    settings_service.set_setting('calibration', 'fixed_leds_per_key', fixed_leds)
                    logger.info(f"Fixed LEDs per key set to: {fixed_leds}")
                except (ValueError, TypeError):
                    return jsonify({
                        'error': f"fixed_leds_per_key must be an integer",
                        'message': 'Setting not applied'
                    }), 400
            
            response = {
                'message': f'Distribution mode changed to: {new_mode}',
                'distribution_mode': new_mode,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # If apply_mapping is true, regenerate the mapping with new mode
            if apply_mapping:
                try:
                    piano_size = settings_service.get_setting('piano', 'size', '88-key')
                    led_count = settings_service.get_setting('led', 'led_count', 246)
                    base_offset = settings_service.get_setting('calibration', 'mapping_base_offset', 0)
                    
                    # Get leds_per_key if in fixed mode
                    leds_per_key = None
                    if new_mode == 'fixed':
                        leds_per_key = settings_service.get_setting('calibration', 'fixed_leds_per_key', 3)
                    
                    # Generate new mapping
                    new_mapping = generate_auto_key_mapping(
                        piano_size,
                        led_count,
                        leds_per_key=leds_per_key,
                        mapping_base_offset=base_offset,
                        distribution_mode=new_mode
                    )
                    
                    logger.info(f"New mapping generated with {len(new_mapping)} keys using {new_mode} mode")
                    
                    response['mapping_regenerated'] = True
                    response['mapping_stats'] = {
                        'total_keys_mapped': len(new_mapping),
                        'piano_size': piano_size,
                        'distribution_mode': new_mode,
                        'base_offset': base_offset
                    }
                    
                except Exception as e:
                    logger.error(f"Error regenerating mapping: {e}")
                    response['warning'] = f"Mapping regeneration failed: {str(e)}"
            
            return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error in distribution_mode endpoint: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Distribution mode operation failed'
        }), 500
