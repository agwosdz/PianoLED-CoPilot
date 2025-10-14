<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import { settings, settingsLoading, settingsError, loadSettings, updateSettings } from '$lib/stores/settings.js';
	import PianoKeyboardSelector from '$lib/components/PianoKeyboardSelector.svelte';
	import GPIOConfigPanel from '$lib/components/GPIOConfigPanel.svelte';
	import LEDStripConfig from '$lib/components/LEDStripConfig.svelte';
	import LEDTestSequence from '$lib/components/LEDTestSequence.svelte';
	import ConfigurationManager from '$lib/components/ConfigurationManager.svelte';
	import DashboardControls from '$lib/components/DashboardControls.svelte';
	import SettingsSection from '$lib/components/SettingsSection.svelte';
	import SettingsValidationMessage from '$lib/components/SettingsValidationMessage.svelte';
	import MidiDeviceSelector from '$lib/components/MidiDeviceSelector.svelte';
	import NetworkMidiConfig from '$lib/components/NetworkMidiConfig.svelte';
	import MidiConnectionStatus from '$lib/components/MidiConnectionStatus.svelte';
	import type { UsbMidiStatus, NetworkMidiStatus } from '$lib/types/midi';
import { normalizeSettings } from '$lib/utils/normalizeSettings.js';

	// Component state
	let message: string = '';
	type MessageType = 'error' | 'success' | 'warning' | 'info' | 'validating';
	let messageType: MessageType = 'info';
	let activeTab: string = 'piano';
	let hasUnsavedChanges: boolean = false;
	let originalSettings: Record<string, any> = {};

	// MIDI device management
	let selectedMidiDevice: string | null = null;
	let midiDevicesExpanded: boolean = true; // Expanded by default
	let networkMidiExpanded: boolean = true; // Expanded by default

	// MIDI connection status
	let usbMidiStatus: UsbMidiStatus = { connected: false, deviceName: null, lastActivity: null, messageCount: 0 };

	let networkMidiStatus: NetworkMidiStatus = { connected: false, activeSessions: [], lastActivity: null, messageCount: 0 };

	// Reactive statements
	let loading: boolean = false;
	let error: string | null = null;
	// currentSettings uses normalization util which returns a plain object
	let currentSettings: Record<string, any> = {};

	$: loading = $settingsLoading;
	$: error = $settingsError;
	$: currentSettings = normalizeSettings($settings);

	// Watch for changes to detect unsaved changes
	$: {
		if (Object.keys(originalSettings).length > 0) {
			hasUnsavedChanges = JSON.stringify(currentSettings) !== JSON.stringify(originalSettings);
		}
	}

	const tabs = [
		{ id: 'piano', label: 'Piano Setup', icon: '🎹' },
		{ id: 'midi', label: 'MIDI Config', icon: '🎵' },
		{ id: 'gpio', label: 'GPIO Config', icon: '🔌' },
		{ id: 'led', label: 'LED Strip', icon: '💡' },
		{ id: 'mapping', label: 'Key Mapping', icon: '🗂️' },
    { id: 'test', label: 'LED Test', icon: '🧪' },
    { id: 'advanced', label: 'Advanced', icon: '⚙️' },
    { id: 'config', label: 'Config Management', icon: '📁' }
  ];

	const pianoSizes = [
		{ value: '25-key', label: '25 Key (2 Octaves)' },
		{ value: '37-key', label: '37 Key (3 Octaves)' },
		{ value: '49-key', label: '49 Key (4 Octaves)' },
		{ value: '61-key', label: '61 Key (5 Octaves)' },
		{ value: '76-key', label: '76 Key (6+ Octaves)' },
		{ value: '88-key', label: '88 Key (Full Piano)' }
	];

	const orientations = [
		{ value: 'normal', label: 'Normal (Low to High)' },
		{ value: 'reversed', label: 'Reversed (High to Low)' }
	];

	onMount(async () => {
		await loadSettingsData();
	});

	async function loadSettingsData() {
		try {
			await loadSettings();
			// Store a normalized snapshot for change detection
			originalSettings = JSON.parse(JSON.stringify(normalizeSettings($settings)));
			hasUnsavedChanges = false;
		} catch (error) {
			console.error('Error loading settings:', error);
			showMessage('Error loading settings', 'error');
		}
	}

	async function saveSettings() {
		try {
			await updateSettings(currentSettings);
			originalSettings = JSON.parse(JSON.stringify(currentSettings));
			hasUnsavedChanges = false;
			showMessage('Settings saved successfully!', 'success');
		} catch (error) {
			console.error('Error saving settings:', error);
			const msg = error instanceof Error ? error.message : String(error);
			showMessage(msg || 'Failed to save settings', 'error');
		}
	}

