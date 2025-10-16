<script lang="ts">
  import { settings } from '$lib/stores/settings';
  import { calibrationState } from '$lib/stores/calibration';

  // Piano configuration
  const PIANO_KEYS = 88;
  const START_NOTE = 'A0'; // A0 is MIDI note 21
  const START_MIDI = 21;
  
  interface KeyInfo {
    midiNote: number;
    noteName: string;
    isBlack: boolean;
    ledIndex: number | null;
    offset: number;
  }

  let ledMapping: Record<number, number> = {};
  let pianoKeys: KeyInfo[] = [];
  let hoveredNote: number | null = null;
  let selectedNote: number | null = null;

  function getMidiNoteName(midiNote: number): string {
    const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const octave = Math.floor(midiNote / 12) - 1;
    const noteIndex = midiNote % 12;
    return `${NOTE_NAMES[noteIndex]}${octave}`;
  }

  function isBlackKey(midiNote: number): boolean {
    const noteIndex = midiNote % 12;
    return [1, 3, 6, 8, 10].includes(noteIndex);
  }

  function generatePianoKeys(): KeyInfo[] {
    const keys: KeyInfo[] = [];
    for (let i = 0; i < PIANO_KEYS; i++) {
      const midiNote = START_MIDI + i;
      keys.push({
        midiNote,
        noteName: getMidiNoteName(midiNote),
        isBlack: isBlackKey(midiNote),
        ledIndex: ledMapping[midiNote] ?? null,
        offset: $calibrationState.key_offsets[midiNote] ?? 0
      });
    }
    return keys;
  }

  function updateLedMapping(): void {
    // For now, we'll use a simple mapping: key index = LED index
    // In a real scenario, this would come from backend config
    const mapping: Record<number, number> = {};
    
    // Assuming each piano key maps to one or more LEDs
    // Simple 1:1 mapping for visualization
    for (let i = 0; i < PIANO_KEYS; i++) {
      const midiNote = START_MIDI + i;
      // Calculate approximate LED index based on key position
      const ledsPerKey = 3; // Approximate
      mapping[midiNote] = i * ledsPerKey;
    }
    
    ledMapping = mapping;
    pianoKeys = generatePianoKeys();
  }

  // Update when settings or calibration changes
  $: if ($settings && $calibrationState) {
    updateLedMapping();
  }

  function handleKeyClick(midiNote: number) {
    selectedNote = selectedNote === midiNote ? null : midiNote;
  }

  function handleKeyHover(midiNote: number | null) {
    hoveredNote = midiNote;
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
  }
</script>

