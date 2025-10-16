<script lang="ts">
  import { settings } from '$lib/stores/settings';
  import { calibrationState, calibrationUI, getKeyLedMapping } from '$lib/stores/calibration';
  import { onMount } from 'svelte';

  // Piano size specifications for different keyboard types
  const PIANO_SPECS: Record<string, { keys: number; midiStart: number; midiEnd: number }> = {
    '25-key': { keys: 25, midiStart: 48, midiEnd: 72 },     // C3 - C5
    '37-key': { keys: 37, midiStart: 36, midiEnd: 72 },     // C2 - C5
    '49-key': { keys: 49, midiStart: 36, midiEnd: 84 },     // C2 - C6
    '61-key': { keys: 61, midiStart: 36, midiEnd: 96 },     // C2 - C7
    '76-key': { keys: 76, midiStart: 28, midiEnd: 103 },    // E1 - G7
    '88-key': { keys: 88, midiStart: 21, midiEnd: 108 }     // A0 - C8
  };

  interface KeyInfo {
    midiNote: number;
    noteName: string;
    isBlack: boolean;
    adjustedLedIndices: number[];
    offset: number;
  }

  let ledMapping: Record<number, number[]> = {}; // Maps MIDI note to array of LED indices (after offsets applied)
  let pianoKeys: KeyInfo[] = [];
  let hoveredNote: number | null = null;
  let selectedNote: number | null = null;
  let currentPianoSize = '88-key';
  let pianoKeyCount = 88;
  let startMidiNote = 21;
  let isLoadingMapping = false;
  let ledOperationInProgress = false; // Prevent overlapping LED operations
  let showingLayoutVisualization = false; // Toggle for layout visualization mode
  let layoutVisualizationActive = false; // Track if LEDs are currently on for visualization

  // Validation and mapping info state
  let validationResults: any = null;
  let mappingInfo: any = null;
  let distributionMode: string = 'proportional';
  let availableDistributionModes: string[] = [];
  let isLoadingValidation = false;
  let isLoadingMappingInfo = false;
  let showValidationPanel = false;
  let showMappingInfo = false;

  // Color configurations - will be fetched from settings
  let BLACK_KEY_COLOR = { r: 150, g: 0, b: 100 };   // Magenta/Pink (default)
  let WHITE_KEY_COLOR = { r: 0, g: 100, b: 150 };   // Cyan/Blue (default)

  async function loadColorsFromSettings(): Promise<void> {
    try {
      const response = await fetch('/api/settings/calibration');
      if (response.ok) {
        const data = await response.json();
        if (data.white_key_color) {
          WHITE_KEY_COLOR = data.white_key_color;
          console.log('[LED] White key color from settings:', WHITE_KEY_COLOR);
        }
        if (data.black_key_color) {
          BLACK_KEY_COLOR = data.black_key_color;
          console.log('[LED] Black key color from settings:', BLACK_KEY_COLOR);
        }
      } else {
        console.warn('[LED] Failed to load colors from settings, using defaults');
      }
    } catch (error) {
      console.warn('[LED] Could not fetch colors from settings, using defaults:', error);
    }
  }

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
    for (let i = 0; i < pianoKeyCount; i++) {
      const midiNote = startMidiNote + i;
      keys.push({
        midiNote,
        noteName: getMidiNoteName(midiNote),
        isBlack: isBlackKey(midiNote),
        adjustedLedIndices: ledMapping[midiNote] ?? [],
        offset: $calibrationState.key_offsets[midiNote] ?? 0
      });
    }
    return keys;
  }

  function updatePianoSize(): void {
    const pianoSize = $settings?.piano?.size || '88-key';
    const spec = PIANO_SPECS[pianoSize] || PIANO_SPECS['88-key'];
    
    currentPianoSize = pianoSize;
    pianoKeyCount = spec.keys;
    startMidiNote = spec.midiStart;
    
    updateLedMapping();
  }

  async function updateLedMapping(): Promise<void> {
    isLoadingMapping = true;
    try {
      // Fetch the LED mapping with offsets applied from the backend
      ledMapping = await getKeyLedMapping();
      pianoKeys = generatePianoKeys();
    } catch (error) {
      console.error('Failed to update LED mapping:', error);
      // Fall back to empty mapping on error
      ledMapping = {};
      pianoKeys = generatePianoKeys();
    } finally {
      isLoadingMapping = false;
    }
  }

  // Update when settings or calibration changes
  $: if ($settings && $calibrationState) {
    updatePianoSize();
    loadColorsFromSettings();
  }

  async function lightUpLedRange(ledIndices: number[]): Promise<void> {
    if (!ledIndices || ledIndices.length === 0) return;
    
    try {
      console.log(`[LED] Lighting up ${ledIndices.length} LEDs: ${ledIndices.join(', ')}`);
      
      const response = await fetch('/api/calibration/leds-on', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leds: ledIndices })
      });
      
      if (!response.ok) {
        console.warn(`[LED] Failed to light LEDs: ${response.status}`);
      } else {
        const data = await response.json();
        console.log(`[LED] Successfully lit ${data.leds_turned_on}/${data.total_requested} LEDs`);
        if (data.errors && data.errors.length > 0) {
          console.warn('[LED] Some errors occurred:', data.errors);
        }
      }
    } catch (error) {
      console.error('[LED] Failed to light up LEDs:', error);
    }
  }

  async function lightUpLedRangeWithColor(ledIndices: number[], color: { r: number; g: number; b: number }): Promise<void> {
    if (!ledIndices || ledIndices.length === 0) return;
    
    try {
      console.log(`[LED] Lighting up ${ledIndices.length} LEDs with color RGB(${color.r},${color.g},${color.b})`);
      
      // Build LED objects with color info
      const ledsWithColor = ledIndices.map(index => ({
        index,
        r: color.r,
        g: color.g,
        b: color.b
      }));
      
      const response = await fetch('/api/calibration/leds-on', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leds: ledsWithColor })
      });
      
      if (!response.ok) {
        console.warn(`[LED] Failed to light LEDs with color: ${response.status}`);
      } else {
        const data = await response.json();
        console.log(`[LED] Successfully lit ${data.leds_turned_on}/${data.total_requested} LEDs with color`);
        if (data.errors && data.errors.length > 0) {
          console.warn('[LED] Some errors occurred:', data.errors);
        }
      }
    } catch (error) {
      console.error('[LED] Failed to light up LEDs with color:', error);
    }
  }

  async function turnOffAllLeds(): Promise<void> {
    try {
      console.log('[LED] Turning off all LEDs...');
      // Turn off all LEDs
      const response = await fetch('/api/hardware-test/led/off', {
        method: 'POST'
      });
      if (!response.ok) {
        console.warn(`[LED] Failed to turn off all LEDs: ${response.status}`);
      } else {
        console.log('[LED] All LEDs turned off successfully');
      }
      // Small delay to ensure hardware state updates
      await new Promise(resolve => setTimeout(resolve, 100));
    } catch (error) {
      console.error('[LED] Failed to turn off LEDs:', error);
    }
  }

  async function handleKeyClick(midiNote: number) {
    console.log(`[LED] Key clicked: MIDI ${midiNote}, currently selected: ${selectedNote}`);
    
    // If clicking the same key, deselect it and turn off LEDs
    if (selectedNote === midiNote) {
      console.log(`[LED] Same key clicked, deselecting...`);
      selectedNote = null;
      await turnOffAllLeds();
      console.log(`[LED] Deselection complete`);
      return;
    }

    // ALWAYS turn off all LEDs first, regardless of state
    console.log(`[LED] Turning off any existing LEDs before selecting new key...`);
    await turnOffAllLeds();
    console.log(`[LED] All LEDs cleared, now proceeding with new key selection`);

    // Select new key and light it up with appropriate color
    console.log(`[LED] Selecting key ${midiNote} and lighting up LEDs...`);
    selectedNote = midiNote;
    const ledIndices = ledMapping[midiNote];
    
    if (ledIndices && ledIndices.length > 0) {
      console.log(`[LED] LED indices for key ${midiNote}: ${ledIndices.join(', ')}`);
      // Verify indices are valid before sending
      const validIndices = ledIndices.filter(idx => typeof idx === 'number' && Number.isFinite(idx));
      if (validIndices.length > 0) {
        console.log(`[LED] Lighting up ${validIndices.length} valid LEDs using batch endpoint...`);
        
        // Determine which color to use based on whether it's a black or white key
        const keyColor = isBlackKey(midiNote) ? BLACK_KEY_COLOR : WHITE_KEY_COLOR;
        console.log(`[LED] Using ${isBlackKey(midiNote) ? 'black' : 'white'} key color: RGB(${keyColor.r},${keyColor.g},${keyColor.b})`);
        
        await lightUpLedRangeWithColor(validIndices, keyColor);
      } else {
        console.warn(`[LED] No valid LED indices found for key ${midiNote}`);
      }
    } else {
      console.warn(`[LED] No LED mapping for key ${midiNote}`);
    }
  }

  function handleKeyHover(midiNote: number | null) {
    hoveredNote = midiNote;
  }

  function getFirstAdjustedLedIndex(midiNote: number): number | null {
    const indices = ledMapping[midiNote];
    if (!indices || indices.length === 0) {
      return null;
    }
    return indices[0];
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
  }

  function openAddOffsetForm(midiNote: number) {
    // Dispatch event to parent or scroll to CalibrationSection2
    // For now, we'll emit an event that parent can listen to
    const event = new CustomEvent('openAddOffset', { 
      detail: { midiNote },
      bubbles: true 
    });
    window.dispatchEvent(event);
  }

  async function toggleLayoutVisualization() {
    if (layoutVisualizationActive) {
      // Turn off visualization
      console.log('[LED] Turning off layout visualization');
      await turnOffAllLeds();
      layoutVisualizationActive = false;
      showingLayoutVisualization = false;
    } else {
      // Turn on visualization - show all white and black keys in their colors
      console.log('[LED] Starting layout visualization');
      showingLayoutVisualization = true;
      layoutVisualizationActive = true;
      
      try {
        // Light all white keys with white key color
        const whiteKeyNotes = pianoKeys.filter(k => !k.isBlack).map(k => k.midiNote);
        const blackKeyNotes = pianoKeys.filter(k => k.isBlack).map(k => k.midiNote);
        
        const whiteKeyLeds: number[] = [];
        const blackKeyLeds: number[] = [];
        
        // Collect all LED indices for white and black keys
        for (const note of whiteKeyNotes) {
          const indices = ledMapping[note];
          if (indices && indices.length > 0) {
            whiteKeyLeds.push(...indices);
          }
        }
        
        for (const note of blackKeyNotes) {
          const indices = ledMapping[note];
          if (indices && indices.length > 0) {
            blackKeyLeds.push(...indices);
          }
        }
        
        console.log(`[LED] Layout visualization: ${whiteKeyLeds.length} white key LEDs, ${blackKeyLeds.length} black key LEDs`);
        
        // Light them up with their respective colors
        if (whiteKeyLeds.length > 0) {
          await lightUpLedRangeWithColor(whiteKeyLeds, WHITE_KEY_COLOR);
        }
        if (blackKeyLeds.length > 0) {
          await lightUpLedRangeWithColor(blackKeyLeds, BLACK_KEY_COLOR);
        }
      } catch (error) {
        console.error('[LED] Layout visualization failed:', error);
        layoutVisualizationActive = false;
        showingLayoutVisualization = false;
      }
    }
  }

  function handleKeyPressWhileVisualizingLayout(event: KeyboardEvent | MouseEvent): void {
    // If layout visualization is active and a key is pressed, turn it off
    if (layoutVisualizationActive) {
      console.log('[LED] Key/click detected during layout visualization, turning off');
      toggleLayoutVisualization();
    }
  }

  // Validation and mapping info functions
  async function loadValidationResults(): Promise<void> {
    isLoadingValidation = true;
    try {
      const pianoSize = $settings?.piano?.size || '88-key';
      const ledCount = $settings?.led?.led_count || 246;
      
      const response = await fetch('/api/calibration/mapping-validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ piano_size: pianoSize, led_count: ledCount })
      });
      
      if (response.ok) {
        validationResults = await response.json();
        showValidationPanel = true;
        console.log('[Validation] Results loaded:', validationResults);
      } else {
        console.warn('[Validation] Failed to load validation results');
      }
    } catch (error) {
      console.error('[Validation] Error loading validation results:', error);
    } finally {
      isLoadingValidation = false;
    }
  }

  async function loadMappingInfo(): Promise<void> {
    isLoadingMappingInfo = true;
    try {
      const response = await fetch('/api/calibration/mapping-info');
      
      if (response.ok) {
        mappingInfo = await response.json();
        showMappingInfo = true;
        console.log('[Mapping Info] Loaded:', mappingInfo);
      } else {
        console.warn('[Mapping Info] Failed to load mapping info');
      }
    } catch (error) {
      console.error('[Mapping Info] Error loading mapping info:', error);
    } finally {
      isLoadingMappingInfo = false;
    }
  }

  async function loadDistributionMode(): Promise<void> {
    try {
      const response = await fetch('/api/calibration/distribution-mode');
      
      if (response.ok) {
        const data = await response.json();
        distributionMode = data.current_mode || 'proportional';
        availableDistributionModes = data.available_modes || ['proportional', 'fixed', 'custom'];
        console.log('[Distribution] Current mode:', distributionMode, 'Available:', availableDistributionModes);
      } else {
        console.warn('[Distribution] Failed to load distribution mode');
      }
    } catch (error) {
      console.error('[Distribution] Error loading distribution mode:', error);
    }
  }

  async function changeDistributionMode(newMode: string): Promise<void> {
    try {
      const response = await fetch('/api/calibration/distribution-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode, apply_mapping: true })
      });
      
      if (response.ok) {
        const result = await response.json();
        distributionMode = newMode;
        console.log('[Distribution] Mode changed to:', newMode);
        // Refresh mapping after mode change
        await updateLedMapping();
        // Reload validation results
        await loadValidationResults();
      } else {
        console.warn('[Distribution] Failed to change distribution mode');
      }
    } catch (error) {
      console.error('[Distribution] Error changing distribution mode:', error);
    }
  }

  // Initialize on mount
  onMount(async () => {
    await loadColorsFromSettings();
    updatePianoSize();
    await loadDistributionMode();
    await loadValidationResults();
    await loadMappingInfo();
  });
