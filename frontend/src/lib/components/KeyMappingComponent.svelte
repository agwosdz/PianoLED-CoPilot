<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher<{ change: any }>();

	export let settings: any = {};
	export let pianoSpecs: any = null;

	type PianoKey = { id: string; midi: number; note: string; type: 'white' | 'black'; ledIndices: number[] | number };
	type LED = { id: string; index: number; assignedKey: number | null; color: string };

	let draggedKey: PianoKey | null = null;
	let draggedLed: LED | null = null;
	let mappingMode: string = settings.mapping_mode || 'auto';
	let keyOffset: number = settings.key_offset || 0;
	let ledsPerKey: number = settings.leds_per_key || 3;
	let mappingBaseOffset: number = settings.mapping_base_offset || 0;
	let showAdvanced: boolean = false;

	// Piano key data
	const keyTypes = {
		white: ['C', 'D', 'E', 'F', 'G', 'A', 'B'],
		black: ['C#', 'D#', 'F#', 'G#', 'A#']
	};

	// Generate piano keys based on specs
	let pianoKeys: PianoKey[] = [];
	let ledStrip: LED[] = [];
	let keyMapping: Record<number, number | number[]> = settings.key_mapping || {};

	$: pianoKeys = generatePianoKeys();
	$: ledStrip = generateLEDStrip();
	$: keyMapping = settings.key_mapping || {};

	function generatePianoKeys(): PianoKey[] {
		if (!pianoSpecs) return [];

		const keys: PianoKey[] = [];
		const startOctave = Math.floor(pianoSpecs.midi_start / 12) - 1;
		const endOctave = Math.floor(pianoSpecs.midi_end / 12) - 1;

		for (let octave = startOctave; octave <= endOctave; octave++) {
			for (const note of keyTypes.white) {
				const midiNote = (octave + 1) * 12 + ['C', 'D', 'E', 'F', 'G', 'A', 'B'].indexOf(note);
				if (midiNote >= pianoSpecs.midi_start && midiNote <= pianoSpecs.midi_end) {
					keys.push({
						id: `key-${midiNote}`,
						midi: midiNote,
						note: `${note}${octave}`,
						type: 'white',
						ledIndices: (keyMapping as any)[midiNote] || []
					});
				}
			}

			for (const note of keyTypes.black) {
				const baseNote = note.replace('#', '');
				const midiNote = (octave + 1) * 12 + ['C', 'D', 'E', 'F', 'G', 'A', 'B'].indexOf(baseNote) + 1;
				if (midiNote >= pianoSpecs.midi_start && midiNote <= pianoSpecs.midi_end) {
					keys.push({
						id: `key-${midiNote}`,
						midi: midiNote,
						note: `${note}${octave}`,
						type: 'black',
						ledIndices: (keyMapping as any)[midiNote] || []
					});
				}
			}
		}

		return keys.sort((a, b) => a.midi - b.midi);
	}

	function generateLEDStrip(): LED[] {
		const ledCount: number = settings.ledCount || 246;
		const leds: LED[] = [];

		for (let i = 0; i < ledCount; i++) {
			leds.push({
				id: `led-${i}`,
				index: i,
				assignedKey: findKeyForLED(i),
				color: getLEDColor(i)
			});
		}

		return leds;
	}

	function findKeyForLED(ledIndex: number): number | null {
		for (const [midi, ledIndices] of Object.entries(keyMapping)) {
			const indices = Array.isArray(ledIndices) ? ledIndices : [ledIndices];
			if ((indices as number[]).includes(ledIndex)) {
				return parseInt(midi);
			}
		}
		return null;
	}

	function getLEDColor(ledIndex: number): string {
		const assignedKey = findKeyForLED(ledIndex);
		if (assignedKey) {
			const key = pianoKeys.find((k) => k.midi === assignedKey);
			return key?.type === 'black' ? '#2d3748' : '#f7fafc';
		}
		return '#e2e8f0';
	}

	function generateAutoMapping(): void {
		const newMapping: Record<number, number | number[]> = {};
		const whiteKeys = pianoKeys.filter((k) => k.type === 'white');
		const ledCount = settings.ledCount || 246;

		if (mappingMode === 'auto') {
			// Auto linear mapping with multi-LED support
			whiteKeys.forEach((key, index) => {
				const baseIndex = mappingBaseOffset + (index * ledsPerKey);
				if (ledsPerKey > 1) {
					const ledIndices: number[] = [];
					for (let i = 0; i < ledsPerKey; i++) {
						const ledIndex = baseIndex + i;
						if (ledIndex < ledCount) {
							ledIndices.push(ledIndex);
						}
					}
					if (ledIndices.length > 0) {
						(newMapping as any)[key.midi] = ledIndices;
					}
				} else {
					if (baseIndex < ledCount) {
						(newMapping as any)[key.midi] = baseIndex;
					}
				}
			});
		} else if (mappingMode === 'proportional') {
			// Proportional mapping with multi-LED support
			const totalKeys = whiteKeys.length;
			const availableLeds = ledCount - mappingBaseOffset;
			const ledsPerKeyFloat = availableLeds / totalKeys;

			whiteKeys.forEach((key, index) => {
				const baseIndex = mappingBaseOffset + Math.floor(index * ledsPerKeyFloat);
				if (ledsPerKey > 1) {
					const ledIndices: number[] = [];
					for (let i = 0; i < ledsPerKey; i++) {
						const ledIndex = baseIndex + i;
						if (ledIndex < ledCount) {
							ledIndices.push(ledIndex);
						}
					}
					if (ledIndices.length > 0) {
						(newMapping as any)[key.midi] = ledIndices;
					}
				} else {
					if (baseIndex < ledCount) {
						(newMapping as any)[key.midi] = baseIndex;
					}
				}
			});
		}

		updateMapping(newMapping);
	}

	function clearMapping() {
		updateMapping({});
	}

	function updateMapping(newMapping?: Record<number, number | number[]>): void {
		const updatedSettings = {
			...settings,
			key_mapping: newMapping,
			mapping_mode: mappingMode,
			key_offset: keyOffset,
			leds_per_key: ledsPerKey,
			mapping_base_offset: mappingBaseOffset
		};
		
		dispatch('change', updatedSettings);
	}

	// Drag and drop handlers
	function handleKeyDragStart(event: DragEvent, key: PianoKey): void {
		draggedKey = key;
		const dt = event.dataTransfer as DataTransfer;
		if (dt) {
			dt.effectAllowed = 'move';
			dt.setData('text/plain', key.id);
		}
	}

	function handleLEDDragStart(event: DragEvent, led: LED): void {
		draggedLed = led;
		const dt = event.dataTransfer as DataTransfer;
		if (dt) {
			dt.effectAllowed = 'move';
			dt.setData('text/plain', led.id);
		}
	}

	function handleKeyDrop(event: DragEvent, targetKey: PianoKey): void {
		event.preventDefault();

		if (draggedLed) {
			// LED dropped on key
			const newMapping: Record<number, number | number[]> = { ...(keyMapping as any) };

			// Remove existing mapping for this LED
			for (const [midi, ledIndex] of Object.entries(newMapping)) {
				const indices = Array.isArray(ledIndex) ? ledIndex : [ledIndex];
				if ((indices as number[]).includes(draggedLed.index)) {
					delete (newMapping as any)[midi];
				}
			}

			// For multi-LED mapping, add to existing array or create new array
			if (ledsPerKey > 1) {
				if (!(newMapping as any)[targetKey.midi]) {
					(newMapping as any)[targetKey.midi] = [];
				}
				if (!Array.isArray((newMapping as any)[targetKey.midi])) {
					(newMapping as any)[targetKey.midi] = [(newMapping as any)[targetKey.midi]];
				}
				if (!(newMapping as any)[targetKey.midi].includes(draggedLed.index)) {
					(newMapping as any)[targetKey.midi].push(draggedLed.index);
					// Limit to ledsPerKey
					if ((newMapping as any)[targetKey.midi].length > ledsPerKey) {
						(newMapping as any)[targetKey.midi] = (newMapping as any)[targetKey.midi].slice(-ledsPerKey);
					}
				}
			} else {
				// Single LED mapping
				(newMapping as any)[targetKey.midi] = draggedLed.index;
			}
			updateMapping(newMapping);
		}

		draggedKey = null;
		draggedLed = null;
	}

	function handleLEDDrop(event: DragEvent, targetLed: LED): void {
		event.preventDefault();

		if (draggedKey) {
			// Key dropped on LED
			const newMapping: Record<number, number | number[]> = { ...(keyMapping as any) };

			// Remove existing mapping for this key
			delete (newMapping as any)[draggedKey.midi];

			// Remove existing mapping for this LED
			for (const [midi, ledIndex] of Object.entries(newMapping)) {
				const indices = Array.isArray(ledIndex) ? ledIndex : [ledIndex];
				if ((indices as number[]).includes(targetLed.index)) {
					delete (newMapping as any)[midi];
				}
			}

			// Add new mapping
			(newMapping as any)[draggedKey.midi] = targetLed.index;
			updateMapping(newMapping);
		}

		draggedKey = null;
		draggedLed = null;
	}

	function handleDragOver(event: DragEvent): void {
		event.preventDefault();
		const dt = event.dataTransfer as DataTransfer;
		if (dt) dt.dropEffect = 'move';
	}

	function removeKeyMapping(key: PianoKey): void {
		if ((keyMapping as any)[key.note]) {
			delete (keyMapping as any)[key.note];
			keyMapping = { ...(keyMapping as any) };
			updateMapping();
		}
	}
