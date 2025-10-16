<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { writable } from 'svelte/store';

	const dispatch = createEventDispatcher();

	interface MidiDevice {
		id: number;
		name: string;
		status: 'available' | 'connected' | 'error';
		type: 'usb' | 'network';
	}

	interface DeviceResponse {
		usb_devices: MidiDevice[];
		rtpmidi_sessions: MidiDevice[];
		total_count: number;
	}

	interface StatusResponse {
		listening: boolean;
		current_device: string | null;
		usb_listening: boolean;
		rtpmidi_listening: boolean;
		last_message_time: number | null;
	}

	export let autoRefresh = false;
	export let refreshInterval = 5000;

	let selectedDevice: number | null = null;

	let devices = writable<DeviceResponse>({
		usb_devices: [],
		rtpmidi_sessions: [],
		total_count: 0
	});

	let statusStore = writable<StatusResponse>({
		listening: false,
		current_device: null,
		usb_listening: false,
		rtpmidi_listening: false,
		last_message_time: null
	});

	let loading = false;
	let error: string | null = null;
	let refreshTimer: NodeJS.Timeout | null = null;
	let statusTimer: NodeJS.Timeout | null = null;
	let fetchInProgress = false;
	let statusFetchInProgress = false;
	let lastDispatchPayload: string | null = null;

	// Connection state
	let isConnecting = false;
	let isDisconnecting = false;
	let connectionError: string | null = null;

	onMount(() => {
		fetchDevices();
		fetchStatus();
		if (autoRefresh) {
			startAutoRefresh();
		}
		startStatusPolling();

		return () => {
			if (refreshTimer) {
				clearInterval(refreshTimer);
			}
			if (statusTimer) {
				clearInterval(statusTimer);
			}
		};
	});

	function startStatusPolling() {
		statusTimer = setInterval(fetchStatus, 2000);
	}

	async function fetchDevices() {
		if (fetchInProgress) {
			return;
		}

		fetchInProgress = true;
		loading = true;
		error = null;

		try {
			const response = await fetch('/api/midi-input/devices');
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const response_data = await response.json();
			const devices_data = response_data.devices || response_data;
			const safeData: DeviceResponse = {
				usb_devices: devices_data.usb_devices || [],
				rtpmidi_sessions: devices_data.rtpmidi_sessions || [],
				total_count: (devices_data.usb_devices?.length || 0) + (devices_data.rtpmidi_sessions?.length || 0)
			};
			devices.set(safeData);

			const serialized = JSON.stringify(safeData);
			if (serialized !== lastDispatchPayload) {
				lastDispatchPayload = serialized;
				dispatch('devicesUpdated', safeData);
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch devices';
			console.error('Error fetching MIDI devices:', err);
		} finally {
			loading = false;
			fetchInProgress = false;
		}
	}

	async function fetchStatus() {
		if (statusFetchInProgress) return;
		statusFetchInProgress = true;

		try {
			const response = await fetch('/api/midi-input/status');
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}

			const data: StatusResponse = await response.json();
			statusStore.set(data);
		} catch (err) {
			console.error('Error fetching MIDI status:', err);
		} finally {
			statusFetchInProgress = false;
		}
	}

	function startAutoRefresh() {
		if (refreshTimer) clearInterval(refreshTimer);
		refreshTimer = setInterval(fetchDevices, refreshInterval);
	}

	function stopAutoRefresh() {
		if (refreshTimer) {
			clearInterval(refreshTimer);
			refreshTimer = null;
		}
	}

	function selectDevice(device: MidiDevice) {
		selectedDevice = device.id;
		connectionError = null; // Clear any previous errors when selecting a new device
		// Note: Not dispatching deviceSelected anymore - connection is now explicit via button click
	}

	async function handleConnect() {
		if (!selectedDevice) {
			connectionError = 'Please select a device first';
			return;
		}

		const device = allDevices.find(d => d.id === selectedDevice);
		if (!device) {
			connectionError = 'Selected device not found';
			return;
		}

		isConnecting = true;
		connectionError = null;

		try {
			const response = await fetch('/api/midi-input/start', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ device_name: device.name })
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.message || 'Failed to connect');
			}

			// Update both status and device list to reflect connection
			await Promise.all([fetchStatus(), fetchDevices()]);
			dispatch('connected', { device });
		} catch (err) {
			connectionError = err instanceof Error ? err.message : 'Connection failed';
			console.error('Error connecting:', err);
		} finally {
			isConnecting = false;
		}
	}

	async function handleDisconnect() {
		if (isDisconnecting) return;

		isDisconnecting = true;
		connectionError = null;

		try {
			const response = await fetch('/api/midi-input/stop', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.message || 'Failed to disconnect');
			}

			// Update both status and device list to reflect disconnection
			await Promise.all([fetchStatus(), fetchDevices()]);
			dispatch('disconnected');
		} catch (err) {
			connectionError = err instanceof Error ? err.message : 'Disconnection failed';
			console.error('Error disconnecting:', err);
		} finally {
			isDisconnecting = false;
		}
	}

	function getDeviceStatusClass(status: string): string {
		switch (status) {
			case 'connected': return 'status-connected';
			case 'available': return 'status-available';
			case 'error': return 'status-error';
			default: return 'status-unknown';
		}
	}

	function getDeviceTypeIcon(type: string): string {
		return type === 'usb' ? '🔌' : '🌐';
	}

	function getDeviceById(id: number): MidiDevice | undefined {
		const allDevices = [...($devices.usb_devices || []), ...($devices.rtpmidi_sessions || [])];
		return allDevices.find(d => d.id === id);
	}

	$: allDevices = [...($devices.usb_devices || []), ...($devices.rtpmidi_sessions || [])];
	$: currentlyConnectedDevice = $statusStore.current_device;
	$: isAnythingConnected = $statusStore.listening;
	$: selectedDeviceObj = getDeviceById(selectedDevice || -1);
	$: isSelectedDeviceConnected = selectedDevice && selectedDeviceObj && currentlyConnectedDevice === selectedDeviceObj.name;</script>

