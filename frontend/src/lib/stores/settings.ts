/**
 * Centralized Settings Store for Piano LED Visualizer
 * Provides reactive settings management with WebSocket synchronization
 */

import { writable, derived, type Writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { getSocket } from '$lib/socket';
import { normalizeSettings } from '$lib/utils/normalizeSettings.js';

// Declare io as any to avoid TypeScript errors
declare const io: any;

// Declare optional global socket IO backend URL to satisfy TypeScript
declare global {
    interface Window {
        socketIOBackendUrl?: string;
    }
}

// Type definitions
interface LEDSettings {
    enabled?: boolean;
    led_count?: number;
    brightness?: number;
    colorScheme?: string;
    animationSpeed?: number;
    gpioPin?: number;
    ledOrientation?: string;
    ledType?: string;
    gammaCorrection?: number;
    color_temperature?: number;
    gamma_correction?: number;
    count?: number;
    leds_per_meter?: number;
}

interface PianoSettings {
    enabled?: boolean;
    octave?: number;
    velocity_sensitivity?: number;
    channel?: number;
    size?: string;
    keys?: number;
    start_note?: string;
    end_note?: string;
}

interface AudioSettings {
    enabled?: boolean;
    volume?: number;
    inputDevice?: string;
    gain?: number;
}

interface GPIOSettings {
    enabled?: boolean;
    pins?: number[];
    debounce_time?: number;
    dma_channel?: number;
}

interface HardwareSettings {
    type?: string;
    board_revision?: string;
    auto_detect_midi?: boolean;
    auto_detect_gpio?: boolean;
    auto_detect_led?: boolean;
}

interface SystemSettings {
    theme?: string;
    debug?: boolean;
}

interface UserSettings {
    name?: string;
    preferences?: Record<string, any>;
}

interface Settings {
    led?: LEDSettings;
    piano?: PianoSettings;
    audio?: AudioSettings;
    gpio?: GPIOSettings;
    hardware?: HardwareSettings;
    system?: SystemSettings;
    user?: UserSettings;
    [key: string]: any;
}

interface FieldMapping {
    [key: string]: [string, string];
}

interface WebSocketMessage {
    type: string;
    category?: string;
    key?: string;
    value?: any;
    data?: any;
}

// Auto-save mechanism
let autoSaveTimeout: NodeJS.Timeout | null = null;
const AUTO_SAVE_DELAY = 2000; // 2 seconds

/**
 * Migrate settings from old structure to new consolidated structure
 */
function migrateSettingsStructure(settings: any): Settings {
    // Check if this is already the new structure
    if (settings && typeof settings === 'object' && 
        (settings.led || settings.piano || settings.audio || settings.gpio || settings.hardware)) {
        return settings;
    }

    // Legacy field mappings for backward compatibility
    const fieldMappings: FieldMapping = {
        // LED settings
        'ledCount': ['led', 'led_count'],
        'brightness': ['led', 'brightness'],
        'colorScheme': ['led', 'colorScheme'],
        'animationSpeed': ['led', 'animationSpeed'],
        'gpioPin': ['led', 'gpioPin'],
        'ledOrientation': ['led', 'ledOrientation'],
        'ledType': ['led', 'ledType'],
        'gammaCorrection': ['led', 'gammaCorrection'],
        
        // Piano settings
        'pianoOctave': ['piano', 'octave'],
        'velocitySensitivity': ['piano', 'velocity_sensitivity'],
        'pianoChannel': ['piano', 'channel'],
        
        // Audio settings
        'audioEnabled': ['audio', 'enabled'],
        'audioVolume': ['audio', 'volume'],
        'audioInputDevice': ['audio', 'inputDevice'],
        'audioGain': ['audio', 'gain'],
        
        // GPIO settings
        'gpioPins': ['gpio', 'pins'],
        'gpioDebounce': ['gpio', 'debounce_time'],
        'gpioDma': ['gpio', 'dma_channel'],
        
        // Hardware settings
        'hardwareType': ['hardware', 'type'],
        'boardRevision': ['hardware', 'board_revision']
    };

    const migratedSettings: Settings = {};
    
    // Initialize category objects
    const categories = ['led', 'piano', 'audio', 'gpio', 'hardware'];
    categories.forEach(category => {
        (migratedSettings as any)[category] = {};
    });

    // Migrate flat fields to nested structure
    for (const [flatKey, value] of Object.entries(settings || {})) {
        const mapping = fieldMappings[flatKey];
        if (mapping) {
            const [category, nestedKey] = mapping;
            if (!migratedSettings[category as keyof Settings]) {
                (migratedSettings as any)[category] = {};
            }
            (migratedSettings as any)[category][nestedKey] = value;
        } else {
            // Keep unmapped fields at top level for now
            migratedSettings[flatKey] = value;
        }
    }

    // Fill in defaults for missing required fields
    const defaults = getAllDefaults();
    categories.forEach(category => {
        if (defaults[category]) {
            (migratedSettings as any)[category] = {
                ...defaults[category],
                ...(migratedSettings as any)[category]
            };
        }
    });

    console.log('Migrated settings from flat to nested structure:', migratedSettings);
    return migratedSettings;
}

/**
 * Consolidate settings from multiple localStorage keys into unified structure
 */
function consolidateStorageData(): Settings {
    const consolidatedSettings: Settings = {};
    
    if (browser) {
        // Check for existing unified settings first
        const unifiedSettings = localStorage.getItem('settings');
        if (unifiedSettings) {
            try {
                return JSON.parse(unifiedSettings);
            } catch (e) {
                console.warn('Failed to parse unified settings, falling back to consolidation');
            }
        }

        // Consolidate from individual category keys
        const categoryKeys = ['led', 'piano', 'audio', 'gpio', 'hardware', 'system', 'user'];
        categoryKeys.forEach(category => {
            const categoryData = localStorage.getItem(`settings_${category}`);
            if (categoryData) {
                try {
                    consolidatedSettings[category as keyof Settings] = JSON.parse(categoryData);
                } catch (e) {
                    console.warn(`Failed to parse ${category} settings:`, e);
                }
            }
        });

        // Also check for legacy flat settings
        const legacySettings = localStorage.getItem('pianoLEDSettings');
        if (legacySettings) {
            try {
                const parsed = JSON.parse(legacySettings);
                const migrated = migrateSettingsStructure(parsed);
                Object.assign(consolidatedSettings, migrated);
            } catch (e) {
                console.warn('Failed to parse legacy settings:', e);
            }
        }
    }
    
    return consolidatedSettings;
}

/**
 * Clean up old localStorage keys after consolidation
 */
function cleanupOldStorageKeys(): void {
    if (browser) {
        const keysToRemove = [
            'pianoLEDSettings',
            'settings_led',
            'settings_piano', 
            'settings_audio',
            'settings_gpio',
            'settings_hardware',
            'settings_system',
            'settings_user'
        ];
        
        keysToRemove.forEach(key => {
            if (localStorage.getItem(key)) {
                localStorage.removeItem(key);
            }
        });
    }
}

/**
 * Merge settings with defaults, preserving existing values
 */
function mergeWithDefaults(settings: Settings, defaults: Settings): Settings {
    const merged: Settings = { ...defaults };
    
    for (const [category, categorySettings] of Object.entries(settings)) {
        if (typeof categorySettings === 'object' && categorySettings !== null) {
            merged[category as keyof Settings] = {
                ...(defaults[category as keyof Settings] || {}),
                ...categorySettings
            };
        } else {
            (merged as any)[category] = categorySettings;
        }
    }
    
    return merged;
}

export const settings: Writable<Settings> = writable({}, (set) => {
    // Initialize settings on store creation
    if (browser) {
        try {
            // First try to get consolidated settings
            let currentSettings = consolidateStorageData();
            
            // If no settings found, start with defaults
            if (!currentSettings || Object.keys(currentSettings).length === 0) {
                currentSettings = getAllDefaults();
            } else {
                // Migrate if needed
                currentSettings = migrateSettingsStructure(currentSettings);
                
                // Merge with defaults to ensure all required fields exist
                const defaults = getAllDefaults();
                currentSettings = mergeWithDefaults(currentSettings, defaults);
            }
            
            // Validate the consolidated settings
            const validation = validateAllSettings(currentSettings);
            if (!validation.isValid) {
                console.warn('Settings validation failed:', validation.errors);
                // Use defaults for invalid settings
                currentSettings = getAllDefaults();
            }
            
            // Save consolidated settings and cleanup old keys
            localStorage.setItem('settings', JSON.stringify(currentSettings));
            cleanupOldStorageKeys();
            
            set(currentSettings);
        } catch (error) {
            console.error('Failed to load settings:', error);
            const defaults = getAllDefaults();
            set(defaults);
            if (browser) {
                localStorage.setItem('settings', JSON.stringify(defaults));
            }
        }
    }

    return () => {
        // Cleanup function
        if (autoSaveTimeout) {
            clearTimeout(autoSaveTimeout);
        }
    };
});

// Auto-save settings to localStorage when they change
if (browser) {
    settings.subscribe((currentSettings: Settings) => {
        if (autoSaveTimeout) {
            clearTimeout(autoSaveTimeout);
        }
        
        autoSaveTimeout = setTimeout(() => {
            try {
                localStorage.setItem('settings', JSON.stringify(currentSettings));
                console.log('Settings auto-saved to localStorage');
            } catch (error) {
                console.error('Failed to save settings to localStorage:', error);
            }
        }, AUTO_SAVE_DELAY);
    });
}

export const settingsLoading: Writable<boolean> = writable(false);
export const settingsError: Writable<string | null> = writable(null);

// Persisted state tracking
export const lastSavedSettings: Writable<Settings | null> = writable(null);
export const isFieldPersisted = (category: string, key: string, value: any, saved: Settings | null): boolean => {
    if (!saved) return false;
    try {
        const cat = (saved as any)[category];
        if (cat && Object.prototype.hasOwnProperty.call(cat, key)) {
            return JSON.stringify(cat[key]) === JSON.stringify(value);
        }
        return false;
    } catch { return false; }
};

export const savingSettings = writable<Record<string, Record<string, boolean>>>({});

function setSavingFlagsForPayload(payload: Record<string, any>) {
    savingSettings.update((curr) => {
        const next = { ...(curr || {}) } as Record<string, Record<string, boolean>>;
        for (const [cat, data] of Object.entries(payload || {})) {
            if (!data || typeof data !== 'object') continue;
            if (!next[cat]) next[cat] = {};
            for (const key of Object.keys(data)) {
                next[cat][key] = true;
            }
        }
        return next;
    });
}

function clearSavingFlagsForPayload(payload: Record<string, any>) {
    savingSettings.update((curr) => {
        const next = { ...(curr || {}) } as Record<string, Record<string, boolean>>;
        for (const [cat, data] of Object.entries(payload || {})) {
            if (!data || typeof data !== 'object') continue;
            if (!next[cat]) continue;
            for (const key of Object.keys(data)) {
                next[cat][key] = false;
            }
        }
        return next;
    });
}

export const failedSettings = writable<Record<string, Record<string, string>>>({});

function setFailedFlagsForPayload(payload: Record<string, any>, message: string = 'Save failed') {
    failedSettings.update((curr) => {
        const next = { ...(curr || {}) } as Record<string, Record<string, string>>;
        for (const [cat, data] of Object.entries(payload || {})) {
            if (!data || typeof data !== 'object') continue;
            if (!next[cat]) next[cat] = {};
            for (const key of Object.keys(data)) {
                next[cat][key] = message;
            }
        }
        return next;
    });
}

function clearFailedFlagsForPayload(payload: Record<string, any>) {
    failedSettings.update((curr) => {
        const next = { ...(curr || {}) } as Record<string, Record<string, string>>;
        for (const [cat, data] of Object.entries(payload || {})) {
            if (!data || typeof data !== 'object') continue;
            if (!next[cat]) continue;
            for (const key of Object.keys(data)) {
                delete next[cat][key];
            }
        }
        return next;
    });
}

// Derived stores for specific setting categories
export const ledSettings = derived(settings, ($settings: Settings): LEDSettings => ({
    enabled: false,
    count: 60,
    brightness: 100,
    color_temperature: 6500,
    gamma_correction: 2.2,
    leds_per_meter: 60,
    ...($settings.led || {})
}));

export const audioSettings = derived(settings, ($settings: Settings): AudioSettings => ({
    enabled: true,
    volume: 100,
    ...($settings.audio || {})
}));

export const pianoSettings = derived(settings, ($settings: Settings): PianoSettings => ({
    enabled: true,
    octave: 4,
    ...($settings.piano || {})
}));

export const gpioSettings = derived(settings, ($settings: Settings): GPIOSettings => ({
    enabled: false,
    pins: [],
    ...($settings.gpio || {})
}));

export const hardwareSettings = derived(settings, ($settings: Settings): HardwareSettings => ({
    auto_detect_midi: false,
    auto_detect_gpio: false,
    auto_detect_led: false,
    ...($settings.hardware || {})
}));

export const systemSettings = derived(settings, ($settings: Settings): SystemSettings => ({
    theme: 'dark',
    debug: false,
    ...($settings.system || {})
}));

export const userSettings = derived(settings, ($settings: Settings): UserSettings => ({
    name: '',
    preferences: {},
    ...($settings.user || {})
}));

// Canonical hardware configuration derived stores
export const canonicalLedCount = derived(settings, (s: Settings) => {
    const count = (s?.led?.led_count ?? (s as any)?.led_count ?? 246) as any;
    try {
        return Number.isFinite(count) ? count : parseInt(String(count));
    } catch {
        return 246;
    }
});

export const canonicalGpioPin = derived(settings, (s: Settings) => {
    const pin = ((s as any)?.gpio?.data_pin ?? (s as any)?.gpio_pin ?? 19) as any;
    try {
        return Number.isFinite(pin) ? pin : parseInt(String(pin));
    } catch {
        return 19;
    }
});

// Settings API class
class SettingsAPI {
    private baseUrl: string;
    private socket: any;
    private initialized: boolean;

    constructor() {
        this.baseUrl = '/api/settings';
        this.socket = null;
        this.initialized = false;
        
        if (browser) {
            this.initializeWebSocket();
        }
    }

    initializeWebSocket(): void {
        try {
            if (typeof io === 'undefined') {
                console.warn('Socket.IO client not available');
                return;
            }
            const isDev = typeof import.meta !== 'undefined' && (import.meta as any)?.env?.DEV;
            // Prefer same-origin in dev (proxied by Vite), otherwise use configured URL if provided
            const backendUrl = (!isDev && typeof window !== 'undefined' && (window as any).socketIOBackendUrl) || undefined;
            this.socket = backendUrl ? io(backendUrl) : io();
            this.initialized = true;

            this.socket.on('connect', () => {
                console.log('Settings WebSocket connected');
            });

            this.socket.on('disconnect', () => {
                console.log('Settings WebSocket disconnected');
            });

            this.socket.on('setting_changed', (data: WebSocketMessage) => {
                console.log('Received setting change:', data);
                this.handleSettingChange(data);
            });

            this.socket.on('settings_update', (data: WebSocketMessage) => {
                if (data && data.category && data.key) {
                    const category = data.category as string; // narrowed
                    const key = data.key as string; // narrowed
                    settings.update((current: Settings) => {
                        const updated = { ...current } as any;
                        if (!updated[category]) {
                            updated[category] = {};
                        }
                        updated[category][key] = data.value;
                        return updated as Settings;
                    });
                } else if (data && (data as any).data) {
                    // Merge full settings payloads
                    const payload = (data as any).data || {};
                    settings.update((current: Settings) => ({ ...current, ...payload }));
                }
            });

            this.socket.on('settings_bulk_update', (data: any) => {
                console.log('Received bulk settings update:', data);
                this.handleBulkUpdate(data);
            });

            this.socket.on('settings_reset', (data: any) => {
                console.log('Received settings reset:', data);
                if (data && data.category) {
                    this.handleCategoryReset(data.category);
                } else {
                    this.loadAllSettings();
                }
            });

            this.socket.on('error', (error: any) => {
                console.error('Settings WebSocket error:', error);
                settingsError.set(`WebSocket error: ${error.message || error}`);
            });
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
        }
    }

    handleSettingChange(data: WebSocketMessage): void {
        if (data && data.category && data.key !== undefined && data.value !== undefined) {
            // Validate the incoming setting
            const validationResult = validateSetting(data.category, data.key, data.value);
            if (!validationResult.isValid) {
                console.error('Invalid setting received via WebSocket:', validationResult.error);
                return;
            }

            settings.update((currentSettings: Settings) => {
                const updated = { ...currentSettings };
                if (!updated[data.category!]) {
                    (updated as any)[data.category!] = {};
                }
                (updated as any)[data.category!][data.key!] = data.value;
                console.log(`Updated setting ${data.category}.${data.key} to:`, data.value);
                return updated;
            });
        } else {
            console.warn('Invalid setting change data received:', data);
        }
    }

    handleBulkUpdate(data: any): void {
        if (data && typeof data === 'object') {
            // Validate all settings in the bulk update
            const validationResult = validateAllSettings(data);
            if (!validationResult.isValid) {
                console.error('Invalid settings received via WebSocket bulk update:', validationResult.errors);
                return;
            }

            settings.update((currentSettings: Settings) => {
                const updated = { ...currentSettings, ...data };
                console.log('Applied bulk settings update:', updated);
                return updated;
            });
        } else {
            console.warn('Invalid bulk update data received:', data);
        }
    }

    handleCategoryReset(category: string): void {
        if (category) {
            // Get default values for the category
            const categoryDefaults = getCategoryDefaults(category);
            if (!categoryDefaults || Object.keys(categoryDefaults).length === 0) {
                console.error(`No defaults found for category: ${category}`);
                return;
            }

            settings.update((currentSettings: Settings) => {
                const updated = { ...currentSettings };
                (updated as any)[category] = { ...categoryDefaults };
                console.log(`Reset category ${category} to defaults`);
                return updated;
            });
        }
    }

    async loadAllSettings(): Promise<Settings> {
        settingsLoading.set(true);
        try {
            const response = await fetch(`${this.baseUrl}/`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const allSettings = await response.json();
            const normalized = normalizeSettings(allSettings) as Settings;
            const merged = mergeWithDefaults(normalized, getAllDefaults());
            settings.set(merged);
            lastSavedSettings.set(merged);
            return merged;
        } catch (error) {
            console.error('Failed to load all settings:', error);
            settingsError.set(`Failed to load settings: ${error instanceof Error ? error.message : String(error)}`);
            throw error;
        } finally {
            settingsLoading.set(false);
        }
    }

    async getCategorySetting(category: string): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/${category}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Validate the category settings
            const validationResult = validateCategory(category, data);
            if (!validationResult.isValid) {
                console.warn(`Invalid ${category} settings received:`, validationResult.errors);
                return getCategoryDefaults(category);
            }
            
            return data;
        } catch (error) {
            console.error(`Failed to get ${category} settings:`, error);
            throw error;
        }
    }

    async getSetting(category: string, key: string): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/${category}/${key}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data.value;
        } catch (error) {
            console.error(`Failed to get setting ${category}.${key}:`, error);
            throw error;
        }
    }

    async setSetting(category: string, key: string, value: any): Promise<void> {
        // Validate the setting before sending
        const validationResult = validateSetting(category, key, value);
        if (!validationResult.isValid) {
            const errorMsg = `Invalid setting value for ${category}.${key}: ${validationResult.error}`;
            console.error(errorMsg);
            settingsError.set(errorMsg);
            throw new Error(errorMsg);
        }

        try {
            const response = await fetch(`${this.baseUrl}/${category}/${key}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ value })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Update local store immediately for responsive UI
            settings.update((currentSettings: Settings) => {
                const updated = { ...currentSettings };
                if (!updated[category as keyof Settings]) {
                    (updated as any)[category] = {};
                }
                (updated as any)[category][key] = value;
                return updated;
            });
            
            console.log(`Successfully set ${category}.${key} to:`, value);
            
        } catch (error) {
            console.error(`Failed to set setting ${category}.${key}:`, error);
            settingsError.set(`Failed to save setting: ${error instanceof Error ? error.message : String(error)}`);
            throw error;
        }
    }

    async updateSettings(settingsData: Settings): Promise<void> {
        const validationResult = validateAllSettings(settingsData);
        if (!validationResult.isValid) {
            const errorMsg = `Invalid settings data: ${JSON.stringify(validationResult.errors)}`;
            console.error(errorMsg);
            settingsError.set(errorMsg);
            throw new Error(errorMsg);
        }

        // Sanitize payload: only allowed categories, move extras to user.preferences, clean invalid email
        const allowedCategories = new Set(['led', 'audio', 'piano', 'gpio', 'hardware', 'system', 'user']);
        const allowedProps: Record<string, Set<string>> = {
            led: new Set([
                'enabled','led_count','max_led_count','led_channel','brightness','led_type','led_strip_type','led_orientation','data_pin','clock_pin','gpioPin','reverse_order','color_mode','colorScheme','color_profile','color_temperature','gamma_correction','white_balance','performance_mode','power_supply_voltage','power_supply_current','power_limiting_enabled','max_power_watts','dither_enabled','update_rate','thermal_protection_enabled','max_temperature_celsius','animationSpeed'
            ]),
    gpio: new Set(['enabled','pins','debounce_time','data_pin','clock_pin']),
            piano: new Set(['enabled','octave','velocity_sensitivity','channel','size','keys','octaves','start_note','end_note','key_mapping','key_mapping_mode']),
            audio: new Set(['enabled','volume','sample_rate','buffer_size','latency','device_id']),
            hardware: new Set(['auto_detect_midi','auto_detect_gpio','auto_detect_led','midi_device_id','rtpmidi_enabled','rtpmidi_port']),
            system: new Set(['theme','debug','log_level','auto_save','backup_settings']),
            user: new Set(['name','email','preferences'])
        };
        const sanitized: Settings = {} as any;

        // Copy allowed categories
        for (const [key, val] of Object.entries(settingsData || {})) {
            if (allowedCategories.has(key)) {
                (sanitized as any)[key] = val;
            }
        }
        // Ensure user and preferences exist
        if (!sanitized.user) {
            sanitized.user = { name: '', preferences: {} };
        }
        if (!sanitized.user.preferences) {
            sanitized.user.preferences = {};
        }
        // Move unknown top-level categories into user.preferences
        for (const [key, val] of Object.entries(settingsData || {})) {
            if (!allowedCategories.has(key)) {
                (sanitized.user!.preferences as any)[key] = val;
            }
        }
        // Remove invalid user.email if present
        if (sanitized.user && typeof (sanitized.user as any).email === 'string') {
            const email = (sanitized.user as any).email as string;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                delete (sanitized.user as any).email;
            }
        }

        // Ensure required LED fields if 'led' category is present
        if (sanitized.led) {
            const current = get(settings) as Settings;
            const ledData: any = sanitized.led || {};
            const currentLed: any = (current?.led || {});
            const enabled = typeof ledData.enabled === 'boolean' ? ledData.enabled : (typeof currentLed.enabled === 'boolean' ? currentLed.enabled : true);
            // Resolve led_count from provided led_count or legacy count or current
            let ledCount = ledData.led_count ?? ledData.count ?? currentLed.led_count ?? currentLed.count ?? 246 as number;
            try { ledCount = parseInt((ledCount as any)); } catch { ledCount = 246; }
            // Normalize brightness to 0-1 range and ensure numeric
            let bRaw: any = ledData.brightness ?? currentLed.brightness ?? 1;
            if (typeof bRaw === 'string') {
                bRaw = bRaw.replace(/[^0-9.]/g, '');
            }
            let bNum = typeof bRaw === 'number' ? bRaw : parseFloat(bRaw);
            if (!isFinite(bNum)) bNum = 1;
            const brightness = bNum > 1 ? Math.max(0, Math.min(1, bNum / 100)) : Math.max(0, Math.min(1, bNum));
            // Normalize PWM channel and ensure valid range
            let channelRaw: any = ledData.led_channel ?? currentLed.led_channel ?? 0;
            let ledChannel = parseInt(String(channelRaw), 10);
            if (!Number.isFinite(ledChannel)) {
                ledChannel = 0;
            }
            ledChannel = Math.min(Math.max(ledChannel, 0), 1);
            // Ensure update_rate present and valid (1-120)
            let updateRateRaw: any = ledData.update_rate ?? currentLed.update_rate ?? (current as any)?.updateRate ?? 60;
            let updateRate = parseInt(String(updateRateRaw));
            if (!Number.isFinite(updateRate) || updateRate < 1) updateRate = 60;
            updateRate = Math.min(Math.max(updateRate, 1), 120);
            // Normalize data pin if present
            let dataPin = ledData.data_pin ?? currentLed.data_pin;
            if (dataPin !== undefined) {
                const parsed = parseInt(String(dataPin), 10);
                dataPin = Number.isFinite(parsed) ? parsed : dataPin;
            }
            sanitized.led = {
                ...ledData,
                ...(dataPin !== undefined ? { data_pin: dataPin } : {}),
                enabled,
                led_count: ledCount,
                led_channel: ledChannel,
                brightness,
                update_rate: updateRate
            } as any;
        }

        // Filter allowed properties per category to avoid backend 400s
        for (const [cat, data] of Object.entries(sanitized)) {
            if (!allowedCategories.has(cat)) continue;
            const props = allowedProps[cat];
            const filtered: any = {};
            for (const [k, v] of Object.entries(data || {})) {
                if (props.has(k)) filtered[k] = v;
            }
            (sanitized as any)[cat] = filtered;
        }

        setSavingFlagsForPayload(sanitized);
        try {
            const response = await fetch(`${this.baseUrl}/bulk`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(sanitized)
            });
            
            if (!response.ok) {
                // Try to parse server error message for clarity
                let serverMsg = '';
                try {
                    const err = await response.json();
                    serverMsg = err?.message || '';
                } catch {}
                throw new Error(`HTTP ${response.status}: ${response.statusText}${serverMsg ? ` — ${serverMsg}` : ''}`);
            }
            
            // Merge partial updates into the local store
            settings.update((current: Settings) => ({ ...current, ...sanitized }));
            lastSavedSettings.update((saved) => ({ ...(saved || {}), ...sanitized }));
            clearSavingFlagsForPayload(sanitized);
            clearFailedFlagsForPayload(sanitized);
            console.log('Successfully updated settings:', sanitized);
            
        } catch (error) {
            console.error('Failed to update settings:', error);
            settingsError.set(`Failed to update settings: ${error instanceof Error ? error.message : String(error)}`);
            // Keep saving flags active to indicate validating until resolved
            setFailedFlagsForPayload(sanitized, 'Save failed');
            throw error;
        }
    }

    async resetCategory(category: string): Promise<void> {
        try {
            const response = await fetch(`${this.baseUrl}/${category}/reset`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Get defaults for the category and update local store
            const categoryDefaults = getCategoryDefaults(category);
            settings.update((currentSettings: Settings) => {
                const updated = { ...currentSettings };
                (updated as any)[category] = { ...categoryDefaults };
                return updated;
            });
            
            console.log(`Successfully reset ${category} settings to defaults`);
            
        } catch (error) {
            console.error(`Failed to reset ${category} settings:`, error);
            settingsError.set(`Failed to reset settings: ${error instanceof Error ? error.message : String(error)}`);
            throw error;
        }
    }

    async resetAllSettings(): Promise<void> {
        try {
            const response = await fetch(`${this.baseUrl}/reset`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Reset to defaults
            const defaults = getAllDefaults();
            settings.set(defaults);
            console.log('Successfully reset all settings to defaults');
            
        } catch (error) {
            console.error('Failed to reset all settings:', error);
            settingsError.set(`Failed to reset settings: ${error instanceof Error ? error.message : String(error)}`);
            throw error;
        }
    }

    async exportSettings(): Promise<string> {
        try {
            const response = await fetch(`${this.baseUrl}/export`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return JSON.stringify(data, null, 2);
        } catch (error) {
            console.error('Failed to export settings:', error);
            throw error;
        }
    }

    async importSettings(settingsData: Settings): Promise<void> {
        // Validate settings before import
        const validationResult = validateAllSettings(settingsData);
        if (!validationResult.isValid) {
            throw new Error(`Invalid settings data: ${JSON.stringify(validationResult.errors)}`);
        }

        try {
            const response = await fetch(`${this.baseUrl}/import`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Update local store
            settings.set(settingsData);
            console.log('Successfully imported settings');
            
        } catch (error) {
            console.error('Failed to import settings:', error);
            throw error;
        }
    }

    async validateSettings(settingsData: Settings): Promise<{ valid: boolean; errors?: any }> {
        try {
            const response = await fetch(`${this.baseUrl}/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to validate settings:', error);
            return { valid: false, errors: [error instanceof Error ? error.message : String(error)] };
        }
    }

    async getSchema(): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/schema`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to get settings schema:', error);
            throw error;
        }
    }
}

// Export singleton instance
export const settingsAPI = new SettingsAPI();

// Convenience functions
export const loadSettings = (): Promise<Settings> => settingsAPI.loadAllSettings();
export const getSetting = (category: string, key: string): Promise<any> => settingsAPI.getSetting(category, key);
export const setSetting = (category: string, key: string, value: any): Promise<void> => settingsAPI.setSetting(category, key, value);
export const updateSettings = (settingsData: Settings): Promise<void> => settingsAPI.updateSettings(settingsData);
export const resetSettings = (category: string | null = null): Promise<void> => {
    return category ? settingsAPI.resetCategory(category) : settingsAPI.resetAllSettings();
};

// Validation functions (placeholder implementations)
function validateSetting(category: string, key: string, value: any): { isValid: boolean; error?: string } {
    // Basic validation - can be enhanced with schema validation
    if (!category || !key) {
        return { isValid: false, error: 'Category and key are required' };
    }
    return { isValid: true };
}

function validateCategory(category: string, data: any): { isValid: boolean; errors?: string[] } {
    // Basic validation - can be enhanced with schema validation
    if (!category || !data) {
        return { isValid: false, errors: ['Category and data are required'] };
    }
    return { isValid: true };
}

function validateAllSettings(settings: Settings): { isValid: boolean; errors?: string[] } {
    // Basic validation - can be enhanced with schema validation
    if (!settings || typeof settings !== 'object') {
        return { isValid: false, errors: ['Settings must be an object'] };
    }
    return { isValid: true };
}

function getCategoryDefaults(category: string): any {
    const defaults: Record<string, any> = {
        led: {
            enabled: false,
            count: 60,
            brightness: 100,
            color_temperature: 6500,
            gamma_correction: 2.2,
            leds_per_meter: 60
        },
        audio: {
            enabled: true,
            volume: 100
        },
        piano: {
            enabled: true,
            octave: 4
        },
        gpio: {
            enabled: false,
            pins: []
        },
        hardware: {
            auto_detect_midi: false,
            auto_detect_gpio: false,
            auto_detect_led: false
        },
        system: {
            theme: 'dark',
            debug: false
        },
        user: {
            name: '',
            preferences: {}
        }
    };
    return defaults[category] || {};
}

function getAllDefaults(): Settings {
    return {
        led: getCategoryDefaults('led'),
        audio: getCategoryDefaults('audio'),
        piano: getCategoryDefaults('piano'),
        gpio: getCategoryDefaults('gpio'),
        hardware: getCategoryDefaults('hardware'),
        system: getCategoryDefaults('system'),
        user: getCategoryDefaults('user')
    };
}