<div class="calibration-section-3">
  <div class="section-intro">
    <h3>Piano LED Mapping</h3>
    <p>Visual representation of how piano keys map to LED indices with current offsets.</p>
  </div>

  <div class="visualization-container">
    <div class="piano-keyboard">
      {#each pianoKeys as key (key.midiNote)}
        <button
          class={`piano-key ${key.isBlack ? 'black' : 'white'} ${
            selectedNote === key.midiNote ? 'selected' : ''
          } ${hoveredNote === key.midiNote ? 'hovered' : ''}`}
          on:click={() => handleKeyClick(key.midiNote)}
          on:mouseenter={() => handleKeyHover(key.midiNote)}
          on:mouseleave={() => handleKeyHover(null)}
          title={`${key.noteName} (MIDI ${key.midiNote})`}
        >
          <div class="key-content">
            <span class="note-label">{key.noteName}</span>
            <div class="led-info">
              {#if key.ledIndex !== null}
                <span class="led-index">LED {key.ledIndex}</span>
                {#if $calibrationState.global_offset !== 0 || key.offset !== 0}
                  <div class="offset-indicators">
                    {#if $calibrationState.global_offset !== 0}
                      <span class="offset-badge global-offset" title="Global offset applied to all keys">
                        G{$calibrationState.global_offset > 0 ? '+' : ''}{$calibrationState.global_offset}
                      </span>
                    {/if}
                    {#if key.offset !== 0}
                      <span class="offset-badge individual-offset" title="Individual offset for this key">
                        I{key.offset > 0 ? '+' : ''}{key.offset}
                      </span>
                    {/if}
                  </div>
                {/if}
              {:else}
                <span class="no-mapping">—</span>
              {/if}
            </div>
          </div>
        </button>
      {/each}
    </div>

    <!-- Details Panel -->
    {#if selectedNote !== null}
      <div class="details-panel">
        <div class="details-header">
          <h4>{getMidiNoteName(selectedNote)} (MIDI {selectedNote})</h4>
          <button
            class="btn-close"
            on:click={() => (selectedNote = null)}
            title="Close"
          >
            ×
          </button>
        </div>

        <div class="details-content">
          {#if ledMapping[selectedNote] !== null}
            <div class="detail-row">
              <span class="detail-label">LED Index:</span>
              <span class="detail-value">{ledMapping[selectedNote]}</span>
              <button
                class="btn-copy"
                on:click={() => selectedNote !== null && copyToClipboard(String(ledMapping[selectedNote]))}
                title="Copy to clipboard"
              >
                📋
              </button>
            </div>

            {#if $calibrationState.global_offset !== 0}
              <div class="detail-row">
                <span class="detail-label">Global Offset:</span>
                <span class="detail-value">
                  {$calibrationState.global_offset > 0 ? '+' : ''}
                  {$calibrationState.global_offset}
                </span>
              </div>
            {/if}

            {#if $calibrationState.key_offsets[selectedNote]}
              <div class="detail-row">
                <span class="detail-label">Individual Offset:</span>
                <span class="detail-value">
                  {$calibrationState.key_offsets[selectedNote] > 0 ? '+' : ''}
                  {$calibrationState.key_offsets[selectedNote]}
                </span>
              </div>
            {/if}

            {#if $calibrationState.global_offset !== 0 || $calibrationState.key_offsets[selectedNote]}
              <div class="detail-row highlight">
                <span class="detail-label">Total Offset:</span>
                <span class="detail-value">
                  {($calibrationState.global_offset + ($calibrationState.key_offsets[selectedNote] ?? 0)) > 0 ? '+' : ''}
                  {$calibrationState.global_offset + ($calibrationState.key_offsets[selectedNote] ?? 0)}
                </span>
              </div>

              <div class="detail-row highlight">
                <span class="detail-label">Adjusted LED:</span>
                <span class="detail-value">
                  {ledMapping[selectedNote] + $calibrationState.global_offset + ($calibrationState.key_offsets[selectedNote] ?? 0)}
                </span>
              </div>
            {/if}
          {:else}
            <p class="no-data">No LED mapping available for this key</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Legend -->
  <div class="legend">
    <div class="legend-item">
      <div class="legend-box white"></div>
      <span>White Key</span>
    </div>
    <div class="legend-item">
      <div class="legend-box black"></div>
      <span>Black Key</span>
    </div>
    <div class="legend-item">
      <div class="legend-box selected"></div>
      <span>Selected</span>
    </div>
    <div class="legend-item">
      <div class="legend-box offset"></div>
      <span>Has Custom Offset</span>
    </div>
  </div>

  <!-- Info -->
  <div class="info-box">
    <p>
      <strong>Total Keys:</strong> {PIANO_KEYS} (A0 - C8)
    </p>
    <p>
      <strong>Keys with Custom Offsets:</strong> {Object.keys($calibrationState.key_offsets).length}
    </p>
    <p>
      <strong>Global Offset:</strong> {$calibrationState.global_offset > 0 ? '+' : ''}{$calibrationState.global_offset}
    </p>
    <p>
      <strong>Status:</strong>
      {#if $calibrationState.enabled}
        <span class="status-badge active">Calibration Active</span>
      {:else}
        <span class="status-badge inactive">Calibration Disabled</span>
      {/if}
    </p>
  </div>
</div>

<style>
  .calibration-section-3 {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
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

  .visualization-container {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .piano-keyboard {
    display: flex;
    gap: 1px;
    background: #334155;
    padding: 1rem;
    border-radius: 8px;
    min-height: 200px;
    overflow-x: auto;
    position: relative;
  }

  .piano-key {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    cursor: pointer;
    border: 2px solid #1e293b;
    border-radius: 4px;
    transition: all 0.2s ease;
    padding: 0.5rem 0.25rem;
    font-size: 0.7rem;
    min-width: 40px;
    flex-shrink: 0;
    position: relative;
    background: none;
  }

  .piano-key.white {
    background: linear-gradient(to bottom, #ffffff, #f1f5f9);
    color: #0f172a;
    height: 140px;
  }

  .piano-key.black {
    background: linear-gradient(to bottom, #1e293b, #0f172a);
    color: #ffffff;
    height: 90px;
    margin: 0 -15px 0 -15px;
    z-index: 10;
  }

  .piano-key.white.hovered {
    background: linear-gradient(to bottom, #f1f5f9, #e2e8f0);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
  }

  .piano-key.black.hovered {
    background: linear-gradient(to bottom, #334155, #1e293b);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }

  .piano-key.selected {
    box-shadow: inset 0 0 0 2px #2563eb, 0 0 10px rgba(37, 99, 235, 0.4);
  }

  .key-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    text-align: center;
  }

  .note-label {
    font-weight: 600;
    font-size: 0.75rem;
  }

  .led-info {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 0.65rem;
  }

  .led-index {
    background: rgba(37, 99, 235, 0.1);
    padding: 0.1rem 0.2rem;
    border-radius: 2px;
  }

  .piano-key.black .led-index {
    background: rgba(255, 255, 255, 0.1);
  }

  .led-offset {
    color: #10b981;
    font-weight: 600;
  }

  .offset-indicators {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .offset-badge {
    display: inline-block;
    padding: 0.15rem 0.3rem;
    border-radius: 2px;
    font-size: 0.6rem;
    font-weight: 700;
    text-align: center;
    line-height: 1;
  }

  .offset-badge.global-offset {
    background: rgba(59, 130, 246, 0.2);
    color: #1e40af;
    border: 1px solid rgba(59, 130, 246, 0.4);
  }

  .piano-key.black .offset-badge.global-offset {
    background: rgba(147, 197, 253, 0.2);
    color: #dbeafe;
    border: 1px solid rgba(147, 197, 253, 0.4);
  }

  .offset-badge.individual-offset {
    background: rgba(34, 197, 94, 0.2);
    color: #15803d;
    border: 1px solid rgba(34, 197, 94, 0.4);
  }

  .piano-key.black .offset-badge.individual-offset {
    background: rgba(134, 239, 172, 0.2);
    color: #86efac;
    border: 1px solid rgba(134, 239, 172, 0.4);
  }

  .no-mapping {
    opacity: 0.6;
  }

  .details-panel {
    background: #f8fafc;
    border: 2px solid #2563eb;
    border-radius: 8px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .details-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .details-header h4 {
    margin: 0;
    font-size: 1rem;
    color: #0f172a;
  }

  .btn-close {
    background: transparent;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #64748b;
  }

  .btn-close:hover {
    color: #0f172a;
  }

  .details-content {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .detail-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem;
    background: #ffffff;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
  }

  .detail-row.highlight {
    background: linear-gradient(135deg, #f0fdf4, #f0fdf4);
    border: 1px solid #86efac;
  }

  .detail-label {
    font-weight: 600;
    color: #475569;
    font-size: 0.9rem;
    min-width: 120px;
  }

  .detail-value {
    font-weight: 700;
    color: #2563eb;
    font-size: 0.9rem;
    flex: 1;
  }

  .btn-copy {
    background: transparent;
    border: 1px solid #d1d5db;
    padding: 0.3rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .btn-copy:hover {
    background: #e5e7eb;
  }

  .no-data {
    margin: 0;
    color: #64748b;
    text-align: center;
    padding: 1rem;
  }

  .legend {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .legend-box {
    width: 24px;
    height: 24px;
    border-radius: 4px;
    border: 2px solid #1e293b;
  }

  .legend-box.white {
    background: linear-gradient(to bottom, #ffffff, #f1f5f9);
  }

  .legend-box.black {
    background: linear-gradient(to bottom, #1e293b, #0f172a);
  }

  .legend-box.selected {
    background: #2563eb;
  }

  .legend-box.offset {
    background: linear-gradient(135deg, #10b981, #059669);
  }

  .legend-item span {
    font-size: 0.9rem;
    color: #0f172a;
  }

  .info-box {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 1rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .info-box p {
    margin: 0;
    font-size: 0.9rem;
    color: #0c4a6e;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .status-badge.active {
    background: #d1fae5;
    color: #065f46;
  }

  .status-badge.inactive {
    background: #fee2e2;
    color: #7f1d1d;
  }

  @media (max-width: 1024px) {
    .piano-keyboard {
      min-height: 150px;
    }

    .piano-key {
      min-width: 35px;
    }

    .piano-key.white {
      height: 100px;
    }

    .piano-key.black {
      height: 65px;
    }
  }

  @media (max-width: 640px) {
    .calibration-section-3 {
      padding: 1rem;
    }

    .piano-keyboard {
      min-height: 120px;
      padding: 0.75rem;
    }

    .piano-key {
      min-width: 30px;
      padding: 0.25rem;
    }

    .piano-key.white {
      height: 80px;
    }

    .piano-key.black {
      height: 50px;
    }

    .info-box {
      grid-template-columns: 1fr;
    }

    .details-panel {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      border-radius: 8px 8px 0 0;
      z-index: 100;
    }
  }
</style>
