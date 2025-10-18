#!/usr/bin/env python3
"""
Weld Offset Management API endpoints for LED strip calibration
Handles LED strip weld/joint offsets for accounting for density discontinuities at solder points
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from datetime import datetime
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Create blueprint for weld offset endpoints
weld_bp = Blueprint('weld', __name__, url_prefix='/api/calibration/weld')

def get_settings_service():
    """Get the global settings service instance"""
    try:
        from backend.app import settings_service
        return settings_service
    except ImportError:
        logger.error("Settings service not available")
        return None

def get_socketio():
    """Get the global socketio instance"""
    try:
        from backend.app import socketio
        return socketio
    except ImportError:
        logger.warning("SocketIO not available")
        return None

def broadcast_weld_update(event_type: str, data: Dict[str, Any]):
    """Broadcast weld offset update via WebSocket"""
    socketio = get_socketio()
    if socketio:
        try:
            socketio.emit('weld_offset_updated', {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }, namespace='/socket.io/')
            logger.debug(f"Broadcasted weld update: {event_type}")
        except Exception as e:
            logger.warning(f"Failed to broadcast weld update: {e}")


@weld_bp.route('/offsets', methods=['GET'])
def get_all_weld_offsets():
    """
    Get all LED strip weld offsets
    
    Returns:
        {
            'success': bool,
            'weld_offsets': {led_index: offset_mm, ...},
            'total_welds': int,
            'timestamp': ISO8601
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        weld_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        
        logger.info(f"Retrieved {len(weld_offsets)} weld offset configurations")
        
        return jsonify({
            'success': True,
            'weld_offsets': weld_offsets,
            'total_welds': len(weld_offsets),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving weld offsets: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve weld offsets'
        }), 500


@weld_bp.route('/offset/<int:led_index>', methods=['GET'])
def get_weld_offset(led_index: int):
    """
    Get weld offset for a specific LED index
    
    Args:
        led_index: LED index where weld occurs
    
    Returns:
        {
            'success': bool,
            'led_index': int,
            'offset_mm': float or null,
            'has_weld': bool
        }
    """
    try:
        if led_index < 0:
            return jsonify({
                'error': 'Invalid LED index',
                'message': 'LED index must be non-negative'
            }), 400
        
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        weld_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        led_index_str = str(led_index)
        
        has_weld = led_index_str in weld_offsets
        offset_value = weld_offsets.get(led_index_str, None)
        
        logger.info(f"Retrieved weld offset for LED {led_index}: {offset_value}mm" if has_weld else f"No weld at LED {led_index}")
        
        return jsonify({
            'success': True,
            'led_index': led_index,
            'offset_mm': offset_value,
            'has_weld': has_weld,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving weld offset for LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': f'Failed to retrieve weld offset for LED {led_index}'
        }), 500


@weld_bp.route('/offset/<int:led_index>', methods=['POST', 'PUT'])
def set_weld_offset(led_index: int):
    """
    Create or update a weld offset at a specific LED index
    
    Args:
        led_index: LED index where weld occurs
    
    Request body:
        {
            'offset_mm': float (required) - Weld offset in millimeters
                        Positive: LEDs after weld move forward
                        Negative: LEDs after weld move backward
                        0: No offset (removes weld if exists)
            'description': str (optional) - Human description of the weld
        }
    
    Returns:
        {
            'success': bool,
            'led_index': int,
            'offset_mm': float,
            'action': 'created'|'updated'|'removed',
            'message': str,
            'timestamp': ISO8601
        }
    """
    try:
        if led_index < 0:
            return jsonify({
                'error': 'Invalid LED index',
                'message': 'LED index must be non-negative'
            }), 400
        
        data = request.get_json() or {}
        
        if 'offset_mm' not in data:
            return jsonify({
                'error': 'Missing required field',
                'message': 'offset_mm is required'
            }), 400
        
        try:
            offset_mm = float(data['offset_mm'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid offset value',
                'message': 'offset_mm must be a number (float)'
            }), 400
        
        # Validate offset range (typically -5 to +5mm for LED strip welds)
        if not (-10.0 <= offset_mm <= 10.0):
            return jsonify({
                'error': 'Offset out of range',
                'message': 'offset_mm must be between -10.0 and +10.0 mm'
            }), 400
        
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        weld_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        led_index_str = str(led_index)
        had_weld = led_index_str in weld_offsets
        
        if offset_mm == 0:
            # Remove weld if offset is 0
            if led_index_str in weld_offsets:
                del weld_offsets[led_index_str]
                settings_service.set_setting('calibration', 'led_weld_offsets', weld_offsets)
                
                logger.info(f"Removed weld offset at LED {led_index}")
                
                broadcast_weld_update('weld_removed', {
                    'led_index': led_index,
                    'description': data.get('description', '')
                })
                
                return jsonify({
                    'success': True,
                    'led_index': led_index,
                    'offset_mm': 0,
                    'action': 'removed',
                    'message': f'Weld offset at LED {led_index} removed',
                    'timestamp': datetime.utcnow().isoformat()
                }), 200
            else:
                return jsonify({
                    'error': 'Weld not found',
                    'message': f'No weld offset exists at LED {led_index}'
                }), 404
        else:
            # Create or update weld
            weld_offsets[led_index_str] = offset_mm
            settings_service.set_setting('calibration', 'led_weld_offsets', weld_offsets)
            
            action = 'updated' if had_weld else 'created'
            logger.info(f"Weld offset at LED {led_index}: {action} to {offset_mm}mm")
            
            broadcast_weld_update('weld_' + action, {
                'led_index': led_index,
                'offset_mm': offset_mm,
                'description': data.get('description', '')
            })
            
            return jsonify({
                'success': True,
                'led_index': led_index,
                'offset_mm': offset_mm,
                'action': action,
                'message': f'Weld offset at LED {led_index} {action}: {offset_mm}mm',
                'timestamp': datetime.utcnow().isoformat()
            }), 200 if had_weld else 201
    
    except Exception as e:
        logger.error(f"Error setting weld offset at LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': f'Failed to set weld offset at LED {led_index}'
        }), 500


