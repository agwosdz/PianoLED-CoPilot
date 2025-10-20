<script lang="ts">
	import { onMount } from 'svelte';
	import UploadedFileList from '$lib/components/UploadedFileList.svelte';

	type UploadedFile = {
		filename: string;
		path: string;
		size: number;
		modified: string;
	};

	interface PlaybackStatus {
		state: string;
		current_time: number;
		total_duration: number;
		filename: string | null;
		progress_percentage: number;
		error_message: string | null;
	}

	let playbackStatus: PlaybackStatus = {
		state: 'idle',
		current_time: 0,
		total_duration: 0,
		filename: null,
		progress_percentage: 0,
		error_message: null
	};

	let uploadedFiles: UploadedFile[] = [];
	let selectedFile: string | null = null;
	let isPlaying = false;
	let currentTime = 0;
	let totalDuration = 0;
	let isLoadingFiles = false;
	let filesError = '';

	// MIDI input state
	let midiInputEnabled = false;
	let midiInputDevices: Array<{ name: string; id: number; status: string; is_current: boolean }> = [];
	let selectedMidiInputDevice: string | null = null;
	let midiInputConnected = false;
	let loadingMidiDevices = false;
	let midiInputError = '';


	async function loadUploadedFiles() {
		try {
			isLoadingFiles = true;
			filesError = '';
			const response = await fetch('/api/uploaded-midi');
			if (response.ok) {
				const data = await response.json();
				const files = data.files || [];
				uploadedFiles = files.map((f: any) => ({
					filename: f.filename || f.name,
					path: f.path,
					size: f.size,
					modified: f.modified || new Date().toISOString()
				}));
			}
		} catch (error) {
			console.error('Failed to load uploaded files:', error);
			filesError = 'Failed to load files';
			uploadedFiles = [];
		} finally {
			isLoadingFiles = false;
		}
	}

	async function fetchPlaybackStatus() {
		try {
			const response = await fetch('/api/playback-status');
			if (response.ok) {
				const data = await response.json();
				playbackStatus = data;
				currentTime = data.current_time || 0;
				if (data.total_duration > 0) {
					totalDuration = data.total_duration;
				}
				isPlaying = data.state === 'playing';

				if (data.filename && !selectedFile) {
					selectedFile = data.filename;
				}
			}
		} catch (error) {
			console.error('Failed to fetch playback status:', error);
		}
	}

	async function handlePlayPause() {
		if (!selectedFile) return;

		try {
			if (!isPlaying) {
				console.log(`▶ Playing: ${selectedFile}`);
				try {
					await fetch('/api/stop', { method: 'POST' });
				} catch (e) {
					// Ignore
				}
			} else {
				console.log(`⏸ Pausing`);
			}

			const method = isPlaying ? 'pause' : 'play';
			const response = await fetch(`/api/${method}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ filename: selectedFile })
			});

			if (response.ok) {
				await fetchPlaybackStatus();
			} else {
				console.error(`Failed to ${method}: ${response.status}`);
			}
		} catch (error) {
			console.error('Failed to control playback:', error);
		}
	}

	async function handleStop() {
		try {
			const response = await fetch('/api/stop', { method: 'POST' });
			if (response.ok) {
				await fetchPlaybackStatus();
				selectedFile = null;
			}
		} catch (error) {
			console.error('Failed to stop playback:', error);
		}
	}

	function handleFileSelect(event: CustomEvent<{ file: UploadedFile }>) {
		selectedFile = event.detail.file.path;
		console.log(`✓ Selected ${selectedFile}`);
	}

	function handleFilePlay(event: CustomEvent<{ file: UploadedFile }>) {
		selectedFile = event.detail.file.path;
		handlePlayPause();
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	async function loadMidiInputDevices(): Promise<void> {
		try {
			loadingMidiDevices = true;
			midiInputError = '';
			const response = await fetch('/api/midi-input/devices');
			if (response.ok) {
				const data = await response.json();
				midiInputDevices = data.devices || [];
				if (midiInputDevices.length > 0 && !selectedMidiInputDevice) {
					const currentDevice = midiInputDevices.find(d => d.is_current);
					if (currentDevice) {
						selectedMidiInputDevice = currentDevice.name;
					}
				}
			}
		} catch (error) {
			console.error('Failed to load MIDI input devices:', error);
			midiInputError = 'Failed to load MIDI input devices';
		} finally {
			loadingMidiDevices = false;
		}
	}

	async function connectMidiInput(deviceName: string): Promise<void> {
		try {
			midiInputError = '';
			const response = await fetch('/api/midi-input/start', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ device_name: deviceName, enable_usb: true, enable_rtpmidi: false })
			});
			if (response.ok) {
				const data = await response.json();
				midiInputConnected = true;
				selectedMidiInputDevice = deviceName;
				console.log('MIDI input connected:', data.message);
			} else {
				midiInputError = 'Failed to connect to MIDI input device';
			}
		} catch (error) {
			console.error('Failed to connect MIDI input:', error);
			midiInputError = 'Network error connecting MIDI input';
		}
	}

	async function disconnectMidiInput(): Promise<void> {
		try {
			midiInputError = '';
			const response = await fetch('/api/midi-input/stop', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});
			if (response.ok) {
				midiInputConnected = false;
				selectedMidiInputDevice = null;
				console.log('MIDI input disconnected');
			} else {
				midiInputError = 'Failed to disconnect from MIDI input device';
			}
		} catch (error) {
			console.error('Failed to disconnect MIDI input:', error);
			midiInputError = 'Network error disconnecting MIDI input';
		}
	}

	async function toggleMidiInput(enabled: boolean): Promise<void> {
		try {
			midiInputError = '';
			if (enabled) {
				await loadMidiInputDevices();
				// Auto-connect to first available device
				if (midiInputDevices.length > 0) {
					const firstDevice = midiInputDevices[0];
					selectedMidiInputDevice = firstDevice.name;
					await connectMidiInput(firstDevice.name);
				}
			} else {
				await disconnectMidiInput();
			}
		} catch (error) {
			console.error('Failed to toggle MIDI input:', error);
			midiInputError = 'Failed to toggle MIDI input';
		}
	}

	async function checkMidiInputStatus(): Promise<void> {
		try {
			const response = await fetch('/api/midi-input/status');
			if (response.ok) {
				const data = await response.json();
				midiInputConnected = data.listening || false;
				if (data.current_device) {
					selectedMidiInputDevice = data.current_device;
					midiInputEnabled = true;
				}
			}
		} catch (error) {
			console.error('Failed to check MIDI input status:', error);
		}
	}

	onMount(() => {
		loadUploadedFiles();
		const statusInterval = setInterval(fetchPlaybackStatus, 100);
		const filesInterval = setInterval(loadUploadedFiles, 5000);
		const midiStatusInterval = setInterval(checkMidiInputStatus, 1000);

		return () => {
			clearInterval(statusInterval);
			clearInterval(filesInterval);
			clearInterval(midiStatusInterval);
		};
	});

</script>

<div class="page-wrapper">
	<div class="page-content">
		<h1>MIDI Playback</h1>

		<!-- File Selection -->
		<div class="section">
			<h2>Select File to Play</h2>
			{#if isLoadingFiles}
				<div class="loading">Loading files...</div>
			{:else if filesError}
				<div class="error-message">{filesError}</div>
			{:else}
				<UploadedFileList 
					files={uploadedFiles}
					selectedPath={selectedFile}
					on:select={handleFileSelect}
					on:play={handleFilePlay}
					on:delete={() => {}}
				/>
			{/if}
		</div>

		<!-- Playback Controls -->
		<div class="section">
			<div class="controls-group">
				<button
					class="btn btn-play"
					on:click={handlePlayPause}
					disabled={!selectedFile}
					type="button"
				>
					{isPlaying ? '⏸ Pause' : '▶ Play'}
				</button>
				<button
					class="btn btn-stop"
					on:click={handleStop}
					disabled={!selectedFile}
					type="button"
				>
					⏹ Stop
				</button>

				<div class="time-display">
					<span>{formatTime(currentTime)}</span>
					<span>/</span>
					<span>{formatTime(totalDuration)}</span>
				</div>
			</div>

			<!-- Progress Bar -->
			<div class="progress-bar">
				<div class="progress-fill" style="width: {playbackStatus.progress_percentage}%"></div>
			</div>

			{#if playbackStatus.error_message}
				<div class="error-message">{playbackStatus.error_message}</div>
			{/if}
		</div>

		<!-- Now Playing & MIDI Input -->
		{#if selectedFile}
			<div class="section">
				<h2>Now Playing</h2>
				<p class="now-playing-file">
					<strong>{selectedFile.split('/').pop()}</strong>
				</p>
				<p class="now-playing-status">
					Status: <strong>{isPlaying ? '🎵 Playing' : 'Paused'}</strong>
				</p>

				<div class="midi-input-section">
					<div class="midi-input-header">
						<label for="midi-input-toggle" class="midi-input-label">
							<input
								id="midi-input-toggle"
								type="checkbox"
								bind:checked={midiInputEnabled}
								on:change={(e) => toggleMidiInput(e.currentTarget.checked)}
								class="midi-toggle-input"
							/>
							<span class="midi-toggle-label">Receive MIDI from USB Keyboard</span>
						</label>
						<span class={`midi-status ${midiInputConnected ? 'connected' : 'disconnected'}`}>
							{midiInputConnected ? '🎹 Connected' : '🔌 Disconnected'}
						</span>
					</div>

					{#if midiInputEnabled}
						<div class="midi-device-selector">
							<div class="device-selector-row">
								<label for="midi-device-select">Select Input Device:</label>
								<button
									class="refresh-button"
									on:click={loadMidiInputDevices}
									disabled={loadingMidiDevices}
									title="Refresh device list"
								>
									🔄 Refresh
								</button>
							</div>
							<select
								id="midi-device-select"
								bind:value={selectedMidiInputDevice}
								on:change={(e) => e.currentTarget.value && connectMidiInput(e.currentTarget.value)}
								disabled={loadingMidiDevices}
								class="device-dropdown"
							>
								{#if loadingMidiDevices}
									<option value="">Loading devices...</option>
								{:else if midiInputDevices.length === 0}
									<option value="">No devices found</option>
								{:else}
									<option value="">Select a device...</option>
									{#each midiInputDevices as device (device.id)}
										<option value={device.name} selected={device.is_current}>
											{device.name}
										</option>
									{/each}
								{/if}
							</select>
						</div>

						{#if midiInputConnected}
							<button
								class="disconnect-button"
								on:click={disconnectMidiInput}
								title="Disconnect from device"
							>
								✕ Disconnect
							</button>
						{/if}

						{#if midiInputError}
							<p class="midi-error">{midiInputError}</p>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.page-wrapper {
		background: #ffffff;
		min-height: 100vh;
		display: flex;
	}

	.page-content {
		flex: 1;
		padding: 2.5rem 1rem 3rem;
		max-width: 900px;
		margin: 0 auto;
		width: 100%;
	}

	h1 {
		font-size: 2rem;
		font-weight: 700;
		color: #1f2937;
		margin: 0 0 2rem;
		letter-spacing: -0.02em;
	}

	h2 {
		font-size: 1.1rem;
		font-weight: 600;
		color: #0f172a;
		margin: 0 0 1rem;
	}

	.section {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		margin-bottom: 1.75rem;
	}

	.loading {
		text-align: center;
		color: #64748b;
		padding: 2rem;
	}

	.controls-group {
		display: flex;
		gap: 1rem;
		align-items: center;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}

	.btn {
		padding: 0.75rem 1.5rem;
		font-size: 1rem;
		font-weight: 600;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s ease;
		white-space: nowrap;
	}

	.btn-play {
		background: linear-gradient(90deg, #2563eb, #3b82f6);
		color: white;
	}

	.btn-play:hover:not(:disabled) {
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
		transform: translateY(-2px);
	}

	.btn-play:active:not(:disabled) {
		transform: translateY(0);
	}

	.btn-stop {
		background: #e2e8f0;
		color: #0f172a;
	}

	.btn-stop:hover:not(:disabled) {
		background: #cbd5e1;
		transform: translateY(-2px);
	}

	.btn-stop:active:not(:disabled) {
		transform: translateY(0);
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.time-display {
		display: flex;
		gap: 0.5rem;
		font-size: 0.95rem;
		font-weight: 600;
		color: #1e293b;
		margin-left: auto;
	}

	.progress-bar {
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
		cursor: pointer;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #2563eb, #3b82f6);
		transition: width 0.05s linear;
	}

	.error-message {
		color: #dc2626;
		font-size: 0.9rem;
		margin-top: 0.75rem;
	}

	.selected-file-info {
		font-size: 0.95rem;
		color: #1e293b;
		margin: 0;
		word-break: break-word;
		overflow-wrap: break-word;
		hyphens: auto;
		max-width: 100%;
	}

	.status-info {
		font-size: 0.95rem;
		color: #1e293b;
		margin: 0.5rem 0 0 0;
	}

	.now-playing-file {
		font-size: 0.95rem;
		color: #1e293b;
		margin: 0;
		word-break: break-word;
		overflow-wrap: break-word;
		hyphens: auto;
		max-width: 100%;
	}

	.now-playing-status {
		font-size: 0.95rem;
		color: #1e293b;
		margin: 0.5rem 0 1.5rem 0;
	}

	.midi-input-section {
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid #e2e8f0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.midi-input-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.midi-input-label {
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

	@media (max-width: 768px) {
		.page-content {
			padding: 1.5rem 1rem 2rem;
		}

		h1 {
			font-size: 1.5rem;
			margin-bottom: 1.5rem;
		}

		.section {
			padding: 1.25rem;
			margin-bottom: 1rem;
		}

		.controls-group {
			gap: 0.75rem;
			margin-bottom: 0.75rem;
		}

		.btn {
			padding: 0.65rem 1.25rem;
			font-size: 0.9rem;
		}

		.time-display {
			flex-basis: 100%;
			justify-content: center;
			margin-left: 0;
			font-size: 0.9rem;
		}
	}
</style>
