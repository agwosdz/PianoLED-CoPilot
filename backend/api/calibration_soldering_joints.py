#!/usr/bin/env python3
"""
Soldering Joint Management API endpoints for LED strip calibration.

Handles LED strip soldering joint configuration including physical width,
offset compensation, and unit conversion between mm and LED indices.

Provides CRUD operations, unit conversion, validation, and WebSocket broadcasting.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from backend.logging_config import get_logger
from backend.utils.soldering_joint_converter import (
    mm_to_leds,
    leds_to_mm,
    normalize_offset,
    validate_offset,
    get_joint_width_in_leds,
    get_joint_statistics
)

logger = get_logger(__name__)

# Create blueprint for soldering joint endpoints
joint_bp = Blueprint('soldering_joints', __name__, url_prefix='/api/calibration/soldering-joints')

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

def get_leds_per_meter() -> int:
    """Get configured LEDs per meter from settings"""
    settings_service = get_settings_service()
    if settings_service:
        try:
            leds_per_meter = settings_service.get_setting('led', 'leds_per_meter', 200)
            return max(1, int(leds_per_meter))
        except Exception as e:
            logger.warning(f"Failed to get leds_per_meter: {e}, using default 200")
    return 200

def broadcast_joint_update(event_type: str, data: Dict[str, Any]):
    """Broadcast soldering joint update via WebSocket"""
    socketio = get_socketio()
    if socketio:
        try:
            socketio.emit('soldering_joint_updated', {
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }, namespace='/socket.io/')
            logger.debug(f"Broadcasted soldering joint update: {event_type}")
        except Exception as e:
            logger.warning(f"Failed to broadcast joint update: {e}")


@joint_bp.route('/offsets', methods=['GET'])
def get_all_soldering_joints():
    """
    Get all LED strip soldering joints.
    
    Returns:
        {
            'success': bool,
            'joints': {led_index: {width_mm, offset_mm, description?, ...}},
            'count': int,
            'statistics': {...},
            'timestamp': ISO8601
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        joints = settings_service.get_setting('calibration', 'led_soldering_joints', {})
        leds_per_meter = get_leds_per_meter()
        stats = get_joint_statistics(joints, leds_per_meter)
        
        logger.info(f"Retrieved {len(joints)} soldering joint configurations")
        
        return jsonify({
            'success': True,
            'joints': joints,
            'count': len(joints),
            'statistics': stats,
            'leds_per_meter': leds_per_meter,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving soldering joints: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve soldering joints'
        }), 500


@joint_bp.route('/offset/<int:led_index>', methods=['GET'])
def get_soldering_joint(led_index: int):
    """
    Get soldering joint details for a specific LED index.
    
    Args:
        led_index: LED index where joint occurs
    
    Returns:
        {
            'success': bool,
            'led_index': int,
            'width_mm': float or null,
            'offset_mm': float or null,
            'offset_leds': int or null,
            'description': str or null,
            'has_joint': bool,
            'created_at': ISO8601,
            'updated_at': ISO8601
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        joints = settings_service.get_setting('calibration', 'led_soldering_joints', {}) or {}
        leds_per_meter = get_leds_per_meter()
        
        if str(led_index) not in joints:
            return jsonify({
                'success': True,
                'led_index': led_index,
                'has_joint': False,
                'width_mm': None,
                'offset_mm': None,
                'offset_leds': None,
                'description': None
            }), 200
        
        joint = joints[str(led_index)]
        offset_mm = joint.get('offset_mm', 0)
        offset_leds = mm_to_leds(offset_mm, leds_per_meter)
        
        return jsonify({
            'success': True,
            'led_index': led_index,
            'has_joint': True,
            'width_mm': joint.get('width_mm'),
            'offset_mm': offset_mm,
            'offset_leds': offset_leds,
            'description': joint.get('description'),
            'created_at': joint.get('created_at'),
            'updated_at': joint.get('updated_at')
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving joint at LED {led_index}: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': f'Failed to retrieve joint at LED {led_index}'}), 500


@joint_bp.route('/offset/<int:led_index>', methods=['POST', 'PUT'])
def create_or_update_soldering_joint(led_index: int):
    """
    Create or update a soldering joint at the specified LED index.
    
    Request body:
        {
            'width_mm': float,           # Physical width of joint in mm
            'offset_mm': float,          # Offset at joint in mm
            'description': string?       # Optional description
        }
    
    Returns:
        {
            'success': bool,
            'action': 'created' | 'updated',
            'led_index': int,
            'width_mm': float,
            'offset_mm': float,
            'offset_leds': int,
            'message': str
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        data = request.get_json() or {}
        
        # Validate required fields
        if 'width_mm' not in data or 'offset_mm' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "width_mm" and "offset_mm"'
            }), 400
        
        try:
            width_mm = float(data['width_mm'])
            offset_mm = float(data['offset_mm'])
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Validation Error',
                'message': 'width_mm and offset_mm must be numbers'
            }), 400
        
        # Validate ranges
        if width_mm <= 0 or width_mm > 50:
            return jsonify({
                'error': 'Validation Error',
                'message': 'width_mm must be between 0.1 and 50 mm'
            }), 400
        
        is_valid, error_msg = validate_offset(offset_mm, 'mm', leds_per_meter=get_leds_per_meter())
        if not is_valid:
            return jsonify({
                'error': 'Validation Error',
                'message': error_msg
            }), 400
        
        # Get current joints
        joints = settings_service.get_setting('calibration', 'led_soldering_joints', {}) or {}
        
        # Check if joint already exists
        was_update = str(led_index) in joints
        
        # Create/update joint entry
        timestamp = datetime.utcnow().isoformat()
        joints[str(led_index)] = {
            'width_mm': width_mm,
            'offset_mm': offset_mm,
            'description': data.get('description', ''),
            'created_at': joints.get(str(led_index), {}).get('created_at', timestamp),
            'updated_at': timestamp
        }
        
        # Save
        settings_service.set_setting('calibration', 'led_soldering_joints', joints)
        settings_service.set_setting('calibration', 'last_calibration', timestamp)
        
        # Broadcast
        leds_per_meter = get_leds_per_meter()
        offset_leds = mm_to_leds(offset_mm, leds_per_meter)
        
        broadcast_joint_update(
            'created' if not was_update else 'updated',
            {
                'led_index': led_index,
                'width_mm': width_mm,
                'offset_mm': offset_mm,
                'offset_leds': offset_leds
            }
        )
        
        action = 'created' if not was_update else 'updated'
        logger.info(f"Soldering joint {action} at LED {led_index}: {width_mm}mm width, {offset_mm}mm offset")
        
        return jsonify({
            'success': True,
            'action': action,
            'led_index': led_index,
            'width_mm': width_mm,
            'offset_mm': offset_mm,
            'offset_leds': offset_leds,
            'message': f'Soldering joint {action} successfully'
        }), 201 if not was_update else 200
    
    except Exception as e:
        logger.error(f"Error creating/updating joint at LED {led_index}: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to save joint at LED {led_index}'
        }), 500