@weld_bp.route('/offset/<int:led_index>', methods=['DELETE'])
def delete_weld_offset(led_index: int):
    """
    Delete a weld offset at a specific LED index
    
    Args:
        led_index: LED index where weld offset should be removed
    
    Returns:
        {
            'success': bool,
            'led_index': int,
            'message': str,
            'timestamp': ISO8601
        }
    """
    try:
        if led_index < 0:
            return jsonify({
                'error': 'Invalid LED index',
                'message': 'LED index must be non-negative'
            }), 400
        
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        weld_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        led_index_str = str(led_index)
        
        if led_index_str not in weld_offsets:
            return jsonify({
                'error': 'Weld not found',
                'message': f'No weld offset exists at LED {led_index}'
            }), 404
        
        removed_offset = weld_offsets.pop(led_index_str)
        settings_service.set_setting('calibration', 'led_weld_offsets', weld_offsets)
        
        logger.info(f"Deleted weld offset at LED {led_index} (was {removed_offset}mm)")
        
        broadcast_weld_update('weld_deleted', {
            'led_index': led_index,
            'previous_offset_mm': removed_offset
        })
        
        return jsonify({
            'success': True,
            'led_index': led_index,
            'deleted_offset_mm': removed_offset,
            'message': f'Weld offset at LED {led_index} deleted',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting weld offset at LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': f'Failed to delete weld offset at LED {led_index}'
        }), 500


@weld_bp.route('/offsets/bulk', methods=['PUT'])
def set_all_weld_offsets():
    """
    Set all weld offsets at once (replaces existing configuration)
    
    Request body:
        {
            'weld_offsets': {led_index: offset_mm, ...},
            'append': bool (optional, default: false) - If true, merge with existing offsets
        }
    
    Returns:
        {
            'success': bool,
            'total_welds': int,
            'created': int,
            'updated': int,
            'removed': int,
            'message': str,
            'timestamp': ISO8601
        }
    """
    try:
        data = request.get_json() or {}
        
        if 'weld_offsets' not in data:
            return jsonify({
                'error': 'Missing required field',
                'message': 'weld_offsets dict is required'
            }), 400
        
        if not isinstance(data['weld_offsets'], dict):
            return jsonify({
                'error': 'Invalid type',
                'message': 'weld_offsets must be a dictionary'
            }), 400
        
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        append_mode = data.get('append', False)
        new_offsets = {}
        errors = []
        
        # Validate and normalize all provided offsets
        for led_idx_str, offset_val in data['weld_offsets'].items():
            try:
                led_idx = int(led_idx_str) if isinstance(led_idx_str, str) else led_idx_str
                offset_mm = float(offset_val)
                
                if led_idx < 0:
                    errors.append(f"LED {led_idx}: Index must be non-negative")
                    continue
                
                if not (-10.0 <= offset_mm <= 10.0):
                    errors.append(f"LED {led_idx}: Offset {offset_mm}mm out of range [-10, +10]")
                    continue
                
                new_offsets[str(led_idx)] = offset_mm
            
            except (ValueError, TypeError) as e:
                errors.append(f"LED {led_idx_str}: Invalid value - {str(e)}")
                continue
        
        if errors:
            logger.warning(f"Validation errors in bulk weld offset update: {errors}")
        
        # Get existing offsets if append mode
        if append_mode:
            existing_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
            combined_offsets = dict(existing_offsets)
            combined_offsets.update(new_offsets)
            final_offsets = combined_offsets
        else:
            final_offsets = new_offsets
        
        # Calculate stats
        old_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        created = sum(1 for k in final_offsets if k not in old_offsets)
        updated = sum(1 for k in final_offsets if k in old_offsets and final_offsets[k] != old_offsets[k])
        removed = sum(1 for k in old_offsets if k not in final_offsets)
        
        # Save new offsets
        settings_service.set_setting('calibration', 'led_weld_offsets', final_offsets)
        
        logger.info(f"Bulk weld offset update: created={created}, updated={updated}, removed={removed}, "
                   f"total={len(final_offsets)}, append_mode={append_mode}")
        
        broadcast_weld_update('weld_bulk_update', {
            'total_welds': len(final_offsets),
            'created': created,
            'updated': updated,
            'removed': removed,
            'append_mode': append_mode
        })
        
        return jsonify({
            'success': True,
            'total_welds': len(final_offsets),
            'created': created,
            'updated': updated,
            'removed': removed,
            'weld_offsets': final_offsets,
            'validation_errors': errors if errors else None,
            'message': f'Bulk update complete: {created} created, {updated} updated, {removed} removed',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error in bulk weld offset update: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Bulk weld offset update failed'
        }), 500


