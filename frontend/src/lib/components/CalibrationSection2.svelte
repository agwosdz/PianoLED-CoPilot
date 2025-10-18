<script lang="ts">
  import { onMount } from 'svelte';
  import { calibrationState, calibrationUI, keyOffsetsList, getMidiNoteName, setKeyOffset, deleteKeyOffset, setStartLed, setEndLed } from '$lib/stores/calibration';
  import { settings } from '$lib/stores/settings';
  import type { KeyOffset } from '$lib/stores/calibration';

  let startLedValue = 0;
  let endLedValue = 245;
  let editingKeyNote: number | null = null;
  let editingKeyOffset = 0;
  let newKeyMidiNote = '';
  let newKeyOffset = 0;
  let showAddForm = false;
  let ledCount = 246;
  let lastLitLedIndex: number | null = null; // Track which LED was last lit for cleanup

  $: startLedValue = $calibrationState.start_led;
  $: endLedValue = $calibrationState.end_led;
  $: ledCount = $settings?.led?.led_count || 246;
  $: {
    // Update default end_led if it hasn't been explicitly set and ledCount changes
    if (endLedValue === 245 && ledCount !== 246) {
      endLedValue = ledCount - 1;
    }
    console.log(`[CalibrationSection2] Reactive update: startLedValue=${startLedValue}, endLedValue=${endLedValue}, ledCount=${ledCount}`);
  }

  onMount(() => {
    // Listen for populateMidiNote event from settings page
    const section2Element = document.querySelector('[data-section="calibration-2"]');
    if (section2Element) {
      section2Element.addEventListener('populateMidiNote', handlePopulateMidiNote);
      return () => {
        section2Element.removeEventListener('populateMidiNote', handlePopulateMidiNote);
      };
    }
  });

  function handlePopulateMidiNote(event: Event) {
    const customEvent = event as CustomEvent<{ midiNote: number }>;
    const { midiNote } = customEvent.detail;
    
    // Populate the MIDI note field with the value from piano visualization
    newKeyMidiNote = String(midiNote);
    // Open the form if not already open
    showAddForm = true;
    // Reset offset to 0
    newKeyOffset = 0;
  }

  async function turnOffPreviousLed(): Promise<void> {
    if (lastLitLedIndex !== null) {
      try {
        await fetch('/api/hardware-test/led/off', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        lastLitLedIndex = null;
      } catch (error) {
        console.warn('Failed to turn off previous LED:', error);
      }
    }
  }

  async function lightUpLed(ledIndex: number): Promise<void> {
    try {
      // Turn off any previously lit LED first
      await turnOffPreviousLed();
      
      // Light up the new LED
      await fetch('/api/calibration/test-led/' + ledIndex, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      lastLitLedIndex = ledIndex;
    } catch (error) {
      console.warn('Failed to light LED:', error);
    }
  }

  async function handleStartLedChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const value = parseInt(target.value, 10);
    if (Number.isFinite(value)) {
      // Ensure start_led doesn't exceed end_led
      if (value <= endLedValue) {
        startLedValue = value;
        await lightUpLed(value);
        await setStartLed(value);
      }
    }
  }

  async function handleEndLedChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const value = parseInt(target.value, 10);
    if (Number.isFinite(value)) {
      // Ensure end_led doesn't go below start_led
      if (value >= startLedValue) {
        endLedValue = value;
        await lightUpLed(value);
        await setEndLed(value);
      }
    }
  }

  function startEditingKeyOffset(item: KeyOffset) {
    editingKeyNote = item.midiNote;
    editingKeyOffset = item.offset;
  }

  function cancelEditingKeyOffset() {
    editingKeyNote = null;
    editingKeyOffset = 0;
  }

  async function saveEditingKeyOffset() {
    if (editingKeyNote !== null) {
      await setKeyOffset(editingKeyNote, editingKeyOffset);
      cancelEditingKeyOffset();
    }
  }

  async function handleDeleteKeyOffset(midiNote: number) {
    if (confirm(`Delete offset for ${getMidiNoteName(midiNote)}?`)) {
      await deleteKeyOffset(midiNote);
    }
  }

  function resetAddForm() {
    newKeyMidiNote = '';
    newKeyOffset = 0;
    showAddForm = false;
  }

  async function handleAddKeyOffset() {
    const midiNote = parseInt(newKeyMidiNote, 10);
    
    if (!Number.isFinite(midiNote) || midiNote < 0 || midiNote > 127) {
      calibrationUI.update(ui => ({ 
        ...ui, 
        error: 'Please enter a valid MIDI note (0-127)' 
      }));
      return;
    }

    try {
      await setKeyOffset(midiNote, newKeyOffset);
      resetAddForm();
      calibrationUI.update(ui => ({ ...ui, success: `Offset added for ${getMidiNoteName(midiNote)}` }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 2000);
    } catch (error) {
      console.error('Failed to add key offset:', error);
    }
  }
</script>

<div class="calibration-section-2">
  <div class="section-intro">
    <h3>LED Strip Alignment</h3>
    <p>Define the mappable area of your LED strip by setting where the piano begins and ends.</p>
  </div>

  <!-- LED Range Bar Visualization -->
  <div class="led-range-container">
    <div class="range-header">
      <h4>Mappable LED Range</h4>
      <p>Define the active portion of your LED strip for piano key mapping</p>
    </div>

    <div class="range-visualization">
      <div class="range-display">
        <div class="range-info-row">
          <div class="range-input-pair">
            <label for="start-led-input">First LED:</label>
            <input
              id="start-led-input"
              type="number"
              min="0"
              max={ledCount - 1}
              bind:value={startLedValue}
              on:change={handleStartLedChange}
              disabled={$calibrationUI.isLoading}
              class="led-input"
            />
          </div>
          <div class="range-bar-wrapper">
            <div class="range-bar-track">
              <div
                class="range-bar-fill"
                style="left: {(startLedValue / (ledCount - 1)) * 100}%; right: {100 - (endLedValue / (ledCount - 1)) * 100}%;"
              ></div>
              <input
                class="range-slider start"
                type="range"
                min="0"
                max={ledCount - 1}
                step="1"
                value={startLedValue}
                on:change={handleStartLedChange}
                disabled={$calibrationUI.isLoading}
              />
              <input
                class="range-slider end"
                type="range"
                min="0"
                max={ledCount - 1}
                step="1"
                value={endLedValue}
                on:change={handleEndLedChange}
                disabled={$calibrationUI.isLoading}
              />
            </div>
            <div class="range-labels">
              <span>0</span>
              <span>{Math.floor((ledCount - 1) / 2)}</span>
              <span>{ledCount - 1}</span>
            </div>
          </div>
          <div class="range-input-pair">
            <label for="end-led-input">Last LED:</label>
            <input
              id="end-led-input"
              type="number"
              min="0"
              max={ledCount - 1}
              bind:value={endLedValue}
              on:change={handleEndLedChange}
              disabled={$calibrationUI.isLoading}
              class="led-input"
            />
          </div>
        </div>

        <div class="range-stats">
          <div class="stat-box">
            <span class="stat-label">Active Range:</span>
            <span class="stat-value">{startLedValue} – {endLedValue}</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Total LEDs:</span>
            <span class="stat-value">{Math.max(0, endLedValue - startLedValue + 1)}</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Coverage:</span>
            <span class="stat-value">{Math.round(((endLedValue - startLedValue + 1) / (ledCount)) * 100)}%</span>
          </div>
        </div>
      </div>

      <p class="range-description">
        Drag the sliders or enter values to set the first and last LED indices that will be mapped to piano keys.
        Leaving LEDs at the start unmapped allows for visual overflow. <strong>First:</strong> {startLedValue}, <strong>Last:</strong> {endLedValue}
      </p>
    </div>
  </div>
</div>

<style>
  .calibration-section-2 {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .section-intro {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .section-intro h3 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
  }

  .section-intro p {
    margin: 0;
    color: #475569;
    font-size: 0.95rem;
  }

  .global-offset-container {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 10px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .led-range-container {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 10px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .range-header {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .range-header h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #0f172a;
  }

  .range-header p {
    margin: 0;
    font-size: 0.85rem;
    color: #475569;
  }

  .range-visualization {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .range-display {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .range-info-row {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .range-input-pair {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 0 0 auto;
    min-width: 100px;
  }

  .range-input-pair label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #0f172a;
  }

  .led-input {
    padding: 0.5rem 0.75rem;
    border: 2px solid #bfdbfe;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #1e40af;
    background: white;
    transition: border-color 0.2s ease;
    width: 90px;
  }

  .led-input:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .led-input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .range-bar-wrapper {
    flex: 1;
    min-width: 250px;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .range-bar-track {
    position: relative;
    height: 40px;
    background: linear-gradient(to right, #e0e7ff, #fce7f3);
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    overflow: visible;
  }

  .range-bar-fill {
    position: absolute;
    top: 0;
    height: 100%;
    background: linear-gradient(to right, #3b82f6, #ec4899);
    border-radius: 7px;
    pointer-events: none;
    z-index: 2;
  }

  .range-slider {
    position: absolute;
    top: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    z-index: 5;
    margin: 0;
    padding: 0;
  }

  .range-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 40px;
    border-radius: 4px;
    background: white;
    border: 2px solid #2563eb;
    cursor: pointer;
    pointer-events: all;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    transition: all 0.2s ease;
  }

  .range-slider::-webkit-slider-thumb:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
  }

  .range-slider::-moz-range-thumb {
    width: 20px;
    height: 40px;
    border-radius: 4px;
    background: white;
    border: 2px solid #2563eb;
    cursor: pointer;
    pointer-events: all;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
    transition: all 0.2s ease;
  }

  .range-slider::-moz-range-thumb:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
  }

  .range-slider.start::-webkit-slider-thumb {
    z-index: 6;
  }

  .range-slider.end::-webkit-slider-thumb {
    z-index: 5;
  }

  .range-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #64748b;
    padding: 0 2px;
  }

  .range-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .stat-box {
    background: white;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .stat-label {
    font-size: 0.8rem;
    color: #64748b;
    font-weight: 500;
  }

  .stat-value {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1e40af;
  }

  .range-description {
    font-size: 0.85rem;
    color: #475569;
    margin: 0;
    line-height: 1.4;
  }

  .led-adjustment-item {
    display: none;
  }

  .adjustment-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .adjustment-header label {
    margin: 0;
    font-weight: 600;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .led-value {
    background: #dbeafe;
    border: 2px solid #2563eb;
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-weight: 700;
    color: #1e40af;
    font-size: 0.9rem;
    min-width: 60px;
    text-align: center;
  }

  .adjustment-description {
    margin: 0;
    color: #64748b;
    font-size: 0.85rem;
    line-height: 1.5;
  }

  .mapping-info {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    padding: 1rem;
    background: #ecfdf5;
    border: 1px solid #86efac;
    border-radius: 8px;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
  }

  .info-label {
    font-weight: 600;
    color: #065f46;
    font-size: 0.9rem;
  }

  .info-value {
    font-weight: 700;
    color: #059669;
    font-size: 0.9rem;
  }

  .offset-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .offset-header label,
  .offset-header h4 {
    margin: 0;
    font-weight: 600;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .offset-header h4 {
    font-size: 1rem;
  }

  .offset-value {
    background: #ffffff;
    border: 2px solid #2563eb;
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-weight: 700;
    color: #2563eb;
    font-size: 0.9rem;
    min-width: 50px;
    text-align: center;
  }

  .count-badge {
    background: #2563eb;
    color: #ffffff;
    border-radius: 50%;
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
    font-weight: 600;
    min-width: 24px;
    text-align: center;
  }

  .slider-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .slider-container input[type="range"] {
    width: 100%;
    height: 8px;
    -webkit-appearance: none;
    appearance: none;
    background: #e2e8f0;
    border-radius: 4px;
    outline: none;
    accent-color: #2563eb;
  }

  .slider-container input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    background: #2563eb;
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
  }

  .slider-container input[type="range"]::-moz-range-thumb {
    width: 20px;
    height: 20px;
    background: #2563eb;
    border-radius: 50%;
    cursor: pointer;
    border: none;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
  }

  .slider-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #64748b;
  }

  .offset-description {
    margin: 0;
    font-size: 0.85rem;
    color: #0c4a6e;
    line-height: 1.4;
  }

  .per-key-offsets-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .offsets-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem;
    background: #fafbfc;
  }

  .offset-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .view-mode {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex: 1;
  }

  .offset-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .note-name {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .note-midi {
    font-size: 0.8rem;
    color: #64748b;
  }

  .offset-value-display {
    background: #e0f2fe;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
  }

  .offset-value-display .value {
    font-weight: 700;
    color: #0c4a6e;
    font-size: 0.9rem;
  }

  .item-actions {
    display: flex;
    gap: 0.5rem;
  }

  .edit-mode {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
  }

  .edit-controls {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
  }

  .note-label {
    font-weight: 600;
    color: #0f172a;
    min-width: 50px;
  }

  .small-slider {
    flex: 1;
    height: 6px;
    accent-color: #2563eb;
  }

  .offset-display {
    font-weight: 700;
    color: #2563eb;
    min-width: 40px;
    text-align: right;
  }

  .edit-actions {
    display: flex;
    gap: 0.5rem;
  }

  .empty-state {
    text-align: center;
    padding: 2rem 1rem;
    color: #64748b;
  }

  .empty-state p {
    margin: 0;
    font-size: 0.9rem;
  }

  .empty-state .hint {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.5rem;
  }

  .add-offset-form {
    border-top: 1px solid #e2e8f0;
    padding-top: 1rem;
  }

  .form-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
  }

  .form-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-field label {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.85rem;
  }

  .form-field input[type="number"],
  .form-field input[type="range"] {
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .form-field input[type="number"] {
    background: #ffffff;
    color: #0f172a;
  }

  .form-field input[type="number"]:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .form-actions {
    display: flex;
    gap: 0.75rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.9rem;
    padding: 0.5rem 1rem;
  }

  .btn-sm {
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
  }

  .btn-primary {
    background: #2563eb;
    color: #ffffff;
  }

  .btn-primary:hover:not(:disabled) {
    background: #1d4ed8;
  }

  .btn-ghost {
    background: transparent;
    border: 1px solid #d1d5db;
    color: #1f2937;
  }

  .btn-ghost:hover:not(:disabled) {
    background: #f3f4f6;
  }

  .btn-add {
    width: 100%;
    background: #10b981;
    color: #ffffff;
    padding: 0.65rem;
  }

  .btn-add:hover:not(:disabled) {
    background: #059669;
  }

  .btn-icon {
    padding: 0.4rem 0.5rem;
    font-size: 0.9rem;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    color: #1f2937;
  }

  .btn-icon:hover:not(:disabled) {
    background: #e5e7eb;
  }

  .btn-danger {
    color: #dc2626;
  }

  .btn-danger:hover:not(:disabled) {
    background: #fee2e2;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  @media (max-width: 640px) {
    .calibration-section-2 {
      padding: 1rem;
      gap: 1.5rem;
    }

    .form-fields {
      grid-template-columns: 1fr;
    }

    .offset-item {
      flex-direction: column;
      align-items: flex-start;
    }

    .view-mode {
      width: 100%;
    }

    .item-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .edit-mode {
      flex-direction: column;
      align-items: stretch;
    }

    .edit-controls {
      flex-direction: column;
    }

    .form-actions {
      flex-direction: column;
    }

    .btn {
      width: 100%;
    }
  }
</style>
