<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';

	// Minimal LED shape used by this visualization (other props may be present)
	type RGB = { r: number; g: number; b: number };
	// Accept either the flat { r,g,b, brightness } shape or legacy { color: { r,g,b }, brightness }
	type LED = (
		{ r: number; g: number; b: number; brightness: number } |
		{ color: RGB; brightness: number }
	) & Record<string, any>;

	// Props
	export let ledState: LED[] = [];
	export let width: number = 800;
	export let height: number = 200;
	export let responsive: boolean = true;
	export let ledSpacing: number = 2;
	export let ledRadius: number = 8;

	// Canvas and rendering
	let canvas: HTMLCanvasElement | null = null;
	let ctx: CanvasRenderingContext2D | null = null;
	let animationFrame: number | null = null;
	let lastUpdateTime: number = 0;
	const targetFPS = 60;
	const frameInterval = 1000 / targetFPS;

	// Responsive dimensions
	let containerWidth: number = width;
	let containerHeight: number = height;
	let actualWidth: number = width;
	let actualHeight: number = height;

	// Performance tracking
	let frameCount: number = 0;
	let fpsStartTime: number = Date.now();
	let currentFPS: number = 0;

	onMount(() => {
		if (canvas) {
			ctx = canvas.getContext('2d');
			if (responsive) {
				updateCanvasSize();
				window.addEventListener('resize', updateCanvasSize);
			}
			startAnimation();
		}

		return () => {
			if (animationFrame !== null) {
				cancelAnimationFrame(animationFrame);
			}
			if (responsive) {
				window.removeEventListener('resize', updateCanvasSize);
			}
		};
	});

	afterUpdate(() => {
		if (ctx) {
			renderLEDs();
		}
	});

	function updateCanvasSize(): void {
		if (!canvas || !canvas.parentElement) return;

		const container = canvas.parentElement as HTMLElement;
		containerWidth = container.clientWidth;

		// Maintain aspect ratio
		const aspectRatio = width / height;
		actualWidth = Math.min(containerWidth, width);
		actualHeight = actualWidth / aspectRatio;

		// Set canvas size with device pixel ratio for crisp rendering
		const dpr = window.devicePixelRatio || 1;
		canvas.width = Math.floor(actualWidth * dpr);
		canvas.height = Math.floor(actualHeight * dpr);
		canvas.style.width = actualWidth + 'px';
		canvas.style.height = actualHeight + 'px';

		// Set transform for high DPI displays (use setTransform to avoid cumulative scaling)
		if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
	}

	function startAnimation(): void {
		function animate(currentTime: number) {
			if (currentTime - lastUpdateTime >= frameInterval) {
				renderLEDs();
				updateFPS();
				lastUpdateTime = currentTime;
			}
			animationFrame = requestAnimationFrame(animate);
		}
		animationFrame = requestAnimationFrame(animate);
	}

	function updateFPS() {
		frameCount++;
		const now = Date.now();
		if (now - fpsStartTime >= 1000) {
			currentFPS = Math.round((frameCount * 1000) / (now - fpsStartTime));
			frameCount = 0;
			fpsStartTime = now;
		}
	}

	// Helper function for rounded rectangle (polyfill for older browsers)
	function drawRoundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
		ctx.beginPath();
		ctx.moveTo(x + radius, y);
		ctx.lineTo(x + width - radius, y);
		ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
		ctx.lineTo(x + width, y + height - radius);
		ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
		ctx.lineTo(x + radius, y + height);
		ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
		ctx.lineTo(x, y + radius);
		ctx.quadraticCurveTo(x, y, x + radius, y);
		ctx.closePath();
	}

	function renderLEDs(): void {
		if (!ctx || !ledState.length) return;

		// Narrow ctx to a non-null local variable so TypeScript doesn't complain
		const c = ctx as CanvasRenderingContext2D;

		// Clear canvas
		c.clearRect(0, 0, actualWidth, actualHeight);

		// Calculate LED layout
		const ledCount = ledState.length;
		const availableWidth = actualWidth - (ledSpacing * 2);
		const ledWidth = (availableWidth - (ledSpacing * (ledCount - 1))) / ledCount;
		const ledSize = Math.max(1, Math.min(ledWidth, ledRadius * 2)); // Ensure minimum size of 1
		const ledY = actualHeight / 2;

		// Skip rendering if ledSize is too small or invalid
		if (ledSize <= 0 || !isFinite(ledSize)) return;

		// Render background strip
		c.fillStyle = '#1a1a1a';
		if ((c as any).roundRect) {
			// Use native roundRect if available
			(c as any).roundRect(ledSpacing / 2, ledY - ledSize / 2 - 5, availableWidth + ledSpacing, ledSize + 10, 5);
		} else {
			// Use polyfill for older browsers
			drawRoundedRect(c, ledSpacing / 2, ledY - ledSize / 2 - 5, availableWidth + ledSpacing, ledSize + 10, 5);
		}
		c.fill();

		// Render individual LEDs
		ledState.forEach((led: LED, index: number) => {
			const ledX = ledSpacing + (index * (ledWidth + ledSpacing)) + ledWidth / 2;
			
			// LED background (off state)
			c.fillStyle = '#333';
			c.beginPath();
			c.arc(ledX, ledY, ledSize / 2, 0, 2 * Math.PI);
			c.fill();

			// LED color (if active)
			// Normalize color shape (support both flat and nested color shapes)
			const rgb: RGB = 'r' in led ? { r: (led as any).r, g: (led as any).g, b: (led as any).b } : ((led as any).color ?? { r: 0, g: 0, b: 0 });
			const brightness = (led as any).brightness ?? 0;

			if (brightness > 0) {
				const { r, g, b } = rgb;
				const alpha = brightness;

				// Inner LED color
				c.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				c.beginPath();
				c.arc(ledX, ledY, (ledSize / 2) * 0.8, 0, 2 * Math.PI);
				c.fill();

				// Glow effect
				if (brightness > 0.3) {
					const gradient = c.createRadialGradient(
						ledX, ledY, 0,
						ledX, ledY, ledSize * 1.5
					);
					gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha * 0.8})`);
					gradient.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${alpha * 0.3})`);
					gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

					c.fillStyle = gradient;
					c.beginPath();
					c.arc(ledX, ledY, ledSize * 1.5, 0, 2 * Math.PI);
					c.fill();
				}

				// Highlight for very bright LEDs
				if (brightness > 0.7) {
					c.fillStyle = `rgba(255, 255, 255, ${(brightness - 0.7) * 0.5})`;
					c.beginPath();
					c.arc(ledX, ledY, (ledSize / 2) * 0.4, 0, 2 * Math.PI);
					c.fill();
				}
			}

			// LED index label (for debugging/testing)
				if (ledSize > 16) {
					c.fillStyle = '#666';
					c.font = '10px monospace';
					c.textAlign = 'center';
					c.fillText(index.toString(), ledX, ledY + ledSize + 15);
				}
		});

		// Performance info overlay
		if (currentFPS > 0) {
			c.fillStyle = 'rgba(0, 0, 0, 0.7)';
			c.fillRect(actualWidth - 80, 5, 75, 25);
			c.fillStyle = '#fff';
			c.font = '12px monospace';
			c.textAlign = 'left';
			c.fillText(`${currentFPS} FPS`, actualWidth - 75, 20);
		}
	}

	// Handle canvas click/touch for LED selection (for testing)
	function handleCanvasClick(event: MouseEvent | TouchEvent): void {
		if (!canvas || !ledState.length) return;

		const rect = canvas.getBoundingClientRect();
		let x: number, y: number;

		// Handle both mouse and touch events
		const touchEvent = event as TouchEvent;
		if (touchEvent.touches && touchEvent.touches.length > 0) {
			x = touchEvent.touches[0].clientX - rect.left;
			y = touchEvent.touches[0].clientY - rect.top;
		} else {
			const mouseEvent = event as MouseEvent;
			x = mouseEvent.clientX - rect.left;
			y = mouseEvent.clientY - rect.top;
		}

		// Scale coordinates to canvas size
		const scaleX = actualWidth / rect.width;
		const scaleY = actualHeight / rect.height;
		const canvasX = x * scaleX;
		const canvasY = y * scaleY;

		// Find clicked LED
		const ledCount = ledState.length;
		const availableWidth = actualWidth - (ledSpacing * 2);
		const ledWidth = (availableWidth - (ledSpacing * (ledCount - 1))) / ledCount;
		const ledY = actualHeight / 2;

		for (let i = 0; i < ledCount; i++) {
			const ledX = ledSpacing + (i * (ledWidth + ledSpacing)) + ledWidth / 2;
			const distance = Math.sqrt((canvasX - ledX) ** 2 + (canvasY - ledY) ** 2);

			if (distance <= ledRadius) {
				// Dispatch LED click event
				const ledClickEvent = new CustomEvent('ledClick', {
					detail: {
						index: i,
						led: ledState[i],
						position: { x: ledX, y: ledY }
					}
				});
				canvas?.dispatchEvent(ledClickEvent);
				break;
			}
		}
	}

	// Handle touch events
	function handleTouchStart(event: TouchEvent) {
		event.preventDefault(); // Prevent scrolling
		handleCanvasClick(event);
	}

	// Handle touch move for dragging selection
	function handleTouchMove(event: TouchEvent) {
		event.preventDefault(); // Prevent scrolling
		handleCanvasClick(event);
	}

	// Expose current FPS for parent component
	export function getCurrentFPS() {
		return currentFPS;
	}

	// Expose LED count for parent component
	export function getLEDCount() {
		return ledState.length;
	}
