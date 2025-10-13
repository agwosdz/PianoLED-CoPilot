import { writable, derived, type Writable, type Readable } from 'svelte/store';
import { browser } from '$app/environment';

// Type definitions for preferences
interface UploadPreferences {
	autoUpload: boolean;
	rememberLastDirectory: boolean;
	showFilePreview: boolean;
	confirmBeforeReset: boolean;
}

interface UIPreferences {
	theme: 'light' | 'dark' | 'auto';
	reducedMotion: boolean;
	showTooltips: boolean;
	tooltipDelay: number;
	animationSpeed: 'slow' | 'normal' | 'fast';
}

interface A11yPreferences {
	highContrast: boolean;
	largeText: boolean;
	keyboardNavigation: boolean;
	screenReaderOptimized: boolean;
}

interface HelpPreferences {
	showOnboarding: boolean;
	showHints: boolean;
	completedTours: string[];
	skippedTours: string[];
}

interface HistoryPreferences {
	maxHistorySize: number;
	autosaveInterval: number;
	persistHistory: boolean;
}

interface Preferences {
	upload: UploadPreferences;
	ui: UIPreferences;
	a11y: A11yPreferences;
	help: HelpPreferences;
	history: HistoryPreferences;
}

type PreferenceCategory = keyof Preferences;
type PreferenceUpdates = Partial<Record<PreferenceCategory, Partial<Preferences[PreferenceCategory]>>>;

// Default preferences
const DEFAULT_PREFERENCES: Preferences = {
	// Upload preferences
	upload: {
		autoUpload: false,
		rememberLastDirectory: true,
		showFilePreview: true,
		confirmBeforeReset: true
	},
	// UI preferences
	ui: {
		theme: 'auto', // 'light', 'dark', 'auto'
		reducedMotion: false,
		showTooltips: true,
		tooltipDelay: 300,
		animationSpeed: 'normal' // 'slow', 'normal', 'fast'
	},
	// Accessibility preferences
	a11y: {
		highContrast: false,
		largeText: false,
		keyboardNavigation: true,
		screenReaderOptimized: false
	},
	// Help preferences
	help: {
		showOnboarding: true,
		showHints: true,
		completedTours: [],
		skippedTours: []
	},
	// History preferences
	history: {
		maxHistorySize: 50,
		autosaveInterval: 30000, // 30 seconds
		persistHistory: true
	}
};

// Load preferences from localStorage
function loadPreferences(): Preferences {
	if (!browser) return DEFAULT_PREFERENCES;
	
	try {
		const stored = localStorage.getItem('midi-visualizer-preferences');
		if (stored) {
			const parsed = JSON.parse(stored);
			// Merge with defaults to ensure all properties exist
			return mergeDeep(DEFAULT_PREFERENCES, parsed);
		}
	} catch (error) {
		console.warn('Failed to load preferences:', error);
	}
	
	return DEFAULT_PREFERENCES;
}

// Save preferences to localStorage
function savePreferences(preferences: Preferences): void {
	if (!browser) return;
	
	try {
		localStorage.setItem('midi-visualizer-preferences', JSON.stringify(preferences));
	} catch (error) {
		console.warn('Failed to save preferences:', error);
	}
}

// Deep merge utility
function mergeDeep<T extends Record<string, any>>(target: T, source: Partial<T>): T {
	const result = { ...target };
	
	for (const key in source) {
		if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
			result[key] = mergeDeep(target[key] || {} as T[Extract<keyof T, string>], source[key] as any);
		} else {
			result[key] = source[key] as any;
		}
	}
	
	return result;
}

// Create the main preferences store
export const preferences: Writable<Preferences> = writable(loadPreferences());

// Subscribe to changes and save to localStorage
if (browser) {
	preferences.subscribe(savePreferences);
}

// Derived stores for specific preference categories
export const uploadPreferences: Readable<UploadPreferences> = derived(
	preferences,
	($preferences: Preferences) => $preferences.upload
);

export const uiPreferences: Readable<UIPreferences> = derived(
	preferences,
	($preferences: Preferences) => $preferences.ui
);

export const a11yPreferences: Readable<A11yPreferences> = derived(
	preferences,
	($preferences: Preferences) => $preferences.a11y
);

export const helpPreferences: Readable<HelpPreferences> = derived(
	preferences,
	($preferences: Preferences) => $preferences.help
);

export const historyPreferences: Readable<HistoryPreferences> = derived(
	preferences,
	($preferences: Preferences) => $preferences.history
);