function resetSettings() {
	if (confirm('Are you sure you want to reset all changes?')) {
		// Reset to original settings by updating the store
		updateSettings(originalSettings);
		hasUnsavedChanges = false;
		showMessage('Settings reset to last saved state', 'info');
	}
}

async function testHardware() {
	try {
		showMessage('Testing hardware configuration...', 'info');
		
		const response = await fetch('/api/hardware-test/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				gpio_pin: currentSettings?.gpio?.data_pin ?? 19,
				led_count: parseInt(currentSettings?.led?.led_count ?? currentSettings?.led_count ?? 246)
			})
		});

		if (response.ok) {
			const result = await response.json();
			showMessage(`Hardware test ${result.success ? 'passed' : 'failed'}: ${result.message}`, result.success ? 'success' : 'error');
		} else {
			showMessage('Hardware test failed', 'error');
		}
	} catch (e) {
		showMessage(`Hardware test error: ${e instanceof Error ? e.message : String(e)}`, 'error');
	}
}

	function handleSettingsChange(newSettings: Record<string, any>) {
	updateSettings({ ...currentSettings, ...newSettings });
}

function handleLEDSettingsChange(newLEDSettings: Record<string, any>) {
	const updated = {
		...currentSettings,
		led: {
			// Only include required/essential fields to avoid backend validation errors
			enabled: currentSettings.led?.enabled ?? true,
			led_count: parseInt(newLEDSettings.ledCount ?? currentSettings.led?.led_count ?? currentSettings.led_count ?? 246),
			brightness: (newLEDSettings.brightness ?? 100) / 100,
			led_orientation: newLEDSettings.ledOrientation ?? (currentSettings.led?.led_orientation ?? currentSettings.led_orientation ?? 'normal'),
			// Include update rate if provided by LEDStripConfig
			...(newLEDSettings.updateRate !== undefined ? { update_rate: parseInt(newLEDSettings.updateRate) } : {})
		},
		gpio: {
			...currentSettings.gpio,
			data_pin: currentSettings.gpio?.data_pin ?? 19
		}
	};
	updateSettings(updated);
	hasUnsavedChanges = true;
}

// LED Test Event Handlers
async function handleLEDTest(event: CustomEvent<{ ledIndex: number; color: { r:number; g:number; b:number }; brightness: number }>) {
	const { ledIndex, color, brightness } = event.detail;
	
	try {
		// If ledIndex is -1, clear all LEDs using a custom sequence
		if (ledIndex === -1) {
			const response = await fetch('/api/hardware-test/led/sequence', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					sequence_type: 'custom',
					duration: 0.2,
					led_count: currentSettings.led?.led_count ?? currentSettings.led_count ?? 246,
					gpio_pin: currentSettings.gpio?.data_pin ?? 19,
					pattern: [
						{ leds: [], color: [0, 0, 0], brightness: 0, duration: 0.1 }
					]
				})
			});

			if (!response.ok) {
				showMessage('LED clear request failed', 'error');
				return;
			}
			showMessage('All LEDs cleared', 'success');
			return;
		}

		// Otherwise, test a specific LED using the correct payload
		const response = await fetch('/api/hardware-test/led/individual', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				led_index: ledIndex,
				color: [color.r, color.g, color.b],
				brightness: brightness,
				duration: 2000, // 2 seconds
				gpio_pin: currentSettings.gpio?.data_pin ?? 19,
				led_count: currentSettings.led?.led_count ?? currentSettings.led_count ?? 246
			})
		});

		if (response.ok) {
			const result = await response.json();
			if (result.success) {
				showMessage(`LED ${ledIndex} test started`, 'success');
			} else {
				showMessage(`LED test failed: ${result.error}`, 'error');
			}
		} else {
			showMessage('LED test request failed', 'error');
		}
	} catch (error) {
		console.error('Error testing LED:', error);
		showMessage('Error testing LED', 'error');
	}
}

