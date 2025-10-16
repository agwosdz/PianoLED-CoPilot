<script lang="ts">
  import { calibrationState, calibrationUI, keyOffsetsList, getMidiNoteName, setKeyOffset, deleteKeyOffset, setGlobalOffset } from '$lib/stores/calibration';
  import type { KeyOffset } from '$lib/stores/calibration';

  let globalOffsetValue = 0;
  let editingKeyNote: number | null = null;
  let editingKeyOffset = 0;
  let newKeyMidiNote = '';
  let newKeyOffset = 0;
  let showAddForm = false;

  $: globalOffsetValue = $calibrationState.global_offset;

  async function handleGlobalOffsetChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const value = parseInt(target.value, 10);
    if (Number.isFinite(value)) {
      // Update local state immediately for responsive UI
      globalOffsetValue = value;
      // Then sync with backend
      await setGlobalOffset(value);
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
    <h3>Offset Adjustment</h3>
    <p>Configure global and per-key LED offsets to align with your piano keys.</p>
  </div>

  <!-- Global Offset Section -->
  <div class="global-offset-container">
    <div class="offset-header">
      <label for="global-offset">Global Offset</label>
      <span class="offset-value">{globalOffsetValue > 0 ? '+' : ''}{globalOffsetValue}</span>
    </div>
    
    <div class="slider-container">
      <input
        id="global-offset"
        type="range"
        min="0"
        max="20"
        step="1"
        value={globalOffsetValue}
        on:change={handleGlobalOffsetChange}
        disabled={$calibrationUI.isLoading}
      />
      <div class="slider-labels">
        <span>0</span>
        <span>10</span>
        <span>20</span>
      </div>
    </div>

    <p class="offset-description">
      Uniformly shifts all LEDs forward (0-20) to account for LED strip position
    </p>
  </div>

  <!-- Per-Key Offsets Section -->
  <div class="per-key-offsets-container">
    <div class="offset-header">
      <h4>Individual Key Offsets</h4>
      <span class="count-badge">{$keyOffsetsList.length}</span>
    </div>

    {#if $keyOffsetsList.length > 0}
      <div class="offsets-list">
        {#each $keyOffsetsList as item (item.midiNote)}
          <div class="offset-item">
            {#if editingKeyNote === item.midiNote}
              <!-- Edit mode -->
              <div class="edit-mode">
                <div class="edit-controls">
                  <span class="note-label">{item.noteName}</span>
                  <input
                    type="range"
                    min="-10"
                    max="10"
                    step="1"
                    bind:value={editingKeyOffset}
                    class="small-slider"
                  />
                  <span class="offset-display">{editingKeyOffset > 0 ? '+' : ''}{editingKeyOffset}</span>
                </div>
                <div class="edit-actions">
                  <button
                    class="btn btn-sm btn-primary"
                    on:click={saveEditingKeyOffset}
                    disabled={$calibrationUI.isLoading}
                  >
                    Save
                  </button>
                  <button
                    class="btn btn-sm btn-ghost"
                    on:click={cancelEditingKeyOffset}
                    disabled={$calibrationUI.isLoading}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            {:else}
              <!-- View mode -->
              <div class="view-mode">
                <div class="offset-info">
                  <span class="note-name">{item.noteName}</span>
                  <span class="note-midi">MIDI {item.midiNote}</span>
                </div>
                <div class="offset-value-display">
                  <span class="value">{item.offset > 0 ? '+' : ''}{item.offset}</span>
                </div>
              </div>
              <div class="item-actions">
                <button
                  class="btn btn-sm btn-icon"
                  title="Edit offset"
                  on:click={() => startEditingKeyOffset(item)}
                  disabled={$calibrationUI.isLoading}
                >
                  ✎
                </button>
                <button
                  class="btn btn-sm btn-icon btn-danger"
                  title="Delete offset"
                  on:click={() => handleDeleteKeyOffset(item.midiNote)}
                  disabled={$calibrationUI.isLoading}
                >
                  🗑
                </button>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state">
        <p>No individual key offsets set yet.</p>
        <p class="hint">Add offsets below to fine-tune specific keys</p>
      </div>
    {/if}

    <!-- Add New Offset Form -->
    <div class="add-offset-form">
      {#if showAddForm}
        <div class="form-container">
          <div class="form-fields">
            <div class="form-field">
              <label for="new-midi-note">MIDI Note (0-127)</label>
              <input
                id="new-midi-note"
                type="number"
                min="0"
                max="127"
                placeholder="e.g., 60 for Middle C"
                bind:value={newKeyMidiNote}
                disabled={$calibrationUI.isLoading}
              />
            </div>

            <div class="form-field">
              <label for="new-offset">Offset ({newKeyOffset > 0 ? '+' : ''}{newKeyOffset})</label>
              <input
                id="new-offset"
                type="range"
                min="-10"
                max="10"
                step="1"
                bind:value={newKeyOffset}
                disabled={$calibrationUI.isLoading}
              />
            </div>
          </div>

          <div class="form-actions">
            <button
              class="btn btn-primary"
              on:click={handleAddKeyOffset}
              disabled={$calibrationUI.isLoading}
            >
              Add Offset
            </button>
            <button
              class="btn btn-ghost"
              on:click={resetAddForm}
              disabled={$calibrationUI.isLoading}
            >
              Cancel
            </button>
          </div>
        </div>
      {:else}
        <button
          class="btn btn-add"
          on:click={() => (showAddForm = true)}
          disabled={$calibrationUI.isLoading}
        >
          + Add Key Offset
        </button>
      {/if}
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
