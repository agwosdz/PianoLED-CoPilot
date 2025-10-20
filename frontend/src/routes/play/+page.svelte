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

		<div class="main-grid">
			<!-- Playback Card -->
			<section class="playback-card grid-section">
			<div class="playback-top">
				<div class="now-playing">
					<span class="label">Now Playing</span>
					<h2 class="track-title" title={selectedFile ? selectedFile.split('/').pop() : 'No file loaded'}>
						{selectedFile ? selectedFile.split('/').pop() : 'No file loaded'}
					</h2>
					{#if selectedFile}
						<div class="track-meta">
							<span>{isPlaying ? 'Playing' : 'Paused'}</span>
						</div>
					{/if}
				</div>
				<span class={`connection-indicator ${midiInputConnected ? 'connected' : 'disconnected'}`}>
					{midiInputConnected ? 'Connected' : 'Disconnected'}
				</span>
			</div>

			<div class="playback-controls">
				<button
					class={`control-button primary ${isPlaying ? 'active' : ''}`}
					on:click={handlePlayPause}
					disabled={!selectedFile}
				>
					<span class="visually-hidden">{isPlaying ? 'Pause playback' : 'Start playback'}</span>
					<span aria-hidden="true">{isPlaying ? '⏸' : '▶'}</span>
				</button>
				<button
					class="control-button"
					on:click={handleStop}
					disabled={!selectedFile}
				>
					<span class="visually-hidden">Stop playback</span>
					<span aria-hidden="true">■</span>
				</button>
			</div>

			<div class="timeline">
				<div class="timeline-track">
					<div class="timeline-fill" style={`width: ${playbackStatus.progress_percentage}%`}></div>
				</div>
				<div class="timeline-meta">
					<span>{formatTime(currentTime)}</span>
					<span>{formatTime(totalDuration)}</span>
				</div>
			</div>

			{#if playbackStatus.error_message}
				<p class="playback-notice">{playbackStatus.error_message}</p>
			{/if}

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
		</section>

		<!-- Options Card (Placeholder) -->
		<section class="options-card grid-section">
			<header class="options-header">
				<h3>Playback Options</h3>
				<p>Configure playback settings and preferences.</p>
			</header>
			
			<div class="options-content">
				<div class="option-item">
					<label for="loop-toggle">Loop Playback</label>
					<input type="checkbox" id="loop-toggle" disabled title="Coming soon">
				</div>
				<div class="option-item">
					<label for="speed-control">Playback Speed</label>
					<input type="range" id="speed-control" min="0.5" max="2" step="0.1" value="1" disabled title="Coming soon">
				</div>
				<p class="placeholder-note">More options coming soon...</p>
			</div>
		</section>

		</div>

		<!-- MIDI Song List -->
		<section class="song-list-card">
		<div class="song-list-header">
			<div>
				<h2>MIDI Song List</h2>
				<p>All songs available for playback</p>
			</div>
			<span class="song-count">{uploadedFiles.length} songs</span>
		</div>

		{#if isLoadingFiles}
			<div class="loading">Loading files...</div>
		{:else if filesError}
			<div class="error-message">{filesError}</div>
		{:else if uploadedFiles.length === 0}
			<p class="no-files">No MIDI files uploaded yet. Use the Listen page to upload files.</p>
		{:else}
			<UploadedFileList 
				files={uploadedFiles}
				selectedPath={selectedFile}
				on:select={handleFileSelect}
				on:play={handleFilePlay}
				on:delete={() => {}}
			/>
		{/if}
	</section>
	</div>
</div>

<style>
	.page-wrapper {
		background: #ffffff;
		min-height: 100vh;
	}

	.page-content {
		padding: 2.5rem 1rem 3rem;
		max-width: 1200px;
		margin: 0 auto;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 2rem;
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

	.playback-card {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
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

	/* Grid layout for responsive sections */
	.main-grid {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: 1.75rem;
	}

	.grid-section {
		display: flex;
		flex-direction: column;
	}

	.options-card {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
	}

	.options-card h3 {
		font-size: 1rem;
		font-weight: 600;
		color: #0f172a;
		margin: 0 0 1rem;
	}

	.options-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.option-item {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.option-item label {
		font-size: 0.9rem;
		font-weight: 500;
		color: #1f2937;
	}

	.option-item input[type='checkbox'],
	.option-item input[type='range'] {
		cursor: pointer;
		opacity: 0.6;
	}

	.option-item input:disabled {
		cursor: not-allowed;
	}

	.placeholder-note {
		margin: 0.5rem 0 0;
		font-size: 0.85rem;
		color: #94a3b8;
		font-style: italic;
	}

	.song-list-card {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
	}

	.song-list-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.5rem;
	}

	.song-list-header div h2 {
		margin: 0;
	}

	.song-list-header div p {
		margin: 0.25rem 0 0;
		color: #64748b;
		font-size: 0.9rem;
	}

	.song-count {
		display: inline-block;
		padding: 0.4rem 0.875rem;
		background: #e0e7ff;
		color: #3730a3;
		border-radius: 0.375rem;
		font-size: 0.85rem;
		font-weight: 600;
	}

	.no-files {
		margin: 0;
		padding: 1.5rem;
		text-align: center;
		color: #64748b;
		font-size: 0.95rem;
	}

	.error-message {
		margin: 0;
		padding: 0.75rem 1rem;
		background: #fee2e2;
		color: #991b1b;
		border-radius: 0.375rem;
		font-size: 0.9rem;
	}

	@media (max-width: 960px) {
		.main-grid {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 640px) {
		.page-wrapper {
			padding: 1.75rem 0.75rem 2.25rem;
		}

		h1 {
			font-size: 1.5rem;
			margin-bottom: 1.5rem;
		}

		.playback-card,
		.options-card,
		.song-list-card {
			padding: 1.5rem;
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
