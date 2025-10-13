/**
 * Settings Schema Definition and Validation
 * Provides comprehensive validation for all settings categories
 */

// Type definitions
interface ValidationResult {
    isValid: boolean;
    error?: string;
    errors?: string[];
}

interface SchemaProperty {
    type: string;
    minimum?: number;
    maximum?: number;
    maxLength?: number;
    format?: string;
    enum?: string[] | number[];
    default?: any;
    items?: SchemaProperty;
    properties?: Record<string, SchemaProperty>;
    required?: string[];
}

interface CategorySchema {
    type: string;
    required?: string[];
    properties: Record<string, SchemaProperty>;
}

type SettingsSchema = Record<string, CategorySchema>;

// Schema definitions for each settings category
export const settingsSchema: SettingsSchema = {
    piano: {
        type: 'object',
        required: ['enabled', 'octave'],
        properties: {
            enabled: { type: 'boolean', default: false },
            octave: { type: 'number', minimum: 0, maximum: 8, default: 4 },
            velocity_sensitivity: { type: 'number', minimum: 0, maximum: 127, default: 64 },
            channel: { type: 'number', minimum: 1, maximum: 16, default: 1 }
        }
    },
    
    gpio: {
        type: 'object',
        required: ['enabled', 'pins'],
        properties: {
            enabled: { type: 'boolean', default: false },
            pins: {
                type: 'array',
                default: [],
                items: {
                    type: 'object',
                    required: ['pin', 'mode', 'note'],
                    properties: {
                        pin: { type: 'number', minimum: 1, maximum: 40 },
                        mode: { type: 'string', enum: ['input', 'output'], default: 'input' },
                        note: { type: 'number', minimum: 0, maximum: 127 },
                        pullup: { type: 'boolean', default: true }
                    }
                }
            },
            debounce_time: { type: 'number', minimum: 0, maximum: 1000, default: 50 }
        }
    },
    
    led: {
        type: 'object',
        required: ['enabled', 'led_count', 'brightness'],
        properties: {
            // Core LED settings
            enabled: { type: 'boolean', default: false },
            led_count: { type: 'number', minimum: 1, maximum: 1000, default: 88 },
            max_led_count: { type: 'number', minimum: 1, maximum: 1000, default: 300 },
            brightness: { type: 'number', minimum: 0, maximum: 100, default: 50 },
            
            // LED hardware configuration
            led_type: { type: 'string', enum: ['WS2812B', 'WS2811', 'WS2813', 'WS2815', 'APA102', 'SK6812'], default: 'WS2812B' },
            led_strip_type: { type: 'string', enum: ['WS2811_STRIP_GRB', 'WS2811_STRIP_RGB', 'WS2811_STRIP_BRG', 'WS2811_STRIP_BGR'], default: 'WS2811_STRIP_GRB' },
            led_orientation: { type: 'string', enum: ['normal', 'reversed'], default: 'normal' },
            data_pin: { type: 'number', minimum: 1, maximum: 40, default: 18 },
            clock_pin: { type: 'number', minimum: 1, maximum: 40, default: 19 },
            gpioPin: { type: 'number', minimum: 1, maximum: 40, default: 19 },
            reverse_order: { type: 'boolean', default: false },
            
            // Color and visual settings
            color_mode: { type: 'string', enum: ['rainbow', 'velocity', 'note', 'custom'], default: 'velocity' },
            colorScheme: { type: 'string', default: 'rainbow' },
            color_profile: { type: 'string', enum: ['Standard RGB', 'sRGB', 'Adobe RGB', 'Wide Gamut'], default: 'Standard RGB' },
            color_temperature: { type: 'number', minimum: 2000, maximum: 10000, default: 6500 },
            gamma_correction: { type: 'number', minimum: 1.0, maximum: 3.0, default: 2.2 },
            white_balance: { type: 'object', default: { r: 1.0, g: 1.0, b: 1.0 } },
            
            // Performance and power settings
            performance_mode: { type: 'string', enum: ['Power Saving', 'Balanced', 'Performance', 'Maximum'], default: 'Balanced' },
            power_supply_voltage: { type: 'number', minimum: 3.0, maximum: 24.0, default: 5.0 },
            power_supply_current: { type: 'number', minimum: 0.1, maximum: 100.0, default: 10.0 },
            power_limiting_enabled: { type: 'boolean', default: true },
            max_power_watts: { type: 'number', minimum: 1, maximum: 1000, default: 50 },
            
            // Advanced settings
            dither_enabled: { type: 'boolean', default: false },
            update_rate: { type: 'number', minimum: 1, maximum: 120, default: 30 },
            thermal_protection_enabled: { type: 'boolean', default: true },
            max_temperature_celsius: { type: 'number', minimum: 40, maximum: 100, default: 70 },
            animationSpeed: { type: 'number', minimum: 0.1, maximum: 5.0, default: 1.0 }
        }
    },
    
    audio: {
        type: 'object',
        required: ['enabled', 'volume'],
        properties: {
            enabled: { type: 'boolean', default: false },
            volume: { type: 'number', minimum: 0, maximum: 100, default: 50 },
            sample_rate: { type: 'number', enum: [22050, 44100, 48000, 96000], default: 44100 },
            buffer_size: { type: 'number', enum: [64, 128, 256, 512, 1024], default: 256 },
            latency: { type: 'number', minimum: 0, maximum: 1000, default: 100 },
            device_id: { type: 'string', default: '' }
        }
    },
    
    hardware: {
        type: 'object',
        required: ['auto_detect_midi', 'auto_detect_gpio', 'auto_detect_led'],
        properties: {
            auto_detect_midi: { type: 'boolean', default: true },
            auto_detect_gpio: { type: 'boolean', default: true },
            auto_detect_led: { type: 'boolean', default: true },
            midi_device_id: { type: 'string', default: '' },
            rtpmidi_enabled: { type: 'boolean', default: false },
            rtpmidi_port: { type: 'number', minimum: 1024, maximum: 65535, default: 5004 }
        }
    },
    
    system: {
        type: 'object',
        required: ['theme', 'debug'],
        properties: {
            theme: { type: 'string', enum: ['light', 'dark', 'auto'], default: 'auto' },
            debug: { type: 'boolean', default: false },
            log_level: { type: 'string', enum: ['debug', 'info', 'warn', 'error'], default: 'info' },
            auto_save: { type: 'boolean', default: true },
            backup_settings: { type: 'boolean', default: true }
        }
    },
    
    user: {
        type: 'object',
        required: ['name', 'preferences'],
        properties: {
            name: { type: 'string', maxLength: 100, default: 'User' },
            email: { type: 'string', format: 'email', default: '' },
            preferences: {
                type: 'object',
                default: {},
                properties: {
                    show_tooltips: { type: 'boolean', default: true },
                    auto_connect: { type: 'boolean', default: true },
                    remember_window_size: { type: 'boolean', default: true }
                }
            }
        }
    },
    
    upload: {
        type: 'object',
        properties: {
            autoUpload: { type: 'boolean', default: false },
            rememberLastDirectory: { type: 'boolean', default: true },
            showFilePreview: { type: 'boolean', default: true },
            confirmBeforeReset: { type: 'boolean', default: true },
            enableValidationPreview: { type: 'boolean', default: true },
            lastUploadedFile: { type: 'string', default: '' }
        }
    },
    
    ui: {
        type: 'object',
        properties: {
            theme: { type: 'string', enum: ['light', 'dark', 'auto'], default: 'auto' },
            reducedMotion: { type: 'boolean', default: false },
            showTooltips: { type: 'boolean', default: true },
            tooltipDelay: { type: 'number', minimum: 0, maximum: 2000, default: 300 },
            animationSpeed: { type: 'string', enum: ['slow', 'normal', 'fast'], default: 'normal' }
        }
    },
    
    a11y: {
        type: 'object',
        properties: {
            highContrast: { type: 'boolean', default: false },
            largeText: { type: 'boolean', default: false },
            keyboardNavigation: { type: 'boolean', default: true },
            screenReaderOptimized: { type: 'boolean', default: false }
        }
    },
    
    help: {
        type: 'object',
        properties: {
            showOnboarding: { type: 'boolean', default: true },
            showHints: { type: 'boolean', default: true },
            completedTours: { type: 'array', items: { type: 'string' }, default: [] },
            skippedTours: { type: 'array', items: { type: 'string' }, default: [] },
            tourCompleted: { type: 'boolean', default: false }
        }
    },
    
    history: {
        type: 'object',
        properties: {
            maxHistorySize: { type: 'number', minimum: 10, maximum: 200, default: 50 },
            autosaveInterval: { type: 'number', minimum: 5000, maximum: 300000, default: 30000 },
            persistHistory: { type: 'boolean', default: true }
        }
    }
};

