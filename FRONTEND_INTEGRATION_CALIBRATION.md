# Frontend Integration Guide: LED Calibration

## Overview
The backend now supports comprehensive LED-to-key calibration with two main parameters:
1. **Global Offset**: Shifts all LEDs uniformly (for LED strip position alignment)
2. **Per-Key Offsets**: Fine-tunes individual keys (for hardware imperfections)

## Frontend Components to Implement

### 1. Calibration Settings Panel
Location: Settings/Calibration tab (placeholder already exists in UX)

#### Toggle Calibration
```typescript
// Enable/disable calibration mode
async function toggleCalibration(enabled: boolean) {
  const endpoint = enabled 
    ? '/api/calibration/enable' 
    : '/api/calibration/disable';
  
  const response = await fetch(endpoint, { method: 'POST' });
  return await response.json();
}
```

#### Global Offset Slider
```typescript
// Set global offset (-100 to +100)
async function setGlobalOffset(offset: number) {
  const response = await fetch('/api/calibration/global-offset', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ global_offset: Math.round(offset) })
  });
  return await response.json();
}

// Get current global offset
async function getGlobalOffset() {
  const response = await fetch('/api/calibration/global-offset');
  const data = await response.json();
  return data.global_offset;
}
```

#### Per-Key Offset Controls
```typescript
// Set offset for specific key (MIDI note 0-127)
async function setKeyOffset(midiNote: number, offset: number) {
  const response = await fetch(`/api/calibration/key-offset/${midiNote}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ offset: Math.round(offset) })
  });
  return await response.json();
}

// Get all key offsets
async function getAllKeyOffsets() {
  const response = await fetch('/api/calibration/key-offsets');
  const data = await response.json();
  return data.key_offsets; // {midi_note: offset, ...}
}

// Batch set multiple key offsets
async function setMultipleKeyOffsets(keyOffsets: Record<number, number>) {
  const response = await fetch('/api/calibration/key-offsets', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key_offsets: keyOffsets })
  });
  return await response.json();
}
```

### 2. Calibration Status Display
```typescript
interface CalibrationStatus {
  enabled: boolean;
  mode: 'none' | 'assisted' | 'manual';
  global_offset: number;
  key_offsets: Record<string, number>;
  last_calibration: string;
  mapping_base_offset: number;
  leds_per_key: number;
}

async function getCalibrationStatus(): Promise<CalibrationStatus> {
  const response = await fetch('/api/calibration/status');
  return await response.json();
}
```

### 3. UI Components Structure

#### Settings Page Layout
```
┌─────────────────────────────────┐
│ LED Calibration Settings        │
├─────────────────────────────────┤
│ ☑ Enable Calibration            │
│                                 │
│ Global Offset                   │
│ [-100] ──●────── [+100]  [3]   │
│ (shifts all LEDs by offset)     │
│                                 │
│ Per-Key Fine Tuning             │
│ ┌─────────────────────────┐     │
│ │ 📌 A0 (21): [-2] ↔ [+2]│     │
│ │ 📌 C2 (36): [-1] ↔ [+1]│     │
│ │ 📌 C4 (60): [0]  ↔ [0] │     │
│ │ ...                      │     │
│ │ 📌 C8 (108): [1] ↔ [+2]│     │
│ └─────────────────────────┘     │
│                                 │
│ [Reset] [Export] [Import]       │
└─────────────────────────────────┘
```

### 4. Calibration Workflow UI

#### Interactive Test Mode
```typescript
interface CalibrationTestMode {
  activeNote: number | null;
  testingKeys: Set<number>;
  
  startTesting(): void;
  testKey(midiNote: number): void;
  stopTesting(): void;
}

// User clicks a key on the piano
function onPianoKeyClick(midiNote: number) {
  // Highlight which LED should light up
  const expectedLed = calculateExpectedLED(midiNote);
  highlightLED(expectedLed);
  
  // Show adjustment controls
  showKeyOffsetControls(midiNote);
}

function calculateExpectedLED(midiNote: number): number {
  // Calculate based on current calibration settings
  const baseMapping = getBaseMapping(midiNote);
  const globalOffset = calibrationState.global_offset;
  const keyOffset = calibrationState.key_offsets[midiNote] || 0;
  return Math.max(0, Math.min(baseMapping + globalOffset + keyOffset, totalLeds - 1));
}
```

#### Quick Adjust Controls
```typescript
interface KeyOffsetControls {
  midiNote: number;
  currentOffset: number;
  minOffset: number;  // -100
  maxOffset: number;  // +100
  
