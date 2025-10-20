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
			return;
		}

		try {
			const response = await fetch(`/api/midi-notes?filename=${encodeURIComponent(selectedFile)}`);
			if (response.ok) {
				const data = await response.json();
				notes = data.notes || [];
				// Update totalDuration from the MIDI file data
				totalDuration = data.total_duration || 0;
				// Also update the playbackStatus for the progress bar
				playbackStatus.total_duration = totalDuration;
				console.log(`✓ Loaded ${notes.length} MIDI notes from ${selectedFile}, duration: ${totalDuration.toFixed(2)}s`);
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
			const response = await fetch('/api/playback-status');
			if (response.ok) {
				const data = await response.json();
				playbackStatus = data;
				currentTime = data.current_time || 0;
				// Only update totalDuration from backend if it's non-zero (file loaded)
				// Otherwise keep the duration we got from /api/midi-notes
				if (data.total_duration > 0) {
					totalDuration = data.total_duration;
				}
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
			// If we're not currently playing, stop any other file first
			if (!isPlaying) {
				console.log(`▶ Playing: ${selectedFile}`);
				// Stop any other playback first (to ensure only one file plays)
				try {
					await fetch('/api/stop', { method: 'POST' });
				} catch (e) {
					// Ignore errors when stopping (nothing might be playing)
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

CONTENT TRUNCATED - This is a backup of the falling notes visualization page.
Refer to git history or original commit for full content.
