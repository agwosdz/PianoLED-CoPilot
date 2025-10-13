/**
 * Settings Validation Utilities
 * Provides real-time validation feedback for settings forms
 */

import { validateSetting, validateCategory, validateAllSettings } from '../schemas/settingsSchema.js';
import { writable, derived, type Writable } from 'svelte/store';

// Type definitions
interface ValidationResult {
    isValid: boolean;
    error?: string;
}

interface CategoryValidationState {
    isValid: boolean;
    errors: Record<string, string | undefined>;
    warnings: Record<string, string>;
    loading: boolean;
}

interface ValidationSummary {
    totalFields: number;
    validFields: number;
    invalidFields: number;
    warningFields: number;
    isAllValid: boolean;
    hasWarnings: boolean;
}

interface CategoryValidation {
    subscribe: Writable<CategoryValidationState>['subscribe'];
    validateField: (key: string, value: any, showLoading?: boolean) => Promise<ValidationResult>;
    validateCategory: (data: any) => Promise<ValidationResult>;
    clear: () => void;
}

type ValidationState = 'none' | 'validating' | 'valid' | 'invalid' | 'warning';

// Validation state store
export const validationState: Writable<Record<string, any>> = writable({});

// Validation results store
export const validationResults: Writable<Record<string, any>> = writable({});

// Loading states for individual fields
export const fieldValidationLoading: Writable<Record<string, boolean>> = writable({});

/**
 * Create a validation store for a specific settings category
 */
export function createCategoryValidation(category: string): CategoryValidation {
    const categoryValidation: Writable<CategoryValidationState> = writable({
        isValid: true,
        errors: {},
        warnings: {},
        loading: false
    });

    return {
        subscribe: categoryValidation.subscribe,
        
        /**
         * Validate a single field in real-time
         */
        validateField: async (key: string, value: any, showLoading: boolean = true): Promise<ValidationResult> => {
            if (showLoading) {
                fieldValidationLoading.update((state: Record<string, boolean>) => ({
                    ...state,
                    [`${category}.${key}`]: true
                }));
            }

            // Simulate async validation delay for better UX
            await new Promise(resolve => setTimeout(resolve, 300));

            const result = validateSetting(category, key, value);
            
            categoryValidation.update((state: CategoryValidationState) => {
                const newErrors = { ...state.errors };
                const newWarnings = { ...state.warnings };
                
                if (result.isValid) {
                    delete newErrors[key];
                    // Check for warnings (optional validation)
                    const warning = getFieldWarning(category, key, value);
                    if (warning) {
                        newWarnings[key] = warning;
                    } else {
                        delete newWarnings[key];
                    }
                } else {
                    newErrors[key] = result.error || 'Validation failed';
                    delete newWarnings[key];
                }

                const isValid = Object.keys(newErrors).length === 0;
                
                return {
                    ...state,
                    isValid,
                    errors: newErrors,
                    warnings: newWarnings
                };
            });

            if (showLoading) {
                fieldValidationLoading.update((state: Record<string, boolean>) => ({
                    ...state,
                    [`${category}.${key}`]: false
                }));
            }

            return result;
        },

        /**
         * Validate entire category
         */
        validateCategory: async (data: any): Promise<ValidationResult> => {
            categoryValidation.update((state: CategoryValidationState) => ({ ...state, loading: true }));

            const result = validateCategory(category, data);
            
            categoryValidation.update((state: CategoryValidationState) => ({
                ...state,
                loading: false,
                isValid: result.isValid,
                errors: result.isValid ? {} : { _category: result.error || 'Category validation failed' },
                warnings: {}
            }));

            return result;
        },

        /**
         * Clear validation state
         */
        clear: (): void => {
            categoryValidation.set({
                isValid: true,
                errors: {},
                warnings: {},
                loading: false
            });
        }
    };
}

/**
 * Get validation state for a specific field
 */