</script>

<div class="space-y-6">
	<div class="flex justify-between items-center">
		<h3 class="text-lg font-medium text-gray-900">Key to LED Mapping</h3>
		<button
			on:click={() => showAdvanced = !showAdvanced}
			class="text-sm text-blue-600 hover:text-blue-800"
		>
			{showAdvanced ? 'Hide' : 'Show'} Advanced Options
		</button>
	</div>

	{#if showAdvanced}
		<div class="bg-gray-50 p-4 rounded-lg space-y-4">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				<div>
					<label for="mapping_mode" class="block text-sm font-medium text-gray-700 mb-2">
						Mapping Mode
					</label>
					<select
						id="mapping_mode"
						bind:value={mappingMode}
						on:change={() => updateMapping(keyMapping)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					>
						<option value="auto">Auto Linear</option>
						<option value="manual">Manual</option>
						<option value="proportional">Proportional</option>
					</select>
				</div>

				<div>
					<label for="leds_per_key" class="block text-sm font-medium text-gray-700 mb-2">
						LEDs per Key
					</label>
					<input
						id="leds_per_key"
						type="number"
						min="1"
						max="10"
						bind:value={ledsPerKey}
						on:input={() => updateMapping(keyMapping)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				<div>
					<label for="mapping_base_offset" class="block text-sm font-medium text-gray-700 mb-2">
						Base Offset
					</label>
					<input
						id="mapping_base_offset"
						type="number"
						min="0"
						max="100"
						bind:value={mappingBaseOffset}
						on:input={() => updateMapping(keyMapping)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				<div>
					<label for="key_offset" class="block text-sm font-medium text-gray-700 mb-2">
						Key Offset
					</label>
					<input
						id="key_offset"
						type="number"
						min="-50"
						max="50"
						bind:value={keyOffset}
						on:input={() => updateMapping(keyMapping)}
						class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				<div class="flex items-end space-x-2 md:col-span-2">
					<button
						on:click={generateAutoMapping}
						class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						Auto Map
					</button>
					<button
						on:click={clearMapping}
						class="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
					>
						Clear
					</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Piano Keys -->
		<div class="space-y-4">
			<h4 class="text-md font-medium text-gray-900">Piano Keys</h4>
			<div class="bg-white border border-gray-300 rounded-lg p-4 max-h-96 overflow-y-auto">
				<div class="space-y-2">
					{#each pianoKeys as key (key.id)}
						<div
							class="flex items-center justify-between p-2 rounded border {key.type === 'black' ? 'bg-gray-800 text-white border-gray-700' : 'bg-white border-gray-300'} cursor-move hover:shadow-md transition-shadow"
							role="button"
							tabindex="0"
							draggable="true"
							on:dragstart={(e) => handleKeyDragStart(e, key)}
							on:dragover={handleDragOver}
							on:drop={(e) => handleKeyDrop(e, key)}
						>
							<div class="flex items-center space-x-2">
								<span class="text-sm font-mono">{key.note}</span>
								<span class="text-xs text-gray-500">MIDI {key.midi}</span>
							</div>
							<div class="flex items-center space-x-2">
								{#if (Array.isArray(key.ledIndices) ? key.ledIndices.length > 0 : key.ledIndices !== null && key.ledIndices !== undefined)}
									{#if Array.isArray(key.ledIndices)}
										<div class="flex flex-wrap gap-1">
											{#each key.ledIndices as ledIndex}
												<span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">LED {ledIndex}</span>
											{/each}
										</div>
									{:else}
										<span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">LED {key.ledIndices}</span>
									{/if}
									<button
										on:click={() => removeKeyMapping(key)}
										class="text-red-600 hover:text-red-800 text-xs"
									>
										✕
									</button>
								{:else}
									<span class="text-xs text-gray-400">Unmapped</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<!-- LED Strip -->
		<div class="space-y-4">
			<h4 class="text-md font-medium text-gray-900">LED Strip ({ledStrip.length} LEDs)</h4>
			<div class="bg-white border border-gray-300 rounded-lg p-4 max-h-96 overflow-y-auto">
				<div class="grid grid-cols-10 gap-1">
					{#each ledStrip as led (led.id)}
						<div
							class="w-6 h-6 rounded-full border-2 cursor-move flex items-center justify-center text-xs font-mono transition-all hover:scale-110"
							role="button"
							tabindex="0"
							style="background-color: {led.color}; border-color: {led.assignedKey ? '#3b82f6' : '#d1d5db'}"
							title="LED {led.index}{led.assignedKey ? ` → Key ${led.assignedKey}` : ''}"
							draggable="true"
							on:dragstart={(e) => handleLEDDragStart(e, led)}
							on:dragover={handleDragOver}
							on:drop={(e) => handleLEDDrop(e, led)}
						>
							{#if led.assignedKey}
								<span class="text-white text-xs">•</span>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		</div>
	</div>

	<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
		<h5 class="text-sm font-medium text-blue-900 mb-2">How to Map Keys to LEDs</h5>
		<ul class="text-sm text-blue-800 space-y-1">
			<li>• Drag piano keys to LED positions or vice versa</li>
			<li>• Use "Auto Map" for automatic linear mapping</li>
			<li>• Adjust key offset to shift the mapping</li>
			<li>• Click ✕ to remove individual mappings</li>
			<li>• White keys are shown in white, black keys in dark gray</li>
		</ul>
	</div>

	<div class="text-sm text-gray-600">
		<strong>Mapping Statistics:</strong>
		{Object.keys(keyMapping).length} of {pianoKeys.length} keys mapped
		({Math.round((Object.keys(keyMapping).length / pianoKeys.length) * 100)}% complete)
	</div>
</div>

<style>
	.cursor-move {
		cursor: move;
	}
	
	.cursor-move:active {
		cursor: grabbing;
	}
</style>