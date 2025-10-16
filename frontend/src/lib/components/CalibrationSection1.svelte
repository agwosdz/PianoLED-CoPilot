<script lang="ts">
  import { calibrationUI, calibrationService } from '$lib/stores/calibration';

  let isLoading = false;
  let midiBasedLoading = false;
  let ledBasedLoading = false;

  $: isLoading = $calibrationUI.isLoading;

  async function handleMidiBasedCalibration() {
    midiBasedLoading = true;
    try {
      // TODO: Implement MIDI-based calibration workflow
      // This would involve:
      // 1. Listen for MIDI note presses
      // 2. Record which key is pressed
      // 3. Show LED index visualization
      // 4. Allow user to confirm offset for that key
      // 5. Repeat for multiple keys to auto-detect offset pattern
      
      console.log('MIDI-based calibration workflow not yet implemented');
      calibrationUI.update(ui => ({ 
        ...ui, 
        error: 'MIDI-based calibration is coming soon in Phase 2' 
      }));
    } finally {
      midiBasedLoading = false;
    }
  }

  async function handleLedBasedCalibration() {
    ledBasedLoading = true;
    try {
      // TODO: Implement LED-based calibration workflow
      // This would involve:
      // 1. Flash each LED individually
      // 2. User identifies which piano key it corresponds to
      // 3. Record the mapping
      // 4. Auto-generate offsets based on mapping
      
      console.log('LED-based calibration workflow not yet implemented');
      calibrationUI.update(ui => ({ 
        ...ui, 
        error: 'LED-based calibration is coming soon in Phase 2' 
      }));
    } finally {
      ledBasedLoading = false;
    }
  }
</script>

<div class="calibration-section-1">
  <div class="section-intro">
    <h3>Auto Calibration Workflows</h3>
    <p>Choose an automated method to detect and set LED offsets for your piano keys.</p>
  </div>

  <div class="button-group">
    <button
      class="btn btn-primary"
      on:click={handleMidiBasedCalibration}
      disabled={isLoading || midiBasedLoading || ledBasedLoading}
    >
      {#if midiBasedLoading}
        <span class="spinner"></span>
        Listening for MIDI...
      {:else}
        🎹 MIDI-Based
      {/if}
    </button>

    <button
      class="btn btn-primary"
      on:click={handleLedBasedCalibration}
      disabled={isLoading || midiBasedLoading || ledBasedLoading}
    >
      {#if ledBasedLoading}
        <span class="spinner"></span>
        Flashing LEDs...
      {:else}
        💡 LED-Based
      {/if}
    </button>
  </div>

  <div class="section-info">
    <p class="info-text">
      <strong>MIDI-Based:</strong> Press piano keys to detect which LED corresponds to each key
    </p>
    <p class="info-text">
      <strong>LED-Based:</strong> We'll flash each LED, and you tell us which key it represents
    </p>
  </div>
</div>

<style>
  .calibration-section-1 {
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

  .button-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s ease;
    padding: 0.85rem 1.25rem;
  }

  .btn-primary {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinner {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 2px solid #ffffff;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .section-info {
    background: #f0f9ff;
    border-left: 4px solid #2563eb;
    padding: 1rem;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .info-text {
    margin: 0;
    font-size: 0.9rem;
    color: #0c4a6e;
    line-height: 1.5;
  }

  .info-text strong {
    color: #0a3f5c;
  }

  @media (max-width: 640px) {
    .calibration-section-1 {
      padding: 1rem;
    }

    .button-group {
      grid-template-columns: 1fr;
    }

    .btn {
      width: 100%;
    }
  }
</style>