@joint_bp.route('/offset/<int:led_index>', methods=['DELETE'])
def delete_soldering_joint(led_index: int):
    """
    Delete a soldering joint.
    
    Returns:
        {
            'success': bool,
            'message': str,
            'deleted_led_index': int
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        joints = settings_service.get_setting('calibration', 'led_soldering_joints', {}) or {}
        
        if str(led_index) not in joints:
            return jsonify({
                'error': 'Not Found',
                'message': f'No soldering joint found at LED {led_index}'
            }), 404
        
        # Delete
        del joints[str(led_index)]
        settings_service.set_setting('calibration', 'led_soldering_joints', joints)
        settings_service.set_setting('calibration', 'last_calibration', datetime.utcnow().isoformat())
        
        # Broadcast
        broadcast_joint_update('deleted', {'led_index': led_index})
        
        logger.info(f"Soldering joint deleted at LED {led_index}")
        
        return jsonify({
            'success': True,
            'message': f'Soldering joint at LED {led_index} deleted successfully',
            'deleted_led_index': led_index
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting joint at LED {led_index}: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': f'Failed to delete joint at LED {led_index}'}), 500


@joint_bp.route('/offsets/bulk', methods=['PUT'])
def bulk_configure_joints():
    """
    Bulk configure multiple soldering joints.
    
    Request body:
        {
            'joints': {
                '100': {'width_mm': 2.5, 'offset_mm': 3.5},
                '200': {'width_mm': 2.0, 'offset_mm': -1.0}
            },
            'mode': 'replace' | 'append'  # Default: 'replace'
        }
    
    Returns:
        {
            'success': bool,
            'created': int,
            'updated': int,
            'total': int,
            'message': str
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        data = request.get_json() or {}
        
        if 'joints' not in data:
            return jsonify({'error': 'Bad Request', 'message': 'Request must include "joints"'}), 400
        
        mode = data.get('mode', 'replace').lower()
        if mode not in ('replace', 'append'):
            return jsonify({'error': 'Bad Request', 'message': 'mode must be "replace" or "append"'}), 400
        
        new_joints = data['joints']
        if not isinstance(new_joints, dict):
            return jsonify({'error': 'Bad Request', 'message': 'joints must be a dictionary'}), 400
        
        # Get current joints
        current_joints = settings_service.get_setting('calibration', 'led_soldering_joints', {}) or {}
        
        # Start with current or empty based on mode
        result_joints = {} if mode == 'replace' else dict(current_joints)
        
        created = 0
        updated = 0
        timestamp = datetime.utcnow().isoformat()
        leds_per_meter = get_leds_per_meter()
        
        # Process each joint
        for led_idx_str, joint_data in new_joints.items():
            try:
                led_idx = int(led_idx_str)
                
                if not isinstance(joint_data, dict):
                    logger.warning(f"Skipping invalid joint entry at LED {led_idx}: not a dict")
                    continue
                
                width_mm = float(joint_data.get('width_mm', 2.0))
                offset_mm = float(joint_data.get('offset_mm', 0.0))
                
                if width_mm <= 0 or width_mm > 50:
                    logger.warning(f"Skipping joint at LED {led_idx}: invalid width {width_mm}mm")
                    continue
                
                was_update = str(led_idx) in result_joints
                
                result_joints[str(led_idx)] = {
                    'width_mm': width_mm,
                    'offset_mm': offset_mm,
                    'description': joint_data.get('description', ''),
                    'created_at': result_joints.get(str(led_idx), {}).get('created_at', timestamp),
                    'updated_at': timestamp
                }
                
                if was_update:
                    updated += 1
                else:
                    created += 1
            
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid joint entry {led_idx_str}: {e}")
                continue
        
        # Save
        settings_service.set_setting('calibration', 'led_soldering_joints', result_joints)
        settings_service.set_setting('calibration', 'last_calibration', timestamp)
        
        # Broadcast
        broadcast_joint_update('bulk_updated', {
            'mode': mode,
            'created': created,
            'updated': updated,
            'total': len(result_joints)
        })
        
        logger.info(f"Bulk joint configuration: created={created}, updated={updated}, total={len(result_joints)}")
        
        return jsonify({
            'success': True,
            'created': created,
            'updated': updated,
            'total': len(result_joints),
            'message': f'Bulk configuration complete: {created} created, {updated} updated'
        }), 200
    
    except Exception as e:
        logger.error(f"Error in bulk joint configuration: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Failed to bulk configure joints'}), 500


@joint_bp.route('/offsets', methods=['DELETE'])
def delete_all_joints():
    """
    Delete all soldering joints.
    
    Returns:
        {
            'success': bool,
            'deleted_count': int,
            'message': str
        }
    """
    try:
        settings_service = get_settings_service()
        if not settings_service:
            return jsonify({'error': 'Settings service unavailable'}), 503
        
        joints = settings_service.get_setting('calibration', 'led_soldering_joints', {}) or {}
        count = len(joints)
        
        settings_service.set_setting('calibration', 'led_soldering_joints', {})
        settings_service.set_setting('calibration', 'last_calibration', datetime.utcnow().isoformat())
        
        broadcast_joint_update('cleared', {'deleted_count': count})
        
        logger.info(f"Cleared all {count} soldering joints")
        
        return jsonify({
            'success': True,
            'deleted_count': count,
            'message': f'Deleted {count} soldering joints'
        }), 200
    
    except Exception as e:
        logger.error(f"Error clearing joints: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Failed to clear joints'}), 500


@joint_bp.route('/convert-offset', methods=['POST'])
def convert_offset_units():
    """
    Convert offset between mm and LED units.
    
    Request body:
        {
            'value': float,
            'from_unit': 'mm' | 'led',
            'to_unit': 'mm' | 'led'
        }
    
    Returns:
        {
            'success': bool,
            'value_mm': float,
            'value_leds': int,
            'spacing_mm': float,
            'conversion_factor': float,
            'leds_per_meter': int,
            'description': str
        }
    """
    try:
        data = request.get_json() or {}
        
        if 'value' not in data:
            return jsonify({'error': 'Bad Request', 'message': 'Request must include "value"'}), 400
        
        try:
            value = float(data['value'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Bad Request', 'message': '"value" must be a number'}), 400
        
        from_unit = data.get('from_unit', 'mm')
        to_unit = data.get('to_unit', 'led')
        leds_per_meter = get_leds_per_meter()
        
        result = normalize_offset(value, from_unit, to_unit, leds_per_meter)
        result['success'] = True
        result['leds_per_meter'] = leds_per_meter
        
        return jsonify(result), 200
    
    except ValueError as e:
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error converting offset: {e}", exc_info=True)
        return jsonify({'error': str(e), 'message': 'Failed to convert offset'}), 500


@joint_bp.route('/validate', methods=['POST'])
def validate_joints():
    """
    Validate soldering joints configuration before saving.
    
    Request body:
        {
            'joints': {
                '100': {'width_mm': 2.5, 'offset_mm': 3.5},
                '200': {'width_mm': 2.0, 'offset_mm': -1.0}
            }
        }
    
    Returns:
        {
            'success': bool,
            'valid': bool,
            'errors': [str, ...],
            'warnings': [str, ...],
            'statistics': {...}
        }
    """
    try:
        data = request.get_json() or {}
        joints = data.get('joints', {})
        
        if not isinstance(joints, dict):
            return jsonify({
                'success': False,
                'valid': False,
                'errors': ['joints must be a dictionary'],
                'warnings': [],
                'statistics': {}
            }), 400
        
        errors = []
        warnings = []
        leds_per_meter = get_leds_per_meter()
        
        # Normalize joints for validation
        normalized = {}
        for led_idx_str, joint_data in joints.items():
            try:
                led_idx = int(led_idx_str)
                if led_idx < 0:
                    errors.append(f"LED index must be non-negative, got {led_idx}")
                    continue
                
                if not isinstance(joint_data, dict):
                    errors.append(f"Joint at LED {led_idx} must be a dictionary")
                    continue
                
                width_mm = float(joint_data.get('width_mm', 2.0))
                offset_mm = float(joint_data.get('offset_mm', 0.0))
                
                if width_mm <= 0 or width_mm > 50:
                    errors.append(f"Joint at LED {led_idx}: width {width_mm}mm out of range (0.1-50mm)")
                    continue
                
                is_valid, error_msg = validate_offset(offset_mm, 'mm', leds_per_meter)
                if not is_valid:
                    errors.append(f"Joint at LED {led_idx}: {error_msg}")
                    continue
                
                normalized[led_idx] = {
                    'width_mm': width_mm,
                    'offset_mm': offset_mm,
                    'description': joint_data.get('description', '')
                }
            
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid joint entry {led_idx_str}: {e}")
                continue
        
        # Check for overlapping joints
        sorted_indices = sorted(normalized.keys())
        for i in range(len(sorted_indices) - 1):
            led_idx = sorted_indices[i]
            next_idx = sorted_indices[i + 1]
            width = normalized[led_idx].get('width_mm', 2.0)
            width_leds = get_joint_width_in_leds(width, leds_per_meter)
            
            if led_idx + width_leds > next_idx:
                warnings.append(
                    f"Joints at LED {led_idx} (width {width}mm) and LED {next_idx} may overlap"
                )
        
        # Get statistics
        stats = get_joint_statistics(normalized, leds_per_meter)
        
        is_valid = len(errors) == 0
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'statistics': stats
        }), 200
    
    except Exception as e:
        logger.error(f"Error validating joints: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'valid': False,
            'errors': [str(e)],
            'warnings': [],
            'statistics': {}
        }), 500