  increment(): void;
  decrement(): void;
  set(value: number): void;
  reset(): void;
}

// For each key being adjusted
function showKeyOffsetControls(midiNote: number) {
  const controls = {
    midiNote,
    currentOffset: calibrationState.key_offsets[midiNote] || 0,
    minOffset: -100,
    maxOffset: 100,
    
    async increment() {
      const newOffset = Math.min(this.currentOffset + 1, this.maxOffset);
      await setKeyOffset(midiNote, newOffset);
      this.currentOffset = newOffset;
      updateDisplay();
    },
    
    async decrement() {
      const newOffset = Math.max(this.currentOffset - 1, this.minOffset);
      await setKeyOffset(midiNote, newOffset);
      this.currentOffset = newOffset;
      updateDisplay();
    },
    
    async set(value: number) {
      const clamped = Math.max(this.minOffset, Math.min(value, this.maxOffset));
      await setKeyOffset(midiNote, clamped);
      this.currentOffset = clamped;
      updateDisplay();
    },
    
    async reset() {
      await setKeyOffset(midiNote, 0);
      this.currentOffset = 0;
      updateDisplay();
    }
  };
  
  return controls;
}
```

### 5. WebSocket Integration

```typescript
import { io } from 'socket.io-client';

const socket = io('http://localhost:5001');

// Listen for calibration changes
socket.on('calibration_enabled', (data) => {
  updateCalibrationUI({ enabled: data.enabled });
  showNotification('Calibration enabled');
});

socket.on('calibration_disabled', (data) => {
  updateCalibrationUI({ enabled: data.enabled });
  showNotification('Calibration disabled');
});

socket.on('global_offset_changed', (data) => {
  updateGlobalOffsetDisplay(data.global_offset);
  calibrationState.global_offset = data.global_offset;
});

socket.on('key_offset_changed', (data) => {
  updateKeyOffsetDisplay(data.midi_note, data.offset);
  calibrationState.key_offsets[data.midi_note] = data.offset;
});

socket.on('key_offsets_changed', (data) => {
  updateAllKeyOffsetsDisplay(data.key_offsets);
  calibrationState.key_offsets = data.key_offsets;
});

socket.on('calibration_reset', (data) => {
  resetCalibrationUI();
  calibrationState = { ...defaultCalibrationState };
  showNotification('Calibration reset to defaults');
});
```

### 6. State Management (Svelte Store Example)

```typescript
// stores/calibration.ts
import { writable, derived } from 'svelte/store';

export interface CalibrationState {
  enabled: boolean;
  mode: 'none' | 'assisted' | 'manual';
  globalOffset: number;
  keyOffsets: Record<number, number>;
  lastCalibration: string;
  isLoading: boolean;
  error: string | null;
}

const defaultState: CalibrationState = {
  enabled: false,
  mode: 'none',
  globalOffset: 0,
  keyOffsets: {},
  lastCalibration: '',
  isLoading: false,
  error: null
};

export const calibration = writable<CalibrationState>(defaultState);

