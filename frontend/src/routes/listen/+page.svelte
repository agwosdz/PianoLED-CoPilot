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

  let connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error' = 'connecting';
  let socketInstance: any = null;
  let unsubscribeSocketStatus: (() => void) | null = null;
  let pollingHandle: ReturnType<typeof setInterval> | null = null;

  const autoPlayAfterUpload = true;
  const statusPollIntervalMs = 3000;

  function resetUploadFeedback(): void {
    uploadMessage = '';
    uploadError = '';
  }

  function deriveOriginalName(filename: string): string {
    if (!filename) return '';
    return filename.replace(/_\d{8}_\d{6}_[a-f0-9]+/, '');
  }

  function updateFromPlayback(payload: any): void {
    if (!payload) return;
    playbackState = (payload.state as PlaybackState) || 'idle';
    currentTime = payload.current_time ?? 0;
    totalDuration = payload.total_duration ?? 0;

    if (payload.filename) {
      playbackFilename = payload.filename;
      playbackOriginalName = payload.original_filename || deriveOriginalName(playbackFilename);
    }

    if (payload.error_message) {
      playbackNotice = payload.error_message;
    } else if (playbackState === 'playing') {
      playbackNotice = 'Playback in progress';
    } else if (playbackState === 'paused') {
      playbackNotice = 'Playback paused';
    } else if (playbackState === 'stopped') {
      playbackNotice = 'Playback stopped';
    } else if (playbackFilename) {
      playbackNotice = 'Ready to play';
    } else {
      playbackNotice = 'Upload a MIDI file to begin';
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

  onMount(() => {
    if (!browser) return;

    fetchPlaybackStatus();
    pollingHandle = setInterval(fetchPlaybackStatus, statusPollIntervalMs);

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

    if (!playbackFilename && browser) {
      const cached = window.localStorage.getItem('lastUploadedFile');
      if (cached) {
        playbackFilename = cached;
        playbackOriginalName = deriveOriginalName(cached);
      }
    }
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
      return;
    }
    selectedFile = file;
    uploadedSize = file.size;
    resetUploadFeedback();
  }

  function handleDragOver(event: DragEvent): void {
    event.preventDefault();
    dragActive = true;
  }

  function handleDragLeave(event: DragEvent): void {
    event.preventDefault();
    dragActive = false;
  }


  function handleDrop(event: DragEvent): void {
    event.preventDefault();
    dragActive = false;
    const file = event.dataTransfer?.files?.[0] ?? null;
    if (file) {
      selectedFile = file;
      uploadedSize = file.size;
      resetUploadFeedback();
    }
  }

  async function beginUpload(): Promise<void> {
    if (!selectedFile) {
      uploadError = 'Select a MIDI file first.';
      return;
    }

    resetUploadFeedback();
    uploadState = 'uploading';
    uploadProgress = 0;

    try {
      const result = await uploadMidiFile(selectedFile, (progress: UploadProgress) => {
        uploadProgress = progress.percentage;
      });

      uploadState = 'complete';
      uploadMessage = result.message || 'Upload complete.';
      playbackFilename = result.filename || playbackFilename;
      playbackOriginalName = result.original_filename || deriveOriginalName(playbackFilename);
      uploadedSize = result.size ?? selectedFile.size;

      if (browser && playbackFilename) {
        window.localStorage.setItem('lastUploadedFile', playbackFilename);
      }

      await fetchPlaybackStatus();

      if (autoPlayAfterUpload && playbackFilename) {
        await handlePlay(true);
      }
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

    playbackNotice = triggeredByUpload ? 'Starting playback...' : 'Starting playback...';

    try {
      const response = await fetch('/api/play', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'Playback started.';
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to start playback.';
      }
    } catch (error) {
      playbackNotice = 'Network error while starting playback.';
    }
  }

  async function handlePause(): Promise<void> {
    try {
      const response = await fetch('/api/pause', { method: 'POST' });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'Playback toggled.';
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to pause playback.';
      }
    } catch (error) {
      playbackNotice = 'Network error while pausing playback.';
    }
  }

  async function handleStop(): Promise<void> {
    try {
      const response = await fetch('/api/stop', { method: 'POST' });
      const data = await response.json();
      if (response.ok && data?.status === 'success') {
        playbackNotice = data.message || 'Playback stopped.';
        await fetchPlaybackStatus();
      } else {
        playbackNotice = data?.message || 'Unable to stop playback.';
      }
    } catch (error) {
      playbackNotice = 'Network error while stopping playback.';
    }
  }

  function formatTime(seconds: number): string {
    const safeSeconds = Math.max(0, Math.floor(seconds || 0));
    const minutes = Math.floor(safeSeconds / 60);
    const remainder = safeSeconds % 60;
    return `${minutes}:${String(remainder).padStart(2, '0')}`;
  }

  $: playbackProgress = totalDuration > 0 ? Math.min(100, Math.round((currentTime / totalDuration) * 100)) : 0;
</script>

<svelte:head>
  <title>Listen - Piano LED Visualizer</title>
  <meta name="description" content="Upload and play MIDI files for the Piano LED visualizer." />
</svelte:head>

<main class="listen-page">
  <div class="listen-container">
    <section class="panel upload-panel">
      <header>
        <h1>Listen</h1>
        <p class="subtitle">Upload a MIDI file and start playback from one place.</p>
      </header>

      <div
        class:drag-active={dragActive}
        class="drop-zone"
        on:dragover={handleDragOver}
        on:dragleave={handleDragLeave}
        on:drop={handleDrop}
      >
        <div class="drop-zone-content">
          <p class="drop-title">Drag and drop a MIDI file here</p>
          <p class="drop-meta">.mid or .midi up to 1 MB</p>
          <label class="file-picker">
            <input type="file" accept=".mid,.midi" on:change={handleFileInput} />
            <span>Browse files</span>
          </label>
        </div>
      </div>

      {#if selectedFile}
        <div class="file-summary">
          <div>
            <span class="file-name">{selectedFile.name}</span>
            <span class="file-size">{formatFileSize(selectedFile.size)}</span>
          </div>
        </div>
      {/if}

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

      <button class="primary" on:click={beginUpload} disabled={uploadState === 'uploading'}>
        {uploadState === 'uploading' ? 'Uploading…' : 'Upload MIDI'}
      </button>
    </section>

    <section class="panel playback-panel">
      <header class="playback-header">
        <h2>Playback</h2>
        <span class={`status ${connectionStatus}`}>
          {connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'connecting' ? 'Connecting…' : connectionStatus === 'error' ? 'Socket error' : 'Offline'}
        </span>
      </header>

      <div class="track-summary">
        <p class="track-name">{playbackOriginalName || playbackFilename || 'No file loaded'}</p>
        {#if playbackFilename}
          <p class="track-meta">{formatFileSize(uploadedSize)} · {playbackState === 'playing' ? 'Playing' : playbackState === 'paused' ? 'Paused' : 'Ready'}</p>
        {/if}
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

      <div class="controls">
        <button class="secondary" on:click={() => handlePlay(false)} disabled={!playbackFilename || playbackState === 'playing'}>Play</button>
        <button class="secondary" on:click={handlePause} disabled={playbackState === 'idle' || playbackState === 'stopped'}>
          {playbackState === 'paused' ? 'Resume' : 'Pause'}
        </button>
        <button class="secondary" on:click={handleStop} disabled={playbackState === 'idle' || playbackState === 'stopped'}>Stop</button>
      </div>
    </section>
  </div>
</main>

<style>
  .listen-page {
    min-height: 100vh;
    background: #f8fafc;
    padding: 2rem 1rem;
    display: flex;
    justify-content: center;
  }

  .listen-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    max-width: 960px;
    width: 100%;
  }

  .panel {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.75rem;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .upload-panel header h1 {
    margin: 0;
    font-size: 1.9rem;
    color: #0f172a;
  }

  .subtitle {
    margin: 0;
    color: #475569;
  }

  .drop-zone {
    border: 2px dashed #cbd5f5;
    border-radius: 12px;
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 1.5rem;
    transition: border-color 0.2s ease, background-color 0.2s ease;
    background: #f1f5f9;
  }

  .drop-zone.drag-active {
    border-color: #2563eb;
    background: #e0ecff;
  }

  .drop-zone-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    color: #1e293b;
  }

  .drop-title {
    font-weight: 600;
    margin: 0;
  }

  .drop-meta {
    margin: 0;
    color: #64748b;
    font-size: 0.9rem;
  }

  .file-picker {
    margin-top: 0.75rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.65rem 1.2rem;
    border-radius: 8px;
    background: #2563eb;
    color: #ffffff;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .file-picker:hover {
    background: #1d4ed8;
  }

  .file-picker input {
    display: none;
  }

  .file-summary {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-radius: 10px;
    background: #e2e8f0;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .file-name {
    font-weight: 600;
  }

  .file-size {
    color: #1e293b;
  }

  .upload-progress {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .progress-bar {
    flex: 1;
    height: 12px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    transition: width 0.2s ease;
  }

  .progress-text {
    font-weight: 600;
    color: #2563eb;
  }

  .upload-message {
    margin: 0;
    font-size: 0.95rem;
  }

  .upload-message.success {
    color: #047857;
  }

  .upload-message.error {
    color: #b91c1c;
  }

  .primary {
    border: none;
    border-radius: 10px;
    padding: 0.75rem 1.25rem;
    font-weight: 600;
    background: #2563eb;
    color: #ffffff;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .primary:disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .primary:not(:disabled):hover {
    background: #1d4ed8;
  }

  .playback-panel {
    gap: 1.25rem;
  }

  .playback-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
  }

  .playback-header h2 {
    margin: 0;
    color: #0f172a;
  }

  .status {
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .status.connected {
    background: #dcfce7;
    color: #166534;
  }

  .status.connecting {
    background: #fef3c7;
    color: #92400e;
  }

  .status.error {
    background: #fee2e2;
    color: #b91c1c;
  }

  .status.disconnected {
    background: #dbeafe;
    color: #1d4ed8;
  }

  .track-summary {
    background: #f1f5f9;
    border-radius: 12px;
    padding: 1rem;
  }

  .track-name {
    margin: 0;
    font-weight: 600;
    color: #0f172a;
  }

  .track-meta {
    margin: 0.25rem 0 0;
    color: #475569;
    font-size: 0.9rem;
  }

  .timeline {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .timeline-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .timeline-fill {
    height: 100%;
    background: linear-gradient(90deg, #2563eb, #3b82f6);
  }

  .timeline-meta {
    display: flex;
    justify-content: space-between;
    color: #475569;
    font-size: 0.85rem;
  }

  .playback-notice {
    margin: 0;
    color: #1e293b;
    font-size: 0.95rem;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .secondary {
    flex: 1 1 100px;
    border: none;
    border-radius: 10px;
    padding: 0.65rem 1rem;
    font-weight: 600;
    background: #e2e8f0;
    color: #0f172a;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .secondary:hover:not(:disabled) {
    background: #cbd5f5;
  }

  .secondary:disabled {
    cursor: not-allowed;
    background: #cbd5e1;
    color: #64748b;
  }

  @media (max-width: 640px) {
    .listen-page {
      padding: 1.25rem 0.75rem;
    }

    .panel {
      padding: 1.5rem;
    }
  }
</style>
