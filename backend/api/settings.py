#!/usr/bin/env python3
"""
Settings API endpoints for Piano LED Visualizer
Provides RESTful API access to the centralized settings service
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from schemas.settings_schema import validate_setting, validate_category, validate_all_settings, get_all_defaults
+from config import get_piano_specs

logger = logging.getLogger(__name__)

# Import settings service - will be initialized in app.py
def get_settings_service():
    """Get the global settings service instance"""
    from app import settings_service
    return settings_service

# Helper: normalize incoming payload to schema-compatible format
def _normalize_settings_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    normalized = {k: (v if isinstance(v, dict) else v) for k, v in data.items()}

    led = dict(normalized.get('led', {}))
    # Map legacy 'count' to 'led_count'
    if 'count' in led and 'led_count' not in led:
        try:
            led['led_count'] = int(led.pop('count'))
        except Exception:
            led.pop('count', None)
    # Clamp and convert brightness 0-100 -> 0-1
    if 'brightness' in led:
        try:
            b = led['brightness']
            if isinstance(b, (int, float)):
                led['brightness'] = max(0.0, min(1.0, float(b) / 100.0)) if float(b) > 1.0 else max(0.0, min(1.0, float(b)))
        except Exception:
            pass
    # Canonicalize color_profile values
    if 'color_profile' in led:
        try:
            cp = str(led['color_profile']).strip().lower()
            if cp in ['standard', 'standard rgb']:
                led['color_profile'] = 'Standard RGB'
            elif cp in ['srgb']:
                led['color_profile'] = 'sRGB'
            elif cp in ['adobe rgb', 'adobe']:
                led['color_profile'] = 'Adobe RGB'
            elif cp in ['wide gamut', 'wide']:
                led['color_profile'] = 'Wide Gamut'
        except Exception:
            pass
    # Canonicalize performance_mode values
    if 'performance_mode' in led:
        try:
            pm = str(led['performance_mode']).strip().lower()
            mapping = {
                'power saving': 'Power Saving',
                'balanced': 'Balanced',
                'performance': 'Performance',
                'maximum': 'Maximum'
            }
            if pm in mapping:
                led['performance_mode'] = mapping[pm]
        except Exception:
            pass
    # Normalize GPIO pin location and key name
    pin = None
    for key in ['gpioPin', 'gpio_pin', 'data_pin']:
        if key in led:
            pin = led.pop(key)
            break
    if pin is None and isinstance(normalized.get('gpio'), dict):
        gpio = normalized['gpio']
        if 'data_pin' in gpio:
            pin = gpio.pop('data_pin')
            normalized['gpio'] = gpio
    if pin is not None:
        try:
            led['gpioPin'] = int(pin)
        except Exception:
            pass
    # Ensure numeric types are proper
    if 'power_supply_voltage' in led:
        try:
            led['power_supply_voltage'] = float(led['power_supply_voltage'])
        except Exception:
            pass
    if 'power_supply_current' in led:
        try:
            led['power_supply_current'] = float(led['power_supply_current'])
        except Exception:
            pass
    if 'led_count' in led:
        try:
            led['led_count'] = int(led['led_count'])
        except Exception:
            pass

    # Remove leftover unknowns that often cause validation errors
    led.pop('count', None)

    normalized['led'] = led
+
+    # Piano normalization: derive specs when size is provided and ensure types
+    piano = dict(normalized.get('piano', {}))
+    if 'size' in piano:
+        try:
+            specs = get_piano_specs(str(piano.get('size')))
+            # Fill missing fields from specs
+            if 'keys' not in piano or piano.get('keys') is None:
+                piano['keys'] = specs.get('keys')
+            if 'octaves' not in piano or piano.get('octaves') is None:
+                piano['octaves'] = specs.get('octaves')
+            if 'start_note' not in piano or not piano.get('start_note'):
+                piano['start_note'] = specs.get('start_note')
+            if 'end_note' not in piano or not piano.get('end_note'):
+                piano['end_note'] = specs.get('end_note')
+        except Exception:
+            pass
+    # Ensure mode and mapping types
+    if 'key_mapping_mode' not in piano or not isinstance(piano.get('key_mapping_mode'), str):
+        piano['key_mapping_mode'] = 'chromatic'
+    km = piano.get('key_mapping')
+    if not isinstance(km, dict):
+        piano['key_mapping'] = {}
+
+    normalized['piano'] = piano
     return normalized

# Create the blueprint
settings_bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')

@settings_bp.route('/', methods=['GET'])
def get_all_settings():
    """Get all settings organized by category"""
    try:
        settings_service = get_settings_service()
        settings = settings_service.get_all_settings()
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error getting all settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to retrieve settings'
        }), 500

@settings_bp.route('/<category>', methods=['GET'])
def get_category_settings(category):
    """Get all settings for a specific category"""
    try:
        settings_service = get_settings_service()
        settings = settings_service.get_category_settings(category)
        if settings is None:
            return jsonify({
                'error': 'Not Found',
                'message': f'Category "{category}" not found'
            }), 404
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error getting category settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to retrieve settings for category "{category}"'
        }), 500

@settings_bp.route('/<category>/<key>', methods=['GET'])
def get_setting(category, key):
    """Get a specific setting value"""
    try:
        settings_service = get_settings_service()
        value = settings_service.get_setting(category, key)
        if value is None:
            return jsonify({
                'error': 'Not Found',
                'message': f'Setting "{category}.{key}" not found'
            }), 404
        return jsonify({'value': value}), 200
    except Exception as e:
        logger.error(f"Error getting setting: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to retrieve setting "{category}.{key}"'
        }), 500

@settings_bp.route('/<category>/<key>', methods=['PUT'])
def set_setting(category, key):
    """Set a specific setting value"""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Request must include "value" field'
            }), 400
        
        # Validate the setting using schema
        try:
            validate_setting(category, key, data['value'])
        except ValueError as e:
            return jsonify({
                'error': 'Validation Error',
                'message': str(e)
            }), 400
        
        settings_service = get_settings_service()
        success = settings_service.set_setting(category, key, data['value'])
        if not success:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Failed to set setting "{category}.{key}"'
            }), 400
        
        return jsonify({'message': 'Setting updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error setting value: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': f'Failed to set setting "{category}.{key}"'
        }), 500

@settings_bp.route('/', methods=['PUT'])
@settings_bp.route('/bulk', methods=['POST'])
def update_multiple_settings():
    """Update multiple settings at once"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'No settings data provided'
            }), 400
        
        # Normalize payload to schema-compatible format
        normalized = _normalize_settings_payload(data)
        
        # Validate all settings using schema
        try:
            result = validate_all_settings(normalized)
            if not result.valid:
                return jsonify({
                    'error': 'Validation Error',
                    'message': ', '.join(result.errors or ['Invalid settings'])
                }), 400
        except ValueError as e:
            return jsonify({
                'error': 'Validation Error',
                'message': str(e)
            }), 400
        
        settings_service = get_settings_service()
        success = settings_service.update_settings(normalized)
        if not success:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Failed to update settings'
            }), 400
        
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to update settings'
        }), 500