@weld_bp.route('/offsets', methods=['DELETE'])
def clear_all_weld_offsets():
    """
    Clear all weld offset configurations
    
    Returns:
        {
            'success': bool,
            'previous_count': int,
            'message': str,
            'timestamp': ISO8601
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        old_offsets = settings_service.get_setting('calibration', 'led_weld_offsets', {})
        previous_count = len(old_offsets)
        
        settings_service.set_setting('calibration', 'led_weld_offsets', {})
        
        logger.info(f"Cleared all weld offsets (removed {previous_count} entries)")
        
        broadcast_weld_update('weld_all_cleared', {
            'previous_count': previous_count
        })
        
        return jsonify({
            'success': True,
            'previous_count': previous_count,
            'message': f'All {previous_count} weld offset configurations cleared',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error clearing all weld offsets: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Failed to clear weld offsets'
        }), 500


@weld_bp.route('/validate', methods=['POST'])
def validate_weld_config():
    """
    Validate a proposed weld configuration without saving it
    
    Request body:
        {
            'weld_offsets': {led_index: offset_mm, ...}
        }
    
    Returns:
        {
            'valid': bool,
            'errors': [str],
            'warnings': [str],
            'affected_leds': [int],
            'coverage': {'first_led': int, 'last_led': int},
            'statistics': {...}
        }
    """
    try:
        data = request.get_json() or {}
        
        if 'weld_offsets' not in data:
            return jsonify({
                'error': 'Missing required field',
                'message': 'weld_offsets dict is required'
            }), 400
        
        if not isinstance(data['weld_offsets'], dict):
            return jsonify({
                'error': 'Invalid type',
                'message': 'weld_offsets must be a dictionary'
            }), 400
        
        weld_offsets = data['weld_offsets']
        errors = []
        warnings = []
        valid_welds = {}
        
        # Validate each weld configuration
        for led_idx_str, offset_val in weld_offsets.items():
            try:
                led_idx = int(led_idx_str) if isinstance(led_idx_str, str) else led_idx_str
                offset_mm = float(offset_val)
                
                if led_idx < 0:
                    errors.append(f"LED {led_idx}: Index must be non-negative")
                    continue
                
                if not (-10.0 <= offset_mm <= 10.0):
                    errors.append(f"LED {led_idx}: Offset {offset_mm}mm out of range [-10, +10]")
                    continue
                
                if offset_mm == 0:
                    warnings.append(f"LED {led_idx}: Offset is 0 (no effect)")
                
                valid_welds[led_idx] = offset_mm
            
            except (ValueError, TypeError) as e:
                errors.append(f"LED {led_idx_str}: Invalid value - {str(e)}")
                continue
        
        # Calculate coverage
        if valid_welds:
            first_led = min(valid_welds.keys())
            last_led = max(valid_welds.keys())
            affected_leds = sorted(valid_welds.keys())
        else:
            first_led = None
            last_led = None
            affected_leds = []
        
        # Calculate statistics
        positive_offsets = [v for v in valid_welds.values() if v > 0]
        negative_offsets = [v for v in valid_welds.values() if v < 0]
        
        statistics = {
            'total_welds': len(valid_welds),
            'positive_offset_count': len(positive_offsets),
            'negative_offset_count': len(negative_offsets),
            'zero_offset_count': len([v for v in valid_welds.values() if v == 0]),
            'max_positive_offset_mm': max(positive_offsets) if positive_offsets else 0,
            'max_negative_offset_mm': min(negative_offsets) if negative_offsets else 0,
            'avg_offset_magnitude_mm': sum(abs(v) for v in valid_welds.values()) / len(valid_welds) if valid_welds else 0
        }
        
        is_valid = len(errors) == 0
        
        logger.info(f"Validated weld configuration: {len(valid_welds)} welds, valid={is_valid}, "
                   f"errors={len(errors)}, warnings={len(warnings)}")
        
        return jsonify({
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'affected_leds': affected_leds,
            'coverage': {
                'first_led': first_led,
                'last_led': last_led
            } if first_led is not None else None,
            'statistics': statistics,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error validating weld configuration: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Weld configuration validation failed'
        }), 500