</script>

<div class="led-visualization-container">
	<canvas 
		bind:this={canvas}
		on:click={handleCanvasClick}
		on:touchstart={handleTouchStart}
		on:touchmove={handleTouchMove}
		class="led-canvas"
		{width}
		{height}
	></canvas>
	
	{#if ledState.length === 0}
		<div class="no-data-overlay">
			<p>No LED data available</p>
			<small>Connect to WebSocket to see real-time LED visualization</small>
		</div>
	{/if}
</div>

<style>
	.led-visualization-container {
		position: relative;
		width: 100%;
		max-width: 100%;
		border-radius: 8px;
		overflow: hidden;
		background: #0a0a0a;
		border: 2px solid #333;
	}

	.led-canvas {
		display: block;
		width: 100%;
		height: auto;
		cursor: pointer;
		background: #0a0a0a;
		touch-action: manipulation;
		-webkit-tap-highlight-color: transparent;
		min-height: 60px;
	}

	.no-data-overlay {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		text-align: center;
		color: #666;
		pointer-events: none;
	}

	.no-data-overlay p {
		margin: 0 0 0.5rem 0;
		font-size: 1.1rem;
		font-weight: 500;
	}

	.no-data-overlay small {
		font-size: 0.9rem;
		opacity: 0.8;
	}

	/* Responsive adjustments */
	@media (max-width: 768px) {
		.led-visualization-container {
			border-width: 1px;
		}
		
		.led-canvas {
			min-height: 50px;
		}
	}

	@media (max-width: 480px) {
		.led-canvas {
			min-height: 40px;
		}
	}
</style>