async function handlePatternTest(event: CustomEvent<{ pattern: string; duration: number }>) {
	const { pattern, duration } = event.detail;
	
	try {
		const response = await fetch('/api/hardware-test/led/sequence', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				sequence_type: pattern,
				duration: duration,
				led_count: currentSettings.led?.led_count ?? currentSettings.led_count ?? 246,
				gpio_pin: currentSettings.gpio?.data_pin ?? 19
			})
		});

		if (response.ok) {
			const result = await response.json();
			if (result.success) {
				showMessage(`Pattern test '${pattern}' started`, 'success');
			} else {
				showMessage(`Pattern test failed: ${result.error}`, 'error');
			}
		} else {
			showMessage('Pattern test request failed', 'error');
		}
	} catch (error) {
		console.error('Error testing pattern:', error);
		showMessage('Error testing pattern', 'error');
	}
}

	function handleLEDCountChange(event: CustomEvent<{ ledCount: number }>) {
	const { ledCount } = event.detail;
	
	// Update the LED count in settings
	const updatedSettings = {
		...currentSettings,
		led: {
			...currentSettings.led,
			led_count: ledCount
		}
	};
	updateSettings(updatedSettings);
	
	showMessage(`LED count updated to ${ledCount}`, 'info');
}

	function showMessage(text: string, type: MessageType) {
	message = text;
	messageType = type;
	setTimeout(() => {
		message = '';
	}, 5000);
}

// MIDI device event handlers
	async function handleMidiDeviceSelected(event: CustomEvent<{ id: string; name: string }>) {
	console.log('MIDI device selected:', event.detail);
	selectedMidiDevice = event.detail.id;
	
	// Connect to the selected MIDI device
	try {
		const response = await fetch('/api/midi-input/start', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				device_name: event.detail.name,
				enable_usb: true,
				enable_rtpmidi: false
			})
		});
		
		if (response.ok) {
			const result = await response.json();
			console.log('MIDI device connected successfully:', result);
			showMessage('MIDI device connected successfully', 'success');
		} else {
			const error = await response.json();
			console.error('Failed to connect to MIDI device:', error);
			showMessage('Failed to connect to MIDI device', 'error');
		}
	} catch (error) {
		console.error('Error connecting to MIDI device:', error);
		showMessage('Error connecting to MIDI device', 'error');
	}
}

	function handleMidiDevicesUpdated(event: CustomEvent<any>) {
		console.log('MIDI devices updated:', event.detail);
	}

	function handleNetworkMidiConnected(event: CustomEvent<any>) {
		console.log('Network MIDI session connected:', event.detail);
		showMessage('Network MIDI session connected', 'success');
	}

	function handleNetworkMidiDisconnected(event: CustomEvent<any>) {
		console.log('Network MIDI session disconnected:', event.detail);
		showMessage('Network MIDI session disconnected', 'info');
	}

	function handleNetworkMidiSessionsUpdated(event: CustomEvent<any>) {
		console.log('Network MIDI sessions updated:', event.detail);
	}

