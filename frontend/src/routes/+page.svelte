<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	type DashboardResponse = {
		status?: string;
		message?: string;
		uploaded_files_count?: number;
		system_status?: {
			backend_status?: string;
			led_controller_available?: boolean;
			midi_parser_available?: boolean;
			playback_service_available?: boolean;
			midi_input_active?: boolean;
			midi_device_name?: string | null;
		};
	};

	let backendStatus = 'Checking...';
	let dashboardLoading = true;
	let dashboardError: string | null = null;
	let dashboardData: DashboardResponse | null = null;

	let hostWithPort = 'localhost:5000';

	onMount(async () => {
		if (browser) {
			const envHost = (import.meta.env.VITE_BACKEND_HOST ?? '').trim();
			const envPort = (import.meta.env.VITE_BACKEND_PORT ?? '').trim();

			if (envHost.length > 0) {
				hostWithPort = envPort.length > 0 ? `${envHost}:${envPort}` : envHost;
			} else if (window.location.host) {
				hostWithPort = window.location.host;
			}

			const proxiedBackend = (window as any)?.socketIOBackendUrl;
			if (proxiedBackend && typeof proxiedBackend === 'string' && proxiedBackend.trim().length > 0) {
				try {
					const proxyUrl = new URL(proxiedBackend);
					hostWithPort = proxyUrl.host;
				} catch (error) {
					console.warn('Unable to parse proxy backend URL:', error);
				}
			}
		}

		await checkBackendHealth();

		if (backendStatus === 'healthy') {
			await fetchDashboard();
		} else {
			dashboardLoading = false;
		}
	});

	async function checkBackendHealth() {
		try {
			const response = await fetch('/health');
			if (response.ok) {
				const data = await response.json();
				backendStatus = data.status;
			} else {
				backendStatus = 'Error';
			}
		} catch (error) {
			backendStatus = 'Offline';
		}
	}

	async function fetchDashboard() {
		dashboardLoading = true;
		try {
			const response = await fetch('/api/dashboard');
			if (!response.ok) {
				dashboardError = `HTTP ${response.status}: ${response.statusText}`;
				dashboardData = null;
				return;
			}

			dashboardData = await response.json();
			dashboardError = null;
		} catch (error) {
			dashboardError = 'Cannot connect to backend server';
			dashboardData = null;
		} finally {
			dashboardLoading = false;
		}
	}

	function getStatusClass(available: boolean | undefined): string {
		return available ? 'healthy' : 'error';
	}
</script>

<svelte:head>
	<title>Piano LED Visualizer - Home</title>
	<meta name="description" content="Piano LED Visualizer - Transform your MIDI files into stunning LED light shows!" />
</svelte:head>