</script>

<div class="calibration-section-3">
  <div class="section-intro">
    <h3>Piano LED Mapping</h3>
    <p>Visual representation of how piano keys map to LED indices with current offsets.</p>
  </div>

  <div class="visualization-container">
    <div class="visualization-controls">
      <button
        class={`btn-show-layout ${layoutVisualizationActive ? 'active' : ''}`}
        on:click={toggleLayoutVisualization}
        title={layoutVisualizationActive ? 'Turn off layout visualization' : 'Show layout with all white/black keys mapped to LEDs'}
      >
        {layoutVisualizationActive ? '✓ Layout Visible' : '🎹 Show Layout'}
      </button>

      <!-- Distribution Mode Selector -->
      <div class="distribution-mode-selector">
        <label for="dist-mode">Distribution Mode:</label>
        <select
          id="dist-mode"
          value={distributionMode}
          on:change={(e) => changeDistributionMode(e.currentTarget.value)}
          class="mode-select"
        >
          {#each availableDistributionModes as mode}
            <option value={mode}>{mode.charAt(0).toUpperCase() + mode.slice(1)}</option>
          {/each}
        </select>
      </div>

      <!-- Validation and Mapping Info Buttons -->
      <button
        class="btn-info"
        on:click={loadValidationResults}
        disabled={isLoadingValidation}
        title="Load validation results for current mapping"
      >
        {isLoadingValidation ? '⏳ Validating...' : '✓ Validate Mapping'}
      </button>
      
      <button
        class="btn-info"
        on:click={loadMappingInfo}
        disabled={isLoadingMappingInfo}
        title="Load mapping statistics"
      >
        {isLoadingMappingInfo ? '⏳ Loading...' : '📊 Mapping Info'}
      </button>
    </div>
    
    <div class="piano-keyboard">
      {#each pianoKeys as key (key.midiNote)}
        <button
          class={`piano-key ${key.isBlack ? 'black' : 'white'} ${
            selectedNote === key.midiNote ? 'selected' : ''
          } ${hoveredNote === key.midiNote ? 'hovered' : ''} ${
            key.offset !== 0 ? 'has-offset' : ''
          }`}
          on:click={(e) => {
            handleKeyPressWhileVisualizingLayout(e);
            handleKeyClick(key.midiNote);
          }}
          on:mouseenter={() => handleKeyHover(key.midiNote)}
          on:mouseleave={() => handleKeyHover(null)}
          title={`${key.noteName} (MIDI ${key.midiNote})`}
        >
          <div class="key-content">
            {#if key.adjustedLedIndices && key.adjustedLedIndices.length > 0}
              <span class="key-display">
                {key.noteName} LED {key.adjustedLedIndices[0]}
                {#if key.adjustedLedIndices.length > 1}
                  -{key.adjustedLedIndices[key.adjustedLedIndices.length - 1]}
                {/if}
              </span>
            {:else}
              <span class="key-display">—</span>
            {/if}
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
            on:click={async () => {
              selectedNote = null;
              await turnOffAllLeds();
            }}
            title="Close"
          >
            ×
          </button>
        </div>

        <div class="details-content">
          {#if ledMapping[selectedNote] && ledMapping[selectedNote].length > 0}
            <div class="detail-row">
              <span class="detail-label">LED Indices (with offsets):</span>
              <span class="detail-value">
                {#if ledMapping[selectedNote].length === 1}
                  {ledMapping[selectedNote][0]}
                {:else}
                  {ledMapping[selectedNote][0]} to {ledMapping[selectedNote][ledMapping[selectedNote].length - 1]}
                {/if}
              </span>
              <button
                class="btn-add-offset"
                on:click={() => selectedNote !== null && openAddOffsetForm(selectedNote)}
                title="Add individual offset for this key"
              >
                ➕ Add Offset
              </button>
            </div>
          {:else}
            <p class="no-data">No LED mapping available for this key</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Validation Results Panel -->
  {#if showValidationPanel && validationResults}
    <div class="validation-panel">
      <div class="panel-header">
        <h4>Validation Results</h4>
        <button class="btn-close" on:click={() => (showValidationPanel = false)}>×</button>
      </div>
      <div class="panel-content">
        {#if validationResults.warnings && validationResults.warnings.length > 0}
          <div class="warnings-section">
            <h5>⚠️ Warnings:</h5>
            <ul>
              {#each validationResults.warnings as warning}
                <li>{warning}</li>
              {/each}
            </ul>
          </div>
        {/if}
        
        {#if validationResults.recommendations && validationResults.recommendations.length > 0}
          <div class="recommendations-section">
            <h5>💡 Recommendations:</h5>
            <ul>
              {#each validationResults.recommendations as rec}
                <li>{rec}</li>
              {/each}
            </ul>
          </div>
        {/if}
        
        {#if validationResults.statistics}
          <div class="stats-section">
            <h5>📈 Statistics:</h5>
            <div class="stats-grid">
              {#each Object.entries(validationResults.statistics) as [key, value]}
                <div class="stat-item">
                  <span class="stat-label">{key.replace(/_/g, ' ')}:</span>
                  <span class="stat-value">{value}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Mapping Info Panel -->
  {#if showMappingInfo && mappingInfo}
    <div class="mapping-info-panel">
      <div class="panel-header">
        <h4>Mapping Information</h4>
        <button class="btn-close" on:click={() => (showMappingInfo = false)}>×</button>
      </div>
      <div class="panel-content">
        {#if mappingInfo.statistics}
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Total Keys Mapped:</span>
              <span class="info-value">{mappingInfo.statistics.total_keys_mapped}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Piano Size:</span>
              <span class="info-value">{mappingInfo.statistics.piano_size}</span>
            </div>
            <div class="info-item">
              <span class="info-label">LED Count:</span>
              <span class="info-value">{mappingInfo.statistics.led_count}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Distribution Mode:</span>
              <span class="info-value">{mappingInfo.statistics.distribution_mode}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Base Offset:</span>
              <span class="info-value">{mappingInfo.statistics.base_offset || 0}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Efficiency:</span>
              <span class="info-value">{((mappingInfo.statistics.total_keys_mapped / (mappingInfo.statistics.piano_size || 88)) * 100).toFixed(1)}%</span>
            </div>
          </div>
        {/if}
        
        {#if mappingInfo.distribution_breakdown}
          <div class="distribution-section">
            <h5>LED Distribution Breakdown:</h5>
            <div class="distribution-items">
              {#each Object.entries(mappingInfo.distribution_breakdown) as [ledCount, keyCount]}
                <div class="distribution-item">
                  <span class="dist-label">{ledCount} LEDs:</span>
                  <span class="dist-value">{keyCount} keys</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

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
    <div class="legend-divider"></div>
    
    <!-- Color Pickers -->
    <div class="legend-color-pickers">
      <div class="color-picker-group">
        <label for="white-key-color-legend">White Key:</label>
        <input
          id="white-key-color-legend"
          type="color"
          value="#{WHITE_KEY_COLOR.r.toString(16).padStart(2, '0')}{WHITE_KEY_COLOR.g.toString(16).padStart(2, '0')}{WHITE_KEY_COLOR.b.toString(16).padStart(2, '0')}"
          on:change={(e) => {
            const hex = e.currentTarget.value.slice(1);
            WHITE_KEY_COLOR = {
              r: parseInt(hex.slice(0, 2), 16),
              g: parseInt(hex.slice(2, 4), 16),
              b: parseInt(hex.slice(4, 6), 16)
            };
            console.log('[LED] White key color changed:', WHITE_KEY_COLOR);
          }}
          title="Select white key LED color"
        />
      </div>
      
      <div class="color-picker-group">
        <label for="black-key-color-legend">Black Key:</label>
        <input
          id="black-key-color-legend"
          type="color"
          value="#{BLACK_KEY_COLOR.r.toString(16).padStart(2, '0')}{BLACK_KEY_COLOR.g.toString(16).padStart(2, '0')}{BLACK_KEY_COLOR.b.toString(16).padStart(2, '0')}"
          on:change={(e) => {
            const hex = e.currentTarget.value.slice(1);
            BLACK_KEY_COLOR = {
              r: parseInt(hex.slice(0, 2), 16),
              g: parseInt(hex.slice(2, 4), 16),
              b: parseInt(hex.slice(4, 6), 16)
            };
            console.log('[LED] Black key color changed:', BLACK_KEY_COLOR);
          }}
          title="Select black key LED color"
        />
      </div>
    </div>
  </div>

  <!-- Info -->
  <div class="info-box">
    <p>
      <strong>Piano Size:</strong> {currentPianoSize}
    </p>
    <p>
      <strong>Total Keys:</strong> {pianoKeyCount} ({getMidiNoteName(startMidiNote)} - {getMidiNoteName(startMidiNote + pianoKeyCount - 1)})
    </p>
    <p>
      <strong>Keys with Custom Offsets:</strong> {Object.keys($calibrationState.key_offsets).length}
    </p>
    <p>
      <strong>LED Range:</strong> {$calibrationState.start_led} — {$calibrationState.end_led}
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

  .visualization-controls {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .btn-show-layout {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border: 2px solid #1e40af;
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-show-layout:hover {
    background: linear-gradient(135deg, #2563eb, #1e40af);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  }

  .btn-show-layout.active {
    background: linear-gradient(135deg, #10b981, #059669);
    border-color: #047857;
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
  }

  .btn-show-layout:active {
    transform: translateY(0);
  }

  .distribution-mode-selector {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .distribution-mode-selector label {
    font-size: 0.95rem;
    font-weight: 600;
    color: #1f2937;
  }

  .mode-select {
    padding: 0.5rem 0.75rem;
    border: 2px solid #cbd5e1;
    border-radius: 6px;
    background: white;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .mode-select:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
  }

  .mode-select:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .btn-info {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed);
    border: 2px solid #6d28d9;
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-info:hover:not(:disabled) {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
  }

  .btn-info:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-info:active:not(:disabled) {
    transform: translateY(0);
  }

  .validation-panel,
  .mapping-info-panel {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
  }

  .panel-header {
    background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
    padding: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #cbd5e1;
  }

  .panel-header h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1e293b;
  }

  .btn-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #64748b;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;
  }

  .btn-close:hover {
    background: rgba(100, 116, 139, 0.1);
    color: #334155;
  }

  .panel-content {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .warnings-section,
  .recommendations-section,
  .distribution-section {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .warnings-section h5,
  .recommendations-section h5,
  .stats-section h5,
  .distribution-section h5 {
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: #1e293b;
  }

  .warnings-section ul,
  .recommendations-section ul {
    margin: 0;
    padding-left: 1.5rem;
    list-style: none;
  }

  .warnings-section li,
  .recommendations-section li {
    margin: 0.25rem 0;
    color: #475569;
    font-size: 0.9rem;
    position: relative;
  }

  .warnings-section li:before {
    content: '⚠️ ';
    position: absolute;
    left: -1.5rem;
  }

  .recommendations-section li:before {
    content: '✓ ';
    position: absolute;
    left: -1.5rem;
    color: #10b981;
  }

  .stats-grid,
  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .stat-item,
  .info-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.75rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
  }

  .stat-label,
  .info-label {
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
  }

  .stat-value,
  .info-value {
    font-size: 1rem;
    font-weight: 600;
    color: #1e293b;
  }

  .distribution-items {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .distribution-item {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 0.9rem;
  }

  .dist-label {
    font-weight: 600;
    color: #475569;
  }

  .dist-value {
    color: #1e293b;
    font-weight: 700;
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
    align-items: flex-end;
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
    padding: 0.5rem 0.08rem;
    font-size: 0.6rem;
    flex: 1;
    min-width: 0;
    position: relative;
    background: none;
  }

  .piano-key.white {
    background: linear-gradient(to bottom, #ffffff, #f1f5f9);
    color: #0f172a;
    height: 180px;
  }

  .piano-key.black {
    background: linear-gradient(to bottom, #1e293b, #0f172a);
    color: #ffffff;
    height: 90px;
    margin: 0 -8px 0 -8px;
    z-index: 10;
    align-self: flex-start;
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

  .piano-key.selected.white {
    background: linear-gradient(to bottom, rgb(0, 100, 150), rgb(0, 85, 127));
    color: #ffffff;
  }

  .piano-key.selected.black {
    background: linear-gradient(to bottom, rgb(150, 0, 100), rgb(127, 0, 85));
    color: #ffffff;
  }

  .piano-key.has-offset {
    border-color: #10b981;
    border-width: 2px;
  }

  .key-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 0.25rem;
    text-align: center;
    width: 100%;
    height: 100%;
    padding-bottom: 1.3rem;
  }

  .key-display {
    font-weight: 600;
    font-size: 0.45rem;
    white-space: nowrap;
    transform: rotate(-90deg);
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 120px;
    line-height: 1.1;
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

  .btn-add-offset {
    background: linear-gradient(135deg, #10b981, #059669);
    border: none;
    color: white;
    padding: 0.4rem 0.8rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  .btn-add-offset:hover {
    background: linear-gradient(135deg, #059669, #047857);
    transform: scale(1.02);
  }

  .btn-add-offset:active {
    transform: scale(0.98);
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
    align-items: center;
    justify-content: flex-start;
  }

  .legend-divider {
    width: 1px;
    height: 30px;
    background: #cbd5e1;
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

  /* Color samples for layout visualization */
  .legend-item.color-sample {
    padding: 0.5rem;
    border-radius: 6px;
  }

  .legend-item.color-sample.white-key {
    background: linear-gradient(135deg, rgb(0, 100, 150), rgb(0, 85, 127));
    border: 2px solid #0c4a6e;
  }

  .legend-item.color-sample.white-key span {
    color: #ffffff;
  }

  .legend-item.color-sample.black-key {
    background: linear-gradient(135deg, rgb(150, 0, 100), rgb(127, 0, 85));
    border: 2px solid #7c1d5e;
  }

  .legend-item.color-sample.black-key span {
    color: #ffffff;
  }

  .legend-item span {
    font-size: 0.9rem;
    color: #0f172a;
  }

  .legend-color-pickers {
    display: flex;
    gap: 1rem;
    flex-wrap: nowrap;
    align-items: center;
  }

  .legend-color-pickers .color-picker-group {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.4rem;
    white-space: nowrap;
  }

  .legend-color-pickers .color-picker-group label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0;
  }

  .legend-color-pickers .color-picker-group input[type="color"] {
    width: 56px;
    height: 40px;
    border: 2px solid #cbd5e1;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
  }

  .legend-color-pickers .color-picker-group input[type="color"]:hover {
    border-color: #64748b;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  }

  .legend-color-pickers .color-picker-group input[type="color"]:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
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
      flex: 1;
      min-width: 0;
    }

    .piano-key.white {
      height: 130px;
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
      flex: 1;
      min-width: 0;
      padding: 0.25rem 0.06rem;
    }

    .piano-key.white {
      height: 110px;
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

  .color-selectors {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .color-picker-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .color-picker-group label {
    font-size: 0.9rem;
    font-weight: 600;
    color: #1e293b;
  }

  .color-picker-input {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .color-picker-input input[type="color"] {
    width: 60px;
    height: 40px;
    border: 2px solid #cbd5e1;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .color-picker-input input[type="color"]:hover {
    border-color: #64748b;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .color-picker-input input[type="color"]:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .color-label {
    font-size: 0.85rem;
    color: #64748b;
    font-family: 'Monaco', 'Courier New', monospace;
    background: #f1f5f9;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
</style>
