<script lang="ts">
	import { onMount } from 'svelte';

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

	// Piano constants
	const MIN_MIDI_NOTE = 21; // A0
	const MAX_MIDI_NOTE = 108; // C8
	const TOTAL_WHITE_KEYS = 52; // 88-key piano has 52 white keys
	const TOTAL_BLACK_KEYS = 36; // 88-key piano has 36 black keys

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

	// Calculate white key index for a MIDI note
	// Note: MIN_MIDI_NOTE (21/A0) is not a white key in our baseline, so we offset by -1
	function getWhiteKeyIndex(note: number): number {
		let whiteKeyIndex = -1; // Start at -1 to account for A0 being "off" the white key baseline
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
			return;
		}

		try {
			const response = await fetch(`/api/midi-notes?filename=${encodeURIComponent(selectedFile)}`);
			if (response.ok) {
				const data = await response.json();
				notes = data.notes || [];
				console.log(`Loaded ${notes.length} MIDI notes from ${selectedFile}`);
				console.log('Notes:', notes.slice(0, 5)); // Log first 5 notes for debugging
			} else {
				console.error('Failed to load MIDI notes:', response.status);
				notes = [];
			}
		} catch (error) {
			console.error('Failed to load MIDI notes:', error);
			notes = [];
		}
	}

	async function fetchPlaybackStatus() {
		try {
			const response = await fetch('/api/playback-status');
			if (response.ok) {
				const data = await response.json();
				playbackStatus = data;
				currentTime = data.current_time || 0;
				totalDuration = data.total_duration || 0;
				isPlaying = data.state === 'playing';

				// If a file is playing but not selected, select it and load notes
				if (data.filename && !selectedFile) {
					selectedFile = data.filename;
					await loadMIDINotes();
				}
			}
		} catch (error) {
			console.error('Failed to fetch playback status:', error);
		}
	}

	async function handlePlayPause() {
		if (!selectedFile) return;

		try {
			const method = isPlaying ? 'pause' : 'play';
			const response = await fetch(`/api/${method}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ filename: selectedFile })
			});

			if (response.ok) {
				await fetchPlaybackStatus();
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
		selectedFile = filePath;
		await loadMIDINotes();

		try {
			const response = await fetch('/api/play', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ filename: filePath })
			});

			if (response.ok) {
				await fetchPlaybackStatus();
			}
		} catch (error) {
			console.error('Failed to play file:', error);
		}
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
		const statusInterval = setInterval(fetchPlaybackStatus, 100);
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
			<!-- Timeline -->
			<div class="timeline-container">
				<div class="timeline-background">
					{#each Array.from({ length: Math.ceil(totalDuration) + 1 }) as _, i}
						<div
							class="timeline-grid-line"
							style="left: {totalDuration > 0 ? (i / totalDuration) * 100 : 0}%"
						></div>
					{/each}

					<!-- Current Position -->
					<div
						class="current-position"
						style="left: {totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0}%"
					></div>

					<!-- Notes -->
					{#each notes as note, index (index)}
						{@const startPercent = totalDuration > 0 ? (note.startTime / totalDuration) * 100 : 0}
						{@const widthPercent = totalDuration > 0 ? Math.max((note.duration / totalDuration) * 100, 1) : 1}
						{@const noteColor = getNoteColor(note.note)}
						<div
							class="note-bar"
							style="
								left: {startPercent}%;
								width: {widthPercent}%;
								background-color: {noteColor};
								opacity: {0.5 + (note.velocity / 127) * 0.5};
							"
							title="Note {note.note}: {note.startTime.toFixed(2)}s - {(note.startTime + note.duration).toFixed(2)}s"
						></div>
					{/each}
				</div>
			</div>

			<!-- Piano Keyboard -->
			<div class="piano-container">
				<div class="piano-keyboard">
					<!-- White Keys -->
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
							<div
								class="key white-key"
								class:active={isActive}
								style="
									left: {getNoteXPercent(note)}%;
									width: {getNoteWidthPercent(note)}%;
									background-color: {isActive ? getNoteColor(note) : '#f5f5f5'};
								"
							></div>
						{/if}
					{/each}

					<!-- Black Keys (layered on top) -->
					{#each Array.from({ length: 88 }) as _, i}
						{@const note = MIN_MIDI_NOTE + i}
						{@const blackKey = !isWhiteKey(note)}
						{@const isActive = notes.some(
							(n) =>
								n.note === note &&
								n.startTime <= currentTime &&
								n.startTime + n.duration >= currentTime
						)}

						{#if blackKey}
							<div
								class="key black-key"
								class:active={isActive}
								style="
									left: {getNoteXPercent(note)}%;
									width: {getNoteWidthPercent(note)}%;
									background-color: {isActive ? getNoteColor(note) : '#1a1a1a'};
								"
							></div>
						{/if}
					{/each}
				</div>
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
		gap: 0;
	}

	/* Timeline Container */
	.timeline-container {
		background: #1f2937;
		border: 1px solid #e2e8f0;
		border-radius: 12px 12px 0 0;
		height: 120px;
		overflow-x: auto;
		overflow-y: hidden;
		position: relative;
	}

	.timeline-background {
		position: relative;
		height: 100%;
		min-width: 100%;
		background: linear-gradient(to bottom, #374151, #1f2937);
	}

	.timeline-grid-line {
		position: absolute;
		top: 0;
		height: 100%;
		width: 1px;
		background: rgba(255, 255, 255, 0.1);
	}

	.current-position {
		position: absolute;
		top: 0;
		height: 100%;
		width: 2px;
		background: #2563eb;
		box-shadow: 0 0 8px rgba(37, 99, 235, 0.6);
		z-index: 10;
	}

	.note-bar {
		position: absolute;
		height: 100%;
		top: 0;
		min-width: 2px;
		border-left: 1px solid rgba(0, 0, 0, 0.2);
		border-right: 1px solid rgba(0, 0, 0, 0.2);
		transition: opacity 0.1s ease;
		cursor: pointer;
	}

	.note-bar:hover {
		opacity: 1 !important;
		filter: brightness(1.2);
	}

	/* Piano Container */
	.piano-container {
		background: #ffffff;
		border: 1px solid #e2e8f0;
		border-radius: 0 0 12px 12px;
		border-top: none;
		overflow-x: auto;
		overflow-y: hidden;
		padding: 0;
	}

	.piano-keyboard {
		position: relative;
		height: 160px;
		background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
		border-top: 1px solid #e5e7eb;
		min-width: 100%;
	}

	.key {
		position: absolute;
		top: 0;
		height: 100%;
		transition: all 0.05s ease;
		box-sizing: border-box;
	}

	.white-key {
		background: linear-gradient(to bottom, #ffffff, #f9fafb);
		border: 1px solid #d1d5db;
		border-right: 1px solid #9ca3af;
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1);
	}

	.white-key:hover {
		background: linear-gradient(to bottom, #f3f4f6, #e5e7eb);
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1), 0 0 8px rgba(37, 99, 235, 0.15);
	}

	.white-key.active {
		box-shadow: inset -1px -1px 3px rgba(0, 0, 0, 0.1), 0 0 12px currentColor;
	}

	.black-key {
		background: linear-gradient(to bottom, #374151, #1f2937);
		border: 1px solid #111827;
		border-right: 2px solid #000000;
		height: 60%;
		top: 0;
		z-index: 5;
		border-radius: 0 0 6px 6px;
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3);
	}

	.black-key:hover {
		background: linear-gradient(to bottom, #4b5563, #374151);
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3), 0 0 12px rgba(37, 99, 235, 0.2);
	}

	.black-key.active {
		box-shadow: inset -1px -1px 2px rgba(0, 0, 0, 0.5), 0 0 12px currentColor;
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

		.timeline-container {
			height: 80px;
			border-radius: 12px 12px 0 0;
		}

		.piano-keyboard {
			height: 120px;
		}
	}
</style>
