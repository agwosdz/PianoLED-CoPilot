/**
 * Calibration Store for LED-to-Key Alignment
 * Manages global offset, per-key offsets, and calibration state
 */

import { writable, derived, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { getSocket } from '$lib/socket';

// Type definitions
export interface CalibrationState {
  enabled: boolean;
  calibration_enabled: boolean;
  global_offset: number;
  key_offsets: Record<number, number>;
  calibration_mode: 'none' | 'assisted' | 'manual';
  last_calibration: string | null;
}

export interface KeyOffset {
  midiNote: number;
  offset: number;
  noteName: string;
}

export interface CalibrationUI {
  isLoading: boolean;
  error: string | null;
  success: string | null;
  showModal: boolean;
  editingKeyNote: number | null;
  editingKeyOffset: number;
}

// MIDI note to note name mapping
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

export function getMidiNoteName(midiNote: number): string {
  const octave = Math.floor(midiNote / 12) - 1;
  const noteIndex = midiNote % 12;
  return `${NOTE_NAMES[noteIndex]}${octave}`;
}

export function getMidiNoteFromName(name: string): number | null {
  const match = name.match(/^([A-G]#?)(-?\d+)$/);
  if (!match) return null;
  
  const noteName = match[1];
  const octave = parseInt(match[2], 10);
  const noteIndex = NOTE_NAMES.indexOf(noteName);
  
  if (noteIndex === -1) return null;
  return (octave + 1) * 12 + noteIndex;
}

// Default calibration state
const defaultCalibrationState: CalibrationState = {
  enabled: false,
  calibration_enabled: false,
  global_offset: 0,
  key_offsets: {},
  calibration_mode: 'none',
  last_calibration: null
};

const defaultUIState: CalibrationUI = {
  isLoading: false,
  error: null,
  success: null,
  showModal: false,
  editingKeyNote: null,
  editingKeyOffset: 0
};

// Main stores
export const calibrationState: Writable<CalibrationState> = writable(defaultCalibrationState);
export const calibrationUI: Writable<CalibrationUI> = writable(defaultUIState);

// Derived stores
export const keyOffsetsList = derived(calibrationState, ($state: CalibrationState): KeyOffset[] => {
  const offsets: KeyOffset[] = [];
  
  for (const [noteStr, offset] of Object.entries($state.key_offsets)) {
    const midiNote = parseInt(noteStr, 10);
    if (Number.isFinite(midiNote)) {
      offsets.push({
        midiNote,
        offset,
        noteName: getMidiNoteName(midiNote)
      });
    }
  }
  
  return offsets.sort((a, b) => a.midiNote - b.midiNote);
});

export const hasKeyOffsets = derived(keyOffsetsList, ($list: KeyOffset[]) => $list.length > 0);

export const isCalibrationActive = derived(
  calibrationState,
  ($state: CalibrationState) => $state.enabled && ($state.global_offset !== 0 || Object.keys($state.key_offsets).length > 0)
);

// API service class
class CalibrationService {
  private baseUrl = '/api/calibration';
  private socket: any = null;
  
  constructor() {
    if (browser) {
      this.initializeWebSocket();
    }
  }

  private initializeWebSocket(): void {
    try {
      this.socket = getSocket();
      
      if (this.socket) {
        // Listen for calibration events
        this.socket.on('calibration_enabled', () => {
          console.log('Calibration enabled via WebSocket');
          this.loadStatus();
        });

        this.socket.on('calibration_disabled', () => {
          console.log('Calibration disabled via WebSocket');
          this.loadStatus();
        });

        this.socket.on('global_offset_changed', (data: any) => {
          console.log('Global offset changed:', data);
          this.loadStatus();
        });

        this.socket.on('key_offset_changed', (data: any) => {
          console.log('Key offset changed:', data);
          this.loadStatus();
        });

        this.socket.on('key_offsets_changed', (data: any) => {
          console.log('Key offsets changed:', data);
          this.loadStatus();
        });

        this.socket.on('calibration_reset', () => {
          console.log('Calibration reset via WebSocket');
          this.loadStatus();
        });
      }
    } catch (error) {
      console.warn('Failed to initialize calibration WebSocket:', error);
    }
  }

  async loadStatus(): Promise<CalibrationState> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const state: CalibrationState = {
        enabled: data.calibration_enabled ?? false,
        calibration_enabled: data.calibration_enabled ?? false,
        global_offset: data.global_offset ?? 0,
        key_offsets: this.normalizeKeyOffsets(data.key_offsets ?? {}),
        calibration_mode: data.calibration_mode ?? 'none',
        last_calibration: data.last_calibration ?? null
      };

      calibrationState.set(state);
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
      return state;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  private normalizeKeyOffsets(offsets: any): Record<number, number> {
    const normalized: Record<number, number> = {};
    
    for (const [key, value] of Object.entries(offsets)) {
      const noteNum = parseInt(key, 10);
      const offset = Number(value);
      
      if (Number.isFinite(noteNum) && Number.isFinite(offset)) {
        normalized[noteNum] = offset;
      }
    }
    
    return normalized;
  }

  async enableCalibration(): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/enable`, { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, success: 'Calibration enabled' }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async disableCalibration(): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/disable`, { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, success: 'Calibration disabled' }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async setGlobalOffset(offset: number): Promise<void> {
    const clamped = Math.max(0, Math.min(20, offset));
    
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/global-offset`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ global_offset: clamped })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Light up the LED at the offset index for visualization
      try {
        await fetch(`${this.baseUrl}/test-led/${clamped}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (ledError) {
        console.warn('Failed to light LED for visualization:', ledError);
        // Don't fail the whole operation if LED lighting fails
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async getGlobalOffset(): Promise<number> {
    try {
      const response = await fetch(`${this.baseUrl}/global-offset`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.global_offset ?? 0;
    } catch (error) {
      console.error('Failed to get global offset:', error);
      throw error;
    }
  }

  async setKeyOffset(midiNote: number, offset: number): Promise<void> {
    const clamped = Math.max(-10, Math.min(10, offset));
    
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/key-offset/${midiNote}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offset: clamped })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async deleteKeyOffset(midiNote: number): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/key-offset/${midiNote}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async batchUpdateKeyOffsets(offsets: Record<number, number>): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/key-offsets`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_offsets: offsets })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async resetCalibration(): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/reset`, { method: 'POST' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, success: 'Calibration reset to defaults' }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async exportCalibration(): Promise<CalibrationState> {
    try {
      const response = await fetch(`${this.baseUrl}/export`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to export calibration:', error);
      throw error;
    }
  }

  async importCalibration(data: CalibrationState): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, success: 'Calibration imported' }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 3000);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }
}

// Export singleton instance
export const calibrationService = new CalibrationService();

// Convenience functions
export const loadCalibration = (): Promise<CalibrationState> => calibrationService.loadStatus();
export const enableCalibration = (): Promise<void> => calibrationService.enableCalibration();
export const disableCalibration = (): Promise<void> => calibrationService.disableCalibration();
export const setGlobalOffset = (offset: number): Promise<void> => calibrationService.setGlobalOffset(offset);
export const setKeyOffset = (midiNote: number, offset: number): Promise<void> => calibrationService.setKeyOffset(midiNote, offset);
export const deleteKeyOffset = (midiNote: number): Promise<void> => calibrationService.deleteKeyOffset(midiNote);
export const resetCalibration = (): Promise<void> => calibrationService.resetCalibration();
