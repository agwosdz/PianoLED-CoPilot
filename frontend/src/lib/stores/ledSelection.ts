/**
 * LED Selection Store
 * Manages per-key LED selection overrides with intelligent reallocation
 */

import { writable, derived, type Writable } from 'svelte/store';
import { browser } from '$app/environment';

// MIDI note to note name mapping
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

/**
 * Convert MIDI note number to note name (e.g., 60 -> "C4")
 */
export function getMidiNoteName(midiNote: number): string {
  const octave = Math.floor(midiNote / 12) - 1;
  const noteIndex = midiNote % 12;
  return `${NOTE_NAMES[noteIndex]}${octave}`;
}

// Type definitions
export interface LEDSelectionState {
  overrides: Record<number, number[]>; // MIDI note -> LED indices
  validLEDRange: [number, number]; // [start_led, end_led]
  isLoading: boolean;
  error: string | null;
  success: string | null;
}

export interface LEDSelectionUI {
  selectedKey: number | null; // MIDI note currently being edited
  baseAllocation: Record<number, number[]>; // Base allocation before override
  currentAllocation: Record<number, number[]>; // Current allocation with override
  toggledLEDs: Set<number>; // LEDs toggled for current key
  showPreview: boolean;
}

export interface LEDAllocationInfo {
  midiNote: number;
  baseAllocation: number[];
  currentAllocation: number[];
  removedLEDs: number[];
  addedLEDs: number[];
  reallocatedFrom: Record<number, number[]>; // LEDs reallocated from this key to others
  reallocatedTo: Record<number, number[]>; // LEDs reallocated to this key from others
}

// Default states
const defaultSelectionState: LEDSelectionState = {
  overrides: {},
  validLEDRange: [4, 249],
  isLoading: false,
  error: null,
  success: null
};

const defaultUIState: LEDSelectionUI = {
  selectedKey: null,
  baseAllocation: {},
  currentAllocation: {},
  toggledLEDs: new Set(),
  showPreview: true
};

// Main stores
export const ledSelectionState: Writable<LEDSelectionState> = writable(defaultSelectionState);
export const ledSelectionUI: Writable<LEDSelectionUI> = writable(defaultUIState);

// Derived: Get override for a specific key
export const getKeyOverride = (midiNote: number) =>
  derived(ledSelectionState, ($state: LEDSelectionState) => {
    return $state.overrides[midiNote] || null;
  });

// Derived: Get all overrides as array
export const allOverrides = derived(
  ledSelectionState,
  ($state: LEDSelectionState): Array<{ midiNote: number; leds: number[] }> => {
    return Object.entries($state.overrides).map(([midiNote, leds]) => ({
      midiNote: parseInt(midiNote, 10),
      leds
    }));
  }
);

// Derived: Check if any overrides exist
export const hasOverrides = derived(
  ledSelectionState,
  ($state: LEDSelectionState) => Object.keys($state.overrides).length > 0
);

// Derived: Get LED allocation info for selected key
export const selectedKeyInfo = derived(
  [ledSelectionState, ledSelectionUI],
  ([$state, $ui]: [LEDSelectionState, LEDSelectionUI]): LEDAllocationInfo | null => {
    if ($ui.selectedKey === null) return null;

    const midiNote = $ui.selectedKey;
    const baseAllocation = $ui.baseAllocation[midiNote] || [];
    const currentAllocation = $ui.currentAllocation[midiNote] || baseAllocation;

    // Calculate removed and added LEDs
    const baseSet = new Set(baseAllocation);
    const currentSet = new Set(currentAllocation);

    const removedLEDs = Array.from(baseSet).filter(led => !currentSet.has(led)).sort((a, b) => a - b);
    const addedLEDs = Array.from(currentSet).filter(led => !baseSet.has(led)).sort((a, b) => a - b);

    // Calculate reallocation
    const reallocatedFrom: Record<number, number[]> = {};
    const reallocatedTo: Record<number, number[]> = {};

    // Find where removed LEDs went
    for (const removedLED of removedLEDs) {
      for (let otherKey = 21; otherKey <= 108; otherKey++) {
        if (otherKey === midiNote) continue;
        const otherCurrent = $ui.currentAllocation[otherKey] || [];
        if (otherCurrent.includes(removedLED)) {
          if (!reallocatedFrom[otherKey]) {
            reallocatedFrom[otherKey] = [];
          }
          reallocatedFrom[otherKey].push(removedLED);
        }
      }
    }

    // Find where added LEDs came from
    for (const addedLED of addedLEDs) {
      for (let otherKey = 21; otherKey <= 108; otherKey++) {
        if (otherKey === midiNote) continue;
        const otherBase = $ui.baseAllocation[otherKey] || [];
        if (otherBase.includes(addedLED)) {
          if (!reallocatedTo[otherKey]) {
            reallocatedTo[otherKey] = [];
          }
          reallocatedTo[otherKey].push(addedLED);
        }
      }
    }

    return {
      midiNote,
      baseAllocation,
      currentAllocation,
      removedLEDs,
      addedLEDs,
      reallocatedFrom,
      reallocatedTo
    };
  }
);