@settings_bp.route('/reset', methods=['POST'])
def reset_settings():
    """Reset all settings to defaults"""
    try:
        data = request.get_json() or {}
        category = data.get('category')
        
        settings_service = get_settings_service()
        settings_service.reset_settings(category)
        
        message = f'Settings for category "{category}" reset to defaults' if category else 'All settings reset to defaults'
        return jsonify({'message': message}), 200
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to reset settings'
        }), 500

@settings_bp.route('/export', methods=['GET'])
def export_settings():
    """Export all settings as JSON"""
    try:
        settings_service = get_settings_service()
        settings = settings_service.export_settings()
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to export settings'
        }), 500

@settings_bp.route('/import', methods=['POST'])
def import_settings():
    """Import settings from JSON"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'No settings data provided'
            }), 400
        
        # Validate imported settings using schema
        try:
            validate_all_settings(data)
        except ValueError as e:
            return jsonify({
                'error': 'Validation Error',
                'message': f'Invalid settings data: {str(e)}'
            }), 400
        
        settings_service = get_settings_service()
        success = settings_service.import_settings(data)
        if not success:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Failed to import settings'
            }), 400
        
        return jsonify({'message': 'Settings imported successfully'}), 200
    except Exception as e:
        logger.error(f"Error importing settings: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to import settings'
        }), 500

@settings_bp.route('/validate', methods=['POST'])
def validate_settings():
    """Validate settings data using schema"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'valid': False, 'errors': ['No data provided']}), 400
        result = validate_all_settings(data)
        return jsonify({'valid': result.valid, 'errors': result.errors}), 200
    except Exception as e:
        logger.error(f"Error validating settings: {e}")
        return jsonify({'valid': False, 'errors': [str(e)]}), 500

@settings_bp.route('/schema', methods=['GET'])
def get_settings_schema():
    """Get the settings schema"""
    try:
        from schemas.settings_schema import SettingsSchema
        schema = SettingsSchema.SCHEMA
        return jsonify(schema), 200
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Failed to retrieve settings schema'
        }), 500

def create_settings_api(settings_service):
    """Create settings API blueprint with the provided settings service."""
    return settings_bp