<div class="midi-device-selector">
	<div class="header">
		<h3>🎹 MIDI Devices</h3>
		<div class="controls">
			<button 
				class="refresh-btn" 
				on:click={fetchDevices} 
				disabled={loading}
				title="Refresh device list"
			>
				{loading ? '⟳' : '🔄'}
			</button>
			<button 
				class="auto-refresh-btn {autoRefresh ? 'active' : ''}" 
				on:click={() => {
					autoRefresh = !autoRefresh;
					if (autoRefresh) startAutoRefresh();
					else stopAutoRefresh();
				}}
				title="Toggle auto-refresh"
			>
				📡
			</button>
		</div>
	</div>

	<!-- Real-time connection status -->
	<div class="status-display" class:connected={isAnythingConnected}>
		<div class="status-dot" class:active={isAnythingConnected}></div>
		<div class="status-info">
			{#if isAnythingConnected}
				<span class="status-label">Connected to</span>
				<span class="status-value">{currentlyConnectedDevice}</span>
			{:else}
				<span class="status-label">Status</span>
				<span class="status-value">Disconnected</span>
			{/if}
		</div>
	</div>

	{#if connectionError}
		<div class="error-message">
			⚠️ {connectionError}
			<button class="error-close" on:click={() => connectionError = null}>×</button>
		</div>
	{/if}

	{#if error}
		<div class="error-message">
			⚠️ {error}
			<button class="retry-btn" on:click={fetchDevices}>Retry</button>
		</div>
	{/if}

	{#if loading}
		<div class="loading">Loading devices...</div>
	{/if}

	<div class="device-sections">
		{#if $devices.usb_devices && $devices.usb_devices.length > 0}
			<div class="device-section">
				<h4>🔌 USB Devices ({$devices.usb_devices.length})</h4>
				<div class="device-list">
					{#each $devices.usb_devices as device}
						<div 
							class="device-item {selectedDevice === device.id ? 'selected' : ''} {getDeviceStatusClass(device.status)}"
							on:click={() => selectDevice(device)}
							role="button"
							tabindex="0"
							on:keydown={(e) => e.key === 'Enter' && selectDevice(device)}
						>
							<div class="device-info">
								<span class="device-icon">{getDeviceTypeIcon(device.type)}</span>
								<span class="device-name">{device.name}</span>
							</div>
							<div class="device-status">
								<span class="status-indicator"></span>
								<span class="status-text">{device.status}</span>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if $devices.rtpmidi_sessions && $devices.rtpmidi_sessions.length > 0}
			<div class="device-section">
				<h4>🌐 Network Devices ({$devices.rtpmidi_sessions.length})</h4>
				<div class="device-list">
					{#each $devices.rtpmidi_sessions as device}
						<div 
							class="device-item {selectedDevice === device.id ? 'selected' : ''} {getDeviceStatusClass(device.status)}"
							on:click={() => selectDevice(device)}
							role="button"
							tabindex="0"
							on:keydown={(e) => e.key === 'Enter' && selectDevice(device)}
						>
							<div class="device-info">
								<span class="device-icon">{getDeviceTypeIcon(device.type)}</span>
								<span class="device-name">{device.name}</span>
							</div>
							<div class="device-status">
								<span class="status-indicator"></span>
								<span class="status-text">{device.status}</span>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if allDevices.length === 0 && !loading}
			<div class="no-devices">
				<div class="no-devices-icon">🎹</div>
				<div class="no-devices-text">
					<p>No MIDI devices found</p>
					<p class="hint">Connect a USB MIDI device or configure network MIDI</p>
				</div>
			</div>
		{/if}
	</div>

	{#if selectedDevice}
		<div class="selected-device-info">
			<span class="label">Selected:</span>
			<span class="selected-name">
				{allDevices.find(d => d.id === selectedDevice)?.name || 'Unknown Device'}
			</span>
		</div>
	{/if}

	<!-- NEW: Connection Actions Section -->
	<div class="connection-actions">
		{#if connectionError}
			<div class="connection-error">
				<span>❌ {connectionError}</span>
				<button class="clear-error-btn" on:click={() => (connectionError = null)}>✕</button>
			</div>
		{/if}

		<div class="action-buttons">
			{#if !selectedDevice}
				<!-- No device selected -->
				<div class="no-selection-prompt">
					👆 Select a device to begin
				</div>
			{:else if isSelectedDeviceConnected}
				<!-- Selected device is currently connected -->
				<div class="connected-state">
					<div class="connected-badge">
						<span class="pulse-dot"></span>
						<span>Connected to {selectedDeviceObj?.name}</span>
					</div>
					<button 
						class="btn-disconnect" 
						on:click={handleDisconnect}
						disabled={isDisconnecting}
						title="Disconnect from current device"
					>
						{#if isDisconnecting}
							🔄 Disconnecting...
						{:else}
							✕ Disconnect
						{/if}
					</button>
				</div>
			{:else if isAnythingConnected}
				<!-- A different device is connected -->
				<div class="different-device-connected">
					<div class="info">A different device is currently connected</div>
					<button 
						class="btn-disconnect-first" 
						on:click={handleDisconnect}
						disabled={isDisconnecting}
						title="Disconnect the current device first"
					>
						{#if isDisconnecting}
							🔄 Disconnecting...
						{:else}
							Disconnect {currentlyConnectedDevice}
						{/if}
					</button>
				</div>
			{:else}
				<!-- Nothing connected, selected device available to connect -->
				<button 
					class="btn-connect" 
					on:click={handleConnect}
					disabled={isConnecting}
					title="Connect to selected device"
				>
					{#if isConnecting}
						🔄 Connecting...
					{:else}
						🔌 Connect Device
					{/if}
				</button>
			{/if}
		</div>
	</div>
</div>

<style>
	.midi-device-selector {
		background: var(--bg-secondary, #f8f9fa);
		border: 1px solid var(--border-color, #e1e5e9);
		border-radius: 8px;
		padding: 16px;
		max-width: 500px;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.header h3 {
		margin: 0;
		font-size: 1.1rem;
		color: var(--text-primary, #2c3e50);
	}

	.status-display {
		display: flex;
		align-items: center;
		gap: 12px;
		background: linear-gradient(135deg, rgba(0,123,255,0.05) 0%, rgba(40,167,69,0.05) 100%);
		border: 1px solid rgba(0,123,255,0.1);
		border-radius: 6px;
		padding: 12px;
		margin-bottom: 12px;
		transition: all 0.3s ease;
	}

	.status-display.connected {
		border-color: rgba(40,167,69,0.3);
		background: linear-gradient(135deg, rgba(40,167,69,0.08) 0%, rgba(40,167,69,0.04) 100%);
	}

	.status-dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: #ccc;
		transition: all 0.3s ease;
		flex-shrink: 0;
	}

	.status-dot.active {
		background: #28a745;
		box-shadow: 0 0 12px rgba(40,167,69,0.6);
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; box-shadow: 0 0 12px rgba(40,167,69,0.6); }
		50% { opacity: 0.6; box-shadow: 0 0 6px rgba(40,167,69,0.3); }
	}

	.status-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.status-label {
		font-size: 0.75rem;
		color: var(--text-secondary, #6c757d);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.status-value {
		font-weight: 600;
		color: var(--text-primary, #2c3e50);
		font-size: 0.95rem;
	}

	.controls {
		display: flex;
		gap: 8px;
	}

	.refresh-btn, .auto-refresh-btn {
		background: var(--bg-primary, #ffffff);
		border: 1px solid var(--border-color, #e1e5e9);
		border-radius: 4px;
		padding: 6px 8px;
		cursor: pointer;
		font-size: 14px;
		transition: all 0.2s ease;
	}

	.refresh-btn:hover, .auto-refresh-btn:hover {
		background: var(--bg-hover, #f1f3f4);
	}

	.refresh-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		animation: spin 1s linear infinite;
	}

	.auto-refresh-btn.active {
		background: var(--accent-color, #007bff);
		color: white;
		border-color: var(--accent-color, #007bff);
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	.error-message {
		background: #fee;
		border: 1px solid #fcc;
		border-radius: 4px;
		padding: 12px;
		margin-bottom: 16px;
		color: #c33;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.retry-btn {
		background: #c33;
		color: white;
		border: none;
		border-radius: 4px;
		padding: 4px 8px;
		cursor: pointer;
		font-size: 12px;
	}

	.loading {
		text-align: center;
		padding: 20px;
		color: var(--text-secondary, #6c757d);
		font-style: italic;
	}

	.device-section {
		margin-bottom: 20px;
	}

	.device-section h4 {
		margin: 0 0 8px 0;
		font-size: 0.9rem;
		color: var(--text-secondary, #6c757d);
		font-weight: 600;
	}

	.device-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.device-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px;
		background: var(--bg-primary, #ffffff);
		border: 1px solid var(--border-color, #e1e5e9);
		border-radius: 6px;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.device-item:hover {
		background: var(--bg-hover, #f1f3f4);
		border-color: var(--accent-color, #007bff);
	}

	.device-item.selected {
		background: var(--accent-light, #e3f2fd);
		border-color: var(--accent-color, #007bff);
		box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
	}

	.device-info {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.device-icon {
		font-size: 16px;
	}

	.device-name {
		font-weight: 500;
		color: var(--text-primary, #2c3e50);
	}

	.device-status {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.status-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #ccc;
	}

	.status-connected .status-indicator {
		background: #28a745;
		box-shadow: 0 0 4px rgba(40, 167, 69, 0.5);
	}

	.status-available .status-indicator {
		background: #ffc107;
	}

	.status-error .status-indicator {
		background: #dc3545;
	}

	.status-text {
		font-size: 12px;
		color: var(--text-secondary, #6c757d);
		text-transform: capitalize;
	}

	.no-devices {
		text-align: center;
		padding: 40px 20px;
		color: var(--text-secondary, #6c757d);
	}

	.no-devices-icon {
		font-size: 48px;
		margin-bottom: 16px;
		opacity: 0.5;
	}

	.no-devices-text p {
		margin: 8px 0;
	}

	.no-devices-text .hint {
		font-size: 0.9rem;
		opacity: 0.8;
	}

	.selected-device-info {
		margin-top: 16px;
		padding: 12px;
		background: var(--accent-light, #e3f2fd);
		border-radius: 6px;
		border-left: 4px solid var(--accent-color, #007bff);
	}

	.selected-device-info .label {
		font-weight: 600;
		color: var(--text-secondary, #6c757d);
	}

	.selected-device-info .selected-name {
		color: var(--text-primary, #2c3e50);
		font-weight: 500;
	}

	/* NEW: Connection Actions Styles */
	.connection-actions {
		margin-top: 16px;
		padding: 16px;
		background: #f0f7ff;
		border: 1px solid #bdd7ee;
		border-radius: 6px;
	}

	.connection-error {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px;
		background: #fee;
		border: 1px solid #fcc;
		border-radius: 4px;
		color: #c33;
		margin-bottom: 12px;
		font-size: 0.9rem;
	}

	.clear-error-btn {
		background: none;
		border: none;
		color: #c33;
		cursor: pointer;
		font-size: 16px;
		padding: 0;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: opacity 0.2s ease;
	}

	.clear-error-btn:hover {
		opacity: 0.7;
	}

	.action-buttons {
		display: flex;
		gap: 8px;
		flex-direction: column;
	}

	.btn-connect {
		padding: 10px 16px;
		background: linear-gradient(135deg, #007bff, #0056b3);
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-weight: 600;
		transition: all 0.2s ease;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
	}

	.btn-connect:hover:not(:disabled) {
		background: linear-gradient(135deg, #0056b3, #003a82);
		box-shadow: 0 4px 12px rgba(0, 86, 179, 0.3);
	}

	.btn-connect:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.connected-state {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}

	.connected-badge {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		background: #d4edda;
		border: 1px solid #c3e6cb;
		border-radius: 4px;
		color: #155724;
		font-weight: 500;
		font-size: 0.9rem;
		flex: 1;
	}

	.pulse-dot {
		width: 8px;
		height: 8px;
		background: #28a745;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	.btn-disconnect {
		padding: 10px 16px;
		background: #dc3545;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-weight: 600;
		transition: all 0.2s ease;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		white-space: nowrap;
	}

	.btn-disconnect:hover:not(:disabled) {
		background: #c82333;
		box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
	}

	.btn-disconnect:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.no-selection-prompt {
		padding: 12px 16px;
		background: #e7f3ff;
		border: 1px solid #b3d9ff;
		border-radius: 4px;
		color: #0056b3;
		text-align: center;
		font-weight: 500;
	}

	.different-device-connected {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px;
		background: #fff3cd;
		border: 1px solid #ffc107;
		border-radius: 4px;
	}

	.different-device-connected .info {
		color: #856404;
		font-size: 0.9rem;
		font-weight: 500;
	}

	.btn-disconnect-first {
		padding: 10px 16px;
		background: #ffc107;
		color: #333;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-weight: 600;
		transition: all 0.2s ease;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
	}

	.btn-disconnect-first:hover:not(:disabled) {
		background: #ffb300;
		box-shadow: 0 4px 12px rgba(255, 193, 7, 0.3);
	}

	.btn-disconnect-first:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
