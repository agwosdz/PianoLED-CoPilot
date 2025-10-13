import { writable, derived, type Writable, type Readable } from 'svelte/store';
import { browser } from '$app/environment';

// Type definitions
interface HelpPreferences {
	showTooltips: boolean;
	tooltipDelay: number;
	showOnboarding: boolean;
	autoShowHelp: boolean;
	helpTheme: 'light' | 'dark';
	reducedMotion: boolean;
}

interface TourStep {
	id: string;
	title: string;
	content: string;
	target?: string;
	position?: 'top' | 'bottom' | 'left' | 'right';
}

interface ActiveTour {
	id: string;
	steps: TourStep[];
	currentStep: number;
}

interface TooltipConfig {
	content: string;
	position?: 'top' | 'bottom' | 'left' | 'right';
	delay?: number;
	persistent?: boolean;
}

interface ActiveTooltip {
	id: string;
	content: string;
	position?: 'top' | 'bottom' | 'left' | 'right';
	delay?: number;
	persistent?: boolean;
}

interface TooltipConfigDerived {
	enabled: boolean;
	delay: number;
	theme: 'light' | 'dark';
	reducedMotion: boolean;
}

interface HelpContent {
	title: string;
	description: string;
	tips: string[];
}

type HelpContext = 'upload' | 'play' | string;

interface HelpActions {
	updatePreferences: (updates: Partial<HelpPreferences>) => void;
	togglePreference: (key: keyof HelpPreferences) => void;
	startTour: (tourId: string, steps?: TourStep[]) => void;
	completeTour: () => void;
	skipTour: () => void;
	resetTour: () => void;
	showTooltip: (id: string, config: TooltipConfig) => void;
	hideTooltip: () => void;
	setContext: (context: HelpContext) => void;
	getContextHelp: (context: HelpContext) => HelpContent | null;
	resetPreferences: () => void;
}

interface HelpUtils {
	prefersReducedMotion: () => boolean;
	getAnimationDuration: (defaultDuration?: number) => number;
	formatForScreenReader: (text: string) => string;
	generateHelpId: (prefix?: string) => string;
}

// Help system configuration
const HELP_STORAGE_KEY = 'midi-app-help-preferences';
const TOUR_STORAGE_KEY = 'midi-app-tour-completed';

// Default help preferences
const defaultPreferences: HelpPreferences = {
	showTooltips: true,
	tooltipDelay: 500,
	showOnboarding: true,
	autoShowHelp: true,
	helpTheme: 'dark',
	reducedMotion: false
};

// Load preferences from localStorage
function loadPreferences(): HelpPreferences {
	if (!browser) return defaultPreferences;
	
	try {
		const stored = localStorage.getItem(HELP_STORAGE_KEY);
		if (stored) {
			return { ...defaultPreferences, ...JSON.parse(stored) };
		}
	} catch (error) {
		console.warn('Failed to load help preferences:', error);
	}
	
	return defaultPreferences;
}

// Save preferences to localStorage
function savePreferences(preferences: HelpPreferences): void {
	if (!browser) return;
	
	try {
		localStorage.setItem(HELP_STORAGE_KEY, JSON.stringify(preferences));
	} catch (error) {
		console.warn('Failed to save help preferences:', error);
	}
}

// Check if tour has been completed
function hasTourBeenCompleted(): boolean {
	if (!browser) return false;
	
	try {
		return localStorage.getItem(TOUR_STORAGE_KEY) === 'true';
	} catch (error) {
		console.warn('Failed to check tour completion:', error);
		return false;
	}
}

// Mark tour as completed
function markTourCompleted(): void {
	if (!browser) return;
	
	try {
		localStorage.setItem(TOUR_STORAGE_KEY, 'true');
	} catch (error) {
		console.warn('Failed to mark tour as completed:', error);
	}
}

// Reset tour completion status
function resetTourCompletion(): void {
	if (!browser) return;
	
	try {
		localStorage.removeItem(TOUR_STORAGE_KEY);
	} catch (error) {
		console.warn('Failed to reset tour completion:', error);
	}
}

// Create stores
export const helpPreferences: Writable<HelpPreferences> = writable(loadPreferences());
export const tourCompleted: Writable<boolean> = writable(hasTourBeenCompleted());
export const activeTour: Writable<ActiveTour | null> = writable(null);
export const activeTooltip: Writable<ActiveTooltip | null> = writable(null);
export const helpContext: Writable<HelpContext> = writable('upload'); // Current page/context

// Derived stores
export const shouldShowOnboarding: Readable<boolean> = derived(
	[helpPreferences, tourCompleted],
	([$preferences, $tourCompleted]: [HelpPreferences, boolean]) => {
		return $preferences.showOnboarding && !$tourCompleted;
	}
);

