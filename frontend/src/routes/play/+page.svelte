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

	// Learning mode state (per-hand configuration)
	let leftHandWaitForNotes = false;
	let leftHandWhiteColor = '#ff6b6b'; // Coral-red
	let leftHandBlackColor = '#c92a2a'; // Deep rose
	let rightHandWaitForNotes = false;
	let rightHandWhiteColor = '#006496'; // Deep teal/cyan
	let rightHandBlackColor = '#960064'; // Deep magenta/purple
	let timingWindow = 500;
	let learningOptionsError = '';
	let isSavingLearningOptions = false;


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
				// Combine USB and rtpMIDI devices into a flat array
				const usbDevices = (data.usb_devices || []).map((d: any) => ({
					...d,
					type: d.type || 'usb'
				}));
				const rtpDevices = (data.rtpmidi_sessions || []).map((d: any) => ({
					...d,
					type: d.type || 'network'
				}));
				midiInputDevices = [...usbDevices, ...rtpDevices];
				
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

	async function loadLearningOptions(): Promise<void> {
		try {
			learningOptionsError = '';
			const response = await fetch('/api/learning/options');
			if (response.ok) {
				const data = await response.json();
				// Load per-hand settings
				const leftHand = data.left_hand ?? {};
				const rightHand = data.right_hand ?? {};
				
				leftHandWaitForNotes = leftHand.wait_for_notes ?? false;
				leftHandWhiteColor = leftHand.white_color ?? '#ff6b6b';
				leftHandBlackColor = leftHand.black_color ?? '#c92a2a';
				
				rightHandWaitForNotes = rightHand.wait_for_notes ?? false;
				rightHandWhiteColor = rightHand.white_color ?? '#006496';
				rightHandBlackColor = rightHand.black_color ?? '#960064';
				
				timingWindow = data.timing_window_ms ?? 500;
			}
		} catch (error) {
			console.error('Failed to load learning options:', error);
			// Use defaults if API not available
		}
	}

	async function saveLearningOptions(): Promise<void> {
		try {
			isSavingLearningOptions = true;
			learningOptionsError = '';
			const response = await fetch('/api/learning/options', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					left_hand: {
						wait_for_notes: leftHandWaitForNotes,
						white_color: leftHandWhiteColor,
						black_color: leftHandBlackColor
					},
					right_hand: {
						wait_for_notes: rightHandWaitForNotes,
						white_color: rightHandWhiteColor,
						black_color: rightHandBlackColor
					},
					timing_window_ms: timingWindow
				})
			});

			if (!response.ok) {
				learningOptionsError = 'Failed to save learning options';
			}
		} catch (error) {
			console.error('Failed to save learning options:', error);
			learningOptionsError = 'Network error saving learning options';
		} finally {
			isSavingLearningOptions = false;
		}
	}

	function resetToDefaults(): void {
		leftHandWaitForNotes = false;
		leftHandWhiteColor = '#ff6b6b';
		leftHandBlackColor = '#c92a2a';
		rightHandWaitForNotes = false;
		rightHandWhiteColor = '#006496';
		rightHandBlackColor = '#960064';
		timingWindow = 500;
		saveLearningOptions();
	}

	onMount(() => {
		loadUploadedFiles();
		loadLearningOptions();
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
		<h1>Play and Learn</h1>

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

		<!-- Learning Options Card -->
		<section class="learning-options-card grid-section">
			<header class="card-header">
				<h3>Learning Options</h3>
				<p>Configure hand-specific settings for learning mode.</p>
			</header>
			
			<div class="learning-content">
				<!-- Left Hand Settings -->
				<div class="hand-section">
					<div class="hand-header">
						<h4 class="hand-title">🎹 Left Hand</h4>
						<span class="hand-label amber">Golden Amber</span>
					</div>

					<!-- Left Hand: Wait for Notes -->
					<div class="setting-group checkbox-group">
						<label class="checkbox-wrapper">
							<input 
								type="checkbox" 
								bind:checked={leftHandWaitForNotes}
								on:change={saveLearningOptions}
								class="checkbox-input"
								title="Pause playback until you play left hand notes"
							/>
							<span class="checkbox-label">
								Wait for MIDI Notes
								<span class="checkbox-description">Playback pauses until you play the correct notes</span>
							</span>
						</label>
					</div>

					<!-- Left Hand Colors -->
					<div class="color-pair-section">
						<div class="field">
							<label for="left-white" class="field-label">White Keys</label>
							<div class="color-input-wrapper">
								<input 
									type="color" 
									id="left-white" 
									bind:value={leftHandWhiteColor}
									on:change={saveLearningOptions}
									class="color-selector"
									title="Color for left hand white keys"
								/>
								<div class="color-swatch" style="background-color: {leftHandWhiteColor};"></div>
								<span class="color-hex">{leftHandWhiteColor}</span>
							</div>
						</div>
						<div class="field">
							<label for="left-black" class="field-label">Black Keys</label>
							<div class="color-input-wrapper">
								<input 
									type="color" 
									id="left-black" 
									bind:value={leftHandBlackColor}
									on:change={saveLearningOptions}
									class="color-selector"
									title="Color for left hand black keys"
								/>
								<div class="color-swatch" style="background-color: {leftHandBlackColor};"></div>
								<span class="color-hex">{leftHandBlackColor}</span>
							</div>
						</div>
					</div>
				</div>

				<div class="divider"></div>

				<!-- Right Hand Settings -->
				<div class="hand-section">
					<div class="hand-header">
						<h4 class="hand-title">🎹 Right Hand</h4>
						<span class="hand-label teal">Teal & Magenta</span>
					</div>

					<!-- Right Hand: Wait for Notes -->
					<div class="setting-group checkbox-group">
						<label class="checkbox-wrapper">
							<input 
								type="checkbox" 
								bind:checked={rightHandWaitForNotes}
								on:change={saveLearningOptions}
								class="checkbox-input"
								title="Pause playback until you play right hand notes"
							/>
							<span class="checkbox-label">
								Wait for MIDI Notes
								<span class="checkbox-description">Playback pauses until you play the correct notes</span>
							</span>
						</label>
					</div>

					<!-- Right Hand Colors -->
					<div class="color-pair-section">
						<div class="field">
							<label for="right-white" class="field-label">White Keys</label>
							<div class="color-input-wrapper">
								<input 
									type="color" 
									id="right-white" 
									bind:value={rightHandWhiteColor}
									on:change={saveLearningOptions}
									class="color-selector"
									title="Color for right hand white keys"
								/>
								<div class="color-swatch" style="background-color: {rightHandWhiteColor};"></div>
								<span class="color-hex">{rightHandWhiteColor}</span>
							</div>
						</div>
						<div class="field">
							<label for="right-black" class="field-label">Black Keys</label>
							<div class="color-input-wrapper">
								<input 
									type="color" 
									id="right-black" 
									bind:value={rightHandBlackColor}
									on:change={saveLearningOptions}
									class="color-selector"
									title="Color for right hand black keys"
								/>
								<div class="color-swatch" style="background-color: {rightHandBlackColor};"></div>
								<span class="color-hex">{rightHandBlackColor}</span>
							</div>
						</div>
					</div>
				</div>

				<div class="divider"></div>

				<!-- Timing Window (Global) -->
				<div class="timing-section">
					<div class="field field-slider">
						<label for="timing-window" class="field-label">
							Note Timing Tolerance: <span class="timing-value">{timingWindow} ms</span>
						</label>
						<input 
							type="range" 
							id="timing-window" 
							min="100" 
							max="2000" 
							step="100" 
							bind:value={timingWindow}
							on:change={saveLearningOptions}
							class="timing-slider"
							title="Time window for matching played notes"
						/>
						<div class="field-hint">How much time tolerance for playing notes (100-2000 ms)</div>
					</div>
				</div>

				<div class="action-row">
					<button 
						class="btn-reset" 
						on:click={resetToDefaults}
						disabled={isSavingLearningOptions}
						title="Reset all settings to defaults"
					>
						🔄 Reset to Defaults
					</button>
				</div>

				{#if learningOptionsError}
					<p class="error-message">{learningOptionsError}</p>
				{/if}
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

	/* Learning Options Card Styles - Matching Settings Page */
	.learning-options-card {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 0;
		box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
		overflow: hidden;
	}

	.card-header {
		padding: 1.75rem 2rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.card-header h3 {
		margin: 0;
		font-size: 1.4rem;
		color: #0f172a;
		font-weight: 600;
	}

	.card-header p {
		margin: 0.25rem 0 0;
		color: #475569;
		font-size: 0.95rem;
	}

	.learning-content {
		display: flex;
		flex-direction: column;
		padding: 1.75rem 2rem;
		gap: 1.75rem;
	}

	.hand-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.hand-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 0.5rem;
	}

	.hand-title {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 600;
		color: #1f2937;
	}

	.hand-label {
		display: inline-block;
		font-size: 0.8rem;
		font-weight: 600;
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.hand-label.amber {
		background: #fef3c7;
		color: #92400e;
	}

	.hand-label.teal {
		background: #ccf0ff;
		color: #004d7a;
	}

	.hand-label.blue {
		background: #dbeafe;
		color: #0c2d6b;
	}

	.setting-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.checkbox-group {
		background: #ffffff;
		padding: 0.75rem;
		border-radius: 8px;
		border: 1px solid #e2e8f0;
	}

	.checkbox-wrapper {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		cursor: pointer;
		user-select: none;
	}

	.checkbox-input {
		width: 1.25rem;
		height: 1.25rem;
		margin-top: 0.2rem;
		cursor: pointer;
		accent-color: #2563eb;
		flex-shrink: 0;
	}

	.checkbox-label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.checkbox-label {
		font-weight: 500;
		color: #1f2937;
		font-size: 0.95rem;
	}

	.checkbox-description {
		font-size: 0.85rem;
		color: #64748b;
		font-weight: normal;
	}

	.color-pair-section {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.field-label {
		font-weight: 600;
		color: #1f2937;
		font-size: 0.9rem;
	}

	.color-input-wrapper {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: #ffffff;
		padding: 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		transition: border-color 0.2s ease, box-shadow 0.2s ease;
	}

	.color-input-wrapper:hover {
		border-color: #9ca3af;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.color-input-wrapper:focus-within {
		border-color: #2563eb;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
	}

	.color-selector {
		width: 3rem;
		height: 2.75rem;
		border: 1px solid #cbd5e1;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.2s;
		flex-shrink: 0;
	}

	.color-selector:hover {
		box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
	}

	.color-selector:focus {
		outline: none;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
	}

	.color-swatch {
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 6px;
		border: 1px solid #cbd5e1;
		flex-shrink: 0;
	}

	.color-hex {
		font-family: 'Monaco', 'Courier New', monospace;
		font-size: 0.8rem;
		font-weight: 600;
		color: #475569;
		letter-spacing: 0.05em;
	}

	.divider {
		height: 1px;
		background: linear-gradient(to right, transparent, #e2e8f0, transparent);
		margin: 0.5rem 0;
	}

	.timing-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.field-slider {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.field-slider .field-label {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.timing-value {
		font-size: 0.875rem;
		font-weight: 700;
		color: #2563eb;
		background: #eff6ff;
		padding: 0.35rem 0.65rem;
		border-radius: 4px;
	}

	.timing-slider {
		width: 100%;
		height: 6px;
		border-radius: 999px;
		background: #e5e7eb;
		outline: none;
		-webkit-appearance: none;
		appearance: none;
		cursor: pointer;
	}

	.timing-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 999px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
		transition: all 0.2s;
		border: 2px solid #ffffff;
	}

	.timing-slider::-webkit-slider-thumb:hover {
		transform: scale(1.15);
		box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
	}

	.timing-slider::-moz-range-thumb {
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 999px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
		border: 2px solid #ffffff;
		transition: all 0.2s;
	}

	.timing-slider::-moz-range-thumb:hover {
		transform: scale(1.15);
		box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
	}

	.timing-slider::-moz-range-track {
		background: transparent;
		border: none;
	}

	.field-hint {
		margin: 0;
		font-size: 0.8rem;
		color: #64748b;
	}

	.action-row {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.btn-reset {
		padding: 0.7rem 1.5rem;
		border: 1px solid #d1d5db;
		border-radius: 8px;
		background: #ffffff;
		color: #1f2937;
		font-size: 0.9rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.btn-reset:hover:not(:disabled) {
		background: #f3f4f6;
		border-color: #9ca3af;
		box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
	}

	.btn-reset:active:not(:disabled) {
		transform: translateY(1px);
	}

	.btn-reset:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error-message {
		margin: 0;
		padding: 0.75rem 1rem;
		background: #fee2e2;
		color: #991b1b;
		border-radius: 8px;
		font-size: 0.9rem;
		border: 1px solid #fecaca;
	}

	.reset-button:active {
		transform: scale(0.95);
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
