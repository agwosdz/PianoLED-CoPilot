<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	import { getSocket, socketStatus } from '$lib/socket';
	import type { UsbMidiStatus, NetworkMidiStatus, MidiStatusUpdate } from '$lib/types/midi';

	const dispatch = createEventDispatcher();


	export let usbMidiStatus: UsbMidiStatus = {
		connected: false,
		deviceName: null,
		lastActivity: null,
		messageCount: 0
	};

	export let networkMidiStatus: NetworkMidiStatus = {
		connected: false,
		activeSessions: [],
		lastActivity: null,
		messageCount: 0
	};

	let socket: ReturnType<typeof getSocket> | null = null;
	let statusUnsubscribe: (() => void) | null = null;

	function connectSocket(): void {
		socket = getSocket();

		// Reflect global socket status
		statusUnsubscribe = socketStatus.subscribe((st: string) => {
			if (st === 'connected') {
				dispatch('connected');
			} else if (st === 'disconnected') {
				dispatch('disconnected');
			} else if (st === 'error') {
				dispatch('error', { error: 'Socket error' });
			}
		});

		// Attach listeners with typed payloads
		socket.on('midi_input_status', (data: any) => {
			const payload: MidiStatusUpdate = {
				type: 'usb_midi_status',
				status: {
					connected: Boolean(data?.active),
					deviceName: data?.device_name ?? null,
					lastActivity: data?.last_event_time ?? null,
					messageCount: data?.notes_received ?? 0
				}
			};
			handleMidiStatusUpdate(payload);
		});

		socket.on('midi_manager_status', (data: any) => {
			if (data?.sources) {
				if (data.sources.USB) {
					handleMidiStatusUpdate({
						type: 'usb_midi_status',
						status: {
							connected: Boolean(data.sources.USB.connected),
							deviceName: data.sources.USB.device_name ?? null,
							lastActivity: data.performance?.last_event_time ?? null,
							messageCount: data.event_counts?.USB ?? 0
						}
					});
				}
				if (data.sources.RTP_MIDI) {
					handleMidiStatusUpdate({
						type: 'network_midi_status',
						status: {
							connected: Boolean(data.sources.RTP_MIDI.connected),
							activeSessions: data.sources.RTP_MIDI.active_sessions ?? [],
							lastActivity: data.performance?.last_event_time ?? null,
							messageCount: data.event_counts?.RTP_MIDI ?? 0
						}
					});
				}
			}
		});

		socket.on('disconnect', (reason: any) => {
			dispatch('disconnected');
		});

		socket.on('connect_error', (error: unknown) => {
			if (error instanceof Error) dispatch('error', { error: error.message });
			else dispatch('error', { error: String(error) });
		});
	}

	function handleMidiStatusUpdate(data: MidiStatusUpdate): void {
		if (data.type === 'usb_midi_status') {
			usbMidiStatus = { ...usbMidiStatus, ...(data.status as Partial<UsbMidiStatus>) };
			dispatch('usbStatusUpdate', usbMidiStatus);
		} else if (data.type === 'network_midi_status') {
			networkMidiStatus = { ...networkMidiStatus, ...(data.status as Partial<NetworkMidiStatus>) };
			dispatch('networkStatusUpdate', networkMidiStatus);
		}
	}

	function formatLastActivity(timestamp: string | null | undefined): string {
		if (!timestamp) return 'Never';
		const now = Date.now();
		const activity = new Date(timestamp).getTime();
		const diffMs = now - activity;
		const diffSecs = Math.floor(diffMs / 1000);
		const diffMins = Math.floor(diffSecs / 60);
		const diffHours = Math.floor(diffMins / 60);

		if (diffSecs < 60) return `${diffSecs}s ago`;
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		return new Date(activity).toLocaleDateString();
	}

	onMount(() => {
		connectSocket();
	});

	onDestroy(() => {
		if (statusUnsubscribe) statusUnsubscribe();
		// Do not disconnect shared socket here; other components rely on it
	});
</script>

