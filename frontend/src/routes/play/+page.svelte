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

	let playbackStatus: PlaybackStatus = {
		state: 'idle',
		current_time: 0,
		total_duration: 0,
		filename: null,
		progress_percentage: 0,
		error_message: null
	};

	let notes: NoteVisualization[] = [];
	let uploadedFiles: Array<{ filename: string; path: string; size: number }> = [];
	let selectedFile: string | null = null;
	let isPlaying = false;
	let currentTime = 0;
	let totalDuration = 0;

	// Piano constants
	const MIN_MIDI_NOTE = 21; // A0
	const MAX_MIDI_NOTE = 108; // C8
	const KEYS_PER_OCTAVE = 12;
	const WHITE_KEYS_PER_OCTAVE = 7;

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

	// Get position of note on keyboard (0-87 for 88-key piano)
	function getNotePosition(note: number): number {
		return note - MIN_MIDI_NOTE;
	}

	// Get X position percentage for a note on the piano keyboard
	function getNoteXPercent(note: number): number {
		const totalWhiteKeys = 52; // 88-key piano has 52 white keys
		let whiteKeyCount = 0;

		for (let i = MIN_MIDI_NOTE; i < note; i++) {
			if (isWhiteKey(i)) {
				whiteKeyCount++;
			}
		}

		return (whiteKeyCount / totalWhiteKeys) * 100;
	}

	// Get width percentage for a note (white keys are wider than black keys)
	function getNoteWidthPercent(note: number): number {
		const totalWhiteKeys = 52;
		return isWhiteKey(note) ? (1 / totalWhiteKeys) * 100 : (0.5 / totalWhiteKeys) * 100;
	}

	async function loadUploadedFiles() {
		try {
			const response = await fetch('/api/uploaded-midi-files');
			if (response.ok) {
				uploadedFiles = await response.json();
			}
		} catch (error) {
			console.error('Failed to load uploaded files:', error);
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
			}
		} catch (error) {
			console.error('Failed to load MIDI notes:', error);
		}
	}

	async function fetchPlaybackStatus() {
		try {
			const response = await fetch('/api/playback-status');
			if (response.ok) {
				const data = await response.json();
				playbackStatus = data;
				currentTime = data.current_time;
				totalDuration = data.total_duration;
				isPlaying = data.state === 'playing';

				// If a file is playing but not selected, select it
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

	async function handleSelectFile(filename: string) {
		selectedFile = filename;
		await loadMIDINotes();

		try {
			const response = await fetch('/api/play', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ filename })
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

<div class="play-container">
	<h1>🎹 Piano Playback</h1>

	<!-- File Selection -->
	<div class="files-section">
		<h2>Uploaded MIDI Files</h2>
		{#if uploadedFiles.length > 0}
			<div class="file-list">
				{#each uploadedFiles as file (file.path)}
					<div
						class="file-item"
						class:active={selectedFile === file.path}
						on:click={() => handleSelectFile(file.path)}
						role="button"
						tabindex="0"
					>
						<div class="file-name">{file.filename}</div>
						<div class="file-size">{(file.size / 1024).toFixed(1)} KB</div>
					</div>
				{/each}
			</div>
		{:else}
			<p class="no-files">No MIDI files uploaded. Upload files in the Listen tab to play them.</p>
		{/if}
	</div>

	<!-- Playback Controls -->
	<div class="controls-section">
		<button
			class="control-btn play-btn"
			on:click={handlePlayPause}
			disabled={!selectedFile}
		>
			{isPlaying ? '⏸ Pause' : '▶ Play'}
		</button>
		<button class="control-btn stop-btn" on:click={handleStop} disabled={!selectedFile}>
			⏹ Stop
		</button>

		<!-- Time Display -->
		<div class="time-display">
			<span>{formatTime(currentTime)}</span>
			<span>/</span>
			<span>{formatTime(totalDuration)}</span>
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
		<h2>MIDI Visualization</h2>

		<!-- Notes Timeline -->
		<div class="notes-timeline">
			<div class="timeline-background">
				<!-- Grid lines -->
				{#each Array.from({ length: Math.ceil(totalDuration) + 1 }) as _, i}
					<div
						class="timeline-grid-line"
						style="left: {(i / totalDuration) * 100}%"
						title="{i}s"
					></div>
				{/each}

				<!-- Current time indicator -->
				<div
					class="current-time-indicator"
					style="left: {totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0}%"
				></div>

				<!-- Notes -->
				{#each notes as note (note)}
					{@const startPercent = totalDuration > 0 ? (note.startTime / totalDuration) * 100 : 0}
					{@const widthPercent = totalDuration > 0 ? (note.duration / totalDuration) * 100 : 0}
					{@const noteColor = getNoteColor(note.note)}
					<div
						class="note-bar"
						style="
							left: {startPercent}%;
							width: {widthPercent}%;
							background-color: {noteColor};
							opacity: {0.5 + (note.velocity / 127) * 0.5};
						"
						title="Note: {note.note} ({60 + note.note}), Time: {formatTime(note.startTime)}, Duration: {note.duration.toFixed(2)}s"
					></div>
				{/each}
			</div>
		</div>

		<!-- Virtual Piano -->
		<div class="piano-section">
			<div class="piano-keyboard">
				<!-- White Keys -->
				{#each Array.from({ length: 88 }) as _, i}
					{@const note = MIN_MIDI_NOTE + i}
					{@const isWhite = isWhiteKey(note)}
					{@const isActive = notes.some(
						(n) =>
							n.note === note &&
							n.startTime <= currentTime &&
							n.startTime + n.duration >= currentTime
					)}

					{#if isWhite}
						<div
							class="key white-key"
							class:active={isActive}
							style="
								left: {getNoteXPercent(note)}%;
								width: {getNoteWidthPercent(note)}%;
								background-color: {isActive ? getNoteColor(note) : 'white'};
							"
							title="Note {note}"
						></div>
					{/if}
				{/each}

				<!-- Black Keys -->
				{#each Array.from({ length: 88 }) as _, i}
					{@const note = MIN_MIDI_NOTE + i}
					{@const isBlack = !isWhiteKey(note)}
					{@const isActive = notes.some(
						(n) =>
							n.note === note &&
							n.startTime <= currentTime &&
							n.startTime + n.duration >= currentTime
					)}

					{#if isBlack}
						<div
							class="key black-key"
							class:active={isActive}
							style="
								left: {getNoteXPercent(note)}%;
								width: {getNoteWidthPercent(note)}%;
								background-color: {isActive ? getNoteColor(note) : 'black'};
							"
							title="Note {note}"
						></div>
					{/if}
				{/each}
			</div>
		</div>
	</div>
</div>

<style>
	.play-container {
		display: flex;
		flex-direction: column;
		gap: 2rem;
		padding: 2rem;
		background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
		color: #fff;
		min-height: 100vh;
	}

	h1 {
		font-size: 2.5rem;
		margin: 0;
		text-align: center;
		background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	h2 {
		font-size: 1.3rem;
		margin: 0 0 1rem 0;
		color: #ffd700;
	}

	/* Files Section */
	.files-section {
		background: rgba(255, 255, 255, 0.05);
		padding: 1.5rem;
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.1);
	}

	.file-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 1rem;
	}

	.file-item {
		background: rgba(255, 255, 255, 0.08);
		padding: 1rem;
		border-radius: 6px;
		border: 2px solid rgba(255, 255, 255, 0.2);
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.file-item:hover {
		background: rgba(255, 255, 255, 0.12);
		border-color: #ffd700;
		transform: translateY(-2px);
	}

	.file-item.active {
		background: rgba(255, 215, 0, 0.2);
		border-color: #ffd700;
		box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
	}

	.file-name {
		font-weight: 600;
		margin-bottom: 0.5rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.file-size {
		font-size: 0.85rem;
		color: #aaa;
	}

	.no-files {
		text-align: center;
		color: #888;
		font-style: italic;
	}

	/* Controls Section */
	.controls-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		background: rgba(255, 255, 255, 0.05);
		padding: 1.5rem;
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.1);
	}

	.control-btn {
		padding: 0.75rem 1.5rem;
		font-size: 1rem;
		font-weight: 600;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.3s ease;
		color: #000;
	}

	.play-btn {
		background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
	}

	.play-btn:hover:not(:disabled) {
		transform: scale(1.05);
		box-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
	}

	.stop-btn {
		background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%);
		color: white;
	}

	.stop-btn:hover:not(:disabled) {
		transform: scale(1.05);
		box-shadow: 0 0 15px rgba(255, 107, 107, 0.5);
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.time-display {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		font-size: 1.1rem;
		font-weight: 600;
		color: #ffd700;
	}

	.progress-bar {
		height: 8px;
		background: rgba(255, 255, 255, 0.1);
		border-radius: 4px;
		overflow: hidden;
		cursor: pointer;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #ffd700 0%, #ffed4e 100%);
		transition: width 0.1s linear;
	}

	.error-message {
		color: #ff6b6b;
		font-size: 0.9rem;
		text-align: center;
	}

	/* Visualization Section */
	.visualization-section {
		background: rgba(255, 255, 255, 0.05);
		padding: 1.5rem;
		border-radius: 8px;
		border: 1px solid rgba(255, 255, 255, 0.1);
	}

	.notes-timeline {
		background: #000;
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 6px;
		height: 150px;
		margin-bottom: 2rem;
		overflow-x: auto;
		position: relative;
	}

	.timeline-background {
		position: relative;
		height: 100%;
		min-width: 100%;
	}

	.timeline-grid-line {
		position: absolute;
		top: 0;
		height: 100%;
		width: 1px;
		background: rgba(255, 255, 255, 0.1);
	}

	.current-time-indicator {
		position: absolute;
		top: 0;
		height: 100%;
		width: 2px;
		background: #ffd700;
		box-shadow: 0 0 10px rgba(255, 215, 0, 0.8);
		z-index: 10;
	}

	.note-bar {
		position: absolute;
		height: 100%;
		top: 0;
		border: 1px solid rgba(255, 255, 255, 0.3);
		box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.5);
		cursor: pointer;
		transition: opacity 0.2s ease;
	}

	.note-bar:hover {
		opacity: 0.9 !important;
	}

	/* Piano Section */
	.piano-section {
		overflow-x: auto;
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 6px;
		background: #1a1a1a;
		padding: 1rem;
	}

	.piano-keyboard {
		position: relative;
		height: 120px;
		background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
		border: 2px solid #555;
		border-radius: 4px;
		min-width: 100%;
	}

	.key {
		position: absolute;
		top: 0;
		height: 100%;
		border: 1px solid rgba(255, 255, 255, 0.3);
		transition: all 0.1s ease;
		box-shadow: inset -1px 0 3px rgba(0, 0, 0, 0.5);
	}

	.white-key {
		background: #f5f5f5;
		color: #000;
		border-bottom: 3px solid #999;
	}

	.white-key:hover {
		background: #fff;
		box-shadow: inset -1px 0 3px rgba(0, 0, 0, 0.3), 0 0 10px rgba(255, 215, 0, 0.3);
	}

	.white-key.active {
		box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5), 0 0 20px currentColor;
	}

	.black-key {
		background: #1a1a1a;
		color: #fff;
		border-bottom: 2px solid #000;
		height: 65%;
		top: 0;
		z-index: 5;
		border-radius: 0 0 4px 4px;
	}

	.black-key:hover {
		background: #333;
		box-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
	}

	.black-key.active {
		box-shadow: 0 0 20px currentColor, inset 0 0 10px rgba(0, 0, 0, 0.8);
	}

	@media (max-width: 768px) {
		.play-container {
			padding: 1rem;
			gap: 1rem;
		}

		h1 {
			font-size: 1.8rem;
		}

		h2 {
			font-size: 1.1rem;
		}

		.file-list {
			grid-template-columns: 1fr;
		}

		.notes-timeline {
			height: 100px;
		}

		.piano-keyboard {
			height: 80px;
		}
	}
</style>
