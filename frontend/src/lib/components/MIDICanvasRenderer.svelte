<script lang="ts">
	import { onMount } from 'svelte';

	export let notes: Array<{ note: number; startTime: number; duration: number; velocity: number }> = [];
	export let currentTime: number = 0;
	export let totalDuration: number = 0;
	export let width: number = 800;
	export let height: number = 400;

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null;
	let animationFrameId: number;

	// Piano constants
	const MIN_MIDI_NOTE = 21; // A0
	const MAX_MIDI_NOTE = 108; // C8
	const TOTAL_WHITE_KEYS = 52;
	const TOTAL_BLACK_KEYS = 36;

	// Derived dimensions
	let keyboardHeight: number;
	let timelineHeight: number;
	let whiteKeyWidth: number;
	let whiteKeyHeight: number;

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
		for (let i = MAX_MIDI_NOTE; i > note; i--) {
			if (isWhiteKey(i)) {
				yOffset += (100 / TOTAL_WHITE_KEYS);
			} else {
				yOffset += (60 / TOTAL_WHITE_KEYS);
			}
		}
		return yOffset;
	}

	// Calculate white key index for a MIDI note
	function getWhiteKeyIndex(note: number): number {
		let whiteKeyIndex = -1;
		for (let i = MIN_MIDI_NOTE; i < note; i++) {
			if (isWhiteKey(i)) {
				whiteKeyIndex++;
			}
		}
		return whiteKeyIndex;
	}

	// Get X position percentage for a note on the piano keyboard
	function getNoteXPercent(note: number): number {
		if (isWhiteKey(note)) {
			const whiteKeyIndex = getWhiteKeyIndex(note);
			return (whiteKeyIndex / TOTAL_WHITE_KEYS) * 100;
		} else {
			const whiteKeyIndex = getWhiteKeyIndex(note) + 1;
			return ((whiteKeyIndex - 0.3) / TOTAL_WHITE_KEYS) * 100;
		}
	}

	// Get width percentage for a note
	function getNoteWidthPercent(note: number): number {
		const baseWidth = (1 / TOTAL_WHITE_KEYS) * 100;
		return isWhiteKey(note) ? baseWidth : baseWidth * 0.65;
	}

	// Render the canvas
	function render() {
		if (!ctx || !canvas) return;

		// Clear canvas
		ctx.fillStyle = '#1a1a1a';
		ctx.fillRect(0, 0, canvas.width, canvas.height);

		// Draw grid lines and timeline
		drawTimeline();

		// Draw note bars
		drawNotes();

		// Draw current position indicator
		drawCurrentPosition();

		// Draw keyboard
		drawKeyboard();

		animationFrameId = requestAnimationFrame(render);
	}

	function drawTimeline() {
		if (!ctx) return;
		const gridLineSpacing = width / (totalDuration || 1); // One grid line per second

		ctx.strokeStyle = '#333333';
		ctx.lineWidth = 1;
		ctx.font = '12px sans-serif';
		ctx.fillStyle = '#666666';

		for (let i = 0; i <= totalDuration; i++) {
			const x = (i / (totalDuration || 1)) * width;
			ctx.beginPath();
			ctx.moveTo(x, 0);
			ctx.lineTo(x, timelineHeight);
			ctx.stroke();

			// Draw time label
			if (i % 5 === 0) {
				ctx.fillText(i + 's', x + 2, 15);
			}
		}
	}

	function drawNotes() {
		if (!ctx) return;
		for (const note of notes) {
			const startPercent = (note.startTime / (totalDuration || 1)) * 100;
			const durationPercent = (note.duration / (totalDuration || 1)) * 100;
			const keyOffset = calculateKeyOffset(note.note);

			const x = (startPercent / 100) * width;
			const noteWidth = (durationPercent / 100) * width;
			const y = (keyOffset / 100) * keyboardHeight;
			const noteHeight = whiteKeyHeight * 0.8;

			// Draw note bar with color and opacity
			const color = getNoteColor(note.note);
			const opacity = 0.6 + (note.velocity / 127) * 0.4;

			// Convert hex color to RGB and use rgba
			const rgb = hexToRgb(color);
			ctx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
			ctx.fillRect(x, y, noteWidth, noteHeight);

			// Draw border
			ctx.strokeStyle = color;
			ctx.lineWidth = 1;
			ctx.strokeRect(x, y, noteWidth, noteHeight);
		}
	}

	// Helper function to convert hex color to RGB
	function hexToRgb(hex: string): { r: number; g: number; b: number } {
		// Remove # if present
		hex = hex.replace(/^#/, '');
		
		// Parse hex values
		const r = parseInt(hex.substring(0, 2), 16);
		const g = parseInt(hex.substring(2, 4), 16);
		const b = parseInt(hex.substring(4, 6), 16);
		
		return { r, g, b };
	}

	function drawKeyboard() {
		if (!ctx) return;
		const keyboardStartY = timelineHeight;

		// Draw all white keys
		for (let note = MIN_MIDI_NOTE; note <= MAX_MIDI_NOTE; note++) {
			if (!isWhiteKey(note)) continue;

			const xPercent = getNoteXPercent(note);
			const x = (xPercent / 100) * width;

			const keyOffset = calculateKeyOffset(note);
			const y = keyboardStartY + (keyOffset / 100) * keyboardHeight;

			ctx.fillStyle = '#cccccc';
			ctx.fillRect(x, y, whiteKeyWidth, whiteKeyHeight);

			ctx.strokeStyle = '#333333';
			ctx.lineWidth = 1;
			ctx.strokeRect(x, y, whiteKeyWidth, whiteKeyHeight);
		}

		// Draw all black keys on top
		for (let note = MIN_MIDI_NOTE; note <= MAX_MIDI_NOTE; note++) {
			if (isWhiteKey(note)) continue;

			const xPercent = getNoteXPercent(note);
			const x = (xPercent / 100) * width;

			const keyOffset = calculateKeyOffset(note);
			const y = keyboardStartY + (keyOffset / 100) * keyboardHeight;
			const blackKeyHeight = whiteKeyHeight * 0.6;

			ctx.fillStyle = '#333333';
			ctx.fillRect(x, y, whiteKeyWidth * 0.65, blackKeyHeight);

			ctx.strokeStyle = '#000000';
			ctx.lineWidth = 1;
			ctx.strokeRect(x, y, whiteKeyWidth * 0.65, blackKeyHeight);
		}
	}

	function drawCurrentPosition() {
		if (!ctx) return;
		if (totalDuration === 0) return;

		const positionPercent = (currentTime / totalDuration) * 100;
		const x = (positionPercent / 100) * width;

		ctx.strokeStyle = '#00ccff';
		ctx.lineWidth = 3;
		ctx.beginPath();
		ctx.moveTo(x, 0);
		ctx.lineTo(x, canvas.height);
		ctx.stroke();
	}

	onMount(() => {
		ctx = canvas.getContext('2d');
		if (!ctx) {
			console.error('Failed to get 2D context');
			return;
		}

		// Calculate dimensions
		keyboardHeight = height * 0.5; // Bottom 50% for keyboard
		timelineHeight = height * 0.5; // Top 50% for timeline
		whiteKeyWidth = width / TOTAL_WHITE_KEYS;
		whiteKeyHeight = keyboardHeight / TOTAL_WHITE_KEYS;

		// Start render loop
		render();

		return () => {
			if (animationFrameId) {
				cancelAnimationFrame(animationFrameId);
			}
		};
	});

	// Handle window resize
	function handleResize() {
		if (canvas && canvas.parentElement) {
			const rect = canvas.parentElement.getBoundingClientRect();
			canvas.width = rect.width;
			canvas.height = rect.height;
			width = canvas.width;
			height = canvas.height;

			// Recalculate dimensions
			keyboardHeight = height * 0.5;
			timelineHeight = height * 0.5;
			whiteKeyWidth = width / TOTAL_WHITE_KEYS;
			whiteKeyHeight = keyboardHeight / TOTAL_WHITE_KEYS;
		}
	}
</script>

<svelte:window on:resize={handleResize} />

<div class="canvas-container">
	<canvas
		bind:this={canvas}
		width={width}
		height={height}
		style="display: block; width: 100%; height: 100%;"
	></canvas>
</div>

<style>
	.canvas-container {
		width: 100%;
		height: 100%;
		overflow: hidden;
		background-color: #1a1a1a;
	}
</style>
