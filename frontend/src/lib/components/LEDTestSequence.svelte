<script>
  import { onMount, onDestroy } from 'svelte';
  import { getSocket, socketStatus } from '$lib/socket';
  import { get } from 'svelte/store';
  import { canonicalLedCount, canonicalGpioPin } from '$lib/stores/settings';
  
  // Receive bound settings from parent
  export let settings = {};

  // Component state
  let activeTab = 'sequence';
  let isTestRunning = false;
  let testProgress = 0;
  let testStatus = '';
  let testError = '';
  let currentTest = null;
  let currentTestId = null;
  let systemCapabilities = null;
  let loadingCapabilities = false;

  // Test configuration
  let selectedSequence = 'rainbow';
  let testDuration = 5;
  let brightness = 100;
  let speed = 50;
  let showAdvanced = false;
  let customPattern = [
    { color: '#FF0000', duration: 1000, brightness: 100 },
    { color: '#00FF00', duration: 1000, brightness: 100 },
    { color: '#0000FF', duration: 1000, brightness: 100 }
  ];

  // Individual LED test
  let ledPin = 18;
  let ledColor = '#FF0000';
  let ledBrightness = 100;

  // GPIO validation
  let gpioPin = 18;

  // Available sequences
  const sequences = [
    { id: 'rainbow', name: 'Rainbow Cycle', description: 'Smooth color transitions through the spectrum' },
    { id: 'chase', name: 'Color Chase', description: 'Moving color pattern across LEDs' },
    { id: 'pulse', name: 'Pulse', description: 'Breathing effect with selected color' },
    { id: 'strobe', name: 'Strobe', description: 'Fast flashing pattern' },
    { id: 'fade', name: 'Fade', description: 'Gradual fade in/out effect' },
    { id: 'custom', name: 'Custom Pattern', description: 'User-defined color sequence' }
  ];

  // Helper functions for API requests and error handling
  async function makeApiRequest(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${url}:`, error);
      throw error;
    }
  }

  function setTestError(message) {
    testStatus = 'error';
    testError = message;
    isTestRunning = false;
  }

  function setTestSuccess(message) {
    testStatus = 'success';
    testError = '';
    if (message) {
      console.log('Test success:', message);
    }
  }

  function resetTestState() {
    testStatus = '';
    testError = '';
    testProgress = 0;
    currentTest = null;
    currentTestId = null;
    isTestRunning = false;
  }

  function handleTestCompletion(data) {
    setTestSuccess('Test completed successfully');
    testProgress = 100;
    isTestRunning = false;
    if (data.results) {
      currentTest = data.results;
    }
  }

  function handleTestError(data) {
    setTestError(data.error || 'Test failed');
    testProgress = 0;
  }

  onMount(async () => {
    await loadSystemCapabilities();
    
    // Subscribe to WebSocket events
    const ws = getSocket();
    if (ws) {
      ws.on('led_sequence_complete', handleTestCompletion);
      ws.on('led_sequence_stop', () => resetTestState());
      ws.on('led_sequence_error', handleTestError);
    }
  });

  onDestroy(() => {
    // Cleanup is handled by the socket library
  });

  function handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'led_sequence_progress':
          testProgress = data.progress || 0;
          if (data.current_step) {
            currentTest = data.current_step;
          }
          break;
          
        case 'led_sequence_complete':
          handleTestCompletion(data);
          break;
          
        case 'led_sequence_stop':
          resetTestState();
          break;
          
        case 'led_sequence_error':
          handleTestError(data);
          break;
          
        case 'led_test_complete':
          setTestSuccess('LED test completed');
          break;
          
        case 'led_test_error':
          handleTestError(data);
          break;
          
        case 'gpio_validation_complete':
          setTestSuccess(`GPIO pin ${data.pin} validation completed`);
          break;
          
        case 'gpio_validation_error':
          handleTestError(data);
          break;
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  // API functions
  async function loadSystemCapabilities() {
    loadingCapabilities = true;
    try {
      systemCapabilities = await makeApiRequest('/api/hardware-test/system/capabilities');
    } catch (error) {
      setTestError(`Failed to load system capabilities: ${error.message}`);
    } finally {
      loadingCapabilities = false;
    }
  }

  async function startTestSequence() {
    resetTestState();
    isTestRunning = true;
    testStatus = 'running';

    const config = {
      sequence_type: selectedSequence,
      duration: parseInt(testDuration),
      brightness: brightness / 100,
      speed: speed / 100,
      gpio_pin: $canonicalGpioPin,
      led_count: $canonicalLedCount,
      colors: selectedSequence === 'custom' ? customPattern.map(step => ({
        color: hexToRgbArray(step.color),
        brightness: step.brightness / 100,
        duration: step.duration / 1000
      })) : undefined,
      ...(selectedSequence === 'custom' && {
        pattern: customPattern.map(step => ({
          color: hexToRgbArray(step.color),
          brightness: step.brightness / 100,
          duration: step.duration / 1000,
          leds: Array.from({ length: $canonicalLedCount }, (_, i) => i)
        }))
      })
    };

    try {
      const result = await makeApiRequest('/api/hardware-test/led/sequence', {
        method: 'POST',
        body: JSON.stringify(config)
      });
      currentTestId = result?.test_id ?? null;
    } catch (error) {
      setTestError(`Failed to start test sequence: ${error.message}`);
    }
  }

  async function stopTestSequence() {
    try {
      if (currentTestId) {
        await makeApiRequest(`/api/hardware-test/led/sequence/${currentTestId}/stop`, {
          method: 'POST'
        });
      }
      // Force turn off all LEDs regardless of controller state
      await turnOffAllLEDs();
      resetTestState();
    } catch (error) {
      setTestError(`Failed to stop test sequence: ${error.message}`);
    }
  }

  async function turnOffAllLEDs() {
    try {
      const result = await makeApiRequest('/api/hardware-test/led/off', {
        method: 'POST'
      });
      setTestSuccess('All LEDs turned off');
    } catch (error) {
      setTestError(`Failed to turn off LEDs: ${error.message}`);
    }
  }
  function hexToRgbArray(hex) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    return [r, g, b];
  }

  async function testIndividualLED() {
    resetTestState();
    testStatus = 'running';

    const config = {
      led_index: 0,
      color: hexToRgbArray(ledColor),
      brightness: ledBrightness / 100,
      duration: 2.0,
      gpio_pin: $canonicalGpioPin,
      led_count: $canonicalLedCount
    };

    try {
      await makeApiRequest('/api/hardware-test/led/individual', {
        method: 'POST',
        body: JSON.stringify(config)
      });
    } catch (error) {
      setTestError(`Failed to test LED: ${error.message}`);
    }
  }

  async function validateGPIO() {
    resetTestState();
    testStatus = 'running';

    try {
      const result = await makeApiRequest('/api/hardware-test/gpio/validate', {
        method: 'POST',
        body: JSON.stringify({ pins: [gpioPin], mode: 'output' })
      });
      setTestSuccess(`GPIO pin ${gpioPin} validation completed`);
    } catch (error) {
      setTestError(`GPIO validation failed: ${error.message}`);
    }
  }

  // Custom pattern management
  function addPatternStep() {
    customPattern = [...customPattern, { color: '#FFFFFF', duration: 1000, brightness: 100 }];
  }

  function removePatternStep(index) {
    customPattern = customPattern.filter((_, i) => i !== index);
  }

  function updatePatternStep(index, field, value) {
    customPattern[index][field] = value;
    customPattern = [...customPattern];
  }
</script>

<div class="led-test-container">
  <div class="header">
    <h2>LED Test Sequence</h2>
    <div class="status-info">
      {#if loadingCapabilities}
        <span class="loading">Loading system capabilities...</span>
      {:else if systemCapabilities}
        <span class="capabilities">
          LEDs: {systemCapabilities.led_count || 'Unknown'} | 
          GPIO: {systemCapabilities.gpio_pins?.length || 0} pins available
        </span>
      {/if}
    </div>
  </div>

  <!-- Test Status -->
  {#if testStatus}
    <div class="test-status {testStatus}">
      <span class="status-icon">
        {#if testStatus === 'running'}⏳{:else if testStatus === 'success'}✅{:else if testStatus === 'error'}❌{/if}
      </span>
      <span>
        {#if testStatus === 'running'}
          Test in progress...
        {:else if testStatus === 'success'}
          Test completed successfully
        {:else if testStatus === 'error'}
          {testError}
        {/if}
      </span>
    </div>
  {/if}

  <!-- Progress Bar -->
  {#if isTestRunning && testProgress > 0}
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" style="width: {testProgress}%"></div>
      </div>
      <span class="progress-text">{testProgress}%</span>
    </div>
  {/if}

  <!-- Test Tabs -->
  <div class="test-tabs">
    <button 
      class="tab-button {activeTab === 'sequence' ? 'active' : ''}"
      on:click={() => activeTab = 'sequence'}
    >
      Sequence Test
    </button>
    <button 
      class="tab-button {activeTab === 'individual' ? 'active' : ''}"
      on:click={() => activeTab = 'individual'}
    >
      Individual LED
    </button>
    <button 
      class="tab-button {activeTab === 'gpio' ? 'active' : ''}"
      on:click={() => activeTab = 'gpio'}
    >
      GPIO Validation
    </button>
  </div>

  <!-- Tab Content -->
  <div class="tab-content">
    {#if activeTab === 'sequence'}
      <div class="test-controls">
        <div class="control-row">
          <div class="control-group">
            <label for="sequence-select">Test Sequence</label>
            <select id="sequence-select" bind:value={selectedSequence} disabled={isTestRunning}>
              {#each sequences as sequence}
                <option value={sequence.id}>{sequence.name}</option>
              {/each}
            </select>
            <p class="sequence-description">
              {sequences.find(s => s.id === selectedSequence)?.description || ''}
            </p>
          </div>

          <div class="control-group">
            <label for="duration">Duration (seconds)</label>
            <input 
              id="duration" 
              type="number" 
              min="1" 
              max="300" 
              bind:value={testDuration}
              disabled={isTestRunning}
            />
            <p class="help-text">How long to run the test sequence</p>
          </div>
        </div>

        <div class="control-row">
          <div class="control-group">
            <label for="brightness">Brightness ({brightness}%)</label>
            <input 
              id="brightness" 
              type="range" 
              min="1" 
              max="100" 
              bind:value={brightness}
              disabled={isTestRunning}
            />
          </div>

          <div class="control-group">
            <label for="speed">Speed ({speed}%)</label>
            <input 
              id="speed" 
              type="range" 
              min="1" 
              max="100" 
              bind:value={speed}
              disabled={isTestRunning}
            />
          </div>
        </div>

        <!-- Advanced Options -->
        <div class="advanced-toggle">
          <button class="toggle-button" on:click={() => showAdvanced = !showAdvanced}>
            {showAdvanced ? '▼' : '▶'} Advanced Options
          </button>
        </div>

        {#if showAdvanced}
          <div class="advanced-options">
            <div class="control-group">
              <label for="advanced-custom-color">Custom Color</label>
              <input id="advanced-custom-color" type="color" bind:value={ledColor} disabled={isTestRunning} />
            </div>
          </div>
        {/if}

        <!-- Custom Pattern Editor -->
        {#if selectedSequence === 'custom'}
          <div class="custom-pattern-editor">
            <h4>Custom Pattern Steps</h4>
            {#each customPattern as step, index}
              <div class="pattern-step">
                <div class="step-header">
                  <span>Step {index + 1}</span>
                  <button 
                    class="remove-step" 
                    on:click={() => removePatternStep(index)}
                    disabled={isTestRunning || customPattern.length <= 1}
                  >
                    ×
                  </button>
                </div>
                <div class="step-controls">
                  <div class="control-group">
                    <label for={`custom-color-${index}`}>Color</label>
                    <input 
                      id={`custom-color-${index}`}
                      type="color" 
                      value={step.color}
                      on:input={(e) => updatePatternStep(index, 'color', e.target.value)}
                      disabled={isTestRunning}
                    />
                  </div>
                  <div class="control-group">
                    <label for={`custom-duration-${index}`}>Duration (ms)</label>
                    <input 
                      id={`custom-duration-${index}`}
                      type="number" 
                      min="100" 
                      max="10000" 
                      value={step.duration}
                      on:input={(e) => updatePatternStep(index, 'duration', parseInt(e.target.value))}
                      disabled={isTestRunning}
                    />
                  </div>
                  <div class="control-group">
                    <label for={`custom-brightness-${index}`}>Brightness (%)</label>
                    <input 
                      id={`custom-brightness-${index}`}
                      type="range" 
                      min="1" 
                      max="100" 
                      value={step.brightness}
                      on:input={(e) => updatePatternStep(index, 'brightness', parseInt(e.target.value))}
                      disabled={isTestRunning}
                    />
                    <span class="range-value">{step.brightness}%</span>
                  </div>
                </div>
              </div>
            {/each}
            <button class="add-step" on:click={addPatternStep} disabled={isTestRunning}>
              Add Step
            </button>
          </div>
        {/if}
      </div>

      <div class="test-actions">
        <button 
          class="btn btn-primary" 
          on:click={startTestSequence}
          disabled={isTestRunning}
        >
          Start Test
        </button>
        <button 
          class="btn btn-secondary" 
          on:click={stopTestSequence}
          disabled={!isTestRunning}
        >
          Stop Test
        </button>
        <button
          class="btn btn-danger"
          on:click={turnOffAllLEDs}
          disabled={isTestRunning}
        >
          Turn Off LEDs
        </button>
      </div>

    {:else if activeTab === 'individual'}
      <div class="individual-test">
        <h4>Test Individual LED</h4>
        <div class="led-test-controls">
          <div class="control-group">
            <label for="led-pin">GPIO Pin</label>
            <input 
              id="led-pin" 
              type="number" 
              min="1" 
              max="40" 
              bind:value={ledPin}
              disabled={isTestRunning}
            />
          </div>
          <div class="control-group">
            <label for="led-color">Color</label>
            <input 
              id="led-color" 
              type="color" 
              bind:value={ledColor}
              disabled={isTestRunning}
            />
          </div>
          <button 
            class="test-led-btn" 
            on:click={testIndividualLED}
            disabled={isTestRunning}
          >
            Test LED
          </button>
        </div>
      </div>

    {:else if activeTab === 'gpio'}
      <div class="gpio-validation">
        <h4>GPIO Pin Validation</h4>
        <div class="gpio-controls">
          <div class="control-group">
            <label for="gpio-pin">GPIO Pin</label>
            <input 
              id="gpio-pin" 
              type="number" 
              min="1" 
              max="40" 
              bind:value={gpioPin}
              disabled={isTestRunning}
            />
          </div>
          <button 
            class="validate-btn" 
            on:click={validateGPIO}
            disabled={isTestRunning}
          >
            Validate Pin
          </button>
        </div>
      </div>
    {/if}
  </div>

  <!-- Current Test Info -->
  {#if currentTest}
    <div class="current-test">
      <h4>Current Test Details</h4>
      <div class="test-info">
        <div class="info-item">
          <span class="label">Sequence</span>
          <span class="value">{currentTest.sequence || 'N/A'}</span>
        </div>
        <div class="info-item">
          <span class="label">Step</span>
          <span class="value">{currentTest.step || 'N/A'}</span>
        </div>
        <div class="info-item">
          <span class="label">Color</span>
          <span class="value">{currentTest.color || 'N/A'}</span>
        </div>
        <div class="info-item">
          <span class="label">Brightness</span>
          <span class="value">{currentTest.brightness ? Math.round(currentTest.brightness * 100) + '%' : 'N/A'}</span>
        </div>
      </div>
    </div>
  {/if}

  <!-- System Capabilities -->
  {#if systemCapabilities}
    <div class="capabilities-section">
      <h4>System Capabilities</h4>
      <div class="capabilities-grid">
        <div class="capability-item">
          <span class="label">LED Count</span>
          <span class="value">{systemCapabilities.led_count || 'Unknown'}</span>
        </div>
        <div class="capability-item">
          <span class="label">GPIO Pins</span>
          <span class="value">{systemCapabilities.gpio_pins?.length || 0}</span>
        </div>
        <div class="capability-item">
          <span class="label">PWM Channels</span>
          <span class="value">{systemCapabilities.pwm_channels || 'Unknown'}</span>
        </div>
        <div class="capability-item">
          <span class="label">SPI Available</span>
          <span class="value">{systemCapabilities.spi_available ? 'Yes' : 'No'}</span>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .led-test-container {
    padding: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
  }

  .header h2 {
    margin: 0;
    color: var(--text-primary);
    font-size: 1.5rem;
  }

  .status-info {
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .loading {
    color: var(--info-color);
  }

  .capabilities {
    color: var(--text-secondary);
  }

  .test-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid var(--border-color);
  }

  .tab-button {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 1rem 1.5rem;
    cursor: pointer;
    font-weight: 500;
    color: var(--text-secondary);
    transition: all 0.2s ease;
  }

  .tab-button:hover {
    color: var(--text-primary);
    background: var(--bg-secondary);
  }

  .tab-button.active {
    color: var(--accent-color);
    border-bottom-color: var(--accent-color);
  }

  .tab-content {
    display: block;
  }

  .test-controls {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .control-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .control-group label {
    font-weight: 500;
    color: var(--text-primary);
    font-size: 0.875rem;
  }

  .control-group select,
  .control-group input {
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.875rem;
  }

  .control-group select:focus,
  .control-group input:focus {
    outline: none;
    border-color: var(--accent-color);
    box-shadow: 0 0 0 2px var(--accent-color-alpha);
  }

  .control-group select:disabled,
  .control-group input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .sequence-description {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin: 0;
    font-style: italic;
  }

  .help-text {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin: 0;
  }

  /* Advanced Options */
  .advanced-toggle {
    margin: 1rem 0;
  }

  .toggle-button {
    background: none;
    border: none;
    color: var(--accent-color);
    cursor: pointer;
    font-weight: 500;
    padding: 0.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .toggle-button:hover {
    text-decoration: underline;
  }

  .advanced-options {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-top: 0.5rem;
  }

  .range-value {
    font-size: 0.875rem;
    color: var(--text-secondary);
    font-weight: 500;
  }

  /* Custom Pattern Editor */
  .custom-pattern-editor {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-top: 1rem;
  }

  .custom-pattern-editor h4 {
    margin: 0 0 1rem 0;
    color: var(--text-primary);
    font-size: 1rem;
  }

  .pattern-step {
    background: var(--bg-primary);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    border: 1px solid var(--border-color);
  }

  .step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .step-header span {
    font-weight: 500;
    color: var(--text-primary);
  }

  .remove-step {
    background: var(--error-color);
    color: white;
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
  }

  .step-controls {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 0.75rem;
  }

  .add-step {
    background: var(--accent-color);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s ease;
  }

  .add-step:hover {
    background: var(--accent-color-hover);
  }

  /* Progress Bar */
  .progress-container {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .progress-bar {
    flex: 1;
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--accent-color);
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    min-width: 40px;
  }

  .test-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.875rem;
    color: var(--text-primary, #111827);
    background: var(--bg-primary, #ffffff);
  }

  .btn:focus {
    outline: none;
    box-shadow: 0 0 0 3px var(--accent-color-alpha, rgba(37,99,235,0.25));
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--accent-color, #2563eb);
    border-color: var(--accent-color, #2563eb);
    color: #ffffff;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--accent-color-hover, #1d4ed8);
    transform: translateY(-1px);
  }

  .btn-secondary {
    background: var(--error-color, #ef4444);
    border-color: var(--error-color, #ef4444);
    color: #ffffff;
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--error-color-hover, #dc2626);
    transform: translateY(-1px);
  }

  /* Test Status */
  .test-status {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    font-weight: 500;
  }

  .test-status.running {
    background: var(--info-bg);
    color: var(--info-text);
    border: 1px solid var(--info-color);
  }

  .test-status.success {
    background: var(--success-bg);
    color: var(--success-text);
    border: 1px solid var(--success-color);
  }

  .test-status.error {
    background: var(--error-bg);
    color: var(--error-text);
    border: 1px solid var(--error-color);
  }

  .status-icon {
    font-size: 1.25rem;
    font-weight: bold;
  }

  /* Current Test Info */
  .current-test {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-top: 1rem;
  }

  .current-test h4 {
    margin: 0 0 0.75rem 0;
    color: var(--text-primary);
    font-size: 1rem;
  }

  .test-info {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .info-item .label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .info-item .value {
    font-size: 0.875rem;
    color: var(--text-primary);
    font-weight: 500;
  }

  /* Individual LED Test */
  .individual-test {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .individual-test h4 {
    margin: 0 0 1rem 0;
    color: var(--text-primary);
    font-size: 1rem;
  }

  .led-test-controls {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
    gap: 1rem;
    align-items: end;
  }

  .test-led-btn {
    background: var(--accent-color);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s ease;
  }

  .test-led-btn:hover:not(:disabled) {
    background: var(--accent-color-hover);
  }

  .test-led-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* GPIO Validation */
  .gpio-validation {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .gpio-validation h4 {
    margin: 0 0 1rem 0;
    color: var(--text-primary);
    font-size: 1rem;
  }

  .gpio-controls {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 1rem;
    align-items: end;
  }

  .validate-btn {
    background: var(--info-color);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s ease;
  }

  .validate-btn:hover:not(:disabled) {
    background: var(--info-color-hover);
  }

  .validate-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* System Capabilities */
  .capabilities-section {
    background: var(--bg-tertiary);
    border-radius: 6px;
    padding: 1rem;
    margin-top: 1rem;
  }

  .capabilities-section h4 {
    margin: 0 0 1rem 0;
    color: var(--text-primary);
    font-size: 1rem;
  }

  .capabilities-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }

  .capability-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .capability-item .label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .capability-item .value {
    font-size: 0.875rem;
    color: var(--text-primary);
    font-weight: 500;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .led-test-container {
      padding: 1rem;
    }

    .header {
      flex-direction: column;
      align-items: flex-start;
      gap: 1rem;
    }

    .test-tabs {
      flex-wrap: wrap;
    }

    .tab-button {
      padding: 0.5rem 1rem;
      font-size: 0.875rem;
    }

    .control-row {
      grid-template-columns: 1fr;
    }

    .led-test-controls {
      grid-template-columns: 1fr;
      gap: 0.75rem;
    }

    .gpio-controls {
      grid-template-columns: 1fr;
      gap: 0.75rem;
    }

    .test-actions {
      flex-direction: column;
    }

    .capabilities-grid {
      grid-template-columns: 1fr;
    }
  }
</style>