export function getFieldValidationState(
    category: string, 
    key: string, 
    errors?: Record<string, string>, 
    warnings?: Record<string, string>, 
    loading?: Record<string, boolean>
): ValidationState {
    const fieldKey = `${category}.${key}`;
    const hasError = errors && errors[key];
    const hasWarning = warnings && warnings[key];
    const isLoading = loading && loading[fieldKey];

    if (isLoading) return 'validating';
    if (hasError) return 'invalid';
    if (hasWarning) return 'warning';
    if (!hasError && !hasWarning && (errors || warnings)) return 'valid';
    return 'none';
}

/**
 * Get formatted error message for a field
 */
export function getFieldErrorMessage(category: string, key: string, error: string): string {
    // Common error message formatting
    const fieldName = key.replace(/([A-Z])/g, ' $1').toLowerCase();
    
    if (error.includes('required')) {
        return `${fieldName} is required`;
    }
    
    if (error.includes('minimum')) {
        return `${fieldName} is below the minimum value`;
    }
    
    if (error.includes('maximum')) {
        return `${fieldName} exceeds the maximum value`;
    }
    
    if (error.includes('type')) {
        return `${fieldName} has an invalid type`;
    }
    
    // Return original error if no specific formatting applies
    return error;
}

/**
 * Get warning message for a field (optional validation)
 */
function getFieldWarning(category: string, key: string, value: any): string | null {
    // LED category warnings
    if (category === 'led') {
        if (key === 'brightness' && typeof value === 'number') {
            if (value > 0.8) return 'High brightness may cause eye strain';
            if (value < 0.1) return 'Very low brightness may be hard to see';
        }
        
        if (key === 'ledCount' && typeof value === 'number') {
            if (value > 200) return 'Large LED counts may impact performance';
        }
    }
    
    // Piano category warnings
    if (category === 'piano') {
        if (key === 'velocity' && typeof value === 'number') {
            if (value > 100) return 'High velocity may cause loud playback';
        }
    }
    
    // Audio category warnings
    if (category === 'audio') {
        if (key === 'volume' && typeof value === 'number') {
            if (value > 0.9) return 'High volume may cause audio distortion';
        }
        
        if (key === 'latency' && typeof value === 'number') {
            if (value > 50) return 'High latency may affect real-time performance';
        }
    }
    
    return null;
}

/**
 * Create a debounced validator function
 */
export function createDebouncedValidator(
    validationFn: (value: any) => Promise<ValidationResult> | ValidationResult, 
    delay: number = 500
): (value: any) => Promise<ValidationResult> {
    let timeoutId: NodeJS.Timeout;
    
    return (value: any): Promise<ValidationResult> => {
        return new Promise((resolve) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(async () => {
                const result = await validationFn(value);
                resolve(result);
            }, delay);
        });
    };
}

/**
 * Batch validation for multiple fields
 */
export async function validateFields(
    category: string, 
    fields: Record<string, any>
): Promise<Record<string, ValidationResult>> {
    const results: Record<string, ValidationResult> = {};
    const promises = Object.entries(fields).map(async ([key, value]) => {
        const result = validateSetting(category, key, value);
        results[key] = result;
        return result;
    });

    await Promise.all(promises);
    return results;
}

/**
 * Get validation summary for a set of validation results
 */
export function getValidationSummary(validationResults: Record<string, ValidationResult>): ValidationSummary {
    const results = Object.values(validationResults);
    const totalFields = results.length;
    const validFields = results.filter(r => r.isValid).length;
    const invalidFields = results.filter(r => !r.isValid).length;
    
    // For warnings, we'd need additional data structure
    const warningFields = 0; // Placeholder - would need warning tracking
    
    return {
        totalFields,
        validFields,
        invalidFields,
        warningFields,
        isAllValid: invalidFields === 0,
        hasWarnings: warningFields > 0
    };
}

/**
 * Utility object with all validation functions
 */
export const validationUtils = {
    createCategoryValidation,
    getFieldValidationState,
    getFieldErrorMessage,
    createDebouncedValidator,
    validateFields,
    getValidationSummary
};