// Preference actions
export const preferenceActions = {
	// Update a specific preference
	update<K extends PreferenceCategory>(category: K, key: keyof Preferences[K], value: Preferences[K][keyof Preferences[K]]): void {
		preferences.update((prefs: Preferences) => ({
			...prefs,
			[category]: {
				...prefs[category],
				[key]: value
			}
		}));
	},
	
	// Update multiple preferences at once
	updateMultiple(updates: PreferenceUpdates): void {
		preferences.update((prefs: Preferences) => {
			const newPrefs = { ...prefs };
			
			for (const [category, categoryUpdates] of Object.entries(updates)) {
				if (categoryUpdates) {
					newPrefs[category as PreferenceCategory] = {
						...newPrefs[category as PreferenceCategory],
						...categoryUpdates
					} as any;
				}
			}
			
			return newPrefs;
		});
	},
	
	// Reset to defaults
	reset(): void {
		preferences.set(DEFAULT_PREFERENCES);
	},
	
	// Reset specific category
	resetCategory(category: PreferenceCategory): void {
		preferences.update((prefs: Preferences) => ({
			...prefs,
			[category]: DEFAULT_PREFERENCES[category]
		}));
	},
	
	// Import preferences
	import(importedPrefs: Partial<Preferences>): boolean {
		try {
			const merged = mergeDeep(DEFAULT_PREFERENCES, importedPrefs);
			preferences.set(merged);
			return true;
		} catch (error) {
			console.error('Failed to import preferences:', error);
			return false;
		}
	},
	
	// Export preferences
	export(): Preferences {
		let currentPrefs: Preferences = DEFAULT_PREFERENCES;
		const unsubscribe = preferences.subscribe((prefs: Preferences) => currentPrefs = prefs);
		unsubscribe();
		return currentPrefs;
	},
	
	// Toggle boolean preference
	toggle<K extends PreferenceCategory>(category: K, key: keyof Preferences[K]): void {
		preferences.update((prefs: Preferences) => ({
			...prefs,
			[category]: {
				...prefs[category],
				[key]: !prefs[category][key]
			}
		}));
	}
};

// Smart defaults based on user environment
export function applySmartDefaults(): void {
	if (!browser) return;
	
	const updates: PreferenceUpdates = {};
	
	// Detect reduced motion preference
	if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
		updates.ui = { reducedMotion: true, animationSpeed: 'slow' };
	}
	
	// Detect high contrast preference
	if (window.matchMedia('(prefers-contrast: high)').matches) {
		updates.a11y = { highContrast: true };
	}
	
	// Detect color scheme preference
	if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
		updates.ui = { ...updates.ui, theme: 'dark' };
	} else if (window.matchMedia('(prefers-color-scheme: light)').matches) {
		updates.ui = { ...updates.ui, theme: 'light' };
	}
	
	// Apply updates if any
	if (Object.keys(updates).length > 0) {
		preferenceActions.updateMultiple(updates);
	}
}

// Initialize smart defaults on first load
if (browser) {
	// Check if this is the first time loading
	const hasStoredPrefs = localStorage.getItem('midi-visualizer-preferences');
	if (!hasStoredPrefs) {
		applySmartDefaults();
	}
}

// Utility functions for common preference checks
export const preferenceUtils = {
	// Check if animations should be reduced
	shouldReduceMotion(): boolean {
		let currentPrefs: Preferences = DEFAULT_PREFERENCES;
		const unsubscribe = preferences.subscribe((prefs: Preferences) => currentPrefs = prefs);
		unsubscribe();
		return currentPrefs.ui.reducedMotion || 
			   (browser && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
	},
	
	// Get animation duration based on speed preference
	getAnimationDuration(baseMs: number = 300): number {
		let currentPrefs: Preferences = DEFAULT_PREFERENCES;
		const unsubscribe = preferences.subscribe((prefs: Preferences) => currentPrefs = prefs);
		unsubscribe();
		
		if (this.shouldReduceMotion()) return 0;
		
		switch (currentPrefs.ui.animationSpeed) {
			case 'slow': return baseMs * 1.5;
			case 'fast': return baseMs * 0.7;
			default: return baseMs;
		}
	},
	
	// Check if tooltips should be shown
	shouldShowTooltips(): boolean {
		let currentPrefs: Preferences = DEFAULT_PREFERENCES;
		const unsubscribe = preferences.subscribe((prefs: Preferences) => currentPrefs = prefs);
		unsubscribe();
		return currentPrefs.ui.showTooltips;
	},
	
	// Get tooltip delay
	getTooltipDelay(): number {
		let currentPrefs: Preferences = DEFAULT_PREFERENCES;
		const unsubscribe = preferences.subscribe((prefs: Preferences) => currentPrefs = prefs);
		unsubscribe();
		return currentPrefs.ui.tooltipDelay;
	}
};

// Export types for use in other modules
export type {
	Preferences,
	UploadPreferences,
	UIPreferences,
	A11yPreferences,
	HelpPreferences,
	HistoryPreferences,
	PreferenceCategory,
	PreferenceUpdates
};