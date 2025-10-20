<script lang="ts">
	import { onMount } from 'svelte';
	import MIDICanvasRenderer from '$lib/components/MIDICanvasRenderer.svelte';

	interface PlaybackStatus {
		state: string;
		current_time: number;
		total_duration: number;
		filename: string | null;
		progress_percentage: number;
		error_message: string | null;
	}

	interface NoteVisualization {
		note: number;
		startTime: number;
		duration: number;
		velocity: number;
	}

	interface UploadedFile {
		name: string;
		path: string;
		size: number;
	}

	let playbackStatus: PlaybackStatus = {
		state: 'idle',
		current_time: 0,
		total_duration: 0,
		filename: null,
		progress_percentage: 0,
		error_message: null
	};

	let notes: NoteVisualization[] = [];
	let uploadedFiles: UploadedFile[] = [];
	let selectedFile: string | null = null;
	let isPlaying = false;
	let currentTime = 0;
	let totalDuration = 0;
	let isLoadingFiles = false;
	let filesError = '';
	let useCanvasRenderer = false; // Toggle between DOM and Canvas rendering
	let pianoWidth = 0; // Track piano container width for pixel calculations

	// Reactive: Log totalDuration changes for debugging
	$: if (totalDuration !== undefined) {
		console.log(`[DEBUG] totalDuration changed to: ${totalDuration}s (isPlaying: ${isPlaying})`);
	}

	// Piano constants
	const MIN_MIDI_NOTE = 21; // A0
	const MAX_MIDI_NOTE = 108; // C8
	const TOTAL_WHITE_KEYS = 52; // 88-key piano has 52 white keys
	const TOTAL_BLACK_KEYS = 36; // 88-key piano has 36 black keys
	const LOOK_AHEAD_TIME = 4; // Show notes 4 seconds before they play (look-ahead window)

	// Get color for a MIDI note based on its pitch
	function getNoteColor(note: number): string {
		const noteInOctave = note % 12;
		const colors = [
			'#ff0000', // C - Red
			'#ff7f00', // C# - Orange
			'#ffff00', // D - Yellow
			'#7fff00', // D# - Yellow-Green
			'#00ff00', // E - Green
			'#00ff7f', // F - Green-Cyan
			'#00ffff', // F# - Cyan
			'#007fff', // G - Cyan-Blue
			'#0000ff', // G# - Blue
			'#7f00ff', // A - Blue-Purple
			'#ff00ff', // A# - Purple
			'#ff007f' // B - Purple-Red
		];
		return colors[noteInOctave];
	}

	// Check if a MIDI note is a white key
	function isWhiteKey(note: number): boolean {
		const noteInOctave = note % 12;
		return [0, 2, 4, 5, 7, 9, 11].includes(noteInOctave);
	}

	// Calculate vertical offset percentage for a note's key position
	function calculateKeyOffset(note: number): number {
		let yOffset = 0;
		// Go through all notes from highest to lowest (top to bottom)
		for (let i = MAX_MIDI_NOTE; i > note; i--) {
			if (isWhiteKey(i)) {
				yOffset += (100 / 52); // White key height
			} else {
				yOffset += (60 / 52); // Black key height
			}
		}
		return yOffset;
	}

	// Calculate white key index for a MIDI note
	// Note: MIN_MIDI_NOTE (21/A0) is not a white key in our baseline, so we offset by -1
	function getWhiteKeyIndex(note: number): number {
		// Count how many white keys come before this note
		let whiteKeyIndex = 0;
		for (let i = MIN_MIDI_NOTE; i < note; i++) {
			if (isWhiteKey(i)) {
				whiteKeyIndex++;
			}
		}
		return whiteKeyIndex;
	}

	// Get X position percentage for a note on the piano keyboard
	function getNoteXPercent(note: number): number {
		const whiteKeyWidth = (1 / TOTAL_WHITE_KEYS) * 100; // Each white key is ~1.92% of keyboard

		if (isWhiteKey(note)) {
			// White keys are positioned at whiteKeyIndex * whiteKeyWidth
			const whiteKeyIndex = getWhiteKeyIndex(note);
			return whiteKeyIndex * whiteKeyWidth;
		} else {
			// Black keys are positioned at (whiteKeyIndex - 0.3) * whiteKeyWidth
			// This places them between the current and previous white key
			const whiteKeyIndex = getWhiteKeyIndex(note) + 1; // Next white key's position
			return (whiteKeyIndex - 0.3) * whiteKeyWidth;
		}
	}

	// Get width percentage for a note (white keys are wider than black keys)
	function getNoteWidthPercent(note: number): number {
		const whiteKeyWidth = (1 / TOTAL_WHITE_KEYS) * 100;
		
		if (isWhiteKey(note)) {
			// Each white key takes up 1/52 of the keyboard
			return whiteKeyWidth;
		} else {
			// Black keys are about 65% of white key width
			return whiteKeyWidth * 0.65;
		}
	}

	// Calculate pixel-based dimensions for proper piano rendering
	function getKeyDimensions(containerWidth: number, note: number) {
		const WHITE_KEY_WIDTH = containerWidth / TOTAL_WHITE_KEYS;
		const BLACK_KEY_WIDTH = WHITE_KEY_WIDTH * 0.65;
		const BLACK_KEY_HEIGHT = 160 * 0.6; // 60% of container height
		const WHITE_KEY_HEIGHT = 160;

		if (isWhiteKey(note)) {
			const whiteKeyIndex = getWhiteKeyIndex(note);
			return {
				x: whiteKeyIndex * WHITE_KEY_WIDTH,
				y: 0,
				w: WHITE_KEY_WIDTH,
				h: WHITE_KEY_HEIGHT
			};
		} else {
			// Black keys positioned between white keys with slight offset for overlap
			const whiteKeyIndex = getWhiteKeyIndex(note) + 1;
			return {
				x: whiteKeyIndex * WHITE_KEY_WIDTH - BLACK_KEY_WIDTH / 2,
				y: 0,
				w: BLACK_KEY_WIDTH,
				h: BLACK_KEY_HEIGHT
			};
		}
	}

	async function loadUploadedFiles() {
		try {
			isLoadingFiles = true;
			filesError = '';
			const response = await fetch('/api/uploaded-midi');
			if (response.ok) {
				const data = await response.json();
				// Handle the response structure: { status, files: [...] }
				const files = data.files || [];
				uploadedFiles = files.map((f: any) => ({
					name: f.filename || f.name,
					path: f.path,
					size: f.size
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

	async function loadMIDINotes() {
		if (!selectedFile) {
			notes = [];
			totalDuration = 0;
			console.log('[DEBUG] loadMIDINotes: No selectedFile');
			return;
		}

		console.log(`[DEBUG] loadMIDINotes: Loading notes for ${selectedFile}`);
		try {
			const response = await fetch(`/api/midi-notes?filename=${encodeURIComponent(selectedFile)}`);
			if (response.ok) {
				const data = await response.json();
				notes = data.notes || [];
				// Update totalDuration from the MIDI file data
				totalDuration = data.total_duration || 0;
				// Also update the playbackStatus for the progress bar
				playbackStatus.total_duration = totalDuration;
				console.log(`✓ Loaded ${notes.length} MIDI notes from ${selectedFile}`);
				console.log(`  Response total_duration: ${data.total_duration}s`);
				console.log(`  Frontend totalDuration now: ${totalDuration}s`);
				if (notes.length > 0) {
					console.log(`  First note: MIDI ${notes[0].note} at ${notes[0].startTime}s`);
					console.log(`  Last note: MIDI ${notes[notes.length - 1].note} at ${notes[notes.length - 1].startTime}s`);
				}
			} else {
				console.error('Failed to load MIDI notes:', response.status);
				notes = [];
				totalDuration = 0;
				playbackStatus.total_duration = 0;
			}
		} catch (error) {
			console.error('Failed to load MIDI notes:', error);
			notes = [];
			totalDuration = 0;
			playbackStatus.total_duration = 0;
		}
	}

	async function fetchPlaybackStatus() {
		try {
			console.log('[DEBUG] fetchPlaybackStatus() called');
			const response = await fetch('/api/playback-status');
			console.log(`[DEBUG] playback-status response status: ${response.status}`);
			if (response.ok) {
				const data = await response.json();
				console.log('[DEBUG] playback-status response data:', data);
				playbackStatus = data;
				currentTime = data.current_time || 0;
				// Only update totalDuration from backend if it's non-zero (file loaded)
				// Otherwise keep the duration we got from /api/midi-notes
				const beforeDuration = totalDuration;
				if (data.total_duration > 0) {
					totalDuration = data.total_duration;
					console.log(`[DEBUG] Updated totalDuration from backend: ${data.total_duration}s`);
				} else if (totalDuration === 0) {
					console.log(`[DEBUG] Backend total_duration is 0, keeping frontend duration: ${totalDuration}s`);
				}
				isPlaying = data.state === 'playing';
				
				// Debug: log state comparison
				if (data.state) {
					console.log(`[DEBUG] State from API: "${data.state}" (type: ${typeof data.state}), isPlaying: ${isPlaying}`);
				} else {
					console.log(`[DEBUG] WARNING: data.state is ${data.state}`);
				}

				// If a file is playing but not selected, select it and load notes
				if (data.filename && !selectedFile) {
					selectedFile = data.filename;
					await loadMIDINotes();
				}
			} else {
				console.error(`[DEBUG] playback-status response NOT OK: ${response.status}`);
			}
		} catch (error) {
			console.error('Failed to fetch playback status:', error);
		}
	}

	async function handlePlayPause() {
		if (!selectedFile) return;

		try {
			// If we're not currently playing, stop any other file first
			if (!isPlaying) {
				console.log(`▶ Playing: ${selectedFile}`);
				// Stop any other playback first (to ensure only one file plays)
				try {
					const stopResp = await fetch('/api/stop', { method: 'POST' });
					console.log(`[DEBUG] Stop request responded with status: ${stopResp.status}`);
				} catch (e) {
					// Ignore errors when stopping (nothing might be playing)
					console.log(`[DEBUG] Stop request error (expected if nothing playing): ${e}`);
				}
			} else {
				console.log(`⏸ Pausing`);
			}

			const method = isPlaying ? 'pause' : 'play';
			console.log(`[DEBUG] Sending ${method} request with filename: ${selectedFile}`);
			const response = await fetch(`/api/${method}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ filename: selectedFile })
			});

			console.log(`[DEBUG] ${method.toUpperCase()} response status: ${response.status}`);
			if (response.ok) {
				const responseBody = await response.json();
				console.log(`[DEBUG] ${method.toUpperCase()} response body:`, responseBody);
				await fetchPlaybackStatus();
			} else {
				const errorBody = await response.text();
				console.error(`Failed to ${method}: ${response.status} - ${errorBody}`);
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
				notes = [];
			}
		} catch (error) {
			console.error('Failed to stop playback:', error);
		}
	}

	async function handleSelectFile(filePath: string) {
		// Stop any currently playing file first
		try {
			await fetch('/api/stop', { method: 'POST' });
		} catch (error) {
			console.warn('Failed to stop previous playback:', error);
		}

		// Select file and load notes, but DON'T auto-play
		selectedFile = filePath;
		await loadMIDINotes();
		console.log(`✓ Selected ${filePath} - click Play to start`);
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
	}

	onMount(() => {
		loadUploadedFiles();
		let lastLoggedTime = 0;
		const statusInterval = setInterval(async () => {
			await fetchPlaybackStatus();
			// Debug: Log current sync status
			if (isPlaying && notes.length > 0) {
				if (currentTime - lastLoggedTime >= 0.5 || lastLoggedTime === 0) {
					const visibleNotes = notes.filter(n => {
						const timeUntilNote = n.startTime - currentTime;
						const timeUntilNoteEnd = (n.startTime + n.duration) - currentTime;
						return timeUntilNote < LOOK_AHEAD_TIME && timeUntilNoteEnd > -0.5;
					});
					console.log(`[${currentTime.toFixed(2)}s] Visible: ${visibleNotes.length}/${notes.length} notes`);
					lastLoggedTime = currentTime;
				}
			}
		}, 100);
		const filesInterval = setInterval(loadUploadedFiles, 5000);

		return () => {
			clearInterval(statusInterval);
			clearInterval(filesInterval);
		};
	});
</script>

<div class="page-wrapper">
	<div class="page-content">
		<h1>Piano Playback Visualizer</h1>
		
		<!-- File Selection -->
		<div class="section">
			<h2>Select MIDI File</h2>
			{#if isLoadingFiles}
				<div class="loading">Loading files...</div>
			{:else if filesError}
				<div class="error-message">{filesError}</div>
			{:else if uploadedFiles.length > 0}
				<div class="file-grid">
					{#each uploadedFiles as file (file.path)}
						<button
							class="file-item"
							class:active={selectedFile === file.path}
							on:click={() => handleSelectFile(file.path)}
							type="button"
						>
							<div class="file-name">{file.name}</div>
							<div class="file-size">{formatFileSize(file.size)}</div>
						</button>
					{/each}
				</div>
			{:else}
				<p class="empty-state">No MIDI files uploaded. Upload files in the Listen tab to play them.</p>
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

				<!-- Time Display -->
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

		<!-- Visualization -->
		<div class="visualization-section">
			<!-- Debug info -->
			{#if notes.length > 0}
				{@const visibleNotes = notes.filter(n => {
					const timeUntilNote = n.startTime - currentTime;
					const timeUntilNoteEnd = (n.startTime + n.duration) - currentTime;
					return timeUntilNote < LOOK_AHEAD_TIME && timeUntilNoteEnd > -0.5;
				})}
				{@const firstNote = notes[0]}
				{@const lastNote = notes[notes.length - 1]}
				{@const firstVisible = visibleNotes[0]}
				{@const firstTimeUntil = firstVisible ? (firstVisible.startTime - currentTime) : 0}
				{@const firstTopPercent = firstVisible ? ((LOOK_AHEAD_TIME - firstTimeUntil) / LOOK_AHEAD_TIME) * 100 : 0}
				<div style="font-size: 0.75rem; color: #333; padding: 0.75rem; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; margin-bottom: 0.5rem; font-family: monospace;">
					<div>Time: {currentTime.toFixed(2)}s / {totalDuration.toFixed(2)}s | Playing: {isPlaying}</div>
					<div>Notes: Loaded={notes.length} | Visible={visibleNotes.length} | Lookahead={LOOK_AHEAD_TIME}s</div>
					{#if firstNote}
						<div>First note: MIDI {firstNote.note} at {firstNote.startTime.toFixed(2)}s</div>
					{/if}
					{#if lastNote}
						<div>Last note: MIDI {lastNote.note} at {lastNote.startTime.toFixed(2)}s</div>
					{/if}
					{#if firstVisible}
						<div>First visible: MIDI {firstVisible.note} | timeUntil={firstTimeUntil.toFixed(2)}s | topPercent={firstTopPercent.toFixed(1)}% | Should be at {firstVisible.note < 54 ? 'LEFT (orange)' : 'RIGHT (yellow)'}</div>
					{/if}
				</div>
			{/if}

			<!-- Falling Notes Visualization -->
			<div class="falling-notes-container">
				<!-- Notes falling from top to bottom -->
				<div class="notes-area">
					{#each notes as note, index (index)}
						{@const timeUntilNote = note.startTime - currentTime}
						{@const timeUntilNoteEnd = (note.startTime + note.duration) - currentTime}
						<!-- Show notes that are upcoming or currently visible (from look-ahead to slightly past keyboard) -->
						{#if timeUntilNote < LOOK_AHEAD_TIME && timeUntilNoteEnd > -0.5}
							{@const xPercent = getNoteXPercent(note.note)}
							{@const noteWidth = getNoteWidthPercent(note.note)}
							{@const isLeftHand = note.note < 54}
							{@const barColor = isLeftHand ? '#FFA500' : '#FFD700'}
							{@const isCurrentlyPlaying = note.startTime <= currentTime && note.startTime + note.duration > currentTime}
							{@const isPast = note.startTime + note.duration <= currentTime}
							
							<!-- Position: top of screen = far future, bottom = piano keys (now) -->
							<!-- When timeUntilNote is positive and large (far future) -> top (0%) -->
							<!-- When timeUntilNote approaches 0 (note about to play) -> bottom (100%) -->
							{@const noteTopPercent = Math.max(0, (LOOK_AHEAD_TIME - timeUntilNote) / LOOK_AHEAD_TIME * 100)}
							{@const finalColor = isCurrentlyPlaying ? '#00a8ff' : (isPast ? '#666666' : barColor)}
							
							<div
								class="falling-note-bar"
								style="
									left: {xPercent}%;
									width: {noteWidth}%;
									top: {Math.min(100, Math.max(-10, noteTopPercent))}%;
									background-color: {finalColor};
									opacity: {isCurrentlyPlaying ? 1.0 : (isPast ? 0.3 : 0.8)};
									height: 40px;
									border-color: {finalColor};
								"
								title="Note {note.note}: {note.startTime.toFixed(2)}s - {(note.startTime + note.duration).toFixed(2)}s"
							></div>
						{/if}
					{/each}
				</div>

				<!-- Piano Keyboard at the bottom -->
				<div class="piano-keyboard-bottom" bind:clientWidth={pianoWidth}>
					<!-- White Keys First (background layer) -->
					{#each Array.from({ length: 88 }) as _, i}
						{@const note = MIN_MIDI_NOTE + i}
						{@const whiteKey = isWhiteKey(note)}
						{@const isActive = notes.some(
							(n) =>
								n.note === note &&
								n.startTime <= currentTime &&
								n.startTime + n.duration >= currentTime
						)}
						{#if whiteKey}
							{@const dims = getKeyDimensions(pianoWidth, note)}
							<div
								class="key-bottom white-key"
								class:active={isActive}
								style="
									left: {dims.x}px;
									width: {dims.w}px;
									height: {dims.h}px;
									background-color: {isActive ? '#00a8ff' : '#f5f5f5'};
								"
								title="Note {note}"
							></div>
						{/if}
					{/each}

					<!-- Black Keys Second (foreground layer) -->
					{#each Array.from({ length: 88 }) as _, i}
						{@const note = MIN_MIDI_NOTE + i}
						{@const whiteKey = isWhiteKey(note)}
						{@const isActive = notes.some(
							(n) =>
								n.note === note &&
								n.startTime <= currentTime &&
								n.startTime + n.duration >= currentTime
						)}
						{#if !whiteKey}
							{@const dims = getKeyDimensions(pianoWidth, note)}
							<div
								class="key-bottom black-key"
								class:active={isActive}
								style="
									left: {dims.x}px;
									width: {dims.w}px;
									height: {dims.h}px;
									top: 0;
									background-color: {isActive ? '#00a8ff' : '#1a1a1a'};
								"
								title="Note {note}"
							></div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- Time Display -->
			<div class="time-display-large">
				<span>{formatTime(currentTime)}</span>
				<span>/</span>
				<span>{formatTime(totalDuration)}</span>
			</div>
		</div>
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
		max-width: 1200px;
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
		margin: 1.75rem 0 1rem;
	}

	/* Section */
	.section {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		margin-bottom: 1.75rem;
	}

	/* File Grid */
	.file-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 1rem;
	}

	.file-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 1.25rem 1rem;
		background: #ffffff;
		border: 2px solid #e2e8f0;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s ease;
		text-align: center;
		min-height: 120px;
		font-size: 0.9rem;
	}

	.file-item:hover {
		border-color: #2563eb;
		background: #eff6ff;
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
	}

	.file-item.active {
		background: #eff6ff;
		border-color: #2563eb;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.file-name {
		font-weight: 600;
		color: #0f172a;
		margin-bottom: 0.5rem;
		overflow: hidden;
		text-overflow: ellipsis;
		word-break: break-word;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.file-size {
		font-size: 0.8rem;
		color: #64748b;
	}

	.empty-state {
		text-align: center;
		color: #64748b;
		padding: 2rem 1rem;
		margin: 0;
	}

	.loading {
		text-align: center;
		color: #64748b;
		padding: 2rem;
	}

	/* Controls */
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

	/* Progress Bar */
	.progress-bar {
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
		cursor: pointer;
		margin-bottom: 1rem;
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

	/* Visualization Section */
	.visualization-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	/* Falling Notes Container */
	.falling-notes-container {
		display: flex;
		flex-direction: column;
		background: #0f0f0f;
		border: 2px solid #d1d5db;
		border-radius: 12px;
		height: 600px;
		overflow: hidden;
		position: relative;
	}

	/* Notes falling area (takes most of the space) */
	.notes-area {
		flex: 1;
		position: relative;
		background: linear-gradient(180deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.1) 100%);
		overflow: hidden;
	}

	/* Falling note bars - travel from top to bottom */
	.falling-note-bar {
		position: absolute;
		border: 2px solid;
		border-radius: 4px;
		transition: top 0.05s linear, background-color 0.2s ease;
		box-shadow: 0 0 8px rgba(0, 0, 0, 0.4);
	}

	.falling-note-bar:hover {
		filter: brightness(1.3);
		box-shadow: 0 0 16px rgba(0, 0, 0, 0.6);
	}

	/* Piano Keyboard at bottom */
	.piano-keyboard-bottom {
		position: relative;
		height: 160px;
		background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
		border-top: 3px solid #d1d5db;
		width: 100%;
		display: block;
		overflow: hidden;
	}

	.key-bottom {
		position: absolute;
		bottom: 0;
		transition: all 0.05s ease;
		box-sizing: border-box;
	}

	.key-bottom.white-key {
		background: linear-gradient(to bottom, #ffffff, #f9fafb);
		border: 1px solid #d1d5db;
		border-right: 1px solid #9ca3af;
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1);
	}

	.key-bottom.white-key:hover {
		background: linear-gradient(to bottom, #f3f4f6, #e5e7eb);
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1), 0 0 8px rgba(37, 99, 235, 0.15);
	}

	.key-bottom.white-key.active {
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1), 0 0 12px currentColor;
		background-color: #00a8ff !important;
	}

	.key-bottom.black-key {
		background: linear-gradient(to bottom, #374151, #1f2937);
		border: 1px solid #111827;
		border-right: 2px solid #000000;
		border-radius: 0 0 6px 6px;
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3);
		z-index: 10;
	}

	.key-bottom.black-key:hover {
		background: linear-gradient(to bottom, #4b5563, #374151);
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3), 0 0 12px rgba(37, 99, 235, 0.2);
	}

	.key-bottom.black-key.active {
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 0 12px currentColor;
		background-color: #00a8ff !important;
	}

	/* Time display for visualization */
	.time-display-large {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #f0f9ff;
		border: 1px solid #bfdbfe;
		border-radius: 8px;
		font-size: 0.95rem;
		font-weight: 600;
		color: #1e293b;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.page-content {
			padding: 1.5rem 1rem 2rem;
		}

		h1 {
			font-size: 1.5rem;
			margin-bottom: 1.5rem;
		}

		h2 {
			font-size: 1rem;
			margin: 1.25rem 0 0.75rem;
		}

		.section {
			padding: 1.25rem;
			margin-bottom: 1rem;
		}

		.file-grid {
			grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
			gap: 0.75rem;
		}

		.file-item {
			padding: 1rem 0.75rem;
			min-height: 100px;
			font-size: 0.85rem;
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

		.falling-notes-container {
			height: 400px;
		}
	}
</style>
