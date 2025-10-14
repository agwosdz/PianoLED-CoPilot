<script lang="ts">
import { createEventDispatcher } from 'svelte';
import SettingsFormField from '$lib/components/SettingsFormField.svelte';
import { canonicalLedCount, canonicalGpioPin } from '$lib/stores/settings';

const dispatch = createEventDispatcher<{ change: any }>();

// Minimal sane default config used when none is provided
export let config: any = {
	gpio_pin: 19,
	gpio_power_pin: null,
	gpio_ground_pin: null,
	pins: [],
	led_frequency: 800000,
	led_dma: 5,
	pwm_range: 1024,
	spi_speed: 8000000,
	gpio_pull_up: false,
	gpio_pull_down: false,
	auto_detect_hardware: false,
	validate_gpio_pins: true,
	hardware_test_enabled: false,
	led_channel: 0,
	led_invert: false,
	debounce_time: 50
};

// Raspberry Pi board pinout (subset used by the UI)
const gpioPinout = [
	{ pin: 16, name: 'GPIO23', type: 'gpio', available: true, gpio: 23 },
	{ pin: 17, name: '3.3V', type: 'power', available: false, gpio: null },
	{ pin: 18, name: 'GPIO24', type: 'gpio', available: true, gpio: 24 },
	{ pin: 19, name: 'GPIO10 (MOSI)', type: 'gpio', available: true, gpio: 10, special: 'SPI' },
	{ pin: 20, name: 'GND', type: 'ground', available: false, gpio: null },
	{ pin: 21, name: 'GPIO9 (MISO)', type: 'gpio', available: true, gpio: 9, special: 'SPI' },
	{ pin: 22, name: 'GPIO25', type: 'gpio', available: true, gpio: 25 },
	{ pin: 23, name: 'GPIO11 (SCLK)', type: 'gpio', available: true, gpio: 11, special: 'SPI' },
	{ pin: 24, name: 'GPIO8 (CE0)', type: 'gpio', available: true, gpio: 8, special: 'SPI' },
	{ pin: 25, name: 'GND', type: 'ground', available: false, gpio: null },
	{ pin: 26, name: 'GPIO7 (CE1)', type: 'gpio', available: true, gpio: 7, special: 'SPI' },
	{ pin: 27, name: 'GPIO0 (ID_SD)', type: 'gpio', available: false, gpio: 0, special: 'ID' },
	{ pin: 28, name: 'GPIO1 (ID_SC)', type: 'gpio', available: false, gpio: 1, special: 'ID' },
	{ pin: 29, name: 'GPIO5', type: 'gpio', available: true, gpio: 5 },
	{ pin: 30, name: 'GND', type: 'ground', available: false, gpio: null },
	{ pin: 31, name: 'GPIO6', type: 'gpio', available: true, gpio: 6 },
	{ pin: 32, name: 'GPIO12 (PWM)', type: 'gpio', available: true, gpio: 12, special: 'PWM' },
	{ pin: 33, name: 'GPIO13 (PWM)', type: 'gpio', available: true, gpio: 13, special: 'PWM' },
	{ pin: 34, name: 'GND', type: 'ground', available: false, gpio: null },
	{ pin: 35, name: 'GPIO19 (PWM)', type: 'gpio', available: true, gpio: 19, special: 'PWM' },
	{ pin: 36, name: 'GPIO16', type: 'gpio', available: true, gpio: 16 },
	{ pin: 37, name: 'GPIO26', type: 'gpio', available: true, gpio: 26 },
	{ pin: 38, name: 'GPIO20 (PWM)', type: 'gpio', available: true, gpio: 20, special: 'PWM' },
	{ pin: 39, name: 'GND', type: 'ground', available: false, gpio: null },
	{ pin: 40, name: 'GPIO21 (PWM)', type: 'gpio', available: true, gpio: 21, special: 'PWM' }
];

