<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import {
    uploadMidiFile,
    UploadError,
    type UploadProgress,
    formatFileSize
  } from '$lib/upload';
  import { getSocket, socketStatus } from '$lib/socket';
  import UploadedFileList from '$lib/components/UploadedFileList.svelte';
  import type { UploadedFile as UploadedFileItem } from '$lib/components/UploadedFileList.svelte';

  type PlaybackState = 'idle' | 'playing' | 'paused' | 'stopped';

  let selectedFile: File | null = null;
  let dragActive = false;
  let uploadState: 'idle' | 'uploading' | 'complete' = 'idle';
  let uploadProgress = 0;
  let uploadMessage = '';
  let uploadError = '';
  let uploadedSize = 0;

  let playbackFilename = '';
  let playbackOriginalName = '';
  let playbackState: PlaybackState = 'idle';
  let playbackNotice = '';
  let currentTime = 0;
  let totalDuration = 0;
  let playbackDisplayName = '';
  let deletingPath: string | null = null;

  let connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error' = 'connecting';
  let socketInstance: any = null;
  let unsubscribeSocketStatus: (() => void) | null = null;
  let pollingHandle: ReturnType<typeof setInterval> | null = null;
  let fileInput: HTMLInputElement | null = null;

  let uploadedFiles: UploadedFileItem[] = [];
  let uploadedFilesError = '';
  let isLoadingUploadedFiles = false;

  // MIDI output state
  let midiOutputEnabled = false;
  let midiOutputDevices: Array<{ name: string; id: number; status: string; is_current: boolean }> = [];
  let selectedMidiOutputDevice: string | null = null;
  let midiOutputConnected = false;
  let loadingMidiDevices = false;
  let midiOutputError = '';

  const statusPollIntervalMs = 3000;

  $: playbackDisplayName = playbackOriginalName || deriveOriginalName(playbackFilename);

  function resetUploadFeedback(): void {
    uploadMessage = '';
    uploadError = '';
  }

  function deriveOriginalName(filename: string): string {
    if (!filename) return '';
    const base = filename.split(/[\\/]/).pop() ?? filename;
    return base.replace(/_\d{8}_\d{6}_[a-f0-9]+(?=\.)/, '');
  }

  function updateFromPlayback(payload: any): void {
    if (!payload) return;

    const incomingState = (payload.state as PlaybackState) || 'idle';
    const incomingFilename = typeof payload.filename === 'string' ? payload.filename : '';

    playbackState = incomingState;
    const isActivePlayback = incomingState === 'playing' || incomingState === 'paused';
    currentTime = isActivePlayback ? payload.current_time ?? 0 : 0;
    totalDuration = isActivePlayback ? payload.total_duration ?? 0 : 0;

    if (incomingFilename && (incomingState === 'playing' || incomingState === 'paused')) {
      playbackFilename = incomingFilename;
      playbackOriginalName = payload.original_filename || deriveOriginalName(incomingFilename);
    }
    if (!incomingFilename) {
      playbackFilename = '';
      playbackOriginalName = '';
      uploadedSize = 0;
      totalDuration = 0;
    }

    if (payload.error_message) {
      playbackNotice = payload.error_message;
    } else if (incomingState === 'playing') {
      playbackNotice = 'Playback in progress';
    } else if (incomingState === 'paused') {
      playbackNotice = 'Playback paused';
    } else if (incomingState === 'stopped') {
      playbackNotice = playbackFilename ? 'Playback stopped' : 'Upload a MIDI file to begin';
    } else if (incomingState === 'idle') {
      playbackNotice = playbackFilename ? 'Ready to play' : 'Upload a MIDI file to begin';
    }
  }

  async function fetchPlaybackStatus(): Promise<void> {
    try {
      const response = await fetch('/api/playback-status');
      if (!response.ok) return;
      const data = await response.json();
      if (data?.playback) {
        updateFromPlayback(data.playback);
      }
    } catch (error) {
      // Ignore transient network errors during polling
    }
  }

  async function loadUploadedFiles(): Promise<void> {
    if (!browser) return;
    try {
      isLoadingUploadedFiles = true;
      uploadedFilesError = '';
      const response = await fetch('/api/uploaded-midi');
      if (!response.ok) {
        uploadedFilesError = 'Failed to load uploaded files';
        uploadedFiles = [];
        return;
      }

      const data = await response.json();
      uploadedFiles = Array.isArray(data?.files) ? data.files : [];

      if (playbackFilename) {
        const match = uploadedFiles.find((file) => file.path === playbackFilename);
        if (!match) {
          playbackFilename = '';
          playbackOriginalName = '';
          uploadedSize = 0;
          playbackState = 'idle';
          currentTime = 0;
          totalDuration = 0;
          playbackNotice = 'Upload a MIDI file to begin';
        }
      }
    } catch (error) {
      uploadedFilesError = 'Failed to load uploaded files';
      uploadedFiles = [];
    } finally {
      isLoadingUploadedFiles = false;
    }
  }

  async function loadMidiOutputDevices(): Promise<void> {
    if (!browser) return;
    try {
      loadingMidiDevices = true;
      midiOutputError = '';
      const response = await fetch('/api/midi-output/devices');
      if (!response.ok) {
        midiOutputError = 'Failed to load MIDI output devices';
        midiOutputDevices = [];
        return;
      }

      const data = await response.json();
      midiOutputDevices = Array.isArray(data?.devices) ? data.devices : [];
      midiOutputConnected = data?.is_connected ?? false;
      selectedMidiOutputDevice = data?.current_device ?? null;
    } catch (error) {
      midiOutputError = 'Failed to load MIDI output devices';
      midiOutputDevices = [];
    } finally {
      loadingMidiDevices = false;
    }
  }

  async function toggleMidiOutput(enabled: boolean, device?: string): Promise<void> {
    if (!browser) return;
    try {
      midiOutputError = '';
      
      // If disabling, disconnect first
      if (!enabled && midiOutputConnected) {
        await disconnectMidiOutput();
      }
      
      const response = await fetch('/api/midi-output/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled,
          device_name: device || null
        })
      });

      if (!response.ok) {
        midiOutputError = 'Failed to update MIDI output setting';
        return;
      }

      const data = await response.json();
      midiOutputEnabled = data?.midi_output_enabled ?? false;
      
      // Reload devices after toggling
      await loadMidiOutputDevices();
    } catch (error) {
      midiOutputError = 'Network error updating MIDI output';
    }
  }

  async function connectMidiOutput(device: string): Promise<void> {
    if (!browser) return;
    try {
      midiOutputError = '';
      const response = await fetch('/api/midi-output/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_name: device })
      });

      if (!response.ok) {
        midiOutputError = 'Failed to connect to MIDI output device';
        return;
      }

      selectedMidiOutputDevice = device;
      midiOutputConnected = true;
      
      // Enable MIDI output
      await toggleMidiOutput(true, device);
    } catch (error) {
      midiOutputError = 'Network error connecting MIDI output';
    }
  }

  async function disconnectMidiOutput(): Promise<void> {
    if (!browser) return;
    try {
      midiOutputError = '';
      const response = await fetch('/api/midi-output/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        midiOutputError = 'Failed to disconnect from MIDI output device';
        return;
      }

      midiOutputConnected = false;
      selectedMidiOutputDevice = null;
    } catch (error) {
      midiOutputError = 'Network error disconnecting MIDI output';
    }
  }

  onMount(() => {
    if (!browser) return;

    fetchPlaybackStatus();
    pollingHandle = setInterval(fetchPlaybackStatus, statusPollIntervalMs);
    loadUploadedFiles();
    loadMidiOutputDevices();

    try {
      socketInstance = getSocket();
      socketInstance?.on?.('playback_status', updateFromPlayback);
      socketInstance?.emit?.('get_status');
    } catch (error) {
      // Socket setup is optional; fall back to polling
    }

    unsubscribeSocketStatus = socketStatus.subscribe((status) => {
      connectionStatus = status;
    });
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
    if (socketInstance?.off) {
      socketInstance.off('playback_status', updateFromPlayback);
    }
    if (unsubscribeSocketStatus) unsubscribeSocketStatus();
  });

  function handleFileInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      selectedFile = null;
      target.value = '';
      return;
    }
    target.value = '';
    void handleIncomingFile(file);
  }

  function handleDragOver(event: DragEvent): void {
    event.preventDefault();
    dragActive = true;
  }

  function handleDragLeave(event: DragEvent): void {
    event.preventDefault();
    const currentTarget = event.currentTarget as HTMLElement | null;
    const related = event.relatedTarget as Node | null;
    if (currentTarget && related && currentTarget.contains(related)) {
      return;
    }
    dragActive = false;
  }

  function handleDrop(event: DragEvent): void {
    event.preventDefault();
    dragActive = false;
    const file = event.dataTransfer?.files?.[0] ?? null;
    if (file) {
      void handleIncomingFile(file);
    }
  }

  function ensureFileInputRef(): HTMLInputElement | null {
    if (fileInput) {
      return fileInput;
    }

    if (typeof document !== 'undefined') {
      const fallback = document.getElementById('midi-file-input');
      if (fallback instanceof HTMLInputElement) {
        fileInput = fallback;
        return fileInput;
      }
    }
    return null;
  }

  function triggerFilePicker(): void {
    const inputEl = ensureFileInputRef();
    if (!inputEl) {
      console.warn('File input element not ready yet');
      return;
    }

    try {
      inputEl.click();
    } catch (error) {
      console.error('Unable to open file browser:', error);
    }
  }

  function handleDropZoneKey(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      triggerFilePicker();
    }
  }

  async function handleIncomingFile(file: File): Promise<void> {
    if (uploadState === 'uploading') {
      uploadError = 'Please wait for the current upload to finish.';
      return;
    }

    selectedFile = file;
    resetUploadFeedback();
    uploadState = 'idle';
    await beginUpload(file);
  }

  async function beginUpload(file?: File): Promise<void> {
    const targetFile = file ?? selectedFile;
    if (!targetFile) {
      uploadError = 'Select a MIDI file first.';
      return;
    }

    resetUploadFeedback();
    uploadState = 'uploading';
    uploadProgress = 0;

    try {
      const result = await uploadMidiFile(targetFile, (progress: UploadProgress) => {
        uploadProgress = progress.percentage;
      });

      uploadState = 'complete';
      uploadMessage = result.message || 'Upload complete.';
      await loadUploadedFiles();
      await fetchPlaybackStatus();
      selectedFile = null;
    } catch (error) {
      uploadState = 'idle';
      uploadProgress = 0;
      if (error instanceof UploadError) {
        uploadError = error.message;
      } else if (error instanceof Error) {
        uploadError = error.message;
      } else {
        uploadError = 'Upload failed.';
      }
    }
  }

  async function handlePlay(triggeredByUpload = false): Promise<void> {
    const filename = playbackFilename;
    if (!filename) {
      playbackNotice = 'Upload a MIDI file before playing.';
      return;
    }

    playbackNotice = triggeredByUpload ? 'Starting playback…' : 'Starting playback…';

    try {
      const response = await fetch('/api/playback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackState = 'playing';
        playbackNotice = data.message || 'Playback started.';
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to start playback.';
        playbackState = 'idle';
      }
    } catch (error) {
      playbackNotice = 'Network error while starting playback.';
      playbackState = 'idle';
    }
  }

  async function handlePlayToggle(): Promise<void> {
    if (!playbackFilename && playbackState !== 'playing' && playbackState !== 'paused') {
      playbackNotice = 'Upload a MIDI file before playing.';
      return;
    }

    if (playbackState === 'playing' || playbackState === 'paused') {
      await handlePause();
    } else {
      await handlePlay(false);
    }
  }

  async function handlePause(): Promise<void> {
    try {
      const response = await fetch('/api/pause', { method: 'POST' });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'Playback toggled.';
        const nextState = (data.playback_state as PlaybackState | undefined) || playbackState;
        if (nextState === 'playing' || nextState === 'paused' || nextState === 'stopped' || nextState === 'idle') {
          playbackState = nextState;
        }
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to pause playback.';
      }
    } catch (error) {
      playbackNotice = 'Network error while pausing playback.';
    }
  }

  async function handleStop(): Promise<boolean> {
    try {
      const response = await fetch('/api/stop', { method: 'POST' });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'Playback stopped.';
        playbackState = 'stopped';
        currentTime = 0;
        totalDuration = 0;
        await fetchPlaybackStatus();
        return true;
      } else {
        playbackNotice = data?.message || 'Unable to stop playback.';
        return false;
      }
    } catch (error) {
      playbackNotice = 'Network error while stopping playback.';
      return false;
    }
    return false;
  }

  async function handleListPlay(file: UploadedFileItem): Promise<void> {
    if (playbackState === 'playing' || playbackState === 'paused') {
      const stopped = await handleStop();
      if (!stopped) {
        return;
      }
    }

    playbackFilename = file.path;
    playbackOriginalName = deriveOriginalName(file.filename);
    uploadedSize = file.size;
    playbackNotice = 'Starting playback…';

    await handlePlay(false);
  }

  function formatTime(seconds: number): string {
    const safeSeconds = Math.max(0, Math.floor(seconds || 0));
    const minutes = Math.floor(safeSeconds / 60);
    const remainder = safeSeconds % 60;
    return `${minutes}:${String(remainder).padStart(2, '0')}`;
  }

  function handleUploadedFileSelection(file: UploadedFileItem): void {
    playbackFilename = file.path;
    playbackOriginalName = deriveOriginalName(file.filename);
    uploadedSize = file.size;
    playbackNotice = 'Ready to play';
    fetchPlaybackStatus();
  }

  async function handleDeleteFile(file: UploadedFileItem): Promise<void> {
    if (deletingPath) {
      return;
    }

    if (browser) {
      const confirmation = window.confirm(`Delete ${deriveOriginalName(file.filename)} from the device?`);
      if (!confirmation) {
        return;
      }
    }

    if (
      playbackFilename === file.path &&
      (playbackState === 'playing' || playbackState === 'paused')
    ) {
      playbackNotice = 'Stopping playback before deletion…';
      const stopped = await handleStop();
      if (!stopped) {
        playbackNotice = 'Unable to stop playback. Delete cancelled.';
        return;
      }
    }

    deletingPath = file.path;
    playbackNotice = 'Deleting file…';

    try {
      const response = await fetch('/api/uploaded-midi', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: file.path })
      });
      const data = await response.json().catch(() => null);

      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'File deleted.';

        if (playbackFilename === file.path) {
          playbackFilename = '';
          playbackOriginalName = '';
          uploadedSize = 0;
          playbackState = 'idle';
          currentTime = 0;
          totalDuration = 0;
        }

        await loadUploadedFiles();
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to delete file.';
      }
    } catch (error) {
      playbackNotice = 'Network error while deleting file.';
    } finally {
      deletingPath = null;
    }
  }

  $: playbackProgress = totalDuration > 0 ? Math.min(100, Math.round((currentTime / totalDuration) * 100)) : 0;
  $: if (playbackFilename && uploadedFiles.length > 0) {
    const matchedFile = uploadedFiles.find((file) => file.path === playbackFilename);
    if (matchedFile) {
      if (uploadedSize !== matchedFile.size) {
        uploadedSize = matchedFile.size;
      }
      const derivedName = deriveOriginalName(matchedFile.filename);
      if (playbackOriginalName !== derivedName) {
        playbackOriginalName = derivedName;
      }
    }
  }