<div class="midi-connection-status">
	<div class="status-section">
		<h3>🔌 USB MIDI</h3>
		<div class="connection-indicator">
			<div class="status-dot {usbMidiStatus.connected ? 'connected' : 'disconnected'}"></div>
			<div class="status-info">
				<div class="status-text">
					{usbMidiStatus.connected ? 'Connected' : 'Disconnected'}
				</div>
				{#if usbMidiStatus.deviceName}
					<div class="device-info">{usbMidiStatus.deviceName}</div>
				{/if}
				<div class="activity-info">
					<span class="message-count">{usbMidiStatus.messageCount} messages</span>
					<span class="last-activity">Last: {formatLastActivity(usbMidiStatus.lastActivity)}</span>
				</div>
			</div>
		</div>
	</div>

	<div class="status-section">
		<h3>🌐 Network MIDI</h3>
		<div class="connection-indicator">
			<div class="status-dot {networkMidiStatus.connected ? 'connected' : 'disconnected'}"></div>
			<div class="status-info">
				<div class="status-text">
					{networkMidiStatus.connected ? 'Connected' : 'Disconnected'}
				</div>
				{#if networkMidiStatus.activeSessions.length > 0}
					<div class="sessions-info">
						{networkMidiStatus.activeSessions.length} active session{networkMidiStatus.activeSessions.length !== 1 ? 's' : ''}
					</div>
					<div class="session-list">
						{#each networkMidiStatus.activeSessions as session}
							<div class="session-item">
								<span class="session-name">{session.name}</span>
								<span class="session-status {session.status}">{session.status}</span>
							</div>
						{/each}
					</div>
				{/if}
				<div class="activity-info">
					<span class="message-count">{networkMidiStatus.messageCount} messages</span>
					<span class="last-activity">Last: {formatLastActivity(networkMidiStatus.lastActivity)}</span>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.midi-connection-status {
		display: flex;
		gap: 2rem;
		padding: 1.5rem;
		background: #f8f9fa;
		border-radius: 8px;
		border: 1px solid #e9ecef;
	}

	.status-section {
		flex: 1;
		min-width: 200px;
		max-width: 300px;
	}

	.status-section h3 {
		margin: 0 0 0.75rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: #495057;
	}

	.connection-indicator {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.status-dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		margin-top: 0.25rem;
		box-shadow: 0 0 0 2px rgba(255,255,255,0.8);
		transition: all 0.3s ease;
	}

	.status-dot.connected {
		background: #28a745;
		box-shadow: 0 0 0 2px rgba(40, 167, 69, 0.3), 0 0 8px rgba(40, 167, 69, 0.6);
		animation: pulse 2s infinite;
	}

	.status-dot.disconnected {
		background: #dc3545;
		box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.3);
	}

	@keyframes pulse {
		0% { transform: scale(1); }
		50% { transform: scale(1.1); }
		100% { transform: scale(1); }
	}

	.status-info {
		flex: 1;
		min-width: 0;
	}

	.status-text {
		font-weight: 600;
		color: #212529;
		margin-bottom: 0.25rem;
	}

	.device-info {
		font-size: 0.9rem;
		color: #6c757d;
		margin-bottom: 0.5rem;
		font-family: monospace;
	}

	.sessions-info {
		font-size: 0.9rem;
		color: #495057;
		margin-bottom: 0.5rem;
	}

	.session-list {
		margin-bottom: 0.5rem;
	}

	.session-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.25rem 0.5rem;
		background: white;
		border-radius: 4px;
		margin-bottom: 0.25rem;
		font-size: 0.85rem;
	}

	.session-name {
		font-family: monospace;
		color: #495057;
	}

	.session-status {
		padding: 0.125rem 0.375rem;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: uppercase;
	}

	.session-status.connected {
		background: #d4edda;
		color: #155724;
	}

	.session-status.connecting {
		background: #fff3cd;
		color: #856404;
	}

	.session-status.disconnected {
		background: #f8d7da;
		color: #721c24;
	}

	.activity-info {
		display: flex;
		justify-content: space-between;
		font-size: 0.8rem;
		color: #6c757d;
		gap: 1rem;
	}

	.message-count {
		font-weight: 500;
	}

	.last-activity {
		font-style: italic;
	}

	@media (max-width: 768px) {
		.midi-connection-status {
			flex-direction: column;
			gap: 1rem;
		}

		.activity-info {
			flex-direction: column;
			gap: 0.25rem;
		}
	}
</style>