// MIDI connection status event handlers
	function handleMidiStatusConnected(event: CustomEvent<any>) {
		console.log('MIDI status WebSocket connected');
	}

	function handleMidiStatusDisconnected(event: CustomEvent<any>) {
		console.log('MIDI status WebSocket disconnected');
	}

	function handleUsbStatusUpdate(event: CustomEvent<any>) {
		usbMidiStatus = event.detail;
	}

	function handleNetworkStatusUpdate(event: CustomEvent<any>) {
		networkMidiStatus = event.detail;
	}
</script>

<svelte:head>
	<title>Settings - Piano LED</title>
</svelte:head>

<div class="page-header">
  <div class="spacer"></div>
  <StatusBadge />
</div>


<div class="container mx-auto px-4 py-8 max-w-6xl">
	<div class="bg-white rounded-lg shadow-lg">
		<div class="p-6 border-b border-gray-200">
			<h1 class="text-3xl font-bold text-gray-800 mb-2">Piano LED Configuration</h1>
			<p class="text-gray-600">Configure your piano LED system hardware and settings</p>
		</div>

		<div class="mx-6 mt-4">
			<SettingsValidationMessage 
				type={messageType} 
				message={message} 
				dismissible={true}
				on:dismiss={() => message = ''}
			/>
		</div>

		<!-- Tab Navigation -->
		<div class="border-b border-gray-200">
			<nav class="flex space-x-8 px-6" aria-label="Tabs">
				{#each tabs as tab}
					<button
						on:click={() => activeTab = tab.id}
						class="{activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
					>
						<span class="mr-2">{tab.icon}</span>
						{tab.label}
					</button>
				{/each}
			</nav>
		</div>

		<!-- Tab Content -->
		<div class="p-6 space-y-6">
			{#if activeTab === 'piano'}
				<SettingsSection
					title="Piano Configuration"
					description="Configure your piano keyboard settings and key mapping"
					icon="🎹"
					loading={loading}
					error={error}
					hasUnsavedChanges={hasUnsavedChanges}
					showActions={false}
				>
					<PianoKeyboardSelector 

						settings={{
							piano: {
								size: (currentSettings.piano && currentSettings.piano.size) || currentSettings.piano_size || '88-key',
								keys: (currentSettings.piano && currentSettings.piano.keys) || currentSettings.piano_keys || 88,
								octaves: (currentSettings.piano && currentSettings.piano.octaves) || currentSettings.piano_octaves || 7,
								startNote: (currentSettings.piano && currentSettings.piano.start_note) || currentSettings.piano_start_note || 'A0',
								endNote: (currentSettings.piano && currentSettings.piano.end_note) || currentSettings.piano_end_note || 'C8',
								keyMapping: (currentSettings.piano && currentSettings.piano.key_mapping_mode) || currentSettings.key_mapping_mode || 'chromatic'
							},
							led: {
								ledCount: parseInt(currentSettings.led?.led_count ?? currentSettings.led_count ?? 246),
								ledOrientation: currentSettings.led?.led_orientation ?? currentSettings.led_orientation ?? 'normal'
							}
						}}
						piano={{
							size: (currentSettings.piano && currentSettings.piano.size) || currentSettings.piano_size || '88-key',
							keys: (currentSettings.piano && currentSettings.piano.keys) || currentSettings.piano_keys || 88,
							octaves: (currentSettings.piano && currentSettings.piano.octaves) || currentSettings.piano_octaves || 7,
							startNote: (currentSettings.piano && currentSettings.piano.start_note) || currentSettings.piano_start_note || 'A0',
							endNote: (currentSettings.piano && currentSettings.piano.end_note) || currentSettings.piano_end_note || 'C8',
							keyMapping: (currentSettings.piano && currentSettings.piano.key_mapping_mode) || currentSettings.key_mapping_mode || 'chromatic'
						}}
						on:change={(e) => handleSettingsChange(e.detail)}
						on:change={(e) => {
							const { piano } = e.detail || {};
							if (piano) {
								const merged = {
									...currentSettings,
									piano_size: piano.size,
									piano_keys: piano.keys,
									piano_octaves: piano.octaves,
									piano_start_note: piano.startNote,
									piano_end_note: piano.endNote,
									key_mapping_mode: piano.keyMapping,
									piano: {
										...(currentSettings.piano || {}),
										size: piano.size,
										keys: piano.keys,
										octaves: piano.octaves,
										start_note: piano.startNote,
										end_note: piano.endNote,
										key_mapping_mode: piano.keyMapping,
										key_mapping: typeof (piano as any).keyMapping === 'object' ? (piano as any).keyMapping : {}
									}
								};
								currentSettings = merged;
								hasUnsavedChanges = true;
							}
							// Also forward to general handler for persistence if needed
							handleSettingsChange(e.detail);
						}}
					/>
				</SettingsSection>
			{:else if activeTab === 'midi'}
				<SettingsSection
					title="MIDI Configuration"
					description="Configure MIDI input devices and network connections"
					icon="🎵"
					loading={loading}
					error={error}
					showActions={false}
				>
					<div class="midi-config-section">
						<!-- MIDI Connection Status -->
						<div class="midi-status-container">
							<h3>MIDI Connection Status</h3>
							<MidiConnectionStatus 
								{usbMidiStatus}
								{networkMidiStatus}
								on:connected={handleMidiStatusConnected}
								on:disconnected={handleMidiStatusDisconnected}
								on:usbStatusUpdate={handleUsbStatusUpdate}
								on:networkStatusUpdate={handleNetworkStatusUpdate}
							/>
						</div>

						<div class="midi-panels">
							<div class="midi-panel">
								<button 
									class="panel-header" 
									type="button"
									on:click={() => midiDevicesExpanded = !midiDevicesExpanded}
									on:keydown={(e) => e.key === 'Enter' && (midiDevicesExpanded = !midiDevicesExpanded)}
								>
									<h3>USB MIDI Devices</h3>
									<span class="expand-icon {midiDevicesExpanded ? 'expanded' : ''}">
										{midiDevicesExpanded ? '▼' : '▶'}
									</span>
								</button>
								{#if midiDevicesExpanded}
									<div class="panel-content">
										<MidiDeviceSelector 
											on:deviceSelected={handleMidiDeviceSelected}
											on:devicesUpdated={handleMidiDevicesUpdated}
										/>
									</div>
								{/if}
							</div>

							<div class="midi-panel">
								<button 
									class="panel-header" 
									type="button"
									on:click={() => networkMidiExpanded = !networkMidiExpanded}
									on:keydown={(e) => e.key === 'Enter' && (networkMidiExpanded = !networkMidiExpanded)}
								>
									<h3>Network MIDI (RTP-MIDI)</h3>
									<span class="expand-icon {networkMidiExpanded ? 'expanded' : ''}">
										{networkMidiExpanded ? '▼' : '▶'}
									</span>
								</button>
								{#if networkMidiExpanded}
									<div class="panel-content">
										<NetworkMidiConfig 
											on:sessionConnected={handleNetworkMidiConnected}
											on:sessionDisconnected={handleNetworkMidiDisconnected}
											on:sessionsUpdated={handleNetworkMidiSessionsUpdated}
										/>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</SettingsSection>
			{:else if activeTab === 'gpio'}
				<SettingsSection
					title="GPIO Configuration"
					description="Configure GPIO pins and hardware settings for LED control"
					icon="🔌"
					loading={loading}
					error={error}
					hasUnsavedChanges={hasUnsavedChanges}
					on:save={() => saveSettings()}
					on:reset={() => resetSettings()}
					showActions={false}
				>
					<GPIOConfigPanel 
						config={{
							gpio_pin: currentSettings.gpio_pin || 19,
							gpio_power_pin: currentSettings.gpio_power_pin || null,
							gpio_ground_pin: currentSettings.gpio_ground_pin || null,
							signal_level: currentSettings.signal_level || 3.3,
							led_frequency: currentSettings.led_frequency || 800000,
							dma_channel: currentSettings.dma_channel || 10,
							auto_detect_hardware: currentSettings.auto_detect_hardware || false,
							validate_gpio_pins: currentSettings.validate_gpio_pins || true,
							hardware_test_enabled: currentSettings.hardware_test_enabled || false,
							gpio_pull_up: currentSettings.gpio_pull_up || [],
							gpio_pull_down: currentSettings.gpio_pull_down || [],
							pwm_range: currentSettings.pwm_range || 4096,
							spi_speed: currentSettings.spi_speed || 8000000
						}}
						on:change={(e) => handleSettingsChange(e.detail)}
					/>
				</SettingsSection>
			{:else if activeTab === 'led'}
				<SettingsSection
					title="LED Strip Configuration"
					description="Configure LED strip settings, power management, and visual effects"
					icon="💡"
					loading={loading}
					error={error}
					hasUnsavedChanges={hasUnsavedChanges}
					on:save={() => saveSettings()}
					on:reset={() => resetSettings()}
					showActions={false}
				>
				<LEDStripConfig 
					settings={{
						ledCount: parseInt(currentSettings.led?.led_count || currentSettings.led?.ledCount || currentSettings.led_count) || 246,
						maxLedCount: parseInt(currentSettings.led?.max_led_count || currentSettings.max_led_count) || 300,
						ledType: currentSettings.led?.ledType || currentSettings.led?.led_type || currentSettings.led_type || 'WS2812B',
						ledOrientation: currentSettings.led?.ledOrientation || currentSettings.led?.led_orientation || currentSettings.led_orientation || 'normal',
						ledStripType: currentSettings.led?.led_strip_type || currentSettings.led_strip_type || 'WS2811_STRIP_GRB',
						powerSupplyVoltage: currentSettings.led?.power_supply_voltage || currentSettings.power_supply_voltage || 5.0,
						powerSupplyCurrent: currentSettings.led?.power_supply_current || currentSettings.power_supply_current || 10.0,
						brightness: ((currentSettings.led?.brightness ?? currentSettings.brightness ?? 0.5) * 100),
						colorProfile: currentSettings.led?.color_profile || currentSettings.color_profile || 'standard',
						performanceMode: currentSettings.led?.performance_mode || currentSettings.performance_mode || 'balanced',
						advancedSettings: {
							gamma: currentSettings.led?.gamma_correction || currentSettings.gamma_correction || 2.2,
							whiteBalance: currentSettings.led?.white_balance || currentSettings.white_balance || { r: 1.0, g: 1.0, b: 1.0 },
							colorTemp: currentSettings.led?.color_temperature || currentSettings.color_temperature || 6500,
							dither: currentSettings.led?.dither_enabled || currentSettings.dither_enabled || true,
							updateRate: currentSettings.led?.update_rate || currentSettings.update_rate || 60,
							powerLimiting: currentSettings.led?.power_limiting_enabled || currentSettings.power_limiting_enabled || false,
							maxPower: currentSettings.led?.max_power_watts || currentSettings.max_power_watts || 100,
							thermalProtection: currentSettings.led?.thermal_protection_enabled || currentSettings.thermal_protection_enabled || true,
							maxTemperature: currentSettings.led?.max_temperature_celsius || currentSettings.max_temperature_celsius || 85
						}
					}}
					on:configChange={(e) => handleLEDSettingsChange(e.detail)}
				/>
				</SettingsSection>
			{:else if activeTab === 'test'}
				<SettingsSection
					title="LED Testing & Diagnostics"
					description="Test LED functionality and run diagnostic sequences"
					icon="🧪"
					loading={loading}
					error={error}
					showActions={false}
				>
					<div class="led-test-container">
						<LEDTestSequence 
							bind:settings={currentSettings}
							on:change={(e) => handleSettingsChange(e.detail)}
						/>
						
						<!-- Manual LED Control Section -->
						<div class="manual-control-section">
							<h3 class="text-lg font-medium text-gray-900 mb-4">Manual LED Control</h3>
							<p class="text-sm text-gray-600 mb-6">Test individual LEDs and patterns for troubleshooting and validation.</p>
							
							<div class="manual-controls-wrapper">
								<DashboardControls 
							connectionStatus={'connected'}
							ledCount={currentSettings.led?.led_count ?? currentSettings.led_count ?? 246}
							on:ledTest={handleLEDTest}
							on:patternTest={handlePatternTest}
							on:ledCountChange={handleLEDCountChange}
						/>
							</div>
						</div>
					</div>
				</SettingsSection>
			{:else if activeTab === 'config'}
				<SettingsSection
					title="Configuration Management"
					description="Import, export, and manage configuration presets"
					icon="📁"
					loading={loading}
					error={error}
					showActions={false}
				>
					<ConfigurationManager 
						bind:settings={currentSettings}
						on:change={(e) => handleSettingsChange(e.detail)}
					/>
				</SettingsSection>
			{:else if activeTab === 'advanced'}
				<SettingsSection
					title="Advanced Settings"
					description="Fine-tune color correction, gamma, and performance settings"
					icon="⚙️"
					loading={loading}
					error={error}
					hasUnsavedChanges={hasUnsavedChanges}
					showActions={false}
				>
				<div class="space-y-6">
					<h3 class="text-lg font-medium text-gray-900">Advanced Settings</h3>
					
					<!-- Color Temperature -->
					<div>
						<label for="color_temperature" class="block text-sm font-medium text-gray-700 mb-2">
							Color Temperature (K)
						</label>
						<input
							id="color_temperature"
							type="number"
							min="2700"
							max="10000"
							step="100"
							bind:value={currentSettings.color_temperature}
							on:input={() => handleSettingsChange({})}
							class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
						/>
						<p class="mt-1 text-sm text-gray-500">
							Adjust the color temperature of white light (2700K = warm, 6500K = daylight, 10000K = cool)
						</p>
					</div>

					<!-- Gamma Correction -->
					<div>
						<label for="gamma_correction" class="block text-sm font-medium text-gray-700 mb-2">
							Gamma Correction
						</label>
						<input
							id="gamma_correction"
							type="number"
							min="1.0"
							max="3.0"
							step="0.1"
							bind:value={currentSettings.gamma_correction}
							on:input={() => handleSettingsChange({})}
							class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
						/>
						<p class="mt-1 text-sm text-gray-500">
							Gamma correction for more natural color perception (2.2 is standard)
						</p>
					</div>

					<!-- Hardware Detection -->
					<div class="space-y-4">
						<h4 class="text-md font-medium text-gray-900">Hardware Detection</h4>
						
						<div class="flex items-center">
							<input
								id="auto_detect_hardware"
								type="checkbox"
								bind:checked={currentSettings.auto_detect_hardware}
								on:change={() => handleSettingsChange({})}
								class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							/>
							<label for="auto_detect_hardware" class="ml-2 block text-sm text-gray-900">
								Auto-detect hardware configuration
							</label>
						</div>

						<div class="flex items-center">
							<input
								id="validate_gpio_pins"
								type="checkbox"
								bind:checked={currentSettings.validate_gpio_pins}
								on:change={() => handleSettingsChange({})}
								class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							/>
							<label for="validate_gpio_pins" class="ml-2 block text-sm text-gray-900">
								Validate GPIO pin assignments
							</label>
						</div>

						<div class="flex items-center">
							<input
								id="hardware_test_enabled"
								type="checkbox"
								bind:checked={currentSettings.hardware_test_enabled}
								on:change={() => handleSettingsChange({})}
								class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							/>
							<label for="hardware_test_enabled" class="ml-2 block text-sm text-gray-900">
								Enable hardware testing
							</label>
						</div>
					</div>
				</div>
				</SettingsSection>
			{:else if activeTab === 'mapping'}
				<SettingsSection
					title="Key Mapping Configuration"
					description="Configure how piano keys map to LED positions"
					icon="🗂️"
					loading={loading}
					error={error}
					hasUnsavedChanges={hasUnsavedChanges}
					on:save={() => saveSettings()}
					on:reset={() => resetSettings()}
					showActions={false}
				>
					<div class="space-y-6">
						<p class="text-gray-600">Key mapping configuration will be available in a future update.</p>
					</div>
				</SettingsSection>
			{/if}
		</div>

		<!-- Action Buttons -->
		<div class="bg-gray-50 px-6 py-4 flex justify-between items-center rounded-b-lg">
			<div class="flex space-x-3">
				<button
					type="button"
					on:click={() => goto('/')}
					class="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
				>
					Back to Home
				</button>
				
				{#if hasUnsavedChanges}
					<button
						type="button"
						on:click={resetSettings}
						class="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
					>
						Reset Changes
					</button>
				{/if}
			</div>

			<div class="flex space-x-3">
				{#if currentSettings.hardware_test_enabled}
					<button
						type="button"
						on:click={testHardware}
						disabled={loading}
						class="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						{loading ? 'Testing...' : 'Test Hardware'}
					</button>
				{/if}
				
				<button
					type="button"
					on:click={saveSettings}
					disabled={loading || !hasUnsavedChanges}
					class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
				>
					{loading ? 'Saving...' : hasUnsavedChanges ? 'Save Settings' : 'Settings Saved'}
				</button>
			</div>
		</div>
	</div>
</div>

<style>
	/* Page Header Styles */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: flex-end; /* align badge to top right */
		padding: 10px 16px 0 16px;
	}
	.page-header .spacer { flex: 1; }

	/* LED Test Container Styles */
	.led-test-container {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.manual-control-section {
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		padding: 1.5rem;
		margin-top: 1rem;
	}

	.manual-controls-wrapper {
		background: white;
		border-radius: 0.375rem;
		padding: 1rem;
		box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
	}

	/* Responsive adjustments */
	@media (max-width: 768px) {
		.led-test-container {
			gap: 1rem;
		}
		
		.manual-control-section {
			padding: 1rem;
		}
		
		.manual-controls-wrapper {
			padding: 0.75rem;
		}
	}

	/* MIDI Configuration Styles */
	.midi-config-section {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.midi-status-container {
		margin-bottom: 0;
	}

	.midi-status-container h3 {
		margin-bottom: 1rem;
		color: #495057;
		font-size: 1.1rem;
		font-weight: 600;
	}

	.midi-panels {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
	}

	.midi-panel {
		border: 1px solid #e9ecef;
		border-radius: 8px;
		overflow: hidden;
	}

	.panel-header {
		background-color: #f8f9fa;
		padding: 1rem;
		cursor: pointer;
		display: flex;
		justify-content: space-between;
		align-items: center;
		transition: background-color 0.2s;
		border: none;
		width: 100%;
		text-align: left;
		font-family: inherit;
	}

	.panel-header:hover {
		background-color: #e9ecef;
	}

	.panel-header h3 {
		margin: 0;
		font-size: 1rem;
		color: #495057;
	}

	.expand-icon {
		font-size: 0.875rem;
		color: #6c757d;
		transition: transform 0.2s;
	}

	.expand-icon.expanded {
		transform: rotate(0deg);
	}

	.panel-content {
		padding: 1rem;
		border-top: 1px solid #e9ecef;
	}

	@media (max-width: 768px) {
		.midi-panels {
			grid-template-columns: 1fr;
		}
	}
</style>