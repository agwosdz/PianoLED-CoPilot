<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import { settingsLoading, settingsError, loadSettings, updateSettings } from '$lib/stores/settings';
  import { loadCalibration } from '$lib/stores/calibration';
  import SettingsValidationMessage from '$lib/components/SettingsValidationMessage.svelte';
  import PianoKeyboardSelector from '$lib/components/PianoKeyboardSelector.svelte';
  import MidiDeviceSelector from '$lib/components/MidiDeviceSelector.svelte';
  import NetworkMidiConfig from '$lib/components/NetworkMidiConfig.svelte';
  import MidiConnectionStatus from '$lib/components/MidiConnectionStatus.svelte';
  import CalibrationSection1 from '$lib/components/CalibrationSection1.svelte';
  import CalibrationSection2 from '$lib/components/CalibrationSection2.svelte';
  import CalibrationSection3 from '$lib/components/CalibrationSection3.svelte';
  import type { UsbMidiStatus, NetworkMidiStatus } from '$lib/types/midi';

  type MessageType = 'error' | 'success' | 'warning' | 'info' | 'validating';

  const clone = (value: Record<string, any> | null | undefined) => JSON.parse(JSON.stringify(value ?? {}));

  let message = '';
  let messageType: MessageType = 'info';

  let hasUnsavedChanges = false;
  let originalSettings: Record<string, any> = {};
  let currentSettings: Record<string, any> = {};

  let loading = false;
  let error: string | null = null;
  $: loading = $settingsLoading;
  $: error = $settingsError;

  let saving = false;

  let midiDevicesExpanded = false;
  let networkMidiExpanded = false;

  let usbMidiStatus: UsbMidiStatus = { connected: false, deviceName: null, lastActivity: null, messageCount: 0 };
  let networkMidiStatus: NetworkMidiStatus = { connected: false, activeSessions: [], lastActivity: null, messageCount: 0 };

  let dataPinSelection = 18;
  let ledCountValue = 246;
  let ledsPerMeterValue = 60;
  let brightnessPercent = 50;
  let orientationSelection = 'normal';
  let pwmChannel = 0;

  let selectedPattern = 'rainbow';
  let patternDuration = 10;
  let isPatternRunning = false;
  let activeTestId: string | null = null;
  let patternLoading = false;
  let patternResetTimer: ReturnType<typeof setTimeout> | null = null;

  const patternOptions = [
    { value: 'rainbow', label: 'Rainbow Cycle' },
    { value: 'chase', label: 'Color Chase' },
    { value: 'fade', label: 'Smooth Fade' },
    { value: 'piano_keys', label: 'Piano Sweep' }
  ];


  const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
  const coerceNumber = (value: any, fallback: number) => {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  };

  function computeLedChannel(pin: number): number {
    return pin === 18 ? 0 : 1;
  }

  function prepareSettingsPayload(state: Record<string, any>): Record<string, any> {
    const led = state.led ?? {};
    const piano = state.piano ?? {};
    const gpio = state.gpio ?? {};

    const ledCount = coerceNumber(
      led.led_count ?? led.ledCount ?? state.led_count ?? state.ledCount,
      246
    );

    const dataPin = coerceNumber(
      led.data_pin ?? state.led_data_pin ?? state.gpio_pin ?? 18,
      18
    );

    const ledChannelCandidate = typeof led.led_channel === 'number' ? led.led_channel : state.led_channel;
    const ledChannel = Number.isFinite(ledChannelCandidate)
      ? clamp(Number(ledChannelCandidate), 0, 1)
      : computeLedChannel(dataPin);

    let brightnessRaw = led.brightness ?? state.brightness;
    let brightness = typeof brightnessRaw === 'number' ? brightnessRaw : parseFloat(String(brightnessRaw));
    if (!Number.isFinite(brightness)) brightness = 0.5;
    brightness = brightness > 1 ? brightness / 100 : brightness;
    brightness = clamp(brightness, 0, 1);

    const octave = clamp(coerceNumber(piano.octave ?? state.piano_octave, 4), 0, 8);
    const velocitySensitivity = clamp(
      coerceNumber(piano.velocity_sensitivity ?? state.velocity_sensitivity, 64),
      1,
      127
    );
    const midiChannel = clamp(coerceNumber(piano.channel ?? state.piano_channel, 1), 1, 16);

    const gpioEnabledSource =
      typeof gpio.enabled === 'boolean'
        ? gpio.enabled
        : typeof state.gpio_enabled === 'boolean'
        ? state.gpio_enabled
        : typeof state.gpio?.enabled === 'boolean'
        ? state.gpio.enabled
        : undefined;
    const gpioDataPin = coerceNumber(
      gpio.data_pin ?? state.gpio_pin ?? dataPin,
      dataPin
    );

    const gpioPinsSource = Array.isArray(gpio.pins)
      ? gpio.pins
      : Array.isArray(state.gpio?.pins)
      ? state.gpio.pins
      : [];

    const clockPinSource =
      gpio.clock_pin ??
      state.led?.clock_pin ??
      state.clock_pin ??
      state.gpio?.clock_pin;

    const payload: Record<string, any> = {
      led: {
        enabled: led.enabled ?? true,
        led_count: ledCount,
        led_orientation: led.led_orientation ?? state.led_orientation ?? 'normal',
        brightness,
        data_pin: dataPin,
        led_channel: ledChannel,
        update_rate: coerceNumber(led.update_rate ?? state.update_rate ?? 60, 60)
      },
      piano: {
        enabled: piano.enabled ?? true,
        size: piano.size ?? state.piano_size ?? '88-key',
        keys: piano.keys ?? state.piano_keys ?? 88,
        octave,
        octaves: piano.octaves ?? state.piano_octaves ?? 7,
        start_note: piano.start_note ?? state.piano_start_note ?? 'A0',
        end_note: piano.end_note ?? state.piano_end_note ?? 'C8',
        key_mapping_mode: piano.key_mapping_mode ?? state.key_mapping_mode ?? 'chromatic',
        velocity_sensitivity: velocitySensitivity,
        channel: midiChannel
      }
    };

    payload.gpio = {
      data_pin: gpioDataPin,
      pins: gpioPinsSource
    };

    if (typeof gpioEnabledSource === 'boolean') {
      payload.gpio.enabled = gpioEnabledSource;
    } else {
      payload.gpio.enabled = true;
    }

    if (clockPinSource !== undefined) {
      payload.gpio.clock_pin = coerceNumber(clockPinSource, 19);
    }

    if (piano.key_mapping) {
      payload.piano.key_mapping = piano.key_mapping;
    }

    return payload;
  }

  onMount(async () => {
    await loadSettingsData();
    await refreshMidiStatuses();
    await loadCalibrationData();

    // Listen for openAddOffset event from CalibrationSection3
    if (browser) {
      window.addEventListener('openAddOffset', handleOpenAddOffset as EventListener);
    }
  });

  onDestroy(() => {
    clearPatternResetTimer();
    // Clean up event listener
    if (browser) {
      window.removeEventListener('openAddOffset', handleOpenAddOffset as EventListener);
    }
  });

  async function loadSettingsData() {
    try {
      const fetched = await loadSettings();
      const snapshot = clone(fetched);
      currentSettings = clone(snapshot);
      originalSettings = clone(snapshot);
      hasUnsavedChanges = false;
    } catch (err) {
      console.error('Error loading settings:', err);
      showMessage('Error loading settings', 'error');
    }
  }

  async function loadCalibrationData() {
    try {
      await loadCalibration();
    } catch (err) {
      console.error('Error loading calibration:', err);
    }
  }

  function updateLocalSettings(updater: (draft: Record<string, any>) => void) {
    const draft = clone(currentSettings);
    updater(draft);
    currentSettings = draft;
    hasUnsavedChanges = JSON.stringify(currentSettings) !== JSON.stringify(originalSettings);
  }

  function handlePianoChange(event: CustomEvent<{ piano?: Record<string, any> }>) {
    const pianoDetails = event.detail?.piano;
    if (!pianoDetails) return;

    updateLocalSettings((draft) => {
      draft.piano = {
        ...(draft.piano || {}),
        size: pianoDetails.size,
        keys: pianoDetails.keys,
        octaves: pianoDetails.octaves,
        start_note: pianoDetails.startNote,
        end_note: pianoDetails.endNote,
        key_mapping_mode: pianoDetails.keyMapping ?? draft.piano?.key_mapping_mode ?? 'chromatic'
      };
      draft.piano_size = pianoDetails.size;
      draft.piano_keys = pianoDetails.keys;
      draft.piano_octaves = pianoDetails.octaves;
      draft.piano_start_note = pianoDetails.startNote;
      draft.piano_end_note = pianoDetails.endNote;
      draft.key_mapping_mode = pianoDetails.keyMapping ?? draft.key_mapping_mode ?? 'chromatic';
    });
  }

  function handleOpenAddOffset(event: Event) {
    const customEvent = event as CustomEvent<{ midiNote: number }>;
    const { midiNote } = customEvent.detail;
    
    // Find CalibrationSection2 element and scroll it into view
    const section2Element = document.querySelector('[data-section="calibration-2"]');
    if (section2Element) {
      section2Element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      
      // Dispatch event to CalibrationSection2 to populate the MIDI note field
      const populateEvent = new CustomEvent('populateMidiNote', { 
        detail: { midiNote },
        bubbles: true 
      });
      section2Element.dispatchEvent(populateEvent);
    }
  }

  function handleDataPinChange(pin: number) {
    if (!Number.isFinite(pin)) return;

    updateLocalSettings((draft) => {
      const channel = computeLedChannel(pin);
      draft.led = { ...(draft.led || {}), data_pin: pin, led_channel: channel };
      draft.gpio = { ...(draft.gpio || {}), data_pin: pin };
      draft.gpio_pin = pin;
      draft.led_channel = channel;
    });

    showMessage(`Data pin set to GPIO ${pin}`, 'info');
  }

  function handleLedCountChange(count: number) {
    const safeCount = Number.isFinite(count) ? Math.max(1, Math.round(count)) : 1;

    updateLocalSettings((draft) => {
      draft.led = { ...(draft.led || {}), led_count: safeCount };
      draft.led_count = safeCount;
    });
  }

  function handleOrientationChange(orientation: string) {
    updateLocalSettings((draft) => {
      draft.led = { ...(draft.led || {}), led_orientation: orientation };
      draft.led_orientation = orientation;
    });
  }

  function handleLedsPerMeterChange(density: number) {
    const validDensities = [60, 72, 100, 120, 144, 160, 180, 200];
    const safeDensity = validDensities.includes(density) ? density : 60;

    updateLocalSettings((draft) => {
      draft.led = { ...(draft.led || {}), leds_per_meter: safeDensity };
      draft.leds_per_meter = safeDensity;
    });
  }

  function handleBrightnessChange(percent: number) {
    const clamped = Math.min(100, Math.max(0, percent));
    const normalized = clamped / 100;

    updateLocalSettings((draft) => {
      draft.led = { ...(draft.led || {}), brightness: normalized };
      draft.brightness = normalized;
    });
  }

  function resolveLedCount(state: Record<string, any>): number {
    const raw = state?.led?.led_count ?? state?.led_count ?? 246;
    const value = Number(raw);
    return Number.isFinite(value) ? value : 246;
  }

  function resolveDataPin(state: Record<string, any>): number {
    const raw = state?.led?.data_pin
      ?? state?.gpio?.data_pin
      ?? state?.led?.gpio_pin
      ?? state?.gpio_pin
      ?? 18;
    const value = Number(raw);
    return Number.isFinite(value) ? value : 18;
  }

  function clearPatternResetTimer() {
    if (patternResetTimer) {
      clearTimeout(patternResetTimer);
      patternResetTimer = null;
    }
  }

  async function startPatternTest() {
    const duration = Math.max(1, Math.round(Number(patternDuration) || 1));
    patternLoading = true;
    clearPatternResetTimer();

    try {
      const response = await fetch('/api/hardware-test/led/sequence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sequence_type: selectedPattern,
          duration,
          led_count: Number(ledCountValue),
          gpio_pin: Number(dataPinSelection)
        })
      });

      if (!response.ok) {
        throw new Error(`Pattern request failed (${response.status})`);
      }

      const result = await response.json();
      activeTestId = result?.test_id ?? null;
      isPatternRunning = true;
      const label = patternOptions.find((p) => p.value === selectedPattern)?.label ?? 'Pattern';
      showMessage(`Started ${label.toLowerCase()} test`, 'success');

      patternResetTimer = setTimeout(() => {
        isPatternRunning = false;
        activeTestId = null;
        patternResetTimer = null;
        showMessage('Pattern test finished', 'info');
      }, duration * 1000);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      showMessage(message || 'Failed to start pattern test', 'error');
      isPatternRunning = false;
      activeTestId = null;
    } finally {
      patternLoading = false;
    }
  }

  async function stopPatternTest() {
    if (patternLoading) return;
    patternLoading = true;
    clearPatternResetTimer();

    try {
      if (activeTestId) {
        await fetch(`/api/hardware-test/led/sequence/${activeTestId}/stop`, {
          method: 'POST'
        });
      }

      await fetch('/api/hardware-test/led/off', {
        method: 'POST'
      });

      showMessage('Stopped LED testing', 'info');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      showMessage(message || 'Failed to stop testing', 'error');
    } finally {
      isPatternRunning = false;
      activeTestId = null;
      patternLoading = false;
    }
  }

  async function refreshMidiStatuses() {
    try {
      const response = await fetch('/api/midi-input/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const payload = await response.json();
      const status = payload?.midi_input ?? {};
      const usb = status?.usb_service ?? {};
      const rtpmidi = status?.rtpmidi_service ?? {};

      const usbDevice = usb?.device;
      const usbDeviceName = typeof usbDevice === 'object' && usbDevice !== null
        ? usbDevice.name ?? usbDevice.device_name ?? usbDevice.id ?? null
        : typeof usbDevice === 'string'
        ? usbDevice
        : null;

      usbMidiStatus = {
        connected: Boolean(usb?.is_listening || usb?.state === 'listening'),
        deviceName: usbDeviceName,
        lastActivity: usb?.last_event_time ?? null,
        messageCount: Number(usb?.event_count ?? 0)
      };

      const sessionsSource = rtpmidi?.active_sessions;
      const sessions = Array.isArray(sessionsSource)
        ? sessionsSource
        : sessionsSource && typeof sessionsSource === 'object'
        ? Object.values(sessionsSource)
        : [];

      networkMidiStatus = {
        connected: Boolean(rtpmidi?.running || rtpmidi?.state === 'listening'),
        activeSessions: Array.isArray(sessions) ? sessions : [],
        lastActivity: rtpmidi?.performance?.last_event_time ?? null,
        messageCount: Number(rtpmidi?.performance?.event_count ?? 0)
      };
    } catch (err) {
      console.error('Failed to refresh MIDI status:', err);
    }
  }

  async function saveCurrentSettings() {
    if (saving || !hasUnsavedChanges) return;

    try {
      saving = true;
      const payload = prepareSettingsPayload(currentSettings);
      await updateSettings(payload);
  const refreshedRaw = await loadSettings();
  const refreshed = clone(refreshedRaw);
      currentSettings = clone(refreshed);
      originalSettings = clone(refreshed);
      hasUnsavedChanges = false;
      showMessage('Settings saved successfully!', 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      showMessage(message || 'Failed to save settings', 'error');
    } finally {
      saving = false;
    }
  }

  function resetSettingsToSaved() {
    if (!hasUnsavedChanges) return;
    if (typeof window !== 'undefined' && !window.confirm('Reset all changes since your last save?')) {
      return;
    }
    currentSettings = clone(originalSettings);
    hasUnsavedChanges = false;
    showMessage('Settings reset to last saved state', 'info');
  }

  function showMessage(text: string, type: MessageType) {
    message = text;
    messageType = type;
    if (text) {
      setTimeout(() => {
        message = '';
      }, 5000);
    }
  }

  async function handleMidiDeviceSelected(event: CustomEvent<{ id: string; name: string }>) {
    try {
      const response = await fetch('/api/midi-input/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_name: event.detail.name,
          enable_usb: true,
          enable_rtpmidi: false
        })
      });

      if (response.ok) {
        showMessage('MIDI device connected successfully', 'success');
      } else {
        const payload = await response.json().catch(() => null);
        const errorMessage = payload?.message || 'Failed to connect to MIDI device';
        showMessage(errorMessage, 'error');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      showMessage(message || 'Error connecting to MIDI device', 'error');
    } finally {
      await refreshMidiStatuses();
    }
  }

  function handleMidiDevicesUpdated(event: CustomEvent<any>) {
    console.log('MIDI devices updated:', event.detail);
  }

  async function handleNetworkMidiConnected(event: CustomEvent<any>) {
    console.log('Network MIDI session connected:', event.detail);
    showMessage('Network MIDI session connected', 'success');
    await refreshMidiStatuses();
  }

  async function handleNetworkMidiDisconnected(event: CustomEvent<any>) {
    console.log('Network MIDI session disconnected:', event.detail);
    showMessage('Network MIDI session disconnected', 'info');
    await refreshMidiStatuses();
  }

  function handleNetworkMidiSessionsUpdated(event: CustomEvent<any>) {
    console.log('Network MIDI sessions updated:', event.detail);
  }

  function handleMidiStatusConnected() {
    console.log('MIDI status WebSocket connected');
    refreshMidiStatuses().catch(() => {});
  }

  function handleMidiStatusDisconnected() {
    console.log('MIDI status WebSocket disconnected');
  }

  function handleUsbStatusUpdate(event: CustomEvent<UsbMidiStatus>) {
    usbMidiStatus = event.detail;
  }

  function handleNetworkStatusUpdate(event: CustomEvent<NetworkMidiStatus>) {
    networkMidiStatus = event.detail;
  }

  function navigateHome() {
    goto('/');
  }

  $: dataPinSelection = resolveDataPin(currentSettings);
  $: ledCountValue = resolveLedCount(currentSettings);
  $: orientationSelection = typeof (currentSettings?.led?.led_orientation ?? currentSettings?.led_orientation) === 'string'
    ? (currentSettings?.led?.led_orientation ?? currentSettings?.led_orientation)
    : 'normal';
  $: ledsPerMeterValue = (() => {
    const validDensities = [60, 72, 100, 120, 144, 160, 180, 200];
    const raw = currentSettings?.led?.leds_per_meter ?? 60;
    const value = Number(raw);
    return validDensities.includes(value) ? value : 60;
  })();
  $: {
    const rawBrightness = Number(currentSettings?.led?.brightness ?? currentSettings?.brightness ?? 0.5);
    const percent = Math.round(Math.min(1, Math.max(0, Number.isFinite(rawBrightness) ? rawBrightness : 0.5)) * 100);
    brightnessPercent = percent;
  }
  $: {
    const storedChannel = currentSettings?.led?.led_channel ?? currentSettings?.led_channel;
    pwmChannel = Number.isFinite(storedChannel)
      ? clamp(Number(storedChannel), 0, 1)
      : computeLedChannel(dataPinSelection);
  }