export const tooltipConfig: Readable<TooltipConfigDerived> = derived(
	helpPreferences,
	($preferences: HelpPreferences) => ({
		enabled: $preferences.showTooltips,
		delay: $preferences.tooltipDelay,
		theme: $preferences.helpTheme,
		reducedMotion: $preferences.reducedMotion
	})
);

// Subscribe to preferences changes and save them
helpPreferences.subscribe((preferences: HelpPreferences) => {
	savePreferences(preferences);
});

// Help system actions
export const helpActions: HelpActions = {
	// Update preferences
	updatePreferences(updates: Partial<HelpPreferences>): void {
		helpPreferences.update((current: HelpPreferences) => ({ ...current, ...updates }));
	},

	// Toggle specific preference
	togglePreference(key: keyof HelpPreferences): void {
		helpPreferences.update((current: HelpPreferences) => ({
			...current,
			[key]: !current[key]
		}));
	},

	// Start a tour
	startTour(tourId: string, steps: TourStep[] = []): void {
		activeTour.set({ id: tourId, steps, currentStep: 0 });
	},

	// Complete current tour
	completeTour(): void {
		activeTour.set(null);
		tourCompleted.set(true);
		markTourCompleted();
	},

	// Skip current tour
	skipTour(): void {
		activeTour.set(null);
		tourCompleted.set(true);
		markTourCompleted();
	},

	// Reset tour (for testing or re-onboarding)
	resetTour(): void {
		tourCompleted.set(false);
		resetTourCompletion();
	},

	// Show tooltip
	showTooltip(id: string, config: TooltipConfig): void {
		activeTooltip.set({ id, ...config });
	},

	// Hide tooltip
	hideTooltip(): void {
		activeTooltip.set(null);
	},

	// Set help context
	setContext(context: HelpContext): void {
		helpContext.set(context);
	},

	// Get context-specific help content
	getContextHelp(context: HelpContext): HelpContent | null {
		const helpContent: Record<string, HelpContent> = {
			upload: {
				title: 'Upload MIDI Files',
				description: 'Learn how to upload and process MIDI files for LED visualization.',
				tips: [
					'Drag and drop files for quick upload',
					'Supported formats: .mid, .midi',
					'Use Ctrl+Z to undo actions',
					'File metadata shows tracks and duration'
				]
			},
			play: {
				title: 'LED Visualization',
				description: 'Control and customize your LED light show.',
				tips: [
					'Use spacebar to play/pause',
					'Adjust speed with +/- keys',
					'Click timeline to seek',
					'Press F for fullscreen'
				]
			}
		};

		return helpContent[context] || null;
	},

	// Reset all preferences to defaults
	resetPreferences(): void {
		helpPreferences.set(defaultPreferences);
	}
};

// Keyboard shortcuts for help system
export function setupHelpKeyboardShortcuts(): (() => void) | void {
	if (!browser) return;

	function handleKeydown(event: KeyboardEvent): void {
		// F1 - Show help
		if (event.key === 'F1') {
			event.preventDefault();
			// Dispatch custom event for help
			window.dispatchEvent(new CustomEvent('show-help'));
		}

		// Ctrl/Cmd + ? - Show keyboard shortcuts
		if ((event.ctrlKey || event.metaKey) && event.key === '/') {
			event.preventDefault();
			window.dispatchEvent(new CustomEvent('show-shortcuts'));
		}

		// Ctrl/Cmd + Shift + ? - Start tour
		if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === '/') {
			event.preventDefault();
			helpActions.resetTour();
			window.dispatchEvent(new CustomEvent('start-tour'));
		}
	}

	document.addEventListener('keydown', handleKeydown);

	// Return cleanup function
	return (): void => {
		document.removeEventListener('keydown', handleKeydown);
	};
}

// Utility functions
export const helpUtils: HelpUtils = {
	// Check if user prefers reduced motion
	prefersReducedMotion(): boolean {
		if (!browser) return false;
		return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	},

	// Get appropriate animation duration based on preferences
	getAnimationDuration(defaultDuration: number = 300): number {
		let preferences: HelpPreferences | undefined;
		const unsubscribe = helpPreferences.subscribe((p: HelpPreferences) => preferences = p);
		unsubscribe();
		
		if (preferences?.reducedMotion || this.prefersReducedMotion()) {
			return 0;
		}
		return defaultDuration;
	},

	// Format help content for accessibility
	formatForScreenReader(text: string): string {
		return text.replace(/\n/g, '. ').replace(/\s+/g, ' ').trim();
	},

	// Generate unique IDs for help elements
	generateHelpId(prefix: string = 'help'): string {
		return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
	}
};