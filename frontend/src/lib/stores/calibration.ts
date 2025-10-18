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
  start_led: number;
  end_led: number;
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
  start_led: 0,
  end_led: 245,
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
  ($state: CalibrationState) => $state.enabled && (Object.keys($state.key_offsets).length > 0 || $state.start_led !== 0 || $state.end_led !== 245)
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
      console.log('[Calibration Store] loadStatus() received from API:', { start_led: data.start_led, end_led: data.end_led });
      
      const state: CalibrationState = {
        enabled: data.calibration_enabled ?? false,
        calibration_enabled: data.calibration_enabled ?? false,
        start_led: data.start_led ?? 0,
        end_led: data.end_led ?? 245,
        key_offsets: this.normalizeKeyOffsets(data.key_offsets ?? {}),
        calibration_mode: data.calibration_mode ?? 'none',
        last_calibration: data.last_calibration ?? null
      };

      console.log('[Calibration Store] Setting calibrationState to:', { start_led: state.start_led, end_led: state.end_led });
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

  async setStartLed(ledIndex: number): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/start-led`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ start_led: ledIndex })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Light up the LED at the start index for visualization
      try {
        await fetch(`${this.baseUrl}/test-led/${ledIndex}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (ledError) {
        console.warn('Failed to light LED for visualization:', ledError);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
      throw error;
    }
  }

  async setEndLed(ledIndex: number): Promise<void> {
    calibrationUI.update(ui => ({ ...ui, isLoading: true, error: null }));
    
    try {
      const response = await fetch(`${this.baseUrl}/end-led`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ end_led: ledIndex })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Light up the LED at the end index for visualization
      try {
        await fetch(`${this.baseUrl}/test-led/${ledIndex}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (ledError) {
        console.warn('Failed to light LED for visualization:', ledError);
      }

      await this.loadStatus();
      calibrationUI.update(ui => ({ ...ui, isLoading: false }));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      calibrationUI.update(ui => ({ ...ui, isLoading: false, error: message }));
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

  async getKeyLedMapping(): Promise<Record<number, number[]>> {
    try {
      const response = await fetch(`${this.baseUrl}/key-led-mapping`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Convert string keys to numbers for the mapping
      const mapping: Record<number, number[]> = {};
      for (const [key, value] of Object.entries(data.mapping)) {
        const midiNote = parseInt(key, 10);
        if (Number.isFinite(midiNote)) {
          mapping[midiNote] = value as number[];
        }
      }
      
      return mapping;
    } catch (error) {
      console.error('Failed to get key-LED mapping:', error);
      throw error;
    }
  }

  async getKeyLedMappingWithRange(): Promise<{ mapping: Record<number, number[]>; start_led: number; end_led: number; led_count: number }> {
    try {
      const response = await fetch(`${this.baseUrl}/key-led-mapping`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Convert string keys to numbers for the mapping
      // IMPORTANT: The backend returns key INDICES (0-87), but we need to convert them to MIDI NOTES (21-108)
      // for proper visualization and calibration logic
      const mapping: Record<number, number[]> = {};
      for (const [key, value] of Object.entries(data.mapping)) {
        const keyIndex = parseInt(key, 10);
        if (Number.isFinite(keyIndex)) {
          // Convert key index (0-87) to MIDI note (21-108) for 88-key piano
          const midiNote = 21 + keyIndex;
          mapping[midiNote] = value as number[];
        }
      }
      
      return {
        mapping,
        start_led: data.start_led ?? 0,
        end_led: data.end_led ?? 245,
        led_count: data.led_count ?? 246
      };
    } catch (error) {
      console.error('Failed to get key-LED mapping with range:', error);
      throw error;
    }
  }

  /**
   * Get LED mapping from physical analysis endpoint (reflects current physics parameters)
   * This is more accurate than key-led-mapping as it uses the current physics parameters
   */
  async getKeyLedMappingFromPhysicalAnalysis(): Promise<{ mapping: Record<number, number[]>; start_led: number; end_led: number; led_count: number }> {
    try {
      const response = await fetch(`${this.baseUrl}/physical-analysis`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const mapping: Record<number, number[]> = {};
      const startLed = data.led_range?.start_led ?? 0;
      const endLed = data.led_range?.end_led ?? 245;
      // Use total_strip_leds (actual physical count) instead of total_leds_analyzed (range size)
      const ledCount = data.led_range?.total_strip_leds ?? data.led_range?.total_leds_analyzed ?? 246;

      // Extract LED indices from per-key analysis
      if (data.per_key_analysis) {
        for (let keyIndex = 0; keyIndex < 88; keyIndex++) {
          const keyAnalysis = data.per_key_analysis[keyIndex];
          if (keyAnalysis && keyAnalysis.led_indices && keyAnalysis.led_indices.length > 0) {
            const midiNote = 21 + keyIndex;
            mapping[midiNote] = keyAnalysis.led_indices;
          }
        }
      }

      console.log('[Calibration] Loaded LED mapping from physical analysis:', { 
        keysWithLeds: Object.keys(mapping).length, 
        startLed, 
        endLed,
        ledCount,
        rawTotalStripLeds: data.led_range?.total_strip_leds,
        rawTotalAnalyzed: data.led_range?.total_leds_analyzed
      });

      return {
        mapping,
        start_led: startLed,
        end_led: endLed,
        led_count: ledCount
      };
    } catch (error) {
      console.error('Failed to get LED mapping from physical analysis:', error);
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
export const setStartLed = (ledIndex: number): Promise<void> => calibrationService.setStartLed(ledIndex);
export const setEndLed = (ledIndex: number): Promise<void> => calibrationService.setEndLed(ledIndex);
export const setKeyOffset = (midiNote: number, offset: number): Promise<void> => calibrationService.setKeyOffset(midiNote, offset);
export const deleteKeyOffset = (midiNote: number): Promise<void> => calibrationService.deleteKeyOffset(midiNote);
export const resetCalibration = (): Promise<void> => calibrationService.resetCalibration();
export const getKeyLedMapping = (): Promise<Record<number, number[]>> => calibrationService.getKeyLedMapping();
export const getKeyLedMappingWithRange = (): Promise<{ mapping: Record<number, number[]>; start_led: number; end_led: number; led_count: number }> => calibrationService.getKeyLedMappingWithRange();
export const getKeyLedMappingFromPhysicalAnalysis = (): Promise<{ mapping: Record<number, number[]>; start_led: number; end_led: number; led_count: number }> => calibrationService.getKeyLedMappingFromPhysicalAnalysis();