</script>

<svelte:head>
  <title>Listen - Piano LED Visualizer</title>
  <meta name="description" content="Upload and play MIDI files for the Piano LED visualizer." />
</svelte:head>

<main class="listen-page">
  <div class="listen-content">
    <section class="hero-section">
      <h1>🎹 Piano LED Visualizer</h1>
      <p>Upload, manage, and play your MIDI songs from one streamlined dashboard.</p>
    </section>

    <div class="upper-row">
      <section class="playback-card">
        <div class="playback-top">
          <div class="now-playing">
            <span class="label">Now Playing</span>
            <h2 class="track-title" title={playbackDisplayName || 'No file loaded'}>
              {playbackDisplayName || 'No file loaded'}
            </h2>
            {#if playbackFilename}
              <div class="track-meta">
                <span>{formatFileSize(uploadedSize)}</span>
                <span aria-hidden="true">•</span>
                <span>{playbackState === 'playing' ? 'Playing' : playbackState === 'paused' ? 'Paused' : 'Ready'}</span>
              </div>
            {/if}
          </div>
          <span class={`connection-indicator ${connectionStatus}`}>
            {connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'connecting' ? 'Connecting…' : connectionStatus === 'error' ? 'Socket error' : 'Offline'}
          </span>
        </div>

        <div class="playback-controls">
          <button
            class={`control-button primary ${playbackState === 'playing' ? 'active' : ''}`}
            on:click={handlePlayToggle}
            disabled={!playbackFilename && playbackState !== 'playing' && playbackState !== 'paused'}
          >
            <span class="visually-hidden">{playbackState === 'playing' ? 'Pause playback' : playbackState === 'paused' ? 'Resume playback' : 'Start playback'}</span>
            <span aria-hidden="true">{playbackState === 'playing' ? '⏸' : playbackState === 'paused' ? '▶' : '▶'}</span>
          </button>
          <button
            class="control-button"
            on:click={handleStop}
            disabled={playbackState === 'idle' || playbackState === 'stopped'}
          >
            <span class="visually-hidden">Stop playback</span>
            <span aria-hidden="true">■</span>
          </button>
        </div>

        <div class="timeline">
          <div class="timeline-track">
            <div class="timeline-fill" style={`width: ${playbackProgress}%`}></div>
          </div>
          <div class="timeline-meta">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(totalDuration)}</span>
          </div>
        </div>

        {#if playbackNotice}
          <p class="playback-notice">{playbackNotice}</p>
        {/if}

        <div class="midi-output-section">
          <div class="midi-output-header">
            <label for="midi-output-toggle" class="midi-output-label">
              <input
                id="midi-output-toggle"
                type="checkbox"
                bind:checked={midiOutputEnabled}
                on:change={(e) => toggleMidiOutput(e.currentTarget.checked)}
                class="midi-toggle-input"
              />
              <span class="midi-toggle-label">Send MIDI to USB Keyboard</span>
            </label>
            <span class={`midi-status ${midiOutputConnected ? 'connected' : 'disconnected'}`}>
              {midiOutputConnected ? '🎹 Connected' : '🔌 Disconnected'}
            </span>
          </div>

          {#if midiOutputEnabled}
            <div class="midi-device-selector">
              <div class="device-selector-row">
                <label for="midi-device-select">Select Output Device:</label>
                <button
                  class="refresh-button"
                  on:click={loadMidiOutputDevices}
                  disabled={loadingMidiDevices}
                  title="Refresh device list"
                >
                  🔄 Refresh
                </button>
              </div>
              <select
                id="midi-device-select"
                bind:value={selectedMidiOutputDevice}
                on:change={(e) => e.currentTarget.value && connectMidiOutput(e.currentTarget.value)}
                disabled={loadingMidiDevices}
                class="device-dropdown"
              >
                {#if loadingMidiDevices}
                  <option value="">Loading devices...</option>
                {:else if midiOutputDevices.length === 0}
                  <option value="">No devices found</option>
                {:else}
                  <option value="">Select a device...</option>
                  {#each midiOutputDevices as device (device.id)}
                    <option value={device.name} selected={device.is_current}>
                      {device.name}
                    </option>
                  {/each}
                {/if}
              </select>
            </div>

            {#if midiOutputConnected}
              <button
                class="disconnect-button"
                on:click={disconnectMidiOutput}
                title="Disconnect from device"
              >
                ✕ Disconnect
              </button>
            {/if}

            {#if midiOutputError}
              <p class="midi-error">{midiOutputError}</p>
            {/if}
          {/if}
        </div>
      </section>

      <section class="upload-card">
        <header class="upload-header">
          <h3>Upload MIDI</h3>
          <p>Drop a file into the box or browse to pick one. Upload starts as soon as you choose a file.</p>
        </header>

        <div
          class="drop-zone"
          class:active={dragActive}
          role="button"
          tabindex="0"
          aria-label="Upload MIDI file by drag and drop"
          on:click={triggerFilePicker}
          on:keydown={handleDropZoneKey}
          on:dragover={handleDragOver}
          on:dragleave={handleDragLeave}
          on:drop={handleDrop}
        >
          <div class="drop-icon" aria-hidden="true">🎵</div>
          <p class="drop-text">Drag &amp; drop a MIDI file here</p>
          <p class="drop-subtext">
            or
            <label
              class="browse-trigger"
              for="midi-file-input"
              on:click={triggerFilePicker}
            >
              <input
                id="midi-file-input"
                bind:this={fileInput}
                type="file"
                accept=".mid,.midi"
                class="file-input-hidden"
                on:change={handleFileInput}
              />
              browse your computer
            </label>
          </p>
          {#if selectedFile}
            <p class="selected-hint" title={selectedFile.name}>
              Selected: <span>{selectedFile.name}</span> ({formatFileSize(selectedFile.size)})
            </p>
          {/if}
        </div>

        <div class="upload-feedback">
          {#if uploadState === 'uploading'}
            <div class="upload-progress">
              <div class="progress-bar">
                <div class="progress-fill" style={`width: ${uploadProgress}%`}></div>
              </div>
              <span class="progress-text">{uploadProgress}%</span>
            </div>
          {/if}

          {#if uploadMessage}
            <p class="upload-message success">{uploadMessage}</p>
          {/if}
          {#if uploadError}
            <p class="upload-message error">{uploadError}</p>
          {/if}
        </div>
      </section>
    </div>

    <section class="song-list-card">
      <header class="song-list-header">
        <div>
          <h2>MIDI Song List</h2>
          <p class="song-list-subtitle">All songs available on the Raspberry Pi</p>
        </div>
        {#if isLoadingUploadedFiles}
          <span class="list-count loading">Loading…</span>
        {:else if uploadedFilesError}
          <span class="list-count error">{uploadedFilesError}</span>
        {:else}
          <span class="list-count">{uploadedFiles.length} {uploadedFiles.length === 1 ? 'song' : 'songs'}</span>
        {/if}
      </header>
      <UploadedFileList
        files={uploadedFiles}
        selectedPath={playbackFilename}
        on:select={(event) => handleUploadedFileSelection(event.detail.file)}
        on:play={(event) => handleListPlay(event.detail.file)}
        on:delete={(event) => handleDeleteFile(event.detail.file)}
      />
    </section>
  </div>
</main>

<style>
  .listen-page {
    min-height: 100vh;
    background: #ffffff;
    padding: 2.5rem 1rem 3rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .listen-content {
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

  .upper-row {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    gap: 1.75rem;
  }

  .playback-card,
  .upload-card,
  .song-list-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.75rem;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  }

  .playback-card {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .playback-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
  }

  .now-playing .label {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .track-title {
    margin: 0;
    font-size: 1.9rem;
    font-weight: 700;
    color: #0f172a;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .track-meta {
    margin-top: 0.3rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.9rem;
    color: #475569;
  }

  .connection-indicator {
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
  }

  .connection-indicator.connected {
    background: #dcfce7;
    color: #166534;
  }

  .connection-indicator.connecting {
    background: #fef3c7;
    color: #92400e;
  }

  .connection-indicator.error {
    background: #fee2e2;
    color: #b91c1c;
  }

  .connection-indicator.disconnected {
    background: #dbeafe;
    color: #1d4ed8;
  }

  .playback-controls {
    display: inline-flex;
    align-items: center;
    gap: 1rem;
  }

  .control-button {
    width: 3.25rem;
    height: 3.25rem;
    border-radius: 999px;
    border: none;
    background: #e2e8f0;
    color: #0f172a;
    font-size: 1.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 8px 16px rgba(15, 23, 42, 0.15);
  }

  .control-button.primary {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff;
  }

  .control-button.primary.active {
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
  }

  .control-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 12px 22px rgba(15, 23, 42, 0.18);
  }

  .control-button:disabled {
    cursor: not-allowed;
    opacity: 0.6;
    box-shadow: none;
  }

  .timeline {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .timeline-track {
    width: 100%;
    height: 12px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
  }

  .timeline-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    transition: width 0.2s ease;
  }

  .timeline-meta {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    color: #475569;
  }

  .playback-notice {
    margin: 0;
    font-size: 0.95rem;
    color: #1e293b;
  }

  .upload-card {
    position: relative;
    border: 1px solid #e2e8f0;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
  }

  .upload-header {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .upload-header h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #0f172a;
  }

  .upload-header p {
    margin: 0;
    color: #475569;
    font-size: 0.95rem;
  }

  .drop-zone {
    width: 100%;
    max-width: 420px;
    border: 2px dashed #cbd5f5;
    border-radius: 16px;
    padding: 2.5rem 1.5rem;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
    transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
  }

  .drop-zone.active {
    border-color: #2563eb;
    background: #eff6ff;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.15);
  }

  .drop-icon {
    font-size: 2.5rem;
    background: #eef2ff;
    color: #1d4ed8;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .drop-text {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: #0f172a;
  }

  .drop-subtext {
    margin: 0;
    color: #475569;
    font-size: 0.95rem;
  }

  .browse-trigger {
    color: #2563eb;
    font-weight: 600;
    cursor: pointer;
    position: relative;
    text-decoration: underline;
  }

  .file-input-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .selected-hint {
    margin: 0;
    font-size: 0.9rem;
    color: #475569;
    max-width: 100%;
    word-break: break-word;
  }

  .selected-hint span {
    color: #1d4ed8;
    font-weight: 600;
  }

  .upload-feedback {
    width: 100%;
    max-width: 420px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
  }

  .upload-progress {
    width: 100%;
    max-width: 360px;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .progress-bar {
    flex: 1;
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #3b82f6);
  }

  .progress-text {
    font-weight: 600;
    color: #2563eb;
  }

  .upload-message {
    margin: 0;
    font-size: 0.9rem;
  }

  .upload-message.success {
    color: #047857;
  }

  .upload-message.error {
    color: #b91c1c;
  }

  .song-list-card {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .song-list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .song-list-header h2 {
    margin: 0;
    font-size: 1.4rem;
    color: #0f172a;
  }

  .song-list-subtitle {
    margin: 0.25rem 0 0;
    color: #475569;
    font-size: 0.9rem;
  }

  .list-count {
    padding: 0.4rem 0.85rem;
    border-radius: 999px;
    background: #f1f5f9;
    color: #1f2937;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .list-count.loading {
    background: #fef3c7;
    color: #92400e;
  }

  .list-count.error {
    background: #fee2e2;
    color: #b91c1c;
  }

  .midi-output-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .midi-output-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .midi-output-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    user-select: none;
  }

  .midi-toggle-input {
    width: 1.25rem;
    height: 1.25rem;
    cursor: pointer;
    accent-color: #0f172a;
  }

  .midi-toggle-label {
    font-weight: 500;
    color: #1f2937;
  }

  .midi-status {
    font-size: 0.875rem;
    padding: 0.4rem 0.75rem;
    border-radius: 0.375rem;
    background: #f0fdf4;
    color: #166534;
    font-weight: 600;
  }

  .midi-status.disconnected {
    background: #fef2f2;
    color: #991b1b;
  }

  .midi-device-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .device-selector-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .midi-device-selector label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #1f2937;
  }

  .refresh-button {
    padding: 0.4rem 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    background: #f8fafc;
    font-size: 0.8rem;
    font-weight: 500;
    color: #1f2937;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .refresh-button:hover:not(:disabled) {
    border-color: #0f172a;
    background: #ffffff;
    box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.1);
  }

  .refresh-button:active:not(:disabled) {
    transform: scale(0.95);
  }

  .refresh-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .device-dropdown {
    padding: 0.625rem 0.875rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    background: white;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .device-dropdown:hover:not(:disabled) {
    border-color: #94a3b8;
    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.05);
  }

  .device-dropdown:focus {
    outline: none;
    border-color: #0f172a;
    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.1);
  }

  .device-dropdown:disabled {
    background: #f8fafc;
    color: #94a3b8;
    cursor: not-allowed;
  }

  .disconnect-button {
    padding: 0.5rem 0.875rem;
    border: 1px solid #fecaca;
    border-radius: 0.375rem;
    background: #fee2e2;
    color: #991b1b;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .disconnect-button:hover {
    background: #fca5a5;
    border-color: #dc2626;
    color: #7f1d1d;
  }

  .disconnect-button:active {
    transform: scale(0.95);
  }

  .midi-error {
    margin: 0;
    padding: 0.75rem;
    background: #fee2e2;
    color: #991b1b;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 960px) {
    .upper-row {
      grid-template-columns: 1fr;
    }

    .upload-card {
      padding: 1.5rem;
    }
    
    .drop-zone,
    .upload-feedback {
      max-width: 100%;
    }
  }

  @media (max-width: 640px) {
    .listen-page {
      padding: 1.75rem 0.75rem 2.25rem;
    }

    .hero-section {
      padding: 2rem 1.25rem;
    }

    .playback-card,
    .upload-card,
    .song-list-card {
      padding: 1.5rem;
    }

    .drop-zone {
      padding: 2rem 1.25rem;
    }

    .playback-controls {
      gap: 0.75rem;
    }

    .control-button {
      width: 3rem;
      height: 3rem;
    }

    .song-list-header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