</script>

<svelte:head>
  <title>Settings - Piano LED Visualizer</title>
  <meta name="description" content="Configure piano, LED strip, and MIDI settings for the Piano LED Visualizer." />
</svelte:head>

<main class="settings-page">
  <div class="settings-content">
    <section class="hero-section">
      <h1>System Settings</h1>
      <p>Choose a category below to configure your piano, LED strip, or MIDI connectivity.</p>
    </section>

    {#if error}
      <SettingsValidationMessage type="error" message={error} />
    {/if}

    {#if message}
      <SettingsValidationMessage
        type={messageType}
        message={message}
        dismissible={true}
        on:dismiss={() => (message = '')}
      />
    {/if}

    <div class="card-stack">
      <section class="settings-panel" id="piano-settings">
        <header class="card-header">
          <h2>Piano Setup</h2>
          <p>Select your keyboard layout.</p>
        </header>

        <div class="card-body">
          <PianoKeyboardSelector
            settings={{
              piano: {
                size: currentSettings.piano?.size ?? currentSettings.piano_size ?? '88-key',
                keys: currentSettings.piano?.keys ?? currentSettings.piano_keys ?? 88,
                octaves: currentSettings.piano?.octaves ?? currentSettings.piano_octaves ?? 7,
                startNote: currentSettings.piano?.start_note ?? currentSettings.piano_start_note ?? 'A0',
                endNote: currentSettings.piano?.end_note ?? currentSettings.piano_end_note ?? 'C8',
                keyMapping: currentSettings.piano?.key_mapping_mode ?? currentSettings.key_mapping_mode ?? 'chromatic'
              },
              led: {
                ledCount: ledCountValue,
                ledOrientation: orientationSelection
              }
            }}
            piano={{
              size: currentSettings.piano?.size ?? currentSettings.piano_size ?? '88-key',
              keys: currentSettings.piano?.keys ?? currentSettings.piano_keys ?? 88,
              octaves: currentSettings.piano?.octaves ?? currentSettings.piano_octaves ?? 7,
              startNote: currentSettings.piano?.start_note ?? currentSettings.piano_start_note ?? 'A0',
              endNote: currentSettings.piano?.end_note ?? currentSettings.piano_end_note ?? 'C8',
              keyMapping: currentSettings.piano?.key_mapping_mode ?? currentSettings.key_mapping_mode ?? 'chromatic'
            }}
            disabled={loading || saving}
            showMapping={false}
            showPreview={false}
            allowCustomSize={false}
            on:change={handlePianoChange}
          />
        </div>
      </section>

      <section class="settings-panel" id="led-settings">
        <header class="card-header">
          <h2>LED Strip Configuration</h2>
          <p>Set the GPIO pin, LED count, and brightness for your strip.</p>
        </header>

        <div class="card-body">
          <div class="field-grid">
            <div class="field">
              <label for="data-pin">Data Pin</label>
              <select
                id="data-pin"
                bind:value={dataPinSelection}
                on:change={() => handleDataPinChange(Number(dataPinSelection))}
                disabled={loading || saving}
              >
                <option value={18}>GPIO 18 · PWM Channel 0</option>
                <option value={19}>GPIO 19 · PWM Channel 1</option>
              </select>
              <p class="field-hint">PWM channel updates automatically based on your selection.</p>
            </div>

            <div class="field">
              <label for="led-count">LED Count</label>
              <input
                id="led-count"
                type="number"
                min="1"
                max="1000"
                bind:value={ledCountValue}
                on:input={() => handleLedCountChange(Number(ledCountValue))}
                disabled={loading || saving}
              />
            </div>

            <div class="field">
              <label for="leds-per-meter">LED Density (LEDs/m)</label>
              <select
                id="leds-per-meter"
                bind:value={ledsPerMeterValue}
                on:change={() => handleLedsPerMeterChange(Number(ledsPerMeterValue))}
                disabled={loading || saving}
              >
                <option value={60}>60 LEDs/m</option>
                <option value={72}>72 LEDs/m</option>
                <option value={100}>100 LEDs/m</option>
                <option value={120}>120 LEDs/m</option>
                <option value={144}>144 LEDs/m</option>
                <option value={160}>160 LEDs/m</option>
                <option value={180}>180 LEDs/m</option>
                <option value={200}>200 LEDs/m</option>
              </select>
              <p class="field-hint">LED strip density for future auto calibration.</p>
            </div>

            <div class="field">
              <label for="orientation">LED Orientation</label>
              <select
                id="orientation"
                bind:value={orientationSelection}
                on:change={() => handleOrientationChange(orientationSelection)}
                disabled={loading || saving}
              >
                <option value="normal">Normal (Low to High)</option>
                <option value="reversed">Reversed (High to Low)</option>
              </select>
            </div>

            <div class="field field-slider">
              <label for="brightness">Global Brightness ({brightnessPercent}%)</label>
              <input
                id="brightness"
                type="range"
                min="5"
                max="100"
                bind:value={brightnessPercent}
                on:input={() => handleBrightnessChange(Number(brightnessPercent))}
                disabled={loading || saving}
              />
            </div>
          </div>

          <div class="pwm-summary">
            <span class="summary-label">Active PWM Channel</span>
            <span class="summary-value">Channel {pwmChannel}</span>
          </div>

          <div class="pattern-tests">
            <div class="pattern-header">
              <h3>Pattern Tests</h3>
              <p>Run a quick pattern to verify your LEDs.</p>
            </div>

            <div class="pattern-controls">
              <div class="field">
                <label for="pattern-select">Pattern</label>
                <select
                  id="pattern-select"
                  bind:value={selectedPattern}
                  disabled={patternLoading}
                >
                  {#each patternOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>

              <div class="field">
                <label for="pattern-duration">Duration (seconds)</label>
                <input
                  id="pattern-duration"
                  type="number"
                  min="1"
                  max="120"
                  bind:value={patternDuration}
                  disabled={patternLoading}
                />
              </div>
            </div>

            <div class="pattern-actions">
              <button
                type="button"
                class="btn primary"
                on:click={startPatternTest}
                disabled={patternLoading || isPatternRunning || loading}
              >
                {patternLoading && !isPatternRunning ? 'Starting…' : 'Start Pattern'}
              </button>

              <button
                type="button"
                class="btn outline"
                on:click={stopPatternTest}
                disabled={patternLoading || (!isPatternRunning && !activeTestId)}
              >
                {patternLoading && isPatternRunning ? 'Stopping…' : 'Stop Testing'}
              </button>
            </div>

            {#if isPatternRunning}
              <p class="pattern-status">
                Running {patternOptions.find((p) => p.value === selectedPattern)?.label ?? 'pattern'}…
              </p>
            {/if}
          </div>
        </div>
      </section>

      <section class="settings-panel midi-panel" id="midi-settings">
        <header class="card-header">
          <h2>MIDI Connections</h2>
          <p>Manage USB devices and RTP-MIDI sessions.</p>
        </header>

        <div class="card-body midi-body">
          <div class="midi-status">
            <MidiConnectionStatus
              {usbMidiStatus}
              {networkMidiStatus}
              on:connected={handleMidiStatusConnected}
              on:disconnected={handleMidiStatusDisconnected}
              on:usbStatusUpdate={handleUsbStatusUpdate}
              on:networkStatusUpdate={handleNetworkStatusUpdate}
            />
          </div>

          <details
            class="midi-panel"
            open={midiDevicesExpanded}
            on:toggle={(event) => (midiDevicesExpanded = (event.currentTarget as HTMLDetailsElement).open)}
          >
            <summary>USB MIDI Devices</summary>
            <div class="panel-content">
              <MidiDeviceSelector
                autoRefresh={false}
                on:deviceSelected={handleMidiDeviceSelected}
                on:devicesUpdated={handleMidiDevicesUpdated}
              />
            </div>
          </details>

          <details
            class="midi-panel"
            open={networkMidiExpanded}
            on:toggle={(event) => (networkMidiExpanded = (event.currentTarget as HTMLDetailsElement).open)}
          >
            <summary>Network MIDI (RTP-MIDI)</summary>
            <div class="panel-content">
              <NetworkMidiConfig
                autoDiscovery={false}
                on:sessionConnected={handleNetworkMidiConnected}
                on:sessionDisconnected={handleNetworkMidiDisconnected}
                on:sessionsUpdated={handleNetworkMidiSessionsUpdated}
              />
            </div>
          </details>
        </div>
      </section>

      <section class="settings-panel calibration-panel" id="calibration-settings">
        <header class="card-header">
          <h2>Calibration</h2>
          <p>Coordinate LEDs with piano keys and fine-tune system alignment.</p>
        </header>

        <div class="card-body">
          <div class="calibration-sections">
            <CalibrationSection1 />
            <div data-section="calibration-2">
              <CalibrationSection2 />
            </div>
            <CalibrationSection3 />
          </div>
        </div>
      </section>
    </div>

    <div class="action-bar">
      <div class="action-left">
        <button type="button" class="btn ghost" on:click={navigateHome}>
          Back to Home
        </button>

        {#if hasUnsavedChanges}
          <button type="button" class="btn ghost" on:click={resetSettingsToSaved}>
            Reset Changes
          </button>
        {/if}
      </div>

      <button
        type="button"
        class="btn primary large"
        on:click={saveCurrentSettings}
        disabled={saving || loading || !hasUnsavedChanges}
      >
        {saving ? 'Saving…' : hasUnsavedChanges ? 'Save Settings' : 'Settings Saved'}
      </button>
    </div>
  </div>
</main>

<style>
  .settings-page {
    min-height: 100vh;
    background: #ffffff;
    padding: 2.5rem 1rem 3rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .settings-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .hero-section {
    text-align: center;
    color: #1f2937;
  }

  .hero-section h1 {
    margin: 0;
    font-size: 2.4rem;
    font-weight: 700;
  }

  .hero-section p {
    margin: 0.5rem 0 0;
    font-size: 1rem;
    color: #4b5563;
  }

  .card-stack {
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
  }

  .settings-panel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.75rem 2rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .card-header h2 {
    margin: 0;
    font-size: 1.4rem;
    color: #0f172a;
  }

  .card-header p {
    margin: 0.25rem 0 0;
    color: #475569;
    font-size: 0.95rem;
  }

  .card-body {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .field-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .field label {
    font-weight: 600;
    color: #1f2937;
    font-size: 0.9rem;
  }

  .field select,
  .field input[type='number'] {
    padding: 0.65rem 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    color: #0f172a;
    font-size: 0.95rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .field select:focus,
  .field input[type='number']:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
  }

  .field select:disabled,
  .field input[type='number']:disabled {
    background: #e2e8f0;
    cursor: not-allowed;
  }

  .field-hint {
    margin: 0;
    font-size: 0.8rem;
    color: #64748b;
  }

  .field-slider input[type='range'] {
    width: 100%;
    accent-color: #2563eb;
  }

  .pwm-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #e0f2fe;
    border: 1px solid #bae6fd;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    color: #0c4a6e;
    font-weight: 600;
  }

  .pattern-tests {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    background: #ffffff;
    border: 1px dashed #cbd5f5;
    border-radius: 12px;
    padding: 1.25rem;
  }

  .pattern-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #0f172a;
  }

  .pattern-header p {
    margin: 0.25rem 0 0;
    color: #475569;
    font-size: 0.9rem;
  }

  .calibration-sections {
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
  }

  .pattern-controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .pattern-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .pattern-status {
    margin: 0;
    font-size: 0.9rem;
    color: #2563eb;
    font-weight: 600;
  }

  .midi-panel .midi-body {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .midi-status {
    padding: 1rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
  }

  details.midi-panel {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #ffffff;
    overflow: hidden;
  }

  details.midi-panel > summary {
    padding: 0.9rem 1.1rem;
    cursor: pointer;
    font-weight: 600;
    color: #0f172a;
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  details.midi-panel[open] > summary {
    background: #eff6ff;
    border-bottom: 1px solid #e2e8f0;
  }

  details.midi-panel > summary::marker,
  details.midi-panel > summary::-webkit-details-marker {
    display: none;
  }

  details.midi-panel > summary::after {
    content: '\25BC';
    font-size: 0.85rem;
    transition: transform 0.2s ease;
  }

  details.midi-panel[open] > summary::after {
    transform: rotate(180deg);
  }

  .panel-content {
    padding: 1rem;
  }

  .action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  }

  .action-left {
    display: flex;
    gap: 0.75rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 999px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
    padding: 0.75rem 1.5rem;
    font-size: 0.95rem;
  }

  .btn.primary {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff;
    box-shadow: 0 8px 16px rgba(37, 99, 235, 0.25);
  }

  .btn.primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 12px 24px rgba(37, 99, 235, 0.3);
  }

  .btn.primary.large {
    padding: 0.85rem 2.5rem;
    font-size: 1rem;
  }

  .btn.outline {
    background: #ffffff;
    border: 1px solid #2563eb;
    color: #1d4ed8;
  }

  .btn.outline:hover:not(:disabled) {
    background: #eff6ff;
  }

  .btn.ghost {
    background: #ffffff;
    border: 1px solid #d1d5db;
    color: #1f2937;
  }

  .btn.ghost:hover:not(:disabled) {
    background: #f1f5f9;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
  }

  @media (max-width: 960px) {
    .action-bar {
      flex-direction: column;
      align-items: stretch;
      gap: 1rem;
    }

    .action-left {
      justify-content: space-between;
    }

    .btn.primary.large {
      width: 100%;
    }
  }

  @media (max-width: 640px) {
    .settings-page {
      padding: 1.75rem 0.75rem 2.25rem;
    }

    .settings-panel {
      padding: 1.5rem;
    }

    .field-grid,
    .pattern-controls {
      grid-template-columns: 1fr;
    }
  }
</style>
