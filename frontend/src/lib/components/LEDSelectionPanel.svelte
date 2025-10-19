<script lang="ts">
  import { onMount } from 'svelte';
  import {
    ledSelectionState,
    ledSelectionUI,
    ledSelectionAPI,
    selectedKeyInfo,
    getMidiNoteName
  } from '$lib/stores/ledSelection';

  let selectedMidi: number | null = null;
  let availableLEDs: number[] = [];
  let selectedLEDs: Set<number> = new Set();

  onMount(async () => {
    // Load existing overrides
    try {
      const overrides = await ledSelectionAPI.fetchAllOverrides();
      ledSelectionState.update(state => ({
        ...state,
        overrides
      }));
    } catch (error) {
      console.error('Failed to load overrides:', error);
    }
  });

  function handleKeySelection(midiNote: number) {
    selectedMidi = midiNote;
    
    ledSelectionUI.update(ui => ({
      ...ui,
      selectedKey: midiNote
    }));

    // Initialize available LEDs (from valid range)
    const [start, end] = $ledSelectionState.validLEDRange;
    availableLEDs = Array.from({ length: end - start + 1 }, (_, i) => start + i);

    // Get current selection
    const override = $ledSelectionState.overrides[midiNote];
    selectedLEDs = new Set(override || []);

    // Scroll to preview
    setTimeout(() => {
      const preview = document.getElementById('led-preview');
      preview?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }

  function handleLEDToggle(ledIndex: number) {
    if (selectedLEDs.has(ledIndex)) {
      selectedLEDs.delete(ledIndex);
    } else {
      selectedLEDs.add(ledIndex);
    }
    selectedLEDs = selectedLEDs; // Trigger reactivity
  }

  async function handleApplySelection() {
    if (selectedMidi === null) return;
    const ledArray = Array.from(selectedLEDs).sort((a, b) => a - b);
    await ledSelectionAPI.setKeyOverride(selectedMidi, ledArray);
  }

  async function handleClearSelection() {
    if (selectedMidi === null) return;
    await ledSelectionAPI.clearKeyOverride(selectedMidi);
    selectedLEDs = new Set();
    selectedMidi = null;
  }

  function handleClearAll() {
    if (confirm('Clear all LED selection overrides?')) {
      ledSelectionAPI.clearAllOverrides();
    }
  }

  function getMidiNoteInfo(midiNote: number): { name: string; octave: number } {
    const noteName = getMidiNoteName(midiNote);
    const octave = Math.floor(midiNote / 12) - 1;
    return { name: noteName, octave };
  }
</script>

<div class="led-selection-container">
  <div class="led-selection-header">
    <h3>🎹 LED Selection Override</h3>
    <p class="description">
      Customize which LEDs are assigned to each piano key. Removed LEDs are automatically reallocated to neighboring keys.
    </p>
  </div>

  {#if $ledSelectionState.error}
    <div class="error-message">
      <strong>Error:</strong> {$ledSelectionState.error}
    </div>
  {/if}

  {#if $ledSelectionState.success}
    <div class="success-message">
      ✓ {$ledSelectionState.success}
    </div>
  {/if}

  <div class="led-selection-content">
    <!-- Key Selector -->
    <div class="key-selector-section">
      <h4>Step 1: Select a Piano Key</h4>
      <p class="section-hint">Valid MIDI range: 21 (A0) to 108 (C8)</p>
      
      <div class="key-selector-grid">
        {#each Array.from({ length: 88 }, (_, i) => i + 21) as midiNote}
          {@const info = getMidiNoteInfo(midiNote)}
          {@const isSelected = selectedMidi === midiNote}
          {@const hasOverride = $ledSelectionState.overrides[midiNote]}
          
          <button
            class="key-button"
            class:selected={isSelected}
            class:has-override={hasOverride && !isSelected}
            on:click={() => handleKeySelection(midiNote)}
            title="{info.name} (MIDI {midiNote})"
          >
            <span class="key-label">{info.name}</span>
            {#if hasOverride}
              <span class="override-indicator">✓</span>
            {/if}
          </button>
        {/each}
      </div>
    </div>

    {#if selectedMidi !== null}
      <div class="led-selector-section">
        <h4>Step 2: Select LEDs for {getMidiNoteName(selectedMidi)}</h4>
        <p class="section-hint">
          Selected: {selectedLEDs.size} LED{selectedLEDs.size !== 1 ? 's' : ''}
        </p>

        <!-- LED Range Info -->
        <div class="led-range-info">
          <div class="range-box">
            <span class="range-label">Valid LED Range:</span>
            <span class="range-value">
              {$ledSelectionState.validLEDRange[0]} - {$ledSelectionState.validLEDRange[1]}
            </span>
          </div>
        </div>

        <!-- LED Grid -->
        <div class="led-grid">
          {#each availableLEDs as ledIndex}
            {@const isSelected = selectedLEDs.has(ledIndex)}
            
            <button
              class="led-button"
              class:selected={isSelected}
              on:click={() => handleLEDToggle(ledIndex)}
              title="LED {ledIndex}"
            >
              <span class="led-number">{ledIndex}</span>
              {#if isSelected}
                <span class="checkmark">✓</span>
              {/if}
            </button>
          {/each}
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <button
            class="btn btn-primary"
            on:click={handleApplySelection}
            disabled={$ledSelectionState.isLoading}
          >
            {#if $ledSelectionState.isLoading}
              <span class="spinner"></span>
              Applying...
            {:else}
              ✓ Apply Selection
            {/if}
          </button>

          <button
            class="btn btn-secondary"
            on:click={handleClearSelection}
            disabled={$ledSelectionState.isLoading}
          >
            Clear This Key
          </button>

          <button
            class="btn btn-outline"
            on:click={() => (selectedMidi = null)}
            disabled={$ledSelectionState.isLoading}
          >
            Cancel
          </button>
        </div>
      </div>
    {/if}
  </div>

  <!-- Overrides Summary -->
  {#if $ledSelectionState.overrides && Object.keys($ledSelectionState.overrides).length > 0}
    <div class="overrides-summary">
      <h4>Active Overrides</h4>
      <div class="overrides-list">
        {#each Object.entries($ledSelectionState.overrides) as [midiStr, leds]}
          {@const midiNote = parseInt(midiStr, 10)}
          
          <div class="override-item">
            <span class="override-key">{getMidiNoteName(midiNote)}</span>
            <span class="override-leds">[{leds.join(', ')}]</span>
            <button
              class="remove-btn"
              on:click={() => ledSelectionAPI.clearKeyOverride(midiNote)}
              title="Remove override for {getMidiNoteName(midiNote)}"
            >
              ✕
            </button>
          </div>
        {/each}
      </div>

      <button class="btn btn-outline btn-small" on:click={handleClearAll}>
        Clear All Overrides
      </button>
    </div>
  {/if}
</div>

<style>
  .led-selection-container {
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
  }

  .led-selection-header {
    margin-bottom: 20px;
  }

  .led-selection-header h3 {
    margin: 0 0 8px 0;
    color: var(--text-primary, #333);
    font-size: 1.3rem;
  }

  .led-selection-header .description {
    margin: 0;
    color: var(--text-secondary, #666);
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .error-message {
    background-color: #fee;
    border: 1px solid #fcc;
    border-radius: 4px;
    color: #c33;
    padding: 12px;
    margin: 10px 0;
    font-size: 0.9rem;
  }

  .success-message {
    background-color: #efe;
    border: 1px solid #cfc;
    border-radius: 4px;
    color: #3c3;
    padding: 12px;
    margin: 10px 0;
    font-weight: 500;
  }

  .led-selection-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .key-selector-section,
  .led-selector-section {
    background: white;
    border-radius: 6px;
    padding: 16px;
    border: 1px solid var(--border-color, #ddd);
  }

  .key-selector-section h4,
  .led-selector-section h4 {
    margin: 0 0 8px 0;
    color: var(--text-primary, #333);
    font-size: 1rem;
  }

  .key-selector-section .section-hint,
  .led-selector-section .section-hint {
    margin: 0 0 12px 0;
    color: var(--text-secondary, #666);
    font-size: 0.85rem;
  }

  .key-selector-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
    gap: 8px;
    margin-bottom: 16px;
  }

  .key-button {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1 / 1;
    border: 2px solid var(--border-color, #ddd);
    border-radius: 4px;
    background: white;
    color: var(--text-primary, #333);
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    padding: 4px;
    line-height: 1.1;
  }

  .key-button:hover {
    background: var(--bg-hover, #f9f9f9);
    border-color: var(--primary-color, #007bff);
  }

  .key-button.selected {
    background: var(--primary-color, #007bff);
    color: white;
    border-color: var(--primary-color, #007bff);
  }

  .key-button.has-override {
    background: var(--success-color, #28a745);
    color: white;
    border-color: var(--success-color, #28a745);
  }

  .key-button .override-indicator {
    position: absolute;
    top: 1px;
    right: 1px;
    font-size: 0.6rem;
  }

  .key-button .key-label {
    text-overflow: ellipsis;
    overflow: hidden;
    max-width: 100%;
  }

  .led-range-info {
    background: var(--bg-tertiary, #fafafa);
    border-left: 4px solid var(--primary-color, #007bff);
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 4px;
  }

  .led-range-info .range-box {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.9rem;
  }

  .led-range-info .range-label {
    color: var(--text-secondary, #666);
    font-weight: 500;
  }

  .led-range-info .range-value {
    color: var(--text-primary, #333);
    font-family: monospace;
    font-weight: 600;
    background: white;
    padding: 4px 8px;
    border-radius: 3px;
    border: 1px solid var(--border-color, #ddd);
  }

  .led-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(45px, 1fr));
    gap: 6px;
    margin-bottom: 16px;
  }

  .led-button {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1 / 1;
    border: 2px solid var(--border-color, #ddd);
    border-radius: 3px;
    background: white;
    color: var(--text-secondary, #666);
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    padding: 2px;
  }

  .led-button:hover {
    background: var(--bg-hover, #f0f0f0);
    border-color: var(--primary-color, #007bff);
    transform: scale(1.05);
  }

  .led-button.selected {
    background: var(--primary-color, #007bff);
    color: white;
    border-color: var(--primary-color, #007bff);
  }

  .led-button .checkmark {
    position: absolute;
    top: 2px;
    right: 2px;
    font-size: 0.6rem;
    font-weight: bold;
  }

  .led-button .led-number {
    line-height: 1;
  }

  .action-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .action-buttons .btn {
    flex: 1;
    min-width: 120px;
    padding: 10px 16px;
    border: none;
    border-radius: 4px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .action-buttons .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .action-buttons .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .action-buttons .btn-primary {
    background: var(--primary-color, #007bff);
    color: white;
  }

  .action-buttons .btn-primary:hover:not(:disabled) {
    background: var(--primary-dark, #0056b3);
  }

  .action-buttons .btn-secondary {
    background: var(--secondary-color, #6c757d);
    color: white;
  }

  .action-buttons .btn-secondary:hover:not(:disabled) {
    background: var(--secondary-dark, #545b62);
  }

  .action-buttons .btn-outline {
    background: white;
    color: var(--primary-color, #007bff);
    border: 1px solid var(--primary-color, #007bff);
  }

  .action-buttons .btn-outline:hover:not(:disabled) {
    background: var(--primary-color, #007bff);
    color: white;
  }

  .overrides-summary {
    background: white;
    border-radius: 6px;
    padding: 16px;
    border: 1px solid var(--border-color, #ddd);
    border-left: 4px solid var(--success-color, #28a745);
  }

  .overrides-summary h4 {
    margin: 0 0 12px 0;
    color: var(--text-primary, #333);
    font-size: 0.95rem;
  }

  .overrides-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
  }

  .override-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-tertiary, #fafafa);
    padding: 10px 12px;
    border-radius: 4px;
    border: 1px solid var(--border-color, #eee);
    font-size: 0.9rem;
  }

  .override-item .override-key {
    font-weight: 600;
    color: var(--text-primary, #333);
    min-width: 50px;
  }

  .override-item .override-leds {
    flex: 1;
    text-align: center;
    color: var(--text-secondary, #666);
    font-family: monospace;
    font-size: 0.85rem;
  }

  .override-item .remove-btn {
    background: none;
    border: none;
    color: var(--danger-color, #dc3545);
    font-size: 1rem;
    cursor: pointer;
    padding: 4px;
    transition: all 0.2s ease;
  }

  .override-item .remove-btn:hover {
    color: #c82333;
    transform: scale(1.2);
  }

  .overrides-summary .btn-small {
    width: 100%;
    padding: 8px 12px;
    font-size: 0.85rem;
  }

  @media (max-width: 768px) {
    .key-selector-grid {
      grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
    }

    .led-grid {
      grid-template-columns: repeat(auto-fill, minmax(35px, 1fr));
    }

    .action-buttons {
      flex-direction: column;
    }

    .action-buttons .btn {
      min-width: 100%;
    }
  }
</style>