/**
 * Validate a single setting value
 */
export function validateSetting(category: string, key: string, value: any): ValidationResult {
    const categorySchema = settingsSchema[category];
    if (!categorySchema) {
        return { isValid: false, error: `Unknown category: ${category}` };
    }
    
    const propertySchema = categorySchema.properties[key];
    if (!propertySchema) {
        return { isValid: false, error: `Unknown property: ${category}.${key}` };
    }
    
    return validateValue(value, propertySchema, `${category}.${key}`);
}

/**
 * Validate an entire settings category
 */
export function validateCategory(category: string, data: Record<string, any>): ValidationResult {
    const categorySchema = settingsSchema[category];
    if (!categorySchema) {
        return { isValid: false, error: `Unknown category: ${category}` };
    }
    
    return validateObject(data, categorySchema, category);
}

/**
 * Validate all settings
 */
export function validateAllSettings(settings: Record<string, any>): ValidationResult {
    const errors: string[] = [];
    
    for (const [category, data] of Object.entries(settings)) {
        const result = validateCategory(category, data);
        if (!result.isValid) {
            if (result.error) {
                errors.push(result.error);
            }
        }
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

/**
 * Get default values for a category
 */
export function getCategoryDefaults(category: string): Record<string, any> {
    const categorySchema = settingsSchema[category];
    if (!categorySchema) {
        return {};
    }
    
    const defaults: Record<string, any> = {};
    for (const [key, property] of Object.entries(categorySchema.properties)) {
        defaults[key] = getDefaultValue(property);
    }
    
    return defaults;
}

/**
 * Get all default settings
 */
export function getAllDefaults(): Record<string, Record<string, any>> {
    const allDefaults: Record<string, Record<string, any>> = {};
    for (const category of Object.keys(settingsSchema)) {
        allDefaults[category] = getCategoryDefaults(category);
    }
    return allDefaults;
}

/**
 * Validate a value against a schema property
 */
function validateValue(value: any, schema: SchemaProperty, path: string): ValidationResult {
    // Type validation
    if (schema.type === 'boolean' && typeof value !== 'boolean') {
        return { isValid: false, error: `${path} must be a boolean` };
    }
    
    if (schema.type === 'number' && typeof value !== 'number') {
        return { isValid: false, error: `${path} must be a number` };
    }
    
    if (schema.type === 'string' && typeof value !== 'string') {
        return { isValid: false, error: `${path} must be a string` };
    }
    
    if (schema.type === 'array' && !Array.isArray(value)) {
        return { isValid: false, error: `${path} must be an array` };
    }
    
    if (schema.type === 'object' && (typeof value !== 'object' || value === null || Array.isArray(value))) {
        return { isValid: false, error: `${path} must be an object` };
    }
    
    // Range validation for numbers
    if (schema.type === 'number' && typeof value === 'number') {
        if (schema.minimum !== undefined && value < schema.minimum) {
            return { isValid: false, error: `${path} must be >= ${schema.minimum}` };
        }
        if (schema.maximum !== undefined && value > schema.maximum) {
            return { isValid: false, error: `${path} must be <= ${schema.maximum}` };
        }
    }
    
    // Length validation for strings
    if (schema.type === 'string' && typeof value === 'string') {
        if (schema.maxLength !== undefined && value.length > schema.maxLength) {
            return { isValid: false, error: `${path} must be <= ${schema.maxLength} characters` };
        }
    }
    
    // Enum validation
    if (schema.enum && !(schema.enum as any[]).includes(value)) {
        return { isValid: false, error: `${path} must be one of: ${schema.enum.join(', ')}` };
    }
    
    // Format validation
    if (schema.format === 'email' && typeof value === 'string') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            return { isValid: false, error: `${path} must be a valid email address` };
        }
    }
    
    // Array item validation
    if (schema.type === 'array' && Array.isArray(value) && schema.items) {
        for (let i = 0; i < value.length; i++) {
            const itemResult = validateValue(value[i], schema.items, `${path}[${i}]`);
            if (!itemResult.isValid) {
                return itemResult;
            }
        }
    }
    
    // Object property validation
    if (schema.type === 'object' && typeof value === 'object' && value !== null && schema.properties) {
        return validateObject(value, schema, path);
    }
    
    return { isValid: true };
}

/**
 * Validate an object against a schema
 */
function validateObject(obj: Record<string, any>, schema: SchemaProperty | CategorySchema, path: string): ValidationResult {
    if (!schema.properties) {
        return { isValid: true };
    }
    
    // Check required properties
    if (schema.required) {
        for (const requiredProp of schema.required) {
            if (!(requiredProp in obj)) {
                return { isValid: false, error: `${path}.${requiredProp} is required` };
            }
        }
    }
    
    // Validate each property
    for (const [key, value] of Object.entries(obj)) {
        if (schema.properties[key]) {
            const result = validateValue(value, schema.properties[key], `${path}.${key}`);
            if (!result.isValid) {
                return result;
            }
        }
    }
    
    return { isValid: true };
}

/**
 * Get the default value for a schema property
 */
function getDefaultValue(schema: SchemaProperty): any {
    if (schema.default !== undefined) {
        return schema.default;
    }
    
    // Fallback defaults based on type
    switch (schema.type) {
        case 'boolean': return false;
        case 'number': return 0;
        case 'string': return '';
        case 'array': return [];
        case 'object': return {};
        default: return null;
    }
}