export const calibrationApi = {
  async fetchStatus() {
    calibration.update(s => ({ ...s, isLoading: true }));
    try {
      const response = await fetch('/api/calibration/status');
      const data = await response.json();
      calibration.update(s => ({
        ...s,
        enabled: data.enabled,
        mode: data.mode,
        globalOffset: data.global_offset,
        keyOffsets: data.key_offsets,
        lastCalibration: data.last_calibration,
        error: null
      }));
    } catch (error) {
      calibration.update(s => ({ 
        ...s, 
        error: (error as Error).message 
      }));
    } finally {
      calibration.update(s => ({ ...s, isLoading: false }));
    }
  },

  async setGlobalOffset(offset: number) {
    calibration.update(s => ({ ...s, isLoading: true }));
    try {
      await fetch('/api/calibration/global-offset', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ global_offset: offset })
      });
    } catch (error) {
      calibration.update(s => ({ 
        ...s, 
        error: (error as Error).message 
      }));
    } finally {
      calibration.update(s => ({ ...s, isLoading: false }));
    }
  },

  async setKeyOffset(midiNote: number, offset: number) {
    try {
      await fetch(`/api/calibration/key-offset/${midiNote}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offset })
      });
    } catch (error) {
      calibration.update(s => ({ 
        ...s, 
        error: (error as Error).message 
      }));
    }
  },

  async reset() {
    calibration.update(s => ({ ...s, isLoading: true }));
    try {
      await fetch('/api/calibration/reset', { method: 'POST' });
      calibration.set(defaultState);
    } catch (error) {
      calibration.update(s => ({ 
        ...s, 
        error: (error as Error).message 
      }));
    } finally {
      calibration.update(s => ({ ...s, isLoading: false }));
    }
  }
};
```

### 7. Svelte Component Example

```svelte
<script lang="ts">
  import { calibration, calibrationApi } from '../stores/calibration';
  import { onMount } from 'svelte';
  
  onMount(async () => {
    await calibrationApi.fetchStatus();
  });
</script>

<div class="calibration-panel">
  <h2>LED Calibration</h2>
  
  {#if $calibration.error}
    <div class="error">{$calibration.error}</div>
  {/if}
  
  <label>
    <input 
      type="checkbox" 
      checked={$calibration.enabled}
      on:change={async (e) => {
        if (e.currentTarget.checked) {
          await fetch('/api/calibration/enable', { method: 'POST' });
        } else {
          await fetch('/api/calibration/disable', { method: 'POST' });
        }
      }}
    />
    Enable Calibration
  </label>
  
  <div class="offset-control">
    <label>Global Offset: {$calibration.globalOffset}</label>
    <input 
      type="range" 
      min="-100" 
      max="100" 
      value={$calibration.globalOffset}
      on:change={async (e) => {
        await calibrationApi.setGlobalOffset(parseInt(e.currentTarget.value));
      }}
      disabled={!$calibration.enabled}
    />
  </div>
  
  <div class="key-offsets">
    <h3>Per-Key Adjustments</h3>
    {#each Object.entries($calibration.keyOffsets) as [note, offset]}
      <div class="key-offset-row">
        <span>MIDI {note}:</span>
        <input 
          type="range" 
          min="-100" 
          max="100" 
          value={offset}
          on:change={async (e) => {
            await calibrationApi.setKeyOffset(
              parseInt(note), 
              parseInt(e.currentTarget.value)
            );
          }}
          disabled={!$calibration.enabled}
        />
        <span>{offset}</span>
      </div>
    {/each}
  </div>
  
  <div class="actions">
    <button on:click={() => calibrationApi.reset()} disabled={$calibration.isLoading}>
      Reset
    </button>
    <button disabled={$calibration.isLoading}>Export</button>
    <button disabled={$calibration.isLoading}>Import</button>
  </div>
</div>

<style>
  .calibration-panel {
    padding: 1rem;
    border: 1px solid #ccc;
    border-radius: 8px;
  }
  
  .error {
    color: #d32f2f;
    margin-bottom: 1rem;
  }
  
  .offset-control {
    margin: 1rem 0;
  }
  
  .key-offsets {
    margin: 1rem 0;
  }
  
  .key-offset-row {
    display: flex;
    gap: 1rem;
    margin: 0.5rem 0;
    align-items: center;
  }
  
  .actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
  }
</style>
```

## Placeholder Locations in Current UX

The existing UX already has placeholders for:
1. **Global Offset Control** - Slider for adjusting LED strip position
2. **Per-Key Adjustments** - List/grid for individual key offsets
3. **Calibration Mode Toggle** - Enable/disable button
4. **Export/Import Buttons** - For backup/restore

These should now be wired to the backend APIs described above.

## Testing Workflow

1. Enable calibration
2. Play a note - observe which LED lights up
3. Adjust global offset slider - all LEDs should shift
4. Play first key (A0) - adjust if misaligned
5. Play middle key (C4) - adjust if misaligned
6. Play last key (C8) - adjust if misaligned
7. Verify across octaves
8. Export calibration when satisfied

## Error Handling

```typescript
async function withErrorHandling<T>(
  fn: () => Promise<T>,
  context: string
): Promise<T | null> {
  try {
    return await fn();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`${context}: ${message}`);
    showErrorNotification(`${context}: ${message}`);
    return null;
  }
}

// Usage
await withErrorHandling(
  () => calibrationApi.setGlobalOffset(5),
  'Failed to set global offset'
);
```

## Performance Considerations

- Calibration applies in real-time without reloading
- WebSocket events provide instant UI feedback
- Offset calculations are lightweight (just integer addition)
- No need to refresh LED controller for offset changes