<main>
	<div class="hero-section">
		<h1>🎹 Piano LED Visualizer</h1>
		<p>Welcome to the Piano LED Visualizer - manage your system and start a light show in moments.</p>
	</div>

	<section class="system-details-card">
		<h2>System Details</h2>
		<div class="detail-grid">
			<div class="detail-item">
				<span class="label">Frontend</span>
				<span class="value healthy">Running</span>
			</div>
			<div class="detail-item">
				<span class="label">Backend</span>
				<span class="value {backendStatus === 'healthy' ? 'healthy' : 'error'}">
					{backendStatus === 'healthy' ? 'Running' : backendStatus}
				</span>
			</div>
			<div class="detail-item">
				<span class="label">Backend Host</span>
				<span class="value">{hostWithPort}</span>
			</div>
			{#if dashboardData?.uploaded_files_count !== undefined}
				<div class="detail-item">
					<span class="label">Total Songs on Device</span>
					<span class="value">{dashboardData.uploaded_files_count}</span>
				</div>
			{/if}
		</div>
	</section>

	{#if backendStatus === 'healthy'}
		{#if dashboardLoading}
			<div class="loading">Loading system information...</div>
		{:else if dashboardError}
			<div class="error-card" role="alert">
				<span class="error-icon">❌</span>
				<span class="error-message">{dashboardError}</span>
			</div>
		{:else if dashboardData?.system_status}
			<section class="services-card">
				<h2>Core Services</h2>
				<div class="service-grid">
					<div class="service-item">
						<span class="service-label">LED Controller</span>
						<span class="service-status {getStatusClass(dashboardData.system_status.led_controller_available)}">
							{dashboardData.system_status.led_controller_available ? 'Available' : 'Unavailable'}
						</span>
					</div>
					<div class="service-item">
						<span class="service-label">MIDI Parser</span>
						<span class="service-status {getStatusClass(dashboardData.system_status.midi_parser_available)}">
							{dashboardData.system_status.midi_parser_available ? 'Available' : 'Unavailable'}
						</span>
					</div>
					<div class="service-item">
						<span class="service-label">Playback Service</span>
						<span class="service-status {getStatusClass(dashboardData.system_status.playback_service_available)}">
							{dashboardData.system_status.playback_service_available ? 'Available' : 'Unavailable'}
						</span>
					</div>
					<div class="service-item">
						<span class="service-label">MIDI Input</span>
						<span class="service-status {dashboardData.system_status.midi_input_active ? 'healthy' : 'warning'}">
							{dashboardData.system_status.midi_input_active ? 'Listening' : 'Idle'}
						</span>
					</div>
				</div>
				{#if dashboardData.system_status.midi_device_name}
					<p class="service-note">Active MIDI device: {dashboardData.system_status.midi_device_name}</p>
				{/if}
			</section>
		{/if}
	{/if}
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
		color: #1f2937;
		margin-bottom: 1rem;
		font-size: 2.5rem;
	}

	.hero-section p {
		font-size: 1.1rem;
		color: #4b5563;
		margin: 0 auto;
		max-width: 640px;
	}

	.system-details-card,
	.services-card {
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.75rem;
		margin-bottom: 2rem;
		box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
	}

	.system-details-card h2,
	.services-card h2 {
		margin: 0 0 1.25rem 0;
		font-size: 1.5rem;
		color: #1f2937;
	}

	.detail-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.detail-item {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 1rem;
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 10px;
	}

	.label {
		font-weight: 600;
		color: #475569;
	}

	.value {
		font-weight: 500;
		color: #1f2937;
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
		word-break: break-word;
	}

	.value.healthy {
		color: #15803d;
	}

	.value.error {
		color: #b91c1c;
	}

	.loading {
		text-align: center;
		padding: 2rem;
		color: #6b7280;
		font-style: italic;
	}

	.error-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		background-color: #fee2e2;
		color: #b91c1c;
		border: 1px solid #fecaca;
		border-radius: 10px;
		margin-bottom: 2rem;
	}

	.error-icon {
		font-size: 1.25rem;
	}

	.service-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 1rem;
	}

	.service-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 10px;
	}

	.service-label {
		font-weight: 600;
		color: #475569;
	}

	.service-status {
		font-weight: 600;
		color: #1f2937;
		padding: 0.25rem 0.75rem;
		border-radius: 9999px;
		font-size: 0.85rem;
		background: #e2e8f0;
	}

	.service-status.healthy {
		background: rgba(34, 197, 94, 0.15);
		color: #15803d;
	}

	.service-status.error {
		background: rgba(239, 68, 68, 0.15);
		color: #b91c1c;
	}

	.service-status.warning {
		background: rgba(251, 191, 36, 0.15);
		color: #b45309;
	}

	.service-note {
		margin-top: 1rem;
		font-size: 0.9rem;
		color: #4b5563;
	}

	@media (max-width: 768px) {
		main {
			padding: 1.5rem 1rem;
		}

		.hero-section h1 {
			font-size: 2rem;
		}

		.system-details-card,
		.services-card {
			padding: 1.5rem 1.25rem;
		}

		.detail-grid,
		.service-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