// API Helper functions
export const ledSelectionAPI = {
  /**
   * Fetch current LED overrides from server
   */
  async fetchAllOverrides(): Promise<Record<number, number[]>> {
    try {
      const response = await fetch('/api/led-selection/all');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to fetch LED overrides:', error);
      throw error;
    }
  },

  /**
   * Set LED override for a key
   */
  async setKeyOverride(midiNote: number, selectedLEDs: number[]): Promise<void> {
    try {
      ledSelectionState.update(state => ({
        ...state,
        isLoading: true,
        error: null
      }));

      const response = await fetch(`/api/led-selection/key/${midiNote}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_leds: selectedLEDs })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to set override');
      }

      // Update store with new override
      ledSelectionState.update(state => ({
        ...state,
        overrides: {
          ...state.overrides,
          [midiNote]: selectedLEDs
        },
        success: `LED selection updated for MIDI ${midiNote}`,
        error: null,
        isLoading: false
      }));

      // Clear success message after 3 seconds
      setTimeout(() => {
        ledSelectionState.update(state => ({ ...state, success: null }));
      }, 3000);
    } catch (error) {
      ledSelectionState.update(state => ({
        ...state,
        error: `Failed to set override: ${error}`,
        isLoading: false
      }));
      throw error;
    }
  },

  /**
   * Toggle a single LED for a key
   */
  async toggleLED(midiNote: number, ledIndex: number): Promise<void> {
    try {
      ledSelectionState.update(state => ({
        ...state,
        isLoading: true,
        error: null
      }));

      const response = await fetch(
        `/api/led-selection/key/${midiNote}/toggle/${ledIndex}`,
        { method: 'POST' }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to toggle LED');
      }

      // Update store
      ledSelectionState.update(state => ({
        ...state,
        overrides: {
          ...state.overrides,
          [midiNote]: result.selected_leds
        },
        success: `LED ${ledIndex} ${result.action === 'added' ? 'selected' : 'deselected'}`,
        error: null,
        isLoading: false
      }));

      setTimeout(() => {
        ledSelectionState.update(state => ({ ...state, success: null }));
      }, 2000);
    } catch (error) {
      ledSelectionState.update(state => ({
        ...state,
        error: `Failed to toggle LED: ${error}`,
        isLoading: false
      }));
      throw error;
    }
  },

  /**
   * Clear override for a specific key
   */
  async clearKeyOverride(midiNote: number): Promise<void> {
    try {
      ledSelectionState.update(state => ({
        ...state,
        isLoading: true,
        error: null
      }));

      const response = await fetch(`/api/led-selection/key/${midiNote}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to clear override');
      }

      // Remove from store
      ledSelectionState.update(state => {
        const newOverrides = { ...state.overrides };
        delete newOverrides[midiNote];
        return {
          ...state,
          overrides: newOverrides,
          success: `LED selection cleared for MIDI ${midiNote}`,
          error: null,
          isLoading: false
        };
      });

      setTimeout(() => {
        ledSelectionState.update(state => ({ ...state, success: null }));
      }, 2000);
    } catch (error) {
      ledSelectionState.update(state => ({
        ...state,
        error: `Failed to clear override: ${error}`,
        isLoading: false
      }));
      throw error;
    }
  },

  /**
   * Clear all overrides
   */
  async clearAllOverrides(): Promise<void> {
    try {
      ledSelectionState.update(state => ({
        ...state,
        isLoading: true,
        error: null
      }));

      const response = await fetch('/api/led-selection/all', {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();

      if (!result.success) {
        throw new Error(result.error || 'Failed to clear all overrides');
      }

      // Clear all from store
      ledSelectionState.update(state => ({
        ...state,
        overrides: {},
        success: 'All LED selections cleared',
        error: null,
        isLoading: false
      }));

      setTimeout(() => {
        ledSelectionState.update(state => ({ ...state, success: null }));
      }, 2000);
    } catch (error) {
      ledSelectionState.update(state => ({
        ...state,
        error: `Failed to clear all overrides: ${error}`,
        isLoading: false
      }));
      throw error;
    }
  }
};

// Initialize: Load overrides on browser startup
if (browser) {
  ledSelectionAPI.fetchAllOverrides().catch(error => {
    console.warn('Could not load LED selection overrides:', error);
  });
}