let validationErrors: Record<string, string | null> = {};
// UI disabled state (used by parent pages to disable inputs during save/loads)
let disabled: boolean = false;
let hardwareTestResults: any = null;
let testingInProgress: boolean = false;

// Extract GPIO number from pin name (e.g., "GPIO19 (PWM)" -> 19)
function extractGpioNumber(pinName: string): number | null {
	const match = pinName.match(/GPIO(\d+)/);
	return match ? parseInt(match[1]) : null;
}

// Get GPIO number for a board pin
function getBoardPinGpio(boardPin: number): number | null {
	const pin = gpioPinout.find((p: any) => p.pin === boardPin);
	return pin ? pin.gpio : null;
}

// Find board pin by GPIO number
function findBoardPinByGpio(gpioNumber: number | null): number | null {
	const pin = gpioPinout.find((p: any) => p.gpio === gpioNumber);
	return pin ? pin.pin : null;
}

// Get pin information by GPIO number
function getPinInfo(gpioNumber: number | null): any {
	return gpioPinout.find((p: any) => p.gpio === gpioNumber);
}

function validatePin(pinNumber: number, pinType: string): string | null {
	const pin = gpioPinout.find((p: any) => p.pin === pinNumber);

	if (!pin) {
		return 'Invalid pin number';
	}

	if (!pin.available) {
		return `Pin ${pinNumber} is reserved (${pin.name})`;
	}

	// Check for conflicts with other assigned pins (convert GPIO numbers to board pins for comparison)
	const currentBoardPins = [
		findBoardPinByGpio(config.gpio_pin),
		findBoardPinByGpio(config.gpio_power_pin),
		findBoardPinByGpio(config.gpio_ground_pin)
	].filter((p) => p !== null && p !== pinNumber) as number[];

	if (currentBoardPins.includes(pinNumber)) {
		return 'Pin already in use';
	}

	// Warn about special function pins
	if (pin.special && pinType === 'gpio_pin') {
		return `Warning: Pin has special function (${pin.special})`;
	}

	return null;
}

function validateAdvancedConfig(): Record<string, string> {
	const errors: Record<string, string> = {};

	// Validate frequency
	if (config.led_frequency < 400000 || config.led_frequency > 1000000) {
		errors.led_frequency = 'Frequency should be between 400kHz and 1MHz';
	}

	// Validate DMA channel
	if (config.led_dma < 0 || config.led_dma > 14) {
		errors.led_dma = 'DMA channel must be between 0 and 14';
	}

	// Validate PWM range
	if (config.pwm_range < 256 || config.pwm_range > 4096) {
		errors.pwm_range = 'PWM range should be between 256 and 4096';
	}

	// Validate SPI speed
	if (config.spi_speed < 1000000 || config.spi_speed > 32000000) {
		errors.spi_speed = 'SPI speed should be between 1MHz and 32MHz';
	}

	// Check for conflicting pull resistor settings
	if (config.gpio_pull_up && config.gpio_pull_down) {
		errors.gpio_pull = 'Cannot enable both pull-up and pull-down resistors';
	}

	return errors;
}

function handleConfigChange(key: string, value: any): void {
	// Convert board pin number to GPIO number for pin-related configs
	if (key.includes('pin') && value !== null) {
		const gpioNumber = getBoardPinGpio(value);
		if (gpioNumber !== null) {
			config = { ...config, [key]: gpioNumber };
		} else {
			config = { ...config, [key]: value };
		}

		// Validate using board pin number
		const error = validatePin(value, key);
		validationErrors = { ...validationErrors, [key]: error };
	} else if (key.includes('pin')) {
		// Clear error if pin is set to null
		config = { ...config, [key]: null };
		const { [key]: removed, ...rest } = validationErrors;
		validationErrors = rest;
	} else {
		config = { ...config, [key]: value };
	}

	// Validate advanced configuration
	const advancedErrors = validateAdvancedConfig();
	validationErrors = { ...validationErrors, ...advancedErrors };

	dispatch('change', config);
}

