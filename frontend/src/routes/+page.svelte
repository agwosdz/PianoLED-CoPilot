<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { settings, getSetting } from '$lib/stores/settings.js';

	let backendStatus: string = 'Checking...';
	let backendMessage: string = '';

	// System status from backend dashboard endpoint
	let systemStatus: any = null;
	let systemStatusLoading: boolean = true;
	let systemStatusError: string | null = null;

	// USB MIDI status object (populated from systemStatus if available)
	type UsbMidiStatus = { connected: boolean; deviceName?: string | null; lastActivity?: string | null; messageCount: number };
	let usbMidiStatus: UsbMidiStatus | null = null;

	onMount(async () => {
		// Check backend health first
		try {
			const response = await fetch('/health');
			if (response.ok) {
				const data = await response.json();
				backendStatus = data.status;
				backendMessage = data.message;
			} else {
				backendStatus = 'Error';
				backendMessage = `HTTP ${response.status}: ${response.statusText}`;
			}
		} catch (error) {
			backendStatus = 'Offline';
			backendMessage = 'Cannot connect to backend server';
		}

		// Initialize dashboard functionality if backend is healthy
		if (backendStatus === 'healthy') {
			fetchSystemStatus();
		}
	});

	onDestroy(() => {
		// No cleanup needed for removed features
	});

	// Fetch system status from backend
	async function fetchSystemStatus() {
		try {
			const response = await fetch('/api/dashboard');
			if (response.ok) {
				systemStatus = await response.json();
				systemStatusError = null;
				
				// Initialize MIDI status based on system status
				if (systemStatus.system_status) {
					usbMidiStatus = {
						connected: systemStatus.system_status.midi_input_active || false,
						deviceName: systemStatus.system_status.midi_device_name || null,
						lastActivity: null,
						messageCount: 0
					};
				}
			} else {
				systemStatusError = `HTTP ${response.status}: ${response.status}`;
			}
		} catch (error) {
			systemStatusError = 'Cannot connect to backend server';
		} finally {
			systemStatusLoading = false;
		}
	}

	// Helper functions for system status display
	function getStatusClass(available: boolean | undefined): string {
		return available ? 'healthy' : 'error';
	}

	function formatDuration(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>Piano LED Visualizer - Home</title>
	<meta name="description" content="Piano LED Visualizer - Transform your MIDI files into stunning LED light shows!" />
</svelte:head>

<main>
	<div class="hero-section">
		<h1>🎹 Piano LED Visualizer</h1>
		<p>Welcome to the Piano LED Visualizer - Transform your MIDI files into stunning LED light shows!</p>
	</div>
	
	<div class="system-details-card">
		<h2>System Details</h2>
		<div class="system-details-grid">
			<div class="detail-item">
				<span class="label">Frontend:</span>
				<span class="value">Running</span>
			</div>
			<div class="detail-item">
				<span class="label">Backend:</span>
				<span class="value {backendStatus === 'healthy' ? 'healthy' : 'error'}">
					{backendStatus === 'healthy' ? 'Healthy' : backendStatus}
				</span>
			</div>
			<div class="detail-item">
				<span class="label">Backend IP/Port:</span>
				<span class="value">{browser ? `${window.location.hostname}:${window.location.port || '5173'}` : 'localhost:5173'}</span>
			</div>
			<div class="detail-item">
				<span class="label">WebSocket:</span>
				<span class="value">Connected</span>
			</div>
			<div class="detail-item">
				<span class="label">Uptime:</span>
				<span class="value">Running</span>
			</div>
			<div class="detail-item">
				<span class="label">Version:</span>
				<span class="value">1.0.0</span>
			</div>
		</div>
		{#if backendMessage}
			<p class="status-message">{backendMessage}</p>
		{/if}
	</div>

	{#if backendStatus === 'healthy'}
		<!-- System Status Details -->
		{#if systemStatusLoading}
			<div class="loading">Loading system status...</div>
		{:else if systemStatusError}
			<div class="error-card">
				<span class="error-icon">❌</span>
				<span class="error-message">{systemStatusError}</span>
			</div>
		{:else if systemStatus}
			<section class="system-details-section">
				<h2>System Details</h2>
				<div class="system-status-grid">
					<div class="status-card">
						<h3>🔧 Components</h3>
						<div class="status-items">
							<div class="status-item">
								<span class="label">Backend:</span>
								<span class="status healthy">{systemStatus.system_status.backend_status}</span>
							</div>
							<div class="status-item">
								<span class="label">LED Controller:</span>
								<span class="status {getStatusClass(systemStatus.system_status.led_controller_available)}">
									{systemStatus.system_status.led_controller_available ? 'Available' : 'Unavailable'}
								</span>
							</div>
							<div class="status-item">
								<span class="label">MIDI Parser:</span>
								<span class="status {getStatusClass(systemStatus.system_status.midi_parser_available)}">
									{systemStatus.system_status.midi_parser_available ? 'Available' : 'Unavailable'}
								</span>
							</div>
							<div class="status-item">
								<span class="label">USB MIDI Input:</span>
								<span class="status {getStatusClass(systemStatus.system_status.midi_input_active)}">
									{systemStatus.system_status.midi_input_active ? 'Active' : 'Inactive'}
								</span>
								{#if systemStatus.system_status.midi_device_name}
									<div class="device-name">Device: {systemStatus.system_status.midi_device_name}</div>
								{/if}
							</div>
							<div class="status-item">
								<span class="label">Playback Service:</span>
								<span class="status {getStatusClass(systemStatus.system_status.playback_service_available)}">
									{systemStatus.system_status.playback_service_available ? 'Available' : 'Unavailable'}
								</span>
							</div>
						</div>
					</div>
				</div>
			</section>
		{/if}
	{/if}

	<div class="navigation-card">
		<h2>Navigation</h2>
		<p>Access all available features of the Piano LED Visualizer:</p>
		<div class="nav-buttons">
			<a href="/listen" class="nav-button">
				<span class="nav-icon">🎵</span>
				<div class="nav-content">
					<h3>Listen</h3>
					<p>Upload and play MIDI files for LED visualization</p>
				</div>
			</a>
			<a href="/settings" class="nav-button">
				<span class="nav-icon">⚙️</span>
				<div class="nav-content">
					<h3>Settings</h3>
					<p>Configure system preferences and LED settings</p>
				</div>
			</a>
		</div>
	</div>
</main>

<style>
	main {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	.hero-section {
		text-align: center;
		margin-bottom: 2rem;
	}

	.hero-section h1 {
		color: #333;
		margin-bottom: 1rem;
		font-size: 2.5rem;
	}

	.hero-section p {
		font-size: 1.1rem;
		color: #666;
		margin-bottom: 0;
	}

	.status-card, .info-card, .navigation-card, .system-details-card {
		background: #f8f9fa;
		border: 1px solid #e9ecef;
		border-radius: 8px;
		padding: 1.5rem;
		margin: 1.5rem 0;
	}

	.system-details-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.detail-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: white;
		border-radius: 6px;
		border: 1px solid #e9ecef;
	}

	.detail-item .label {
		font-weight: 600;
		color: #495057;
	}

	.detail-item .value {
		font-weight: 500;
		color: #2d3748;
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
	}

	.detail-item .value.healthy {
		color: #155724;
		font-weight: 600;
	}

	.detail-item .value.error {
		color: #721c24;
		font-weight: 600;
	}

	.status-message {
		margin-top: 1rem;
		padding: 0.75rem;
		background: #e2e3e5;
		border-radius: 4px;
		font-size: 0.875rem;
		color: #495057;
	}

	/* Dashboard-specific styles */
	.system-details-section {
		background: white;
		border: 1px solid #e9ecef;
		border-radius: 12px;
		padding: 2rem;
		margin: 2rem 0;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.system-status-grid {
		display: grid;
		gap: 1.5rem;
	}

	.system-status-grid .status-card {
		background: #f8f9fa;
		border: 1px solid #e9ecef;
		border-radius: 8px;
		padding: 1.5rem;
		margin: 0;
	}

	.system-status-grid .status-card h3 {
		margin-top: 0;
		margin-bottom: 1rem;
		color: #495057;
	}

	.status-items {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.device-name {
		font-size: 0.875rem;
		color: #6c757d;
		margin-top: 0.25rem;
	}

	.loading {
		text-align: center;
		padding: 2rem;
		color: #6c757d;
		font-style: italic;
	}

	.error-card {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 1rem;
		background-color: #f8d7da;
		color: #721c24;
		border: 1px solid #f5c6cb;
		border-radius: 8px;
		margin: 1rem 0;
	}


	.nav-buttons {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1rem;
		margin-top: 1rem;
	}

	.nav-button {
		display: flex;
		align-items: center;
		padding: 1.25rem;
		background: white;
		border: 2px solid #e9ecef;
		border-radius: 8px;
		text-decoration: none;
		color: inherit;
		transition: all 0.2s ease;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.nav-button:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		border-color: #007bff;
	}

	.nav-icon {
		font-size: 2rem;
		margin-right: 1rem;
		flex-shrink: 0;
	}

	.nav-content h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1.25rem;
		font-weight: 600;
	}

	.nav-content p {
		margin: 0;
		font-size: 0.9rem;
		opacity: 0.8;
		line-height: 1.4;
	}

	@media (max-width: 768px) {
		main {
			padding: 1rem;
		}

		.visualization-header {
			flex-direction: column;
			align-items: stretch;
		}

		.connection-info {
			justify-content: center;
		}

		.nav-buttons {
			grid-template-columns: 1fr;
		}
		
		.nav-button {
			padding: 1rem;
		}
		
		.nav-icon {
			font-size: 1.5rem;
			margin-right: 0.75rem;
		}
	}
</style>
