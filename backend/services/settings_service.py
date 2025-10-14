#!/usr/bin/env python3
"""
Settings Service for Piano LED Visualizer
Provides centralized, persistent configuration management with real-time synchronization
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from contextlib import contextmanager
from services.settings_validator import SettingsValidator
from logging_config import get_logger

try:
    from config import get_piano_specs
except ImportError:
    def get_piano_specs(piano_size: str) -> Dict[str, Any]:
        """Fallback piano specs helper when config module is unavailable."""
        default_specs = {
            '88-key': {'keys': 88, 'midi_start': 21, 'midi_end': 108},
            '76-key': {'keys': 76, 'midi_start': 28, 'midi_end': 103},
            '61-key': {'keys': 61, 'midi_start': 36, 'midi_end': 96},
            '49-key': {'keys': 49, 'midi_start': 36, 'midi_end': 84},
            '25-key': {'keys': 25, 'midi_start': 48, 'midi_end': 72},
        }
        return default_specs.get(piano_size, default_specs['88-key'])

logger = get_logger(__name__)

class SettingsService:
    """
    Centralized settings management service with database persistence
    and real-time WebSocket synchronization capabilities.
    """
    
    def __init__(self, db_path: Optional[str] = None, websocket_callback=None):
        """
        Initialize the settings service.
        
        Args:
            db_path: Path to SQLite database file
            websocket_callback: Callback function for WebSocket events
        """
        self.db_path = db_path or self._get_default_db_path()
        self.websocket_callback = websocket_callback
        self._defaults_schema = self._get_default_settings_schema()
        self._listeners = []
        self._init_database()
        self._load_default_settings()
        self._migrate_legacy_keys()
        
    def _get_default_db_path(self) -> str:
        """Get the default database path."""
        backend_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent
        return str(backend_dir / "settings.db")
    
    def _init_database(self):
        """Initialize the SQLite database with settings table."""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category VARCHAR(50) NOT NULL,
                        key VARCHAR(100) NOT NULL,
                        value TEXT NOT NULL,
                        data_type VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(category, key)
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)')
                
                conn.commit()
                logger.info("Settings database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize settings database: {e}")
            raise
    
    @contextmanager
    def _get_db_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _load_default_settings(self):
        """Load default settings into the database if they don't exist."""
        default_settings = self._defaults_schema

        for category, settings in default_settings.items():
            for key, config in settings.items():
                if not self._setting_exists(category, key):
                    self._create_setting(category, key, config['default'], config['type'])

    def _get_default_value(self, category: str, key: str, fallback: Any = None) -> Any:
        """Helper to fetch default values from the schema."""
        try:
            return self._defaults_schema[category][key]['default']
        except KeyError:
            return fallback
    
    def _get_default_settings_schema(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get the default settings schema with types and constraints."""
        return {
            'audio': {
                'enabled': {'type': 'boolean', 'default': False},
                'volume': {'type': 'number', 'default': 50, 'min': 0, 'max': 100},
                'input_device': {'type': 'string', 'default': 'default'},
                'gain': {'type': 'number', 'default': 1.0, 'min': 0, 'max': 2.0},
                'latency': {'type': 'number', 'default': 50, 'min': 0, 'max': 500},
                'sample_rate': {'type': 'number', 'default': 44100},
                'buffer_size': {'type': 'number', 'default': 1024}
            },
            'piano': {
                'enabled': {'type': 'boolean', 'default': False},
                'octave': {'type': 'number', 'default': 4, 'min': 0, 'max': 8},
                'velocity_sensitivity': {'type': 'number', 'default': 64, 'min': 0, 'max': 127},
                'channel': {'type': 'number', 'default': 1, 'min': 1, 'max': 16},
                # Extended piano defaults
                'size': {'type': 'string', 'default': '88-key'},
                'keys': {'type': 'number', 'default': 88, 'min': 0, 'max': 128},
                'octaves': {'type': 'number', 'default': 7.25, 'min': 0, 'max': 10},
                'start_note': {'type': 'string', 'default': 'A0'},
                'end_note': {'type': 'string', 'default': 'C8'},
                'key_mapping_mode': {'type': 'string', 'default': 'chromatic'},
                'key_mapping': {'type': 'object', 'default': {}}
            },
            'gpio': {
                'enabled': {'type': 'boolean', 'default': False},
                'pins': {'type': 'array', 'default': []},
                'debounce_time': {'type': 'number', 'default': 50, 'min': 0, 'max': 1000},
                'data_pin': {'type': 'number', 'default': 18, 'min': 1, 'max': 40},
                'clock_pin': {'type': 'number', 'default': 19, 'min': 1, 'max': 40}
            },
            'led': {
                'enabled': {'type': 'boolean', 'default': False},
                'led_count': {'type': 'number', 'default': 246, 'min': 1, 'max': 1000},
                'max_led_count': {'type': 'number', 'default': 1000, 'min': 1, 'max': 1000},
                'led_channel': {'type': 'number', 'default': 0, 'min': 0, 'max': 1},
                # Use 0-1 scale to match backend schema
                'brightness': {'type': 'number', 'default': 0.5, 'min': 0, 'max': 1},
                'led_type': {'type': 'string', 'default': 'WS2812B', 'enum': ['WS2812B', 'WS2811', 'WS2813', 'WS2815', 'APA102', 'SK6812']},
                'led_orientation': {'type': 'string', 'default': 'normal', 'enum': ['normal', 'reversed']},
                'led_strip_type': {'type': 'string', 'default': 'WS2811_STRIP_GRB', 'enum': ['WS2811_STRIP_GRB', 'WS2811_STRIP_RGB', 'WS2811_STRIP_BRG', 'WS2811_STRIP_BGR']},
                'power_supply_voltage': {'type': 'number', 'default': 5.0, 'min': 3.0, 'max': 24.0},
                'power_supply_current': {'type': 'number', 'default': 10.0, 'min': 0.1, 'max': 100.0},
                'color_profile': {'type': 'string', 'default': 'Standard RGB', 'enum': ['Standard RGB', 'sRGB', 'Adobe RGB', 'Wide Gamut']},
                'performance_mode': {'type': 'string', 'default': 'Balanced', 'enum': ['Power Saving', 'Balanced', 'Performance', 'Maximum']},
                'gamma_correction': {'type': 'number', 'default': 2.2, 'min': 1.0, 'max': 3.0},
                'white_balance': {'type': 'object', 'default': {'r': 1.0, 'g': 1.0, 'b': 1.0}},
                'color_temperature': {'type': 'number', 'default': 6500, 'min': 2000, 'max': 10000},
                'dither_enabled': {'type': 'boolean', 'default': False},
                'update_rate': {'type': 'number', 'default': 60, 'min': 1, 'max': 120},
                'power_limiting_enabled': {'type': 'boolean', 'default': False},
                'max_power_watts': {'type': 'number', 'default': 100, 'min': 1, 'max': 1000},
                'thermal_protection_enabled': {'type': 'boolean', 'default': False},
                'max_temperature_celsius': {'type': 'number', 'default': 80, 'min': 40, 'max': 100},
                'data_pin': {'type': 'number', 'default': 18, 'min': 1, 'max': 40},
                'clock_pin': {'type': 'number', 'default': 19, 'min': 1, 'max': 40},
                'reverse_order': {'type': 'boolean', 'default': False},
                'color_mode': {'type': 'string', 'default': 'velocity', 'enum': ['rainbow', 'velocity', 'note', 'custom']},
                'color_scheme': {'type': 'string', 'default': 'rainbow'},
                'animation_speed': {'type': 'number', 'default': 1.0, 'min': 0.1, 'max': 3.0},
                'gpio_pin': {'type': 'number', 'default': 19}
            },
            'hardware': {
                'auto_detect_midi': {'type': 'boolean', 'default': False},
                'auto_detect_gpio': {'type': 'boolean', 'default': True},
                'auto_detect_led': {'type': 'boolean', 'default': True},
                'midi_device_id': {'type': 'string', 'default': ''},
                'rtpmidi_enabled': {'type': 'boolean', 'default': False},
                'rtpmidi_port': {'type': 'number', 'default': 5004, 'min': 1024, 'max': 65535}
            },
            'system': {
                'theme': {'type': 'string', 'default': 'auto', 'enum': ['light', 'dark', 'auto']},
                'debug': {'type': 'boolean', 'default': False},
                'log_level': {'type': 'string', 'default': 'info', 'enum': ['debug', 'info', 'warn', 'error']},
                'auto_save': {'type': 'boolean', 'default': True},
                'backup_settings': {'type': 'boolean', 'default': True},
                'performance_mode': {'type': 'string', 'default': 'balanced', 'enum': ['power_save', 'balanced', 'performance']}
            },
            'user': {
                'name': {'type': 'string', 'default': 'User'},
                'email': {'type': 'string', 'default': ''},
                'preferences': {'type': 'object', 'default': {}},
                'favorite_schemes': {'type': 'array', 'default': []},
                'recent_configs': {'type': 'array', 'default': []},
                'last_used_device': {'type': 'string', 'default': ''},
                'navigation_collapsed': {'type': 'boolean', 'default': False}
            },
            'upload': {
                'auto_upload': {'type': 'boolean', 'default': False},
                'remember_last_directory': {'type': 'boolean', 'default': True},
                'show_file_preview': {'type': 'boolean', 'default': True},
                'confirm_before_reset': {'type': 'boolean', 'default': True},
                'last_uploaded_file': {'type': 'string', 'default': ''}
            },
            'ui': {
                'theme': {'type': 'string', 'default': 'auto', 'enum': ['light', 'dark', 'auto']},
                'reduced_motion': {'type': 'boolean', 'default': False},
                'show_tooltips': {'type': 'boolean', 'default': True},
                'tooltip_delay': {'type': 'number', 'default': 300, 'min': 0, 'max': 2000},
                'animation_speed': {'type': 'string', 'default': 'normal', 'enum': ['slow', 'normal', 'fast']}
            },
            'a11y': {
                'highContrast': {'type': 'boolean', 'default': False},
                'largeText': {'type': 'boolean', 'default': False},
                'keyboardNavigation': {'type': 'boolean', 'default': True},
                'screenReaderOptimized': {'type': 'boolean', 'default': False}
            },
            'help': {
                'showOnboarding': {'type': 'boolean', 'default': True},
                'showHints': {'type': 'boolean', 'default': True},
                'completedTours': {'type': 'array', 'default': []},
                'skippedTours': {'type': 'array', 'default': []},
                'tourCompleted': {'type': 'boolean', 'default': False}
            },
            'history': {
                'maxHistorySize': {'type': 'number', 'default': 50, 'min': 10, 'max': 200},
                'autosaveInterval': {'type': 'number', 'default': 30000, 'min': 5000, 'max': 300000},
                'persistHistory': {'type': 'boolean', 'default': True}
            }
        }
    
    def _setting_exists(self, category: str, key: str) -> bool:
        """Check if a setting exists in the database."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT 1 FROM settings WHERE category = ? AND key = ?',
                    (category, key)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking setting existence: {e}")
            return False
    
    def _create_setting(self, category: str, key: str, value: Any, data_type: str):
        """Create a new setting in the database."""
        try:
            with self._get_db_connection() as conn:
                conn.execute(
                    '''INSERT INTO settings (category, key, value, data_type) 
                       VALUES (?, ?, ?, ?)''',
                    (category, key, json.dumps(value), data_type)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error creating setting {category}.{key}: {e}")
            raise

    def _delete_setting(self, category: str, key: str) -> None:
        """Remove a setting from the database if it exists."""
        try:
            with self._get_db_connection() as conn:
                conn.execute(
                    'DELETE FROM settings WHERE category = ? AND key = ?',
                    (category, key)
                )
                conn.commit()
        except Exception as exc:
            logger.error(f"Error deleting setting {category}.{key}: {exc}")

    def _migrate_legacy_keys(self) -> None:
        """Normalize legacy/camelCase keys that may already exist in the database."""
        legacy_key_mappings = {
            ('led', 'ledOrientation'): ('led', 'led_orientation'),
            ('led', 'orientation'): ('led', 'led_orientation'),
        }

        try:
            with self._get_db_connection() as conn:
                changes_made = False

                for (old_category, old_key), (new_category, new_key) in legacy_key_mappings.items():
                    cursor = conn.execute(
                        'SELECT value, data_type FROM settings WHERE category = ? AND key = ?',
                        (old_category, old_key)
                    )
                    row = cursor.fetchone()

                    if not row:
                        continue

                    value = json.loads(row['value'])

                    schema = SettingsValidator._get_category_schema(new_category) or {}
                    normalized_value, errors = SettingsValidator._validate_and_normalize_setting(
                        new_category,
                        new_key,
                        value,
                        schema.get(new_key, {})
                    )

                    if errors:
                        logger.warning(
                            "Skipping migration for %s.%s due to validation error: %s",
                            old_category,
                            old_key,
                            errors[0]
                        )
                        continue

                    target_exists = conn.execute(
                        'SELECT 1 FROM settings WHERE category = ? AND key = ?',
                        (new_category, new_key)
                    ).fetchone()

                    if not target_exists:
                        conn.execute(
                            '''INSERT OR REPLACE INTO settings (category, key, value, data_type, updated_at)
                               VALUES (?, ?, ?, ?, ?)''',
                            (
                                new_category,
                                new_key,
                                json.dumps(normalized_value),
                                self._get_data_type(normalized_value),
                                datetime.now().isoformat()
                            )
                        )
                        logger.info(
                            "Migrated legacy setting %s.%s to %s.%s",
                            old_category,
                            old_key,
                            new_category,
                            new_key
                        )
                    else:
                        logger.info(
                            "Removing legacy duplicate setting %s.%s (canonical key already present)",
                            old_category,
                            old_key
                        )

                    conn.execute(
                        'DELETE FROM settings WHERE category = ? AND key = ?',
                        (old_category, old_key)
                    )
                    changes_made = True

                if changes_made:
                    conn.commit()

        except Exception as exc:
            logger.error(f"Legacy settings migration failed: {exc}")

    def add_listener(self, callback: Callable[[str, str, Any], None]) -> None:
        """Register a callback to be notified when a setting changes."""
        if callback and callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, str, Any], None]) -> None:
        """Remove a previously registered setting change callback."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, category: str, key: str, value: Any) -> None:
        """Notify registered listeners about a setting change."""
        if not self._listeners:
            return

        for callback in list(self._listeners):
            try:
                callback(category, key, value)
            except Exception as exc:
                logger.error(f"Settings listener error for {category}.{key}: {exc}")
    
    def get_setting(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a single setting value.
        
        Args:
            category: Setting category
            key: Setting key
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT value, data_type FROM settings WHERE category = ? AND key = ?',
                    (category, key)
                )
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row['value'])
                return default
        except Exception as e:
            logger.error(f"Error getting setting {category}.{key}: {e}")
            return default
    
    def set_setting(self, category: str, key: str, value: Any) -> bool:
        """
        Set a single setting value.
        
        Args:
            category: Setting category
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            storage_key = SettingsValidator.resolve_key_alias(category, key)
            schema = SettingsValidator._get_category_schema(category) or {}

            # Validate and normalize the setting
            normalized_value, errors = SettingsValidator._validate_and_normalize_setting(
                category,
                storage_key,
                value,
                schema.get(storage_key, {})
            )
            
            if errors:
                logger.error(f"Validation failed for {category}.{storage_key}: {errors[0]}")
                return False
            
            data_type = self._get_data_type(normalized_value)
            
            with self._get_db_connection() as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO settings 
                       (category, key, value, data_type, updated_at) 
                       VALUES (?, ?, ?, ?, ?)''',
                    (category, storage_key, json.dumps(normalized_value), data_type, datetime.now().isoformat())
                )
                conn.commit()
            
            # Notify internal listeners before broadcasting
            self._notify_listeners(category, storage_key, normalized_value)

            # Broadcast the change via WebSocket
            self._broadcast_setting_change(category, storage_key, normalized_value)
            
            logger.info(f"Setting updated: {category}.{storage_key} = {normalized_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting {category}.{key}: {e}")
            return False
    
    def get_category_settings(self, category: str) -> Dict[str, Any]:
        """
        Get all settings for a specific category.
        
        Args:
            category: Setting category
            
        Returns:
            Dictionary of settings for the category
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    'SELECT key, value FROM settings WHERE category = ?',
                    (category,)
                )
                settings = {}
                for row in cursor.fetchall():
                    settings[row['key']] = json.loads(row['value'])
            # Merge with defaults so new keys are visible
            defaults = self._defaults_schema.get(category, {})
            merged: Dict[str, Any] = {k: cfg['default'] for k, cfg in defaults.items()}
            merged.update(settings)
            return merged
        except Exception as e:
            logger.error(f"Error getting category settings {category}: {e}")
            return {}
    
    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings organized by category.
        
        Returns:
            Dictionary of all settings organized by category
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('SELECT category, key, value FROM settings')
                settings: Dict[str, Dict[str, Any]] = {}
                for row in cursor.fetchall():
                    category = row['category']
                    if category not in settings:
                        settings[category] = {}
                    settings[category][row['key']] = json.loads(row['value'])
            # Ensure defaults are present in all categories
            defaults_schema = self._defaults_schema
            for category, defaults in defaults_schema.items():
                existing = settings.get(category, {})
                merged = {k: cfg['default'] for k, cfg in defaults.items()}
                merged.update(existing)
                settings[category] = merged
            return settings
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}
    
    def update_settings(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """
        Update multiple settings at once.
        
        Args:
            settings: Dictionary of settings organized by category
            
        Returns:
            True if all updates successful, False otherwise
        """
        try:
            # Validate and normalize all settings
            normalized_settings, errors = SettingsValidator.validate_and_normalize(settings)
            
            if errors:
                logger.error(f"Settings validation failed: {errors}")
                return False
            
            updated_settings = []
            
            for category, category_settings in normalized_settings.items():
                for key, value in category_settings.items():
                    if self.set_setting(category, key, value):
                        updated_settings.append((category, key, value))
            
            # Broadcast bulk update
            if updated_settings:
                self._broadcast_bulk_update(updated_settings)
            
            return len(updated_settings) == sum(len(cat_settings) for cat_settings in normalized_settings.values())
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    def reset_category(self, category: str) -> bool:
        """
        Reset all settings in a category to defaults.
        
        Args:
            category: Category to reset
            
        Returns:
            True if successful, False otherwise
        """
        try:
            default_settings = self._defaults_schema
            if category not in default_settings:
                logger.error(f"Unknown category: {category}")
                return False
            
            category_defaults = default_settings[category]
            updated_settings = []
            
            for key, config in category_defaults.items():
                if self.set_setting(category, key, config['default']):
                    updated_settings.append((category, key, config['default']))
            
            logger.info(f"Reset category {category} to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting category {category}: {e}")
            return False
    
    def reset_all_settings(self) -> bool:
        """
        Reset all settings to defaults.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            default_settings = self._defaults_schema
            
            for category in default_settings.keys():
                if not self.reset_category(category):
                    return False
            
            self._broadcast_settings_reset()
            logger.info("All settings reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting all settings: {e}")
            return False
    
    def export_settings(self) -> Dict[str, Any]:
        """
        Export all settings for backup/sharing.
        
        Returns:
            Dictionary containing all settings and metadata
        """
        try:
            settings = self.get_all_settings()
            return {
                'settings': settings,
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return {}
    
    def import_settings(self, settings_data: Dict[str, Any], validate: bool = True) -> bool:
        """
        Import settings from backup/sharing.
        
        Args:
            settings_data: Settings data to import
            validate: Whether to validate settings before import
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'settings' not in settings_data:
                logger.error("Invalid settings data format")
                return False
            
            settings = settings_data['settings']
            
            if validate:
                # Validate and normalize settings
                normalized_settings, errors = SettingsValidator.validate_and_normalize(settings)
                if errors:
                    logger.error(f"Settings validation failed: {errors}")
                    return False
                settings = normalized_settings
            
            return self.update_settings(settings)
            
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False
    
    def _validate_setting(self, category: str, key: str, value: Any) -> bool:
        """Validate a single setting using the centralized validator."""
        normalized, errors = SettingsValidator._validate_and_normalize_setting(category, key, value, 
            SettingsValidator._get_category_schema(category).get(key, {}))
        return len(errors) == 0
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type using the centralized validator."""
        return SettingsValidator._validate_type(value, expected_type)
    
    def _validate_settings_bulk(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """Validate multiple settings using the centralized validator."""
        normalized, errors = SettingsValidator.validate_and_normalize(settings)
        return len(errors) == 0
    
    def _get_data_type(self, value: Any) -> str:
        """Get the data type string for a value."""
        if isinstance(value, str):
            return 'string'
        elif isinstance(value, (int, float)):
            return 'number'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, list):
            return 'array'
        else:
            return 'object'
    
    def _broadcast_setting_change(self, category: str, key: str, value: Any):
        """Broadcast a single setting change via WebSocket."""
        if self.websocket_callback:
            try:
                # Use background task for non-critical setting updates to avoid blocking
                import socketio
                if hasattr(socketio, 'start_background_task'):
                    # We're in a SocketIO context, use background task
                    socketio.start_background_task(self._do_broadcast_setting_change, category, key, value)
                else:
                    # Fallback to direct call
                    self.websocket_callback('settings:update', {
                        'category': category,
                        'key': key,
                        'value': value,
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error broadcasting setting change: {e}")

    def _do_broadcast_setting_change(self, category: str, key: str, value: Any):
        """Actual broadcast implementation for background task."""
        if self.websocket_callback:
            try:
                self.websocket_callback('settings:update', {
                    'category': category,
                    'key': key,
                    'value': value,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error in background broadcast of setting change: {e}")

    def _broadcast_bulk_update(self, updated_settings: List[tuple]):
        """Broadcast multiple setting changes via WebSocket."""
        if self.websocket_callback:
            try:
                # Use background task for bulk updates to avoid blocking
                import socketio
                if hasattr(socketio, 'start_background_task'):
                    socketio.start_background_task(self._do_broadcast_bulk_update, updated_settings)
                else:
                    # Fallback to direct call
                    changes = [
                        {'category': category, 'key': key, 'value': value}
                        for category, key, value in updated_settings
                    ]
                    self.websocket_callback('settings:bulk_update', {
                        'changes': changes,
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error broadcasting bulk update: {e}")

    def _do_broadcast_bulk_update(self, updated_settings: List[tuple]):
        """Actual bulk broadcast implementation for background task."""
        if self.websocket_callback:
            try:
                changes = [
                    {'category': category, 'key': key, 'value': value}
                    for category, key, value in updated_settings
                ]
                self.websocket_callback('settings:bulk_update', {
                    'changes': changes,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error in background broadcast of bulk update: {e}")

    def _broadcast_settings_reset(self):
        """Broadcast settings reset event via WebSocket."""
        if self.websocket_callback:
            try:
                # Use background task for reset notifications
                import socketio
                if hasattr(socketio, 'start_background_task'):
                    socketio.start_background_task(self._do_broadcast_settings_reset)
                else:
                    # Fallback to direct call
                    self.websocket_callback('settings:reset', {
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error broadcasting settings reset: {e}")

    def _do_broadcast_settings_reset(self):
        """Actual reset broadcast implementation for background task."""
        if self.websocket_callback:
            try:
                self.websocket_callback('settings:reset', {
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error in background broadcast of settings reset: {e}")

    def get_led_configuration(self) -> Dict[str, Any]:
        """Return key LED runtime configuration values with fallbacks."""
        led_count_value = self.get_setting('led', 'led_count', self._get_default_value('led', 'led_count', 0))
        try:
            led_count = int(led_count_value)
        except (TypeError, ValueError):
            led_count = int(self._get_default_value('led', 'led_count', 0))

        return {
            'enabled': self.get_setting('led', 'enabled', self._get_default_value('led', 'enabled', False)),
            'led_count': led_count,
            'orientation': self.get_setting('led', 'led_orientation', self._get_default_value('led', 'led_orientation', 'normal')),
            'brightness': self.get_setting('led', 'brightness', self._get_default_value('led', 'brightness', 0.5)),
            'gpio_pin': self.get_setting('led', 'gpio_pin', self._get_default_value('led', 'gpio_pin', 19))
        }

    def get_piano_configuration(self) -> Dict[str, Any]:
        """Return key piano runtime configuration values with derived specs."""
        size = self.get_setting('piano', 'size', self._get_default_value('piano', 'size', '88-key'))
        keys_value = self.get_setting('piano', 'keys', self._get_default_value('piano', 'keys', 88))
        try:
            keys = int(keys_value)
        except (TypeError, ValueError):
            keys = int(self._get_default_value('piano', 'keys', 88))
        specs = get_piano_specs(size)

        if keys <= 0:
            keys = specs.get('keys', keys)

        return {
            'size': size,
            'keys': keys,
            'midi_start': specs.get('midi_start', 21),
            'midi_end': specs.get('midi_end', 108)
        }