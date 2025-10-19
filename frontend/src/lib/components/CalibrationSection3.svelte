<script lang="ts">
  import { settings } from '$lib/stores/settings';
  import { calibrationState, calibrationUI, getKeyLedMappingWithRange, getKeyLedMappingFromPhysicalAnalysis, keyOffsetsList, getMidiNoteName, setKeyOffset, deleteKeyOffset } from '$lib/stores/calibration';
  import { ledSelectionState, ledSelectionAPI } from '$lib/stores/ledSelection';
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

  // LED range info for coverage determination
  let ledRangeStart = 0;
  let ledRangeEnd = 245;
  let totalLedCount = 246;

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

  // Advanced physics parameters
  interface PhysicsParameters {
    white_key_width: number;
    black_key_width: number;
    white_key_gap: number;
    led_physical_width: number;
    overhang_threshold_mm: number;
  }

  interface ParameterRange {
    min: number;
    max: number;
    default: number;
  }

  let physicsParameters: PhysicsParameters = {
    white_key_width: 22.0,
    black_key_width: 12.0,
    white_key_gap: 1.0,
    led_physical_width: 2.0,
    overhang_threshold_mm: 1.5
  };

  let parameterRanges: Record<string, ParameterRange> = {
    white_key_width: { min: 18.5, max: 28.5, default: 22.0 },
    black_key_width: { min: 10.0, max: 20.0, default: 12.0 },
    white_key_gap: { min: 0.0, max: 3.0, default: 1.0 },
    led_physical_width: { min: 1.0, max: 10.0, default: 2.0 },
    overhang_threshold_mm: { min: 0.5, max: 5.0, default: 1.5 }
  };

  let parameterDisplayNames: Record<string, string> = {
    white_key_width: 'White Key Width (mm)',
    black_key_width: 'Black Key Width (mm)',
    white_key_gap: 'Key Gap (mm)',
    led_physical_width: 'LED Width (mm)',
    overhang_threshold_mm: 'Overhang Threshold (mm)'
  };

  let isLoadingPhysicsParams = false;
  let isSavingPhysicsParams = false;
  let physicsParamsChanged = false;
  let pitchCalibrationInfo: any = null;

  async function loadPhysicsParameters(): Promise<void> {
    try {
      const response = await fetch('/api/calibration/physics-parameters');
      if (response.ok) {
        const data = await response.json();
        console.log('[Physics] Full GET response:', data);
        physicsParameters = data.physics_parameters;
        // Merge backend ranges with local ranges, preferring frontend values
        if (data.parameter_ranges) {
          parameterRanges = { ...data.parameter_ranges, ...parameterRanges };
        }
        // Load pitch calibration info if available
        if (data.pitch_calibration_info) {
          pitchCalibrationInfo = data.pitch_calibration_info;
          console.log('[Physics] Pitch calibration info loaded from GET:', pitchCalibrationInfo);
        } else {
          console.log('[Physics] No pitch_calibration_info in GET response. Data keys:', Object.keys(data));
        }
        physicsParamsChanged = false;
        console.log('[Physics] Parameters loaded:', physicsParameters);
      } else {
        console.error('[Physics] GET failed, status:', response.status);
      }
    } catch (error) {
      console.error('[Physics] Error loading parameters:', error);
    }
  }

  async function savePhysicsParameters(regenerateMapping: boolean = false): Promise<void> {
    isSavingPhysicsParams = true;
    try {
      const response = await fetch('/api/calibration/physics-parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...physicsParameters,
          apply_mapping: true  // Always regenerate mapping when parameters change
        })
      });

      if (response.ok) {
        const result = await response.json();
        physicsParamsChanged = false;
        
        console.log('[Physics] Response received:', result);
        
        // Always update LED mapping to reflect parameter changes in the visualization
        await updateLedMapping();
        pianoKeys = generatePianoKeys();
        
        // Capture pitch calibration info if available
        if (result.pitch_calibration_info) {
          pitchCalibrationInfo = result.pitch_calibration_info;
          console.log('[Physics] Pitch calibration info captured:', pitchCalibrationInfo);
          console.log('[Physics] Pitch was adjusted:', pitchCalibrationInfo.was_adjusted);
        } else {
          console.log('[Physics] No pitch_calibration_info in response');
          pitchCalibrationInfo = null;
        }
        console.log('[Physics] Parameters saved and visualization updated');
      } else {
        console.error('[Physics] Failed to save parameters, status:', response.status);
        const errorData = await response.json().catch(() => null);
        console.error('[Physics] Error response:', errorData);
      }
    } catch (error) {
      console.error('[Physics] Error saving parameters:', error);
    } finally {
      isSavingPhysicsParams = false;
    }
  }

  function resetPhysicsParameters(): void {
    physicsParameters = {
      white_key_width: 22.0,
      black_key_width: 12.0,
      white_key_gap: 1.0,
      led_physical_width: 2.0,
      overhang_threshold_mm: 1.5
    };
    physicsParamsChanged = true;
  }

  // Individual Key Offsets Management
  let editingKeyNote: number | null = null;
  let editingKeyOffset = 0;
  let newKeyMidiNote = '';
  let newKeyOffset = 0;
  let showAddForm = false;

  // LED Selection for Individual Keys
  let selectedLEDsForNewKey: Set<number> = new Set();
  let availableLEDsForForm: number[] = [];
  let showLEDGrid = false;
  let currentKeyLEDAllocation: number[] = []; // Currently assigned LEDs for the selected key
  let allKeysLEDMapping: Record<number, number[]> = {}; // All keys' LED allocations
  let lastInitializedMidiNote: number | null = null; // Track which MIDI note we last initialized for

  function startEditingKeyOffset(midiNote: number, offset: number) {
    editingKeyNote = midiNote;
    editingKeyOffset = offset;
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
    selectedLEDsForNewKey = new Set();
    showLEDGrid = false;
    showAddForm = false;
    lastInitializedMidiNote = null;
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
      // Calculate LED trims based on the original vs modified allocation
      let leftTrim = 0;
      let rightTrim = 0;
      
      if (currentKeyLEDAllocation.length > 0 && selectedLEDsForNewKey.size > 0) {
        // Calculate left trim (how many LEDs removed from the left)
        for (let i = 0; i < currentKeyLEDAllocation.length; i++) {
          if (!selectedLEDsForNewKey.has(currentKeyLEDAllocation[i])) {
            leftTrim++;
          } else {
            break; // Stop counting when we hit a selected LED
          }
        }
        
        // Calculate right trim (how many LEDs removed from the right)
        for (let i = currentKeyLEDAllocation.length - 1; i >= 0; i--) {
          if (!selectedLEDsForNewKey.has(currentKeyLEDAllocation[i])) {
            rightTrim++;
          } else {
            break; // Stop counting when we hit a selected LED
          }
        }
      }
      
      // Save offset and trims in a single API call
      console.log(`[Key Adjustment] MIDI ${midiNote}: offset=${newKeyOffset}, left_trim=${leftTrim}, right_trim=${rightTrim}`);
      await calibrationService.setKeyOffset(midiNote, newKeyOffset, leftTrim, rightTrim);
      
      resetAddForm();
      calibrationUI.update(ui => ({ ...ui, success: `Key adjustment added for ${getMidiNoteName(midiNote)}` }));
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, success: null }));
      }, 2000);
    } catch (error) {
      console.error('Failed to add key offset:', error);
    }
  }

  function handleMidiNoteInput(midiNoteStr: string) {
    newKeyMidiNote = midiNoteStr;
    const midiNote = parseInt(midiNoteStr, 10);
    
    if (Number.isFinite(midiNote) && midiNote >= 0 && midiNote <= 127) {
      // Initialize available LEDs based on valid range
      let [start, end] = $ledSelectionState.validLEDRange;
      
      // Fallback to default range if undefined
      if (!start || !end || start < 0 || end < start) {
        start = 4;
        end = 249;
      }
      
      availableLEDsForForm = Array.from({ length: end - start + 1 }, (_, i) => start + i);
      console.log(`[handleMidiNoteInput] MIDI ${midiNote}: validLEDRange=${start}-${end}, availableLEDsForForm.length=${availableLEDsForForm.length}`);
      
      // Load currently assigned LEDs for this key
      currentKeyLEDAllocation = ledMapping[midiNote] ?? [];
      console.log(`[handleMidiNoteInput] MIDI ${midiNote}: currentKeyLEDAllocation=[${currentKeyLEDAllocation.join(',')}]`);
      console.log(`[handleMidiNoteInput] Full ledMapping keys:`, Object.keys(ledMapping).map(k => `${k}:[${ledMapping[parseInt(k,10)].join(',')}]`));
      
      // Load existing override for this key if any
      const existingOverride = $ledSelectionState.overrides[midiNote];
      if (existingOverride) {
        selectedLEDsForNewKey = new Set(existingOverride);
        console.log(`[handleMidiNoteInput] MIDI ${midiNote}: using existing override [${existingOverride.join(',')}]`);
      } else {
        // Pre-populate with currently assigned LEDs if no override exists
        selectedLEDsForNewKey = new Set(currentKeyLEDAllocation);
        console.log(`[handleMidiNoteInput] MIDI ${midiNote}: using current allocation [${currentKeyLEDAllocation.join(',')}]`);
      }
    } else {
      console.log(`[handleMidiNoteInput] Invalid MIDI note: "${midiNoteStr}"`);
    }
  }

  // Ensure LED allocation is populated when checkbox is checked (only initialize once per MIDI note)
  $: if (showLEDGrid && newKeyMidiNote) {
    const midiNote = parseInt(newKeyMidiNote, 10);
    // Only initialize if we haven't already initialized this MIDI note
    if (Number.isFinite(midiNote) && midiNote >= 0 && midiNote <= 127 && lastInitializedMidiNote !== midiNote) {
      currentKeyLEDAllocation = ledMapping[midiNote] ?? [];
      // Initialize selectedLEDsForNewKey with all current allocations (default to green/ON)
      selectedLEDsForNewKey = new Set(currentKeyLEDAllocation);
      lastInitializedMidiNote = midiNote;
      console.log(`[Reactive] Initialized for MIDI ${midiNote}: currentKeyLEDAllocation=[${currentKeyLEDAllocation.join(',')}], selectedLEDs=[${Array.from(selectedLEDsForNewKey).join(',')}]`);
    }
  }

  function toggleLED(ledIndex: number) {
    if (selectedLEDsForNewKey.has(ledIndex)) {
      selectedLEDsForNewKey.delete(ledIndex);
    } else {
      selectedLEDsForNewKey.add(ledIndex);
    }
    selectedLEDsForNewKey = selectedLEDsForNewKey; // Trigger reactivity
  }

  function handleReallocateLED(ledIndex: number) {
    // When clicking an assigned LED, remove it and reallocate to adjacent key
    const midiNote = parseInt(newKeyMidiNote, 10);
    
    if (!selectedLEDsForNewKey.has(ledIndex)) {
      return; // LED not currently selected, ignore
    }

    // Remove LED from current key
    selectedLEDsForNewKey.delete(ledIndex);
    selectedLEDsForNewKey = selectedLEDsForNewKey;

    // Determine which adjacent key to add it to
    // If LED index is on left side of range, add to previous key
    // If LED index is on right side of range, add to next key
    const currentRange = currentKeyLEDAllocation;
    const midpoint = currentRange.length > 0 
      ? (currentRange[0] + currentRange[currentRange.length - 1]) / 2
      : ledIndex;

    const targetMidi = ledIndex < midpoint ? midiNote - 1 : midiNote + 1;

    // Only reallocate if target MIDI is valid
    if (targetMidi >= 0 && targetMidi <= 127) {
      // Show feedback that LED will be reallocated
      calibrationUI.update(ui => ({
        ...ui,
        info: `LED ${ledIndex} reallocated to ${getMidiNoteName(targetMidi)}`
      }));
      
      setTimeout(() => {
        calibrationUI.update(ui => ({ ...ui, info: null }));
      }, 2000);
    }
  }

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

  function isBlackKey(midiNote: number): boolean {
    const noteIndex = midiNote % 12;
    return [1, 3, 6, 8, 10].includes(noteIndex);
  }

  /**
   * Determine if a key is covered by the LED range.
   * A key is covered if the range [start_led, end_led] includes the LED indices that would be
   * assigned to this key. If end_led >= the maximum LED index needed for the last piano key,
   * then all piano keys are covered.
   */
  function isKeyCovered(midiNote: number): boolean {
    // If the key has explicit LED indices, it's covered
    const indices = ledMapping[midiNote];
    if (indices && indices.length > 0) {
      return true;
    }
    
    // Otherwise, a key is NOT covered if the mapping is empty for it.
    // This means the backend already determined it's outside the valid range.
    return false;
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
      // Fetch the LED mapping from key-led-mapping endpoint (the proven working endpoint)
      const { mapping, start_led, end_led, led_count } = await getKeyLedMappingWithRange();
      ledMapping = mapping;
      ledRangeStart = start_led;
      ledRangeEnd = end_led;
      totalLedCount = led_count;
      
      console.log(`[CalibrationSection3] updateLedMapping() - Received: start_led=${start_led}, end_led=${end_led}, led_count=${led_count}`);
      
      // Debug logging
      const coveredKeys = Object.keys(mapping).length;
      const uncoveredKeys = pianoKeyCount - coveredKeys;
      const mappedMidiNotes = Object.keys(mapping).map(k => parseInt(k, 10)).sort((a,b) => a - b);
      const firstKey = startMidiNote;
      const lastKey = startMidiNote + pianoKeyCount - 1;
      const firstMapped = mappedMidiNotes[0];
      const lastMapped = mappedMidiNotes[mappedMidiNotes.length - 1];
      
      console.log(`[CalibrationSection3] LED Range: ${start_led}-${end_led} (total: ${led_count})`);
      console.log(`[CalibrationSection3] Piano: ${pianoKeyCount} keys (MIDI ${firstKey}-${lastKey})`);
      console.log(`[CalibrationSection3] Mapping: ${coveredKeys} keys with LEDs, ${uncoveredKeys} keys without LEDs`);
      console.log(`[CalibrationSection3] Mapped keys: MIDI ${firstMapped}-${lastMapped}`);
      if (lastMapped < lastKey) {
        console.log(`[CalibrationSection3] ⚠️ Missing keys: ${lastKey - lastMapped} keys at end (MIDI ${lastMapped + 1}-${lastKey})`);
      }
      
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

  // Track previous LED range to detect changes
  let prevStartLed: number | undefined = undefined;
  let prevEndLed: number | undefined = undefined;

  // Update when settings or calibration changes
  $: if ($settings && $calibrationState) {
    updatePianoSize();
    loadColorsFromSettings();
  }

  // Refresh LED mapping when LED range selection changes (detects actual changes, not initial load)
  $: if ($calibrationState?.start_led !== undefined && $calibrationState?.end_led !== undefined) {
    if (prevStartLed !== $calibrationState.start_led || prevEndLed !== $calibrationState.end_led) {
      prevStartLed = $calibrationState.start_led;
      prevEndLed = $calibrationState.end_led;
      console.log(`[CalibrationSection3] LED range changed: ${prevStartLed}-${prevEndLed}, refreshing mapping...`);
      updateLedMapping();
    }
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
    // Set form values and open the add offset form in the Individual Key Offsets section
    newKeyMidiNote = midiNote.toString();
    newKeyOffset = 0;
    showAddForm = true;
    showLEDGrid = false; // Let user manually check to customize LEDs if needed
    
    // Trigger the reactive statement to populate LED allocations
    lastInitializedMidiNote = null;
    
    // Scroll to the Individual Key Offsets section
    const offsetsSection = document.querySelector('.per-key-offsets-container');
    if (offsetsSection) {
      offsetsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    console.log(`[Offsets] Opening form to add offset for MIDI note ${midiNote} (${getMidiNoteName(midiNote)})`);
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
        distributionMode = data.current_mode || 'Piano Based (with overlap)';
        availableDistributionModes = data.available_modes || [
          'Piano Based (with overlap)',
          'Piano Based (no overlap)',
          'Custom'
        ];
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
      console.log('[Distribution] Changing mode to:', newMode);
      
      const response = await fetch('/api/calibration/distribution-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode, apply_mapping: true })
      });
      
      if (response.ok) {
        const result = await response.json();
        distributionMode = newMode;
        console.log('[Distribution] Mode changed to:', newMode);
        console.log('[Distribution] Mapping stats:', result.mapping_stats);
        
        // Immediately update LED mapping to reflect new distribution
        await updateLedMapping();
        
        // Update piano key visualization
        pianoKeys = generatePianoKeys();
        
        console.log('[Distribution] Visualization updated with new distribution');
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
    // Load physics parameters if using physics-based mode
    if (distributionMode === 'Physics-Based LED Detection') {
      await loadPhysicsParameters();
    }
    // Mapping is now auto-updated when distribution mode changes
    // No need to load validation/mapping info on mount
  });
</script>

<div class="calibration-section-3">
  <div class="section-intro">
    <h3>Piano LED Mapping</h3>
    <p>Visual representation of how piano keys map to LED indices with current offsets.</p>
  </div>

  <div class="visualization-container">
    <div class="visualization-controls">
      <!-- Distribution Mode Selector (PRIMARY CONTROL) -->
      <div class="distribution-mode-selector">
        <label for="dist-mode">Distribution Mode:</label>
        <select
          id="dist-mode"
          value={distributionMode}
          on:change={(e) => changeDistributionMode(e.currentTarget.value)}
          class="mode-select"
          title="Select how LEDs are distributed across piano keys"
        >
          {#each availableDistributionModes as mode}
            <option value={mode}>{mode}</option>
          {/each}
        </select>
      </div>

      <!-- Layout Visualization Button -->
      <button
        class={`btn-show-layout ${layoutVisualizationActive ? 'active' : ''}`}
        on:click={toggleLayoutVisualization}
        title={layoutVisualizationActive ? 'Turn off layout visualization' : 'Show layout with all white/black keys mapped to LEDs'}
      >
        {layoutVisualizationActive ? '✓ Layout Visible' : '🎹 Show Layout'}
      </button>
    </div>
    
    <div class="piano-keyboard">
      {#each pianoKeys as key (key.midiNote)}
        <button
          class={`piano-key ${key.isBlack ? 'black' : 'white'} ${
            selectedNote === key.midiNote ? 'selected' : ''
          } ${hoveredNote === key.midiNote ? 'hovered' : ''} ${
            key.offset !== 0 ? 'has-offset' : ''
          } ${isKeyCovered(key.midiNote) ? 'covered' : 'uncovered'}`}
          on:click={(e) => {
            handleKeyPressWhileVisualizingLayout(e);
            handleKeyClick(key.midiNote);
          }}
          on:mouseenter={() => handleKeyHover(key.midiNote)}
          on:mouseleave={() => handleKeyHover(null)}
          title={`${key.noteName} (MIDI ${key.midiNote})${isKeyCovered(key.midiNote) ? ' - Within LED Range' : ' - Outside LED Range'}`}
        >
          <div class="key-content">
            {#if key.adjustedLedIndices && key.adjustedLedIndices.length > 0}
              <span class="key-display">
                {key.noteName} LED {key.adjustedLedIndices[0]}
                {#if key.adjustedLedIndices.length > 1}
                  -{key.adjustedLedIndices[key.adjustedLedIndices.length - 1]}
                {/if}
              </span>
            {:else if isKeyCovered(key.midiNote)}
              <span class="key-display">{key.noteName} ✓</span>
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

  <!-- Advanced Settings (Physics-Based Mode) -->
  {#if distributionMode === 'Physics-Based LED Detection'}
    <div class="advanced-settings-section">
      <div class="advanced-settings-header">
        <h4>🔧 Advanced Physics Parameters</h4>
        <p>Fine-tune keyboard geometry for your piano model</p>
      </div>

      <div class="parameters-grid">
        {#each Object.entries(parameterDisplayNames) as [paramKey, displayName]}
          <div class="parameter-control">
            <label for={`param-${paramKey}`}>{displayName}</label>
            <div class="parameter-input-group">
              <input
                id={`param-${paramKey}`}
                type="range"
                min={parameterRanges[paramKey].min}
                max={parameterRanges[paramKey].max}
                step="0.1"
                value={physicsParameters[paramKey as keyof PhysicsParameters]}
                on:change={(e) => {
                  physicsParameters[paramKey as keyof PhysicsParameters] = parseFloat(e.currentTarget.value);
                  physicsParamsChanged = true;
                }}
                title={`${displayName} - Default: ${parameterRanges[paramKey].default}mm`}
              />
              <input
                type="number"
                min={parameterRanges[paramKey].min}
                max={parameterRanges[paramKey].max}
                step="0.1"
                value={physicsParameters[paramKey as keyof PhysicsParameters]}
                on:change={(e) => {
                  const val = parseFloat(e.currentTarget.value);
                  const range = parameterRanges[paramKey];
                  physicsParameters[paramKey as keyof PhysicsParameters] = Math.max(range.min, Math.min(range.max, val));
                  physicsParamsChanged = true;
                }}
                class="parameter-number-input"
              />
              <span class="parameter-default-hint">
                Default: {parameterRanges[paramKey].default}
              </span>
            </div>
          </div>
        {/each}

        <!-- Actual Pitch Used - Always visible -->
        <div class="parameter-control pitch-display-box">
          <div class="pitch-display-label">Actual Pitch Used</div>
          <div class="pitch-display-content">
            {#if pitchCalibrationInfo}
              <div class="pitch-value-row">
                <span class="value-label">Pitch:</span>
                <span class="value-data">{pitchCalibrationInfo.calibrated_pitch_mm?.toFixed(4)} mm</span>
              </div>
              {#if pitchCalibrationInfo.was_adjusted}
                <div class="pitch-adjustment-indicator">
                  <span class="adjustment-badge">Auto-Adjusted</span>
                </div>
              {/if}
            {:else}
              <div class="pitch-value-row">
                <span class="value-label">Loading...</span>
              </div>
            {/if}
          </div>
        </div>
      </div>

      <div class="advanced-settings-actions">
        <button
          class="btn-reset"
          on:click={resetPhysicsParameters}
          disabled={isSavingPhysicsParams}
          title="Reset all parameters to defaults"
        >
          ↻ Reset to Defaults
        </button>
        
        <div class="action-buttons">
          <button
            class="btn-apply"
            on:click={() => savePhysicsParameters(true)}
            disabled={!physicsParamsChanged || isSavingPhysicsParams}
            title="Save parameters and regenerate LED mapping"
          >
            {isSavingPhysicsParams ? '⏳ Applying...' : '✓ Apply Changes'}
          </button>
          
          <button
            class="btn-preview"
            on:click={() => savePhysicsParameters(false)}
            disabled={!physicsParamsChanged || isSavingPhysicsParams}
            title="Save parameters without regenerating mapping"
          >
            {isSavingPhysicsParams ? '⏳ Saving...' : '💾 Save Only'}
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Individual Key Adjustments -->
  <div class="per-key-offsets-container">
    <div class="offsets-header">
      <h4>
        <span class="offsets-title-icon">🔑</span>
        Per-Key Adjustments
        {#if Object.keys($keyOffsetsList).length > 0}
          <span class="badge">{Object.keys($keyOffsetsList).length}</span>
        {/if}
      </h4>
      <p class="offsets-description">Adjust timing and LED allocation for specific keys</p>
    </div>

    {#if showAddForm}
      <div class="add-offset-form">
        <div class="form-group">
          <label for="midi-note-input">MIDI Note (0-127):</label>
          <input
            id="midi-note-input"
            type="number"
            min="0"
            max="127"
            on:input={(e) => handleMidiNoteInput(e.currentTarget.value)}
            value={newKeyMidiNote}
            placeholder="e.g., 60 for Middle C"
            class="offset-input"
          />
        </div>

        <div class="form-group">
          <label for="offset-value-input">Offset (LEDs):</label>
          <input
            id="offset-value-input"
            type="number"
            step="1"
            bind:value={newKeyOffset}
            placeholder="LED offset"
            class="offset-input"
          />
        </div>

        {#if newKeyMidiNote}
          <div class="form-group">
            <label class="led-selection-label">
              <input
                type="checkbox"
                bind:checked={showLEDGrid}
              />
              Customize LED allocation for this key
            </label>
          </div>

          {#if showLEDGrid}
            <div class="led-selection-section">
              <div class="led-info">
                <span>Valid LED Range: {$ledSelectionState.validLEDRange[0]} - {$ledSelectionState.validLEDRange[1]}</span>
                <span class="led-count">Modified: {currentKeyLEDAllocation.length - selectedLEDsForNewKey.size} LED{(currentKeyLEDAllocation.length - selectedLEDsForNewKey.size) !== 1 ? 's' : ''}</span>
              </div>

              <!-- Current Allocation Display -->
              <div class="current-allocation">
                <div class="allocation-header">
                  <span class="allocation-title">Currently Assigned LEDs:</span>
                  <span class="allocation-count">{selectedLEDsForNewKey.size} LED{selectedLEDsForNewKey.size !== 1 ? 's' : ''}</span>
                </div>
                {#if currentKeyLEDAllocation.length > 0}
                  <div class="led-grid-current">
                    {#each currentKeyLEDAllocation as ledIndex (ledIndex)}
                      <button
                        class="led-button-assigned"
                        class:unassigned={!selectedLEDsForNewKey.has(ledIndex)}
                        on:click={() => {
                          const newSet = new Set(selectedLEDsForNewKey);
                          if (newSet.has(ledIndex)) {
                            newSet.delete(ledIndex);
                          } else {
                            newSet.add(ledIndex);
                          }
                          selectedLEDsForNewKey = newSet;
                          console.log(`[LED Click] MIDI ${newKeyMidiNote}: LED ${ledIndex}, selected=${selectedLEDsForNewKey.has(ledIndex)}, total=${selectedLEDsForNewKey.size}`);
                        }}
                        type="button"
                        title="Click to toggle LED {ledIndex} assignment"
                      >
                        <span>{ledIndex}</span>
                      </button>
                    {/each}
                  </div>
                {:else}
                  <p class="no-allocation">No LED allocation for this key</p>
                {/if}
              </div>

              <!-- Add Adjustment Button -->
              <div class="led-action-buttons">
                <button
                  class="btn-save-offset"
                  on:click={handleAddKeyOffset}
                  disabled={!newKeyMidiNote}
                  title="Save offset with LED customizations"
                >
                  ✓ Add Adjustment
                </button>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    {/if}

    {#if $keyOffsetsList.length > 0}
      <div class="offsets-list">
        {#each $keyOffsetsList as offsetItem (offsetItem.midiNote)}
          {@const midiNote = offsetItem.midiNote}
          {@const offset = offsetItem.offset}
          {@const hasLedOverride = $ledSelectionState.overrides[midiNote]}
          {#if editingKeyNote === midiNote}
            <div class="offset-item editing">
              <div class="offset-info">
                <span class="offset-note">{getMidiNoteName(midiNote)}</span>
                <input
                  type="number"
                  step="1"
                  bind:value={editingKeyOffset}
                  class="offset-edit-input"
                />
              </div>
              <div class="offset-actions">
                <button
                  class="btn-save"
                  on:click={saveEditingKeyOffset}
                  title="Save changes"
                >
                  ✓
                </button>
                <button
                  class="btn-cancel"
                  on:click={cancelEditingKeyOffset}
                  title="Cancel editing"
                >
                  ✕
                </button>
              </div>
            </div>
          {:else}
            <div class="offset-item">
              <div class="offset-info">
                <div class="offset-main">
                  <span class="offset-note">{getMidiNoteName(midiNote)}</span>
                  <span class="offset-value">{offset} LEDs offset</span>
                </div>
                {#if hasLedOverride}
                  <div class="led-override-badge">
                    <span>LEDs: [{hasLedOverride.join(', ')}]</span>
                  </div>
                {/if}
              </div>
              <div class="offset-actions">
                <button
                  class="btn-edit"
                  on:click={() => startEditingKeyOffset(midiNote, offset)}
                  title="Edit adjustment"
                >
                  ✎
                </button>
                <button
                  class="btn-delete"
                  on:click={() => handleDeleteKeyOffset(midiNote)}
                  title="Delete adjustment"
                >
                  🗑
                </button>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    {:else if !showAddForm}
      <p class="empty-state">
        No adjustments configured. Add one to customize timing and LED allocation for specific keys.
      </p>
    {/if}
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

  .piano-key.uncovered {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .piano-key.uncovered.white {
    background: #d1d5db;
  }

  .piano-key.uncovered.black {
    background: #6b7280;
  }

  .piano-key.covered {
    opacity: 1;
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

  /* Advanced Settings Section */
  .advanced-settings-section {
    background: linear-gradient(135deg, #f0f9ff, #f8fafc);
    border: 2px solid #3b82f6;
    border-radius: 12px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .advanced-settings-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    border-bottom: 2px solid #3b82f6;
    padding-bottom: 1rem;
  }

  .advanced-settings-header h4 {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e40af;
  }

  .advanced-settings-header p {
    margin: 0;
    font-size: 0.9rem;
    color: #475569;
  }

  .parameters-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
  }

  .parameter-control {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .parameter-control label {
    font-size: 0.9rem;
    font-weight: 600;
    color: #1e293b;
  }

  .pitch-display-label {
    font-size: 0.9rem;
    font-weight: 600;
    color: #1e293b;
  }

  .parameter-input-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .parameter-input-group input[type="range"] {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(to right, #cbd5e1, #94a3b8);
    outline: none;
    -webkit-appearance: none;
    appearance: none;
  }

  .parameter-input-group input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    cursor: pointer;
    border: 2px solid #1e40af;
    transition: all 0.2s ease;
  }

  .parameter-input-group input[type="range"]::-webkit-slider-thumb:hover {
    transform: scale(1.2);
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.5);
  }

  .parameter-input-group input[type="range"]::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    cursor: pointer;
    border: 2px solid #1e40af;
    transition: all 0.2s ease;
  }

  .parameter-input-group input[type="range"]::-moz-range-thumb:hover {
    transform: scale(1.2);
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.5);
  }

  .parameter-number-input {
    padding: 0.4rem 0.6rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #1e293b;
    background: #ffffff;
    transition: all 0.2s ease;
  }

  .parameter-number-input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .parameter-default-hint {
    font-size: 0.75rem;
    color: #64748b;
    font-style: italic;
  }

  .pitch-adjustment-box {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    border: 2px solid #fbbf24;
    border-radius: 8px;
    padding: 0.75rem;
    opacity: 0.95;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .pitch-adjustment-box.pitch-not-adjusted {
    background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
    border: 2px solid #9ca3af;
  }

  .pitch-adjustment-box label {
    font-weight: 600;
    color: #1e293b;
    font-size: 0.9rem;
  }

  .pitch-adjustment-box.pitch-not-adjusted label {
    color: #1e293b;
  }

  .pitch-display-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .pitch-status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .status-badge.adjusted {
    background: #fcd34d;
    color: #92400e;
    border: 1px solid #fbbf24;
  }

  .status-badge.not-adjusted {
    background: #d1d5db;
    color: #374151;
    border: 1px solid #9ca3af;
  }

  .pitch-values {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.8rem;
  }

  .pitch-value-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .value-label {
    font-weight: 600;
    color: #64748b;
  }

  .value-data {
    font-weight: 700;
    color: #1e293b;
    font-family: 'Courier New', monospace;
  }

  .advanced-settings-actions {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: center;
    border-top: 1px solid #cbd5e1;
    padding-top: 1rem;
  }

  .action-buttons {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
  }

  .btn-reset {
    background: #f1f5f9;
    border: 2px solid #94a3b8;
    color: #1e293b;
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-reset:hover:not(:disabled) {
    background: #e2e8f0;
    border-color: #64748b;
    transform: translateY(-2px);
  }

  .btn-reset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-apply {
    background: linear-gradient(135deg, #10b981, #059669);
    border: 2px solid #047857;
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-apply:hover:not(:disabled) {
    background: linear-gradient(135deg, #059669, #047857);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  }

  .btn-apply:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-preview {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border: 2px solid #b45309;
    color: white;
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-preview:hover:not(:disabled) {
    background: linear-gradient(135deg, #d97706, #b45309);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
  }

  .btn-preview:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .preview-stats {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    padding: 1rem;
    margin-top: 0.5rem;
  }

  .preview-stats p {
    margin: 0 0 0.5rem 0;
    font-weight: 600;
    color: #166534;
    font-size: 0.9rem;
  }

  .preview-stats ul {
    margin: 0;
    padding-left: 1.5rem;
    list-style: disc;
  }

  .preview-stats li {
    color: #16a34a;
    font-size: 0.85rem;
    line-height: 1.4;
  }

  @media (max-width: 768px) {
    .parameters-grid {
      grid-template-columns: 1fr;
    }

    .advanced-settings-actions {
      flex-direction: column;
    }

    .action-buttons {
      width: 100%;
      flex-direction: column;
    }

    .btn-reset,
    .btn-apply,
    .btn-preview {
      width: 100%;
    }
  }

  /* Individual Key Offsets Styles */
  .per-key-offsets-container {
    background: linear-gradient(135deg, rgba(102, 187, 106, 0.05), rgba(76, 175, 80, 0.05));
    border: 2px solid #a5d6a7;
    border-radius: 10px;
    padding: 1.5rem;
    margin: 1.5rem 0;
  }

  .offsets-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .offsets-header h4 {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #1b5e20;
    font-size: 1.1rem;
  }

  .offsets-title-icon {
    font-size: 1.3rem;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #2e7d32;
    color: white;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .btn-add-offset {
    background: #66bb6a;
    border: 2px solid #43a047;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-add-offset:hover {
    background: #43a047;
    transform: translateY(-2px);
  }

  .add-offset-form {
    background: white;
    border: 1px solid #c8e6c9;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    flex: 1;
    min-width: 120px;
  }

  .form-group label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #2e7d32;
  }

  .offset-input {
    padding: 0.5rem 0.75rem;
    border: 1px solid #81c784;
    border-radius: 4px;
    font-size: 0.9rem;
    background: white;
    color: #1b5e20;
  }

  .offset-input:focus {
    outline: none;
    border-color: #2e7d32;
    box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.1);
  }

  .btn-save-offset {
    background: #2e7d32;
    border: none;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  .btn-save-offset:hover:not(:disabled) {
    background: #1b5e20;
    transform: translateY(-2px);
  }

  .btn-save-offset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .offsets-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .offset-item {
    background: white;
    border: 1px solid #c8e6c9;
    border-radius: 6px;
    padding: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.2s ease;
  }

  .offset-item:hover {
    border-color: #66bb6a;
    box-shadow: 0 2px 8px rgba(102, 187, 106, 0.15);
  }

  .offset-info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex: 1;
  }

  .offset-main {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .offset-note {
    font-weight: 700;
    color: #1b5e20;
    min-width: 60px;
  }

  .offset-value {
    color: #558b2f;
    font-size: 0.9rem;
  }

  .led-override-badge {
    background: #e8f5e9;
    border-left: 3px solid #66bb6a;
    padding: 0.5rem 0.75rem;
    border-radius: 3px;
    font-size: 0.8rem;
    color: #2e7d32;
    font-family: monospace;
    overflow-x: auto;
  }

  .offsets-description {
    margin: 0;
    color: #666;
    font-size: 0.85rem;
  }

  .offset-item.editing {
    background: #f1f8e9;
    border-color: #2e7d32;
  }

  .offset-edit-input {
    padding: 0.4rem 0.6rem;
    border: 1px solid #2e7d32;
    border-radius: 4px;
    font-family: monospace;
    color: #1b5e20;
    background: white;
    min-width: 80px;
  }

  .offset-edit-input:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.2);
  }

  /* LED Selection Styles */
  .led-selection-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
    color: #1b5e20;
  }

  .led-selection-label input[type='checkbox'] {
    cursor: pointer;
    width: 18px;
    height: 18px;
  }

  .led-selection-section {
    background: #f1f8e9;
    border: 1px solid #c8e6c9;
    border-radius: 6px;
    padding: 1rem;
    gap: 0.75rem;
  }

  .led-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85rem;
    color: #558b2f;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #c8e6c9;
  }

  .led-count {
    font-weight: 600;
    color: #2e7d32;
  }

  /* Current Allocation Section */
  .current-allocation {
    background: white;
    border: 2px solid #81c784;
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .allocation-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #66bb6a;
  }

  .allocation-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: #1b5e20;
  }

  .allocation-count {
    background: #c8e6c9;
    color: #1b5e20;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .led-grid-current {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(45px, 1fr));
    gap: 6px;
    margin-bottom: 0.75rem;
  }

  .led-action-buttons {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid #c8e6c9;
  }

  .led-button-assigned {
    aspect-ratio: 1 / 1;
    border: 2px solid #66bb6a;
    border-radius: 6px;
    background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%);
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 4px rgba(102, 187, 106, 0.3);
  }

  .led-button-assigned:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 8px rgba(102, 187, 106, 0.4);
  }

  .led-button-assigned.unassigned {
    background: linear-gradient(135deg, #bdbdbd 0%, #9e9e9e 100%);
    border-color: #757575;
    box-shadow: 0 2px 4px rgba(93, 93, 93, 0.3);
  }

  .led-button-assigned.unassigned:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 8px rgba(93, 93, 93, 0.4);
  }

  .allocation-hint {
    margin: 0;
    font-size: 0.75rem;
    color: #558b2f;
    font-style: italic;
  }

  .no-allocation {
    margin: 0;
    padding: 0.75rem;
    font-size: 0.85rem;
    color: #666;
    background: #f5f5f5;
    border-radius: 4px;
    text-align: center;
    font-style: italic;
  }

  .full-grid-header {
    font-size: 0.85rem;
    font-weight: 600;
    color: #2e7d32;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px dashed #81c784;
  }

  .led-grid-compact {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(35px, 1fr));
    gap: 4px;
    margin-bottom: 0.75rem;
  }

  .led-button-compact {
    aspect-ratio: 1 / 1;
    border: 2px solid #81c784;
    border-radius: 4px;
    background: white;
    color: #558b2f;
    font-size: 0.65rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .led-button-compact:hover {
    background: #e8f5e9;
    border-color: #66bb6a;
    transform: scale(1.05);
  }

  .led-button-compact.selected {
    background: #66bb6a;
    color: white;
    border-color: #2e7d32;
  }

  .led-button-compact.current {
    background: #fff9c4;
    border-color: #f57f17;
    color: #f57f17;
    font-weight: 700;
  }

  .led-button-compact.selected .checkmark {
    position: absolute;
    top: 1px;
    right: 1px;
    font-size: 0.5rem;
    font-weight: bold;
  }

  .offset-actions {
    display: flex;
    gap: 0.5rem;
  }

  .btn-edit,
  .btn-delete,
  .btn-save,
  .btn-cancel {
    padding: 0.4rem 0.6rem;
    border: 1px solid #c8e6c9;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s ease;
  }

  .btn-edit {
    color: #2e7d32;
  }

  .btn-edit:hover {
    background: #f1f8e9;
    border-color: #2e7d32;
  }

  .btn-delete {
    color: #d32f2f;
  }

  .btn-delete:hover {
    background: #ffebee;
    border-color: #d32f2f;
  }

  .btn-save {
    background: #2e7d32;
    color: white;
    border-color: #2e7d32;
  }

  .btn-save:hover {
    background: #1b5e20;
  }

  .btn-cancel {
    background: #ef5350;
    color: white;
    border-color: #ef5350;
  }

  .btn-cancel:hover {
    background: #d32f2f;
  }

  .empty-state {
    color: #558b2f;
    font-size: 0.9rem;
    text-align: center;
    padding: 1rem;
    margin: 0;
    font-style: italic;
  }
</style>
