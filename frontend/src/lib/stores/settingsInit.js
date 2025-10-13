/**
 * Settings Initialization Module
 * Handles proper initialization of settings store with server synchronization
 */

import { settingsAPI } from './settings.js';
import { browser } from '$app/environment';

/** @type {Promise<boolean> | null} */
let initializationPromise = null;

/**
 * Initialize settings by loading from server
 * This should be called once during app startup
 * @returns {Promise<boolean>}
 */
export async function initializeSettings() {
    if (initializationPromise) {
        return initializationPromise;
    }
    
    if (!browser) {
        return Promise.resolve(true);
    }
    
    initializationPromise = settingsAPI.loadAllSettings()
        .then(() => {
            console.log('Settings initialized successfully');
            return true;
        })
        .catch(error => {
            console.error('Failed to initialize settings:', error);
            // Return false to indicate failure but don't throw
            return false;
        });
    
    return initializationPromise;
}

/**
 * Check if settings have been initialized
 * @returns {boolean}
 */
export function areSettingsInitialized() {
    return initializationPromise !== null;
}