async function testHardware(): Promise<void> {
	testingInProgress = true;
	hardwareTestResults = null;

	try {
		// Fetch system capabilities first
		await fetch('/api/hardware-test/system/capabilities');

		const response = await fetch('/api/hardware-test/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				gpio_pin: $canonicalGpioPin,
				led_count: $canonicalLedCount
			})
		});

		const data = await response.json();
			if (response.ok) {
				hardwareTestResults = data;
			} else {
				throw new Error(data?.error || data?.message || 'Hardware test failed');
			}
		} catch (error) {
			console.error('Hardware test error:', error);
			const message = error instanceof Error ? error.message : String(error);
			hardwareTestResults = { success: false, error: message, message };
		} finally {
			testingInProgress = false;
		}
	}

	async function detectHardware(): Promise<void> {
		try {
			const response = await fetch('/api/hardware-test/system/capabilities');
			const detected = await response.json();

			if (response.ok) {
				const recommendedGpio = detected?.recommended_gpio_pin ?? detected?.gpio_pin ?? detected?.default_gpio_pin;
				if (recommendedGpio !== undefined && recommendedGpio !== null) {
					handleConfigChange('gpio_pin', parseInt(recommendedGpio));
				}
				const recommendedFreq = detected?.recommended_frequency ?? detected?.led_frequency ?? detected?.default_frequency;
				if (recommendedFreq !== undefined && recommendedFreq !== null) {
					handleConfigChange('led_frequency', parseInt(recommendedFreq));
				}
			} else {
				console.error('Hardware capabilities detection failed:', detected?.error || detected?.message || 'Unknown error');
			}
		} catch (error) {
			console.error('Hardware detection failed:', error);
		}
	}

	function getPinStatus(pinNumber: number) : string | null {
		// Convert GPIO numbers to board pins for comparison
		const dataBoardPin = findBoardPinByGpio(config.gpio_pin);
		const powerBoardPin = findBoardPinByGpio(config.gpio_power_pin);
		const groundBoardPin = findBoardPinByGpio(config.gpio_ground_pin);
		
		if (pinNumber === dataBoardPin) return 'data';
		if (pinNumber === powerBoardPin) return 'power';
		if (pinNumber === groundBoardPin) return 'ground';
		return null;
	}

	function getPinClass(pin: any): string {
		const status = getPinStatus(pin.pin);
		if (status) return `assigned assigned-${status}`;
		if (!pin.available) return 'unavailable';
		if (pin.special) return 'special';
		return 'available';
	}

	// Per-pin assignments handlers
	function addPinAssignment(): void {
		const defaultBoardPin = 12; // reasonable default (GPIO18 PWM board pin 12)
		const newPin = { pin: defaultBoardPin, mode: 'output', note: 60, pullup: false };
		const pins = [...(config.pins || []), newPin];
		config = { ...config, pins };
		// Validate only the new pin
		const err = validatePin(defaultBoardPin, 'pin');
		validationErrors = { ...validationErrors, [`pins_${pins.length - 1}`]: err };
		dispatch('change', config);
	}

	function updatePinField(index: number, field: string, value: any): void {
		const pins = [...(config.pins || [])];
		pins[index] = { ...pins[index], [field]: value };
		config = { ...config, pins };
		// Validate board pin when updated
		if (field === 'pin') {
			const err = validatePin(value, 'pin');
			validationErrors = { ...validationErrors, [`pins_${index}`]: err };
		}
		dispatch('change', config);
	}


	function removePinAssignment(index: number): void {
			const pins = (config.pins || []).filter((_: any, i: number) => i !== index);
		config = { ...config, pins };
		const { [`pins_${index}`]: removed, ...rest } = validationErrors;
		validationErrors = rest;
		dispatch('change', config);
	}

	$: hasErrors = Object.values(validationErrors).some(error => error !== null);
	
	// Computed values for select bindings (convert GPIO numbers to board pins for display)
	$: selectedDataPin = findBoardPinByGpio(config.gpio_pin) || config.gpio_pin;
	$: selectedPowerPin = config.gpio_power_pin ? findBoardPinByGpio(config.gpio_power_pin) : null;
	$: selectedGroundPin = config.gpio_ground_pin ? findBoardPinByGpio(config.gpio_ground_pin) : null;
	$: dataPinInfo = getPinInfo(config.gpio_pin);
</script>

<div class="gpio-config-panel">
	<div class="config-section">
		<h3>GPIO Pin Configuration</h3>
		
		<div class="pin-configs">
			<div class="pin-config">
				<label for="gpio-data-pin">Data Pin (Required)</label>
				<select
					id="gpio-data-pin"
					bind:value={selectedDataPin}
					on:change={(e) => handleConfigChange('gpio_pin', parseInt((e.target as HTMLSelectElement).value))}
					{disabled}
					class:error={validationErrors.gpio_pin}
				>
					{#each gpioPinout.filter(p => p.available) as pin}
						<option value={pin.pin}>
							Pin {pin.pin} - {pin.name}
							{#if pin.special}(⚡ {pin.special}){/if}
						</option>
					{/each}
				</select>
				{#if dataPinInfo?.special}
					<div class="pin-info">
						<span class="special-function">⚡ Special Function: {dataPinInfo.special}</span>
					</div>
				{/if}
				{#if validationErrors.gpio_pin}
					<span class="error-message">{validationErrors.gpio_pin}</span>
				{/if}
			</div>

			<div class="pin-config">
				<label for="gpio-power-pin">Power Control Pin (Optional)</label>
				<select
					id="gpio-power-pin"
					bind:value={selectedPowerPin}
					on:change={(e) => handleConfigChange('gpio_power_pin', (e.target as HTMLSelectElement).value === '' ? null : parseInt((e.target as HTMLSelectElement).value))}
					{disabled}
					class:error={validationErrors.gpio_power_pin}
				>
					<option value={null}>None</option>
					{#each gpioPinout.filter(p => p.available) as pin}
						<option value={pin.pin}>Pin {pin.pin} - {pin.name}</option>
					{/each}
				</select>
				{#if validationErrors.gpio_power_pin}
					<span class="error-message">{validationErrors.gpio_power_pin}</span>
				{/if}
			</div>

			<div class="pin-config">
				<label for="gpio-ground-pin">Ground Reference Pin (Optional)</label>
				<select
					id="gpio-ground-pin"
					bind:value={selectedGroundPin}
					on:change={(e) => handleConfigChange('gpio_ground_pin', (e.target as HTMLSelectElement).value === '' ? null : parseInt((e.target as HTMLSelectElement).value))}
					{disabled}
					class:error={validationErrors.gpio_ground_pin}
				>
					<option value={null}>None</option>
					{#each gpioPinout.filter(p => p.available) as pin}
						<option value={pin.pin}>Pin {pin.pin} - {pin.name}</option>
					{/each}
				</select>
				{#if validationErrors.gpio_ground_pin}
					<span class="error-message">{validationErrors.gpio_ground_pin}</span>
				{/if}
			</div>
		</div>

		<div class="signal-config">
			<div class="config-row">
				<label for="signal-level">Signal Level</label>
				<select
					id="signal-level"
					bind:value={config.signal_level}
					on:change={(e) => handleConfigChange('signal_level', parseFloat((e.target as HTMLSelectElement).value))}
					{disabled}
				>
					<option value={3.3}>3.3V (Raspberry Pi GPIO)</option>
					<option value={5.0}>5.0V (Arduino/External)</option>
				</select>
			</div>

			<div class="config-row">
				<label for="gpio-pin">GPIO Data Pin</label>
				<SettingsFormField
					type="number"
					id="gpio-pin"
					bind:value={config.gpio_pin}
					min="1"
					max="40"
					category="gpio"
					settingKey="data_pin"
					helpText="Select the GPIO pin used for LED data"
					on:change={(e: CustomEvent) => handleConfigChange('gpio_pin', parseInt((e.detail as any).value))}
				/>
				{#if validationErrors.led_frequency}
					<span class="error-message">{validationErrors.led_frequency}</span>
				{/if}
			</div>

			<div class="config-row">
				<label for="led-frequency">LED Frequency (Hz)</label>
				<SettingsFormField
					type="number"
					id="led-frequency"
					bind:value={config.led_frequency}
					min="400000"
					max="1000000"
					step="10000"
					category="led"
					settingKey="update_rate"
					helpText="PWM/Signal frequency for LED driver"
					on:change={(e: CustomEvent) => handleConfigChange('led_frequency', parseInt((e.detail as any).value))}
				/>
				{#if validationErrors.led_frequency}
					<span class="error-message">{validationErrors.led_frequency}</span>
				{/if}
			</div>

			<div class="config-row">
				<label for="led-dma">DMA Channel</label>
				<input
					id="led-dma"
					type="number"
					min="0"
					max="14"
					bind:value={config.led_dma}
					on:input={(e) => handleConfigChange('led_dma', parseInt((e.target as HTMLInputElement).value))}
					{disabled}
					class:error={validationErrors.led_dma}
				/>
				{#if validationErrors.led_dma}
					<span class="error-message">{validationErrors.led_dma}</span>
				{/if}
			</div>

			<div class="config-row">
				<label for="led-channel">PWM Channel</label>
				<select
					id="led-channel"
					bind:value={config.led_channel}
					on:change={(e) => handleConfigChange('led_channel', parseInt((e.target as HTMLSelectElement).value))}
					{disabled}
				>
					<option value={0}>Channel 0</option>
					<option value={1}>Channel 1</option>
				</select>
			</div>

			<div class="config-row checkbox-row">
				<SettingsFormField
					type="checkbox"
					id="led-invert"
					label="Invert Signal Polarity"
					bind:value={config.led_invert}
					category="led"
					settingKey="reverse_order"
					helpText="Invert signal polarity"
					on:change={(e: CustomEvent) => handleConfigChange('led_invert', !!(e.detail as any).value)}
				/>
			</div>
		</div>
	</div>

	<!-- Advanced Configuration Section -->
	<div class="config-section">
		<h3>Advanced Configuration</h3>
		
		<div class="advanced-config">
			<div class="config-row">
				<label for="pwm-range">PWM Range</label>
				<input
					id="pwm-range"
					type="number"
					min="256"
					max="4096"
					step="256"
					bind:value={config.pwm_range}
					on:input={(e) => handleConfigChange('pwm_range', parseInt((e.target as HTMLInputElement).value))}
					{disabled}
					class:error={validationErrors.pwm_range}
				/>
				{#if validationErrors.pwm_range}
					<span class="error-message">{validationErrors.pwm_range}</span>
				{/if}
			</div>

			<div class="config-row">
				<label for="spi-speed">SPI Speed (Hz)</label>
				<select
					id="spi-speed"
					bind:value={config.spi_speed}
					on:change={(e) => handleConfigChange('spi_speed', parseInt((e.target as HTMLSelectElement).value))}
					{disabled}
					class:error={validationErrors.spi_speed}
				>
					<option value={1000000}>1 MHz</option>
					<option value={4000000}>4 MHz</option>
					<option value={8000000}>8 MHz (Standard)</option>
					<option value={16000000}>16 MHz</option>
					<option value={32000000}>32 MHz (Maximum)</option>
				</select>
				{#if validationErrors.spi_speed}
					<span class="error-message">{validationErrors.spi_speed}</span>
				{/if}
			</div>

			<div class="config-row checkbox-row">
				<label for="gpio-pull-up">
					<input
						id="gpio-pull-up"
						type="checkbox"
						bind:checked={config.gpio_pull_up}
						on:change={(e) => handleConfigChange('gpio_pull_up', (e.target as HTMLInputElement).checked)}
						{disabled}
					/>
					Enable Pull-up Resistor
				</label>
			</div>

			<div class="config-row checkbox-row">
				<label for="gpio-pull-down">
					<input
						id="gpio-pull-down"
						type="checkbox"
						bind:checked={config.gpio_pull_down}
						on:change={(e) => handleConfigChange('gpio_pull_down', (e.target as HTMLInputElement).checked)}
						{disabled}
					/>
					Enable Pull-down Resistor
				</label>
			</div>

			{#if validationErrors.gpio_pull}
				<span class="error-message">{validationErrors.gpio_pull}</span>
			{/if}

				<div class="config-row">
					<label for="debounce-time">Debounce Time (ms)</label>
					<SettingsFormField
						type="number"
						id="debounce-time"
						bind:value={config.debounce_time}
						min="0"
						max="1000"
						step="10"
						category="gpio"
						settingKey="debounce_time"
						helpText="Debounce time for GPIO inputs (0–1000 ms)"
						on:change={(e: CustomEvent) => handleConfigChange('debounce_time', parseInt((e.detail as any).value))}
					/>
					{#if validationErrors.debounce_time}
						<span class="error-message">{validationErrors.debounce_time}</span>
					{/if}
				</div>
		</div>
	</div>

	<!-- GPIO Pin Assignments (hidden: single-strip mode) -->
  <div class="config-section" style="display:none">
 		<h3 class="section-title">GPIO Pin Assignments</h3>
		<p class="section-help">Define per-pin assignments for inputs/outputs that the backend understands (board pin numbers 1–40).</p>
		<div class="pin-assignments">
			{#each config.pins || [] as assignment, index}
				<div class="pin-row">
					<SettingsFormField
						label="Board Pin"
						id={`pin-${index}`}
						type="select"
						options={gpioPinout.filter(p => p.available).map(p => ({ value: p.pin, label: `${p.pin} — ${p.name}` }))}
						value={assignment.pin}
						category="gpio"
						settingKey="pins"
						helpText="Select the board header pin (1–40)"
						on:change={(e) => updatePinField(index, 'pin', parseInt(String(e.detail.value)))}
					/>

					<SettingsFormField
						label="Mode"
						id={`mode-${index}`}
						type="select"
						options={[{ value: 'input', label: 'Input' }, { value: 'output', label: 'Output' }]}
						value={assignment.mode}
						category="gpio"
						settingKey="pins"
						helpText="Select pin function"
						on:change={(e) => updatePinField(index, 'mode', String(e.detail.value))}
					/>

					<SettingsFormField
						label="Note"
						id={`note-${index}`}
						type="number"
						min="0"
						max="127"
						value={assignment.note}
						category="gpio"
						settingKey="pins"
						helpText="MIDI note (0–127) if applicable"
						on:change={(e) => updatePinField(index, 'note', parseInt(String(e.detail.value)))}
					/>

					<SettingsFormField
						label="Pull-up"
						id={`pullup-${index}`}
						type="checkbox"
						value={assignment.pullup}
						category="gpio"
						settingKey="pins"
						helpText="Enable internal pull-up resistor"
						on:change={(e) => updatePinField(index, 'pullup', !!e.detail.value)}
					/>

					<button class="btn btn-danger" on:click={() => removePinAssignment(index)}>Remove</button>
					{#if validationErrors[`pins_${index}`]}
						<span class="error-message">{validationErrors[`pins_${index}`]}</span>
					{/if}
				</div>
			{/each}

			<button class="btn btn-primary" on:click={addPinAssignment}>Add Pin</button>
		</div>
	</div>

	<!-- Hardware Detection and Testing -->
	<div class="config-section">
		<h3>Hardware Detection & Testing</h3>
		
		<div class="hardware-controls">
				<div class="config-row checkbox-row">
					<label for="auto-detect">
						<input
							id="auto-detect"
							type="checkbox"
							bind:checked={config.auto_detect_hardware}
							on:change={(e) => handleConfigChange('auto_detect_hardware', (e.target as HTMLInputElement).checked)}
							{disabled}
						/>
						Auto-detect Hardware
					</label>
				</div>

			<div class="config-row checkbox-row">
				<SettingsFormField
					type="checkbox"
					id="validate-pins"
					label="Validate GPIO Pins"
					bind:value={config.validate_gpio_pins}
					category="user"
					settingKey="preferences.validate_gpio_pins"
					helpText="Validate GPIO Pins"
					on:change={(e) => handleConfigChange('validate_gpio_pins', !!e.detail.value)}
				/>
			</div>

			<div class="config-row checkbox-row">
				<SettingsFormField
					type="checkbox"
					id="hardware-test"
					label="Enable Hardware Testing"
					bind:value={config.hardware_test_enabled}
					category="hardware"
					settingKey="auto_detect_gpio"
					helpText="Enable Hardware Testing"
					on:change={(e) => handleConfigChange('hardware_test_enabled', !!e.detail.value)}
				/>
			</div>

			<div class="hardware-actions">
				<button 
					type="button" 
					on:click={detectHardware}
					{disabled}
					class="detect-btn"
				>
					🔍 Detect Hardware
				</button>

				<button 
					type="button" 
					on:click={testHardware}
					disabled={disabled || testingInProgress || !config.hardware_test_enabled}
					class="test-btn"
				>
					{#if testingInProgress}
						⏳ Testing...
					{:else}
						🧪 Test Hardware
					{/if}
				</button>
			</div>
		</div>

		{#if hardwareTestResults}
			<div class="test-results" class:success={hardwareTestResults.success} class:error={!hardwareTestResults.success}>
				<h4>Hardware Test Results</h4>
				{#if hardwareTestResults.success}
					<div class="success-message">
						✅ Hardware test passed successfully!
						{#if hardwareTestResults.details}
							<ul>
								{#each hardwareTestResults.details as detail}
									<li>{detail}</li>
								{/each}
							</ul>
						{/if}
						{#if hardwareTestResults.suggestions}
							<div class="suggestions">
								<strong>Suggestions:</strong>
								<ul>
									{#each hardwareTestResults.suggestions as suggestion}
										<li>{suggestion}</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{:else}
					<div class="error-message">
						⚠️ Hardware test failed.
						{#if hardwareTestResults.error}
							<p>{hardwareTestResults.error}</p>
						{/if}
						{#if hardwareTestResults.message}
							<p>{hardwareTestResults.message}</p>
						{/if}
						{#if hardwareTestResults.suggestions}
							<div class="suggestions">
								<strong>Suggestions:</strong>
								<ul>
									{#each hardwareTestResults.suggestions as suggestion}
										<li>{suggestion}</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}

	<!-- PINOUT DIAGRAM (temporarily disabled for parser isolation) -->
	<div class="pinout-diagram-placeholder">
		<p>Pinout diagram temporarily disabled while debugging parser issues.</p>
	</div>

	{#if hasErrors}
		<div class="validation-summary">
			<h4>⚠️ Configuration Issues</h4>
			<ul>
				{#each Object.entries(validationErrors) as [key, error]}
					{#if error}
						<li>{key.replace('_', ' ')}: {error}</li>
					{/if}
				{/each}
			</ul>
		</div>
	{/if}
</div>

<!-- End of component root -->
</div>

<style>
	.gpio-config-panel {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		padding: 1rem;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: #fafafa;
	}

	.config-section h3 {
		margin: 0 0 1rem 0;
		color: #333;
		font-size: 1.2rem;
		font-weight: 600;
	}

	.pin-configs {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.pin-config {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.pin-config label {
		font-weight: 500;
		color: #333;
		font-size: 0.9rem;
	}

	.pin-config select, .config-row input, .config-row select {
		padding: 0.5rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		background: white;
		font-size: 0.9rem;
	}

	.pin-config select.error, .config-row input.error, .config-row select.error {
		border-color: #dc3545;
		box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.1);
	}

	.error-message {
		color: #dc3545;
		font-size: 0.8rem;
		font-weight: 500;
	}

	.pin-info {
		margin-top: 0.25rem;
	}

	.special-function {
		color: #ff9800;
		font-size: 0.8rem;
		font-weight: 500;
	}

	.signal-config, .advanced-config {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		padding: 1rem;
		background: white;
		border-radius: 6px;
		border: 1px solid #e0e0e0;
	}

	.config-row {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.config-row label {
		font-weight: 500;
		color: #333;
		font-size: 0.9rem;
	}

	.checkbox-row {
		flex-direction: row;
		align-items: center;
	}

	.checkbox-row label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}

	.hardware-controls {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: 1rem;
		background: white;
		border-radius: 6px;
		border: 1px solid #e0e0e0;
	}

	.hardware-actions {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
	}

	.detect-btn, .test-btn {
		padding: 0.75rem 1.5rem;
		border: none;
		border-radius: 6px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.detect-btn {
		background: #2196f3;
		color: white;
	}

	.detect-btn:hover:not(:disabled) {
		background: #1976d2;
	}

	.test-btn {
		background: #4caf50;
		color: white;
	}

	.test-btn:hover:not(:disabled) {
		background: #388e3c;
	}

	.detect-btn:disabled, .test-btn:disabled {
		background: #ccc;
		cursor: not-allowed;
	}

	.test-results {
		margin-top: 1rem;
		padding: 1rem;
		border-radius: 6px;
		border: 1px solid;
	}

	.test-results.success {
		background: #e8f5e8;
		border-color: #4caf50;
		color: #2d5a2d;
	}

	.test-results.error {
		background: #ffebee;
		border-color: #f44336;
		color: #c62828;
	}

	.test-results h4 {
		margin: 0 0 0.5rem 0;
		font-size: 1rem;
	}

	.success-message, .error-message {
		font-weight: 500;
	}

	.suggestions {
		margin-top: 0.5rem;
	}

	.suggestions ul {
		margin: 0.5rem 0 0 0;
		padding-left: 1.5rem;
	}

	/* Pinout diagram styles removed: the diagram is intentionally disabled
	   in the markup (see .pinout-diagram-placeholder). If the diagram
	   is re-enabled later, reintroduce these styles then. */

	.validation-summary {
		padding: 1rem;
		background: #fff3cd;
		border: 1px solid #ffeaa7;
		border-radius: 6px;
	}

	.validation-summary h4 {
		margin: 0 0 0.5rem 0;
		color: #856404;
		font-size: 1rem;
	}

	.validation-summary ul {
		margin: 0;
		padding-left: 1.5rem;
		color: #856404;
	}

	/* Pin assignments section styles */
	.config-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; }
	.section-title { font-weight: 600; margin-bottom: 0.5rem; }
	.section-help { color: #6b7280; font-size: 0.9rem; margin-bottom: 0.75rem; }
	.pin-assignments { display: flex; flex-direction: column; gap: 0.75rem; }
	.pin-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr auto; gap: 0.75rem; align-items: center; }
	.btn.btn-danger { background: #dc2626; color: white; padding: 0.5rem 0.75rem; border-radius: 0.375rem; }
	.btn.btn-primary { background: #2563eb; color: white; padding: 0.5rem 0.75rem; border-radius: 0.375rem; }
	.error-message { color: #b91c1c; font-size: 0.85rem; }

	@media (max-width: 768px) {
		.pin-configs, .signal-config, .advanced-config {
			grid-template-columns: 1fr;
		}
		
		.hardware-actions {
			flex-direction: column;
		}
		
		/* pinout related responsive tweaks removed (diagram disabled) */
		
		.pin-row { grid-template-columns: 1fr; }
	}
</style>
 