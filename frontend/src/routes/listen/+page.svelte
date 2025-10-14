<script lang="ts" context="module">
	// Declare io from global Socket.IO client loaded in app.html
	declare const io: any;
</script>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import InteractiveButton from '$lib/components/InteractiveButton.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import Tooltip from '$lib/components/Tooltip.svelte';
	import ValidationPreview from '$lib/components/ValidationPreview.svelte';
	import ErrorRecoveryPanel from '$lib/components/ErrorRecoveryPanel.svelte';
	import OnboardingTour from '$lib/components/OnboardingTour.svelte';
	import PreferencesModal from '$lib/components/PreferencesModal.svelte';
	import { derived, get } from 'svelte/store';
	import { settings, settingsAPI } from '$lib/stores/settings';
	import { toastStore } from '$lib/stores/toastStore.js';
	import { historyStore, setupHistoryKeyboardShortcuts } from '$lib/stores/historyStore.js';
	import { getSocket } from '$lib/socket';
	import { statusManager, statusUtils } from '$lib/statusCommunication';
	import type { UploadProgress } from '$lib/upload';
	import { uploadMidiFile, validateMidiFile, formatFileSize, UploadError } from '$lib/upload';
	import type { ValidationResult } from '$lib/upload';
	import { handleUploadError, handleValidationError } from '$lib/errorRecovery';
	import type { ErrorContext } from '$lib/errorRecovery';
	interface SongInfo {
		filename: string;
		originalFilename: string;
		size: number;
		metadata: any | null;
	}

// Create derived stores for specific preference categories from unified settings
const uploadPreferences = derived(settings, ($settings) => $settings.user?.preferences?.upload ?? {});
const uiPreferences = derived(settings, ($settings) => $settings.user?.preferences?.ui ?? {});
const helpPreferences = derived(settings, ($settings) => $settings.user?.preferences?.help ?? {});

// Preference helper stores
const shouldShowTooltips = derived(uiPreferences, (ui) => ui.showTooltips !== false);
const tooltipDelay = derived(uiPreferences, (ui) => ui.tooltipDelay ?? 500);
const shouldShowOnboarding = derived(helpPreferences, (help) => !help.tourCompleted && help.showOnboarding !== false);

	// Playback state
	let playbackState: 'idle' | 'playing' | 'paused' | 'stopped' = 'idle';
	let currentTime = 0;
	let totalDuration = 0;
	let songInfo: SongInfo = {
		filename: '',
		originalFilename: '',
		size: 0,
		metadata: null
	};

	// Enhanced playback controls
	let tempoMultiplier = 1.0;
	let volumeMultiplier = 1.0;
	let loopEnabled = false;
	let loopStart = 0;
	let loopEnd = 0;
	let isDragging = false;
	let timelineElement: HTMLElement;

	// Upload state
	let fileInput: HTMLInputElement;
	let dropZone: HTMLDivElement;
	let selectedFile: File | null = null;
	let uploadStatus: 'idle' | 'uploading' | 'success' | 'error' = 'idle';
	let uploadMessage = '';
	let uploadProgress = 0;
	let isDragOver = false;
	let dragCounter = 0;
	let showOnboardingTour = false;
	let showPreferencesModal = false;
	let validationResult: ValidationResult | null = null;
	let currentError: ErrorContext | null = null;

	// Validation preview state
	let showValidationPreview = false;
	let previewFiles: File[] = [];
	let validationPreviewEnabled = true;

	// UI state
	let isLoading = false;
	let errorMessage = '';
	let progressPercentage = 0;

	// WebSocket connection for real-time updates
	let websocket: any = null;
	let statusInterval: NodeJS.Timeout | null = null;
	let reconnectAttempts = 0;
	const maxReconnectAttempts = 5;
	let connectionStatus = 'disconnected'; // 'connected', 'connecting', 'disconnected', 'polling'

	// Performance monitoring
	let midiEventCount = 0;
	let lastMidiEventTime = 0;
	let midiEventRate = 0;
	let performanceMonitorInterval: NodeJS.Timeout | null = null;

let autoUploadTimeout: ReturnType<typeof setTimeout> | null = null;
let onboardingTimeout: ReturnType<typeof setTimeout> | null = null;

// Sync validation preview preference
$: {
	const prefs = $uploadPreferences;
	if (prefs?.enableValidationPreview !== undefined) {
		validationPreviewEnabled = prefs.enableValidationPreview;
	}
}

// Automatically upload when preference enabled
$: {
	const prefs = $uploadPreferences;
	if (prefs?.autoUpload && selectedFile && uploadStatus === 'idle') {
		if (autoUploadTimeout) {
			clearTimeout(autoUploadTimeout);
		}
		autoUploadTimeout = setTimeout(() => {
			if (uploadStatus === 'idle' && selectedFile === fileInput?.files?.[0]) {
				handleUpload();
			}
			autoUploadTimeout = null;
		}, 1000);
	} else if (autoUploadTimeout) {
		clearTimeout(autoUploadTimeout);
		autoUploadTimeout = null;
	}
}

// Start onboarding tour when preference says so
$: {
	if ($shouldShowOnboarding && !showOnboardingTour) {
		if (onboardingTimeout) {
			clearTimeout(onboardingTimeout);
		}
		onboardingTimeout = setTimeout(() => {
			showOnboardingTour = true;
			onboardingTimeout = null;
		}, 1000);
	} else if (onboardingTimeout) {
		clearTimeout(onboardingTimeout);
		onboardingTimeout = null;
	}
}

	let fileMetadata: {
		name: string;
		size: string;
		type: string;
		lastModified: string;
	} | null = null;

	// Handle file selection (both click and drag-drop)
	async function handleFileSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];

		if (!file) {
			selectedFile = null;
			fileMetadata = null;
			resetValidationPreview();
			return;
		}

		// Show validation preview if enabled
		if (validationPreviewEnabled) {
			previewFiles = [file];
			showValidationPreview = true;
			return;
		}

		// Direct processing if preview is disabled
		await processFileSelection(file);
	}

	async function processFileSelection(file: File) {
		// Validate file type
		if (!file.name.toLowerCase().match(/\.(mid|midi)$/)) {
			uploadMessage = 'Only .mid and .midi files are supported';
			uploadStatus = 'error';
			return;
		}

		// Validate file size (1MB limit)
		if (file.size > 1024 * 1024) {
			uploadMessage = 'File size must be less than 1MB';
			uploadStatus = 'error';
			return;
		}

		// Clear any previous error states
		uploadMessage = '';
		uploadStatus = 'idle';

		// Remember last directory if preference is enabled
		const prefs = get(uploadPreferences);
		if (prefs?.rememberLastDirectory && file.webkitRelativePath) {
			settingsAPI.setSetting('upload', 'lastDirectory', file.webkitRelativePath);
		}

		await processSelectedFile(file);

		// Save state after file selection
		if (file) {
			saveState(`Selected file: ${file.name}`);
		}
	}

	function resetValidationPreview() {
		showValidationPreview = false;
		previewFiles = [];
	}

	// Process a selected file (common logic for click and drag-drop)
	async function processSelectedFile(file: File) {
		// Start processing status
		const processingId = statusUtils.processingStart(file.name);

		const validation = validateMidiFile(file);
		validationResult = validation;

		if (!validation.valid) {
			// Use enhanced error recovery system for validation errors
			currentError = handleValidationError(
				validation,
				() => {
					// Retry action - allow user to select a new file
					fileInput?.click();
				}
			);

			uploadStatus = 'error';
			uploadMessage = validation.message;
			selectedFile = null;
			fileMetadata = null;

			statusUtils.processingError(processingId, file.name, [
				{
					label: 'Retry',
					action: () => {
						// Retry validation
						processSelectedFile(file);
					},
					variant: 'primary',
					icon: '🔄'
				}
			]);

			// Clear the input if it was from file input
			if (fileInput) {
				fileInput.value = '';
			}
			return;
		}

		selectedFile = file;
		uploadStatus = 'idle';
		uploadMessage = '';
		validationResult = null; // Clear validation on success

		statusUtils.processingSuccess(processingId, file.name);		// Generate file metadata
		fileMetadata = {
			name: file.name,
			size: formatFileSize(file.size),
			type: file.type || 'audio/midi',
			lastModified: new Date(file.lastModified).toLocaleString()
		};

		// Save state after processing file
		saveState(`Processed file: ${file.name}`);
	}

	// Drag and drop event handlers
	function handleDragEnter(event: DragEvent) {
		event.preventDefault();
		dragCounter++;
		if (dragCounter === 1) {
			isDragOver = true;
		}
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		dragCounter--;
		if (dragCounter === 0) {
			isDragOver = false;
		}
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		// Ensure we show the correct drop effect
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'copy';
		}
	}

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragOver = false;
		dragCounter = 0;

		const files = event.dataTransfer?.files;
		if (files && files.length > 0) {
			const file = files[0];

			// Show validation preview if enabled
			if (validationPreviewEnabled) {
				previewFiles = [file];
				showValidationPreview = true;
				return;
			}

			// Direct processing if preview is disabled
			await processDroppedFile(file);
		}
	}

	async function processDroppedFile(file: File) {
		// Validate file type
		if (!file.name.toLowerCase().match(/\.(mid|midi)$/)) {
			currentError = handleValidationError({
				valid: false,
				message: 'Only .mid and .midi files are supported',
				errorType: 'extension',
				suggestion: 'Please select a MIDI file (.mid or .midi)',
				details: {
					actualExtension: file.name.split('.').pop() || 'no extension',
					allowedExtensions: ['.mid', '.midi']
				}
			}, () => {
				// Retry action - allow user to select a new file
				fileInput?.click();
			});
			uploadMessage = 'Only .mid and .midi files are supported';
			uploadStatus = 'error';
			return;
		}

		// Validate file size (1MB limit)
		if (file.size > 1024 * 1024) {
			currentError = handleValidationError({
				valid: false,
				message: 'File size must be less than 1MB',
				errorType: 'size',
				suggestion: 'Please select a smaller MIDI file (under 1MB)',
				details: {
					actualSize: `${(file.size / (1024 * 1024)).toFixed(2)}MB`,
					maxSize: '1MB'
				}
			}, () => {
				// Retry action - allow user to select a new file
				fileInput?.click();
			});
			uploadMessage = 'File size must be less than 1MB';
			uploadStatus = 'error';
			return;
		}

		// Clear any previous error states
		uploadMessage = '';
		uploadStatus = 'idle';

		await processSelectedFile(file);

		// Save state after drag and drop
		if (file) {
			saveState(`Dropped file: ${file.name}`);
		}
	}

	// Handle file upload with progress tracking
	async function handleUpload() {
		if (!selectedFile) return;

		// Start upload progress tracking
		const progressId = statusUtils.uploadStart(selectedFile.name);
		uploadStatus = 'uploading';
			uploadProgress = 0;
			uploadMessage = 'Uploading...';

			// Save state before upload
			saveState(`Started upload: ${selectedFile.name}`);

		try {
			const result = await uploadMidiFile(selectedFile, (progress: UploadProgress) => {
				uploadProgress = progress.percentage;
				uploadMessage = `Uploading... ${progress.percentage}%`;
				statusUtils.uploadProgress(progressId, progress.percentage, `${progress.percentage}%`);
			});

			uploadStatus = 'success';
			uploadMessage = `Successfully uploaded: ${result.filename}`;
			uploadProgress = 100;

			// Complete upload with success status
			statusUtils.uploadSuccess(progressId, result.filename || '', [
				{
					label: 'Start Playback',
					action: () => handlePlay(),
					variant: 'primary',
					icon: '▶'
				},
				{
					label: 'Upload Another',
					action: () => resetUpload(),
					variant: 'secondary',
					icon: '📁'
				}
			]);

			// Store the uploaded filename for playback
			localStorage.setItem('lastUploadedFile', result.filename || '');

			// Load song information
			await loadSongInfo(result.filename || '');

			// Save successful upload state
			saveState(`Upload completed: ${result.filename}`);

			// Reset form after a short delay
			setTimeout(() => {
				resetUpload();
				saveState('Reset upload form');
			}, 2000);
		} catch (error) {
			// Use enhanced error recovery system for upload errors
			const errorMessage = error instanceof UploadError ? error.message : 'An unexpected error occurred during upload';

			currentError = await handleUploadError(
				new Error(errorMessage),
				selectedFile.name,
				async () => {
					// Retry action
					await handleUpload();
				},
				() => {
					// Clear error and reset
					currentError = null;
					resetUpload();
				}
			);

			uploadStatus = 'error';
			uploadMessage = errorMessage;

			// Show upload error with retry action
			statusUtils.uploadError(progressId, selectedFile.name, errorMessage, [
				{
					label: 'Retry Upload',
					action: () => handleUpload(),
					variant: 'primary',
					icon: '🔄'
				},
				{
					label: 'Choose Different File',
					action: () => resetUpload(),
					variant: 'secondary',
					icon: '📁'
				}
			]);

			// Save error state
			saveState(`Upload failed: ${errorMessage}`);
		}
	}

	// Reset upload state
	function resetUpload() {
		// Show confirmation if preference is enabled and there's content to lose
		const prefs = get(uploadPreferences);
		if (prefs?.confirmBeforeReset && (selectedFile || uploadStatus === 'success')) {
			const confirmed = confirm('Are you sure you want to reset? This will clear your current file and progress.');
			if (!confirmed) return;
		}

		selectedFile = null;
		fileMetadata = null;
		uploadStatus = 'idle';
		uploadMessage = '';
			uploadProgress = 0;
			validationResult = null;
			fileInput.value = '';

			// Clear status messages
			statusManager.clearMessages();

			// Save reset state
			saveState('Reset upload form');
	}

	// Playback functions
	async function handlePlay() {
		try {
			isLoading = true;
			errorMessage = '';

			const response = await fetch('/api/play', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					filename: songInfo.filename
				})
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to start playback';
			}

		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to start playback';
			console.error('Playback error:', error);
		} finally {
			isLoading = false;
		}
	}

	async function handlePause() {
		try {
			errorMessage = '';
			const response = await fetch('/api/pause', {
				method: 'POST'
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to pause/resume playback';
			}

		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to pause/resume playback';
			console.error('Pause error:', error);
		}
	}

	async function handleStop() {
		try {
			errorMessage = '';
			const response = await fetch('/api/stop', {
				method: 'POST'
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to stop playback';
			}

		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to stop playback';
			console.error('Stop error:', error);
		}
	}

	// Enhanced playback control functions
	async function handleSeek(time: number) {
		try {
			errorMessage = '';
			const response = await fetch('/api/seek', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ time })
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to seek';
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to seek';
			console.error('Seek error:', error);
		}
	}

	async function handleTempoChange(tempo: number) {
		try {
			errorMessage = '';
			const response = await fetch('/api/tempo', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ tempo })
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to set tempo';
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to set tempo';
			console.error('Tempo error:', error);
		}
	}

	async function handleVolumeChange(volume: number) {
		try {
			errorMessage = '';
			const response = await fetch('/api/volume', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ volume })
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to set volume';
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to set volume';
			console.error('Volume error:', error);
		}
	}

	async function handleLoopToggle() {
		try {
			errorMessage = '';
			const response = await fetch('/api/loop', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					enabled: !loopEnabled,
					start: loopStart,
					end: loopEnd || totalDuration
				})
			});

			const data = await response.json();
			if (data.status !== 'success') {
				errorMessage = data.message || 'Failed to toggle loop';
			}
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Network error: Failed to toggle loop';
			console.error('Loop error:', error);
		}
	}

	// WebSocket and status functions
	function initWebSocket() {
		if (!browser) return;

		try {
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			const wsUrl = `${protocol}//${window.location.host}/socket.io/?EIO=4&transport=websocket`;

			// Use Socket.IO client if available, otherwise fallback to WebSocket
			if (typeof io !== 'undefined') {
				// Socket.IO connection to backend server (use relative path for proxy)
				connectionStatus = 'connecting';
				const isDev = typeof import.meta !== 'undefined' && (import.meta as any)?.env?.DEV;
				websocket = getSocket();

				websocket.on('connect', () => {
					console.log('WebSocket connected');
					reconnectAttempts = 0;
					connectionStatus = 'connected';

					// Show connection success status
					statusManager.showMessage(
						'🔗 Real-time connection established',
						'success',
						{ duration: 2000 }
					);

					// Stop polling when WebSocket is connected
					if (statusInterval) {
						clearInterval(statusInterval);
						statusInterval = null;
					}
					// Request current status
					websocket.emit('get_status');
				});

				websocket.on('playback_status', (data: any) => {
					updatePlaybackState(data);
				});

				websocket.on('extended_playback_status', (data: any) => {
					updateExtendedPlaybackState(data);
				});

				websocket.on('disconnect', (reason: any) => {
					console.log('WebSocket disconnected:', reason);
					connectionStatus = 'disconnected';

					// Show disconnection status
					statusManager.showMessage(
						'⚠️ Real-time connection lost - switching to polling',
						'warning',
						{ duration: 3000 }
					);

					// Resume polling as fallback
					if (!statusInterval) {
						startStatusPolling();
					}
				});

				websocket.on('error', (error: any) => {
					console.error('WebSocket error:', error);
					reconnectAttempts++;

					// Calculate exponential backoff delay (max 30 seconds)
					const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 30000);

					if (reconnectAttempts <= 5) {
						statusManager.showMessage(
							`🔄 Connection failed - retrying in ${Math.ceil(delay / 1000)}s (${reconnectAttempts}/5)`,
							'error',
							{ duration: delay }
						);

						// Attempt reconnection with exponential backoff
						setTimeout(() => {
							if (websocket && !websocket.connected) {
								websocket.connect();
							}
						}, delay);
					} else {
						// Max retries reached - fall back to polling
						statusManager.showMessage(
							'❌ Real-time connection failed - using polling mode',
							'error',
							{ duration: 5000 }
						);
						if (!statusInterval) {
							startStatusPolling();
						}
					}
				});

				// Handle real-time MIDI events
				websocket.on('live_midi_event', (data: any) => {
					handleLiveMidiEvent(data);
				});

				// Handle rtpMIDI status updates
				websocket.on('rtpmidi_status_update', (data: any) => {
					handleRtpMidiStatus(data);
				});
			} else {
				console.log('Socket.IO not available, using polling');
			}
		} catch (error) {
			console.error('Failed to initialize WebSocket:', error);
		}
	}

	function startStatusPolling() {
		// Poll status every 500ms (reduced frequency when WebSocket is primary)
		connectionStatus = 'polling';
		statusInterval = setInterval(async () => {
			await updateStatus();
		}, 500);
	}

	function startPerformanceMonitoring() {
		// Monitor MIDI event rate every second
		performanceMonitorInterval = setInterval(() => {
			const now = Date.now();
			const timeSinceLastEvent = now - lastMidiEventTime;

			// Calculate events per second over the last 5 seconds
			if (timeSinceLastEvent < 5000) {
				midiEventRate = midiEventCount / 5; // Approximate rate
			} else {
				midiEventRate = 0;
				midiEventCount = 0; // Reset counter if no recent events
			}
		}, 1000);
	}

	function updatePlaybackState(data: any) {
		// Handle WebSocket status updates
		playbackState = data.state || 'idle';
		currentTime = data.current_time || 0;
		totalDuration = data.total_duration || 0;
		progressPercentage = data.progress_percentage || 0;

		if (data.filename && data.filename !== songInfo.filename) {
			songInfo.filename = data.filename;
			songInfo.originalFilename = data.filename.replace(/_\d+_[a-f0-9]+/, '');
		}

		if (data.error_message) {
			errorMessage = data.error_message;
		} else {
			errorMessage = '';
		}
	}

	function updateExtendedPlaybackState(data: any) {
		// Handle extended WebSocket status updates
		playbackState = data.state || 'idle';
		currentTime = data.current_time || 0;
		totalDuration = data.total_duration || 0;
		progressPercentage = data.progress_percentage || 0;

		// Update enhanced controls
		tempoMultiplier = data.tempo_multiplier || 1.0;
		volumeMultiplier = data.volume_multiplier || 1.0;
		loopEnabled = data.loop_enabled || false;
		loopStart = data.loop_start || 0;
		loopEnd = data.loop_end || 0;

		if (data.filename && data.filename !== songInfo.filename) {
			songInfo.filename = data.filename;
			songInfo.originalFilename = data.filename.replace(/_\d+_[a-f0-9]+/, '');
		}

		if (data.error_message) {
			errorMessage = data.error_message;
		} else {
			errorMessage = '';
		}
	}

	async function updateStatus() {
		try {
			const response = await fetch('/api/playback-status');
			const data = await response.json();

			if (data.status === 'success' && data.playback) {
				updatePlaybackState(data.playback);
			}
		} catch (err) {
			console.error('Failed to get playback status:', err);
		}
	}

	async function loadSongInfo(filename: string) {
		try {
			isLoading = true;
			errorMessage = '';

			// Initialize basic song info
			songInfo = {
				filename,
				originalFilename: filename.replace(/_\d+_[a-f0-9]+/, ''), // Remove timestamp and UUID
				size: 0,
				metadata: null
			};

			// Fetch MIDI metadata from backend
			try {
				const response = await fetch('/api/parse-midi', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({ filename })
				});

				if (response.ok) {
					const data = await response.json();
					if (data.metadata) {
						songInfo.metadata = data.metadata;
					}
					if (data.duration) {
						totalDuration = data.duration / 1000; // Convert ms to seconds
					} else {
						totalDuration = 180; // Fallback duration
					}
				} else {
					console.warn('Failed to fetch MIDI metadata, using defaults');
					totalDuration = 180; // Fallback duration
				}
			} catch (metadataError) {
				console.warn('Error fetching MIDI metadata:', metadataError);
				totalDuration = 180; // Fallback duration
			}

		} catch (error) {
			errorMessage = 'Failed to load song information';
			console.error('Error loading song info:', error);
		} finally {
			isLoading = false;
		}
	}

	// Real-time MIDI event handlers
	function handleLiveMidiEvent(data: any) {
		try {
			// Performance monitoring
			midiEventCount++;
			const now = Date.now();
			lastMidiEventTime = now;

			// Display real-time MIDI event feedback
			const eventInfo = {
				timestamp: data.timestamp || now,
				note: data.note,
				velocity: data.velocity,
				channel: data.channel || 1,
				event_type: data.event_type,
				source: data.source || 'unknown'
			};

			// Throttle status messages to prevent UI spam
			if (midiEventCount % 10 === 0) {
				if (data.event_type === 'note_on') {
					statusManager.showMessage(
						`🎹 Live MIDI: Note ${data.note} ON (vel: ${data.velocity}) - ${data.source} [Rate: ${midiEventRate.toFixed(1)}/s]`,
						'info',
						{ duration: 800 }
					);
				} else if (data.event_type === 'note_off') {
					statusManager.showMessage(
						`🎹 Live MIDI: Note ${data.note} OFF - ${data.source} [Rate: ${midiEventRate.toFixed(1)}/s]`,
						'info',
						{ duration: 600 }
					);
				}
			}

			// Log for debugging (throttled)
			if (midiEventCount % 50 === 0) {
				console.log(`Live MIDI events processed: ${midiEventCount}, Rate: ${midiEventRate.toFixed(1)}/s`);
			}

		} catch (error) {
			console.error('Error handling live MIDI event:', error);
		}
	}

	function handleRtpMidiStatus(data: any) {
		try {
			// Handle rtpMIDI connection status updates
			if (data.state === 'listening') {
				statusManager.showMessage(
					'🌐 rtpMIDI: Listening for network connections',
					'success',
					{ duration: 3000 }
				);
			} else if (data.state === 'error') {
				statusManager.showMessage(
					'🌐 rtpMIDI: Connection error',
					'error',
					{ duration: 5000 }
				);
			}

			// Log active sessions
			if (data.active_sessions && Object.keys(data.active_sessions).length > 0) {
				console.log('Active rtpMIDI sessions:', data.active_sessions);
			}

		} catch (error) {
			console.error('Error handling rtpMIDI status:', error);
		}
	}

	// Timeline interaction functions
	function handleTimelineClick(event: MouseEvent | TouchEvent) {
		if (!timelineElement || totalDuration === 0) return;

		const rect = timelineElement.getBoundingClientRect();
		let clientX: number;

		if (event instanceof TouchEvent) {
			if (event.touches.length === 0) return;
			clientX = event.touches[0].clientX;
		} else {
			clientX = event.clientX;
		}

		const clickX = clientX - rect.left;
		const percentage = clickX / rect.width;
		const newTime = percentage * totalDuration;

		handleSeek(Math.max(0, Math.min(newTime, totalDuration)));
	}

	function handleTimelineDragStart(event: MouseEvent | TouchEvent) {
		isDragging = true;
		event.preventDefault();
	}

	function handleTimelineDrag(event: MouseEvent | TouchEvent) {
		if (!isDragging || !timelineElement || totalDuration === 0) return;

		const rect = timelineElement.getBoundingClientRect();
		let clientX: number;

		if (event instanceof TouchEvent) {
			if (event.touches.length === 0) return;
			clientX = event.touches[0].clientX;
			// Prevent page scrolling while dragging the timeline
			event.preventDefault();
		} else {
			clientX = event.clientX;
		}

		const dragX = clientX - rect.left;
		const percentage = Math.max(0, Math.min(1, dragX / rect.width));
		const newTime = percentage * totalDuration;

		// Update current time immediately for visual feedback
		currentTime = newTime;
		progressPercentage = percentage * 100;
	}

	function handleTimelineDragEnd(event: MouseEvent | TouchEvent) {
		if (!isDragging) return;

		isDragging = false;
		handleSeek(currentTime);
	}

	function handleTimelineKeydown(event: KeyboardEvent) {
		const step = totalDuration * 0.01; // 1% of total duration
		let newTime = currentTime;

		switch (event.key) {
			case 'ArrowLeft':
				event.preventDefault();
				newTime = Math.max(0, currentTime - step);
				break;
			case 'ArrowRight':
				event.preventDefault();
				newTime = Math.min(totalDuration, currentTime + step);
				break;
			case 'Home':
				event.preventDefault();
				newTime = 0;
				break;
			case 'End':
				event.preventDefault();
				newTime = totalDuration;
				break;
			case ' ':
			case 'Enter':
				event.preventDefault();
				togglePlayback();
				return;
			default:
				return;
		}

		handleSeek(newTime);
	}

	function togglePlayback() {
		if (playbackState === 'playing') {
			handlePause();
		} else {
			handlePlay();
		}
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	// State management functions
	function saveState(description: string) {
		const state = {
			selectedFile: selectedFile ? {
				name: selectedFile.name,
				size: selectedFile.size,
				type: selectedFile.type,
				lastModified: selectedFile.lastModified
			} : null,
			fileMetadata,
			uploadStatus,
			uploadMessage,
			uploadProgress
		};
		historyStore.pushState(state, description);
	}

	function restoreState(state: any, description: string) {
		selectedFile = state.selectedFile ? new File([], state.selectedFile.name, {
			type: state.selectedFile.type,
			lastModified: state.selectedFile.lastModified
		}) : null;
		fileMetadata = state.fileMetadata;
		uploadStatus = state.uploadStatus;
		uploadMessage = state.uploadMessage;
		uploadProgress = state.uploadProgress;

		toastStore.info(description, {
			title: 'State Restored'
		});
	}

	// Onboarding tour handlers
	async function handleTourComplete() {
		try {
			await settingsAPI.setSetting('help', 'tourCompleted', true);
			showOnboardingTour = false;
		} catch (error) {
			console.error('Failed to save tour completion:', error);
		}
	}

	async function handleTourSkip() {
		try {
			await settingsAPI.setSetting('help', 'tourCompleted', true);
			await settingsAPI.setSetting('help', 'tourSkipped', true);
			showOnboardingTour = false;
		} catch (error) {
			console.error('Failed to save tour skip:', error);
		}
	}

	// Preferences modal handlers
	function openPreferences() {
		showPreferencesModal = true;
	}

	function closePreferences() {
		showPreferencesModal = false;
	}

	onMount(() => {
		if (!browser) return;

		// Auto-focus the file input when component mounts
		if (fileInput) {
			fileInput.focus();
		}

		// Setup keyboard shortcuts for undo/redo
		const cleanupKeyboardShortcuts = setupHistoryKeyboardShortcuts(
			(state, description) => {
				// Undo callback - restore previous state
				restoreState(state, description);
			},
			(state, description) => {
				// Redo callback - restore next state
				restoreState(state, description);
			}
		);

		// Set help context
		settingsAPI.setSetting('help', 'currentContext', 'listen');

		// Initialize WebSocket connection
		initWebSocket();

		// Fallback polling in case WebSocket fails
		startStatusPolling();

		// Start performance monitoring
		startPerformanceMonitoring();

		// Check if onboarding should be shown
		const checkOnboarding = () => {
			const shouldShow = get(shouldShowOnboarding);
			if (shouldShow) {
				// Delay to ensure DOM is ready
				setTimeout(() => {
					showOnboardingTour = true;
				}, 1000);
			}
		};

		// Initial check
		checkOnboarding();

		// Listen for help events
		function handleShowHelp() {
			showOnboardingTour = true;
		}

		function handleStartTour() {
			showOnboardingTour = true;
		}

		window.addEventListener('show-help', handleShowHelp);
		window.addEventListener('start-tour', handleStartTour);

		// Cleanup on component destroy
		return () => {
			cleanupKeyboardShortcuts();
			window.removeEventListener('show-help', handleShowHelp);
			window.removeEventListener('start-tour', handleStartTour);
		};
	});

	onDestroy(() => {
		if (autoUploadTimeout) {
			clearTimeout(autoUploadTimeout);
			autoUploadTimeout = null;
		}
		if (onboardingTimeout) {
			clearTimeout(onboardingTimeout);
			onboardingTimeout = null;
		}
		if (websocket) {
			websocket.close();
		}
		if (statusInterval) {
			clearInterval(statusInterval);
		}
		if (performanceMonitorInterval) {
			clearInterval(performanceMonitorInterval);
		}
	});

	// Validation preview event handlers
	async function handleValidationProceed(event: CustomEvent<{ files: File[] }>) {
		const files = event.detail.files;
		if (files.length > 0) {
			const file = files[0];

			// Track prevention event - user reviewed and proceeded
			// errorAnalytics.trackPrevention({
			// 	category: 'validation',
			// 	message: 'User reviewed validation preview and proceeded with file',
			// 	preventedIssues: ['file-type-error', 'file-size-error'],
			// 	userAction: 'fixed',
			// 	context: {
			// 		fileType: file.type,
			// 		fileSize: file.size
			// 	}
			// });

			await processFileSelection(file);
		}
		resetValidationPreview();
	}

	function handleValidationCancel() {
		// Track prevention event - user cancelled after review
		// errorAnalytics.trackPrevention({
		// 	category: 'validation',
		// 	message: 'User cancelled after validation preview',
		// 	preventedIssues: ['potential-upload-errors'],
		// 	userAction: 'cancelled',
		// 	context: {
		// 		uploadAttempt: previewFiles.length
		// 	}
		// });

		resetValidationPreview();
		// Reset file input
		if (fileInput) {
			fileInput.value = '';
		}
	}

	function handleValidationFix(event: CustomEvent<{ issue: any; files: File[] }>) {
		const { issue } = event.detail;

		// Track prevention event - user chose to fix issues
		// errorAnalytics.trackPrevention({
		// 	category: 'validation',
		// 	message: 'User chose to fix validation issues',
		// 	preventedIssues: ['file-selection-error'],
		// 	userAction: 'fixed',
		// 	context: {
		// 		fileType: issue.type === 'error' ? undefined : 'unknown'
		// 	}
		// });

		// Handle different types of fixes
		if (issue.type === 'error') {
			// For errors, show file picker to select a new file
			fileInput?.click();
		}

		resetValidationPreview();
	}
</script>

<svelte:head>
	<title>Listen - Piano LED Visualizer</title>
	<meta name="description" content="Upload and play MIDI files for LED visualization" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
</svelte:head>

<a href="#main-content" class="skip-link">Skip to main content</a>

<div class="listen-container">
	{#if $shouldShowTooltips}
		<Tooltip text="Use Ctrl+Z/Ctrl+Y or these buttons to undo/redo actions" position="left" delay={$tooltipDelay}>
			<!-- <UndoRedoControls 
				on:undo={(event) => restoreState(event.detail.state, `Undid: ${event.detail.description}`)}
				on:redo={(event) => restoreState(event.detail.state, `Redid: ${event.detail.description}`)}
			/> -->
		</Tooltip>
	{:else}
		<!-- <UndoRedoControls 
			on:undo={(event) => restoreState(event.detail.state, `Undid: ${event.detail.description}`)}
			on:redo={(event) => restoreState(event.detail.state, `Redid: ${event.detail.description}`)}
		/> -->
	{/if}

	<!-- Preferences Button -->
	<div class="preferences-button-container">
		{#if $shouldShowTooltips}
			<Tooltip text="Open preferences to customize upload settings" position="left" delay={$tooltipDelay}>
				<InteractiveButton
					variant="ghost"
					size="sm"
					className="preferences-btn"
					on:click={openPreferences}
				>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="preferences-icon">
						<circle cx="12" cy="12" r="3"/>
						<path d="M12 1v6m0 6v6m11-7h-6m-6 0H1m17-4a4 4 0 0 1-8 0 4 4 0 0 1 8 0zM7 21a4 4 0 0 1-8 0 4 4 0 0 1 8 0z"/>
					</svg>
				</InteractiveButton>
			</Tooltip>
		{:else}
			<InteractiveButton
				variant="ghost"
				size="sm"
				className="preferences-btn"
				on:click={openPreferences}
			>
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="preferences-icon">
					<circle cx="12" cy="12" r="3"/>
					<path d="M12 1v6m0 6v6m11-7h-6m-6 0H1m17-4a4 4 0 0 1-8 0 4 4 0 0 1 8 0zM7 21a4 4 0 0 1-8 0 4 4 0 0 1 8 0z"/>
				</svg>
			</InteractiveButton>
		{/if}
	</div>

	<!-- Status Display -->
	<!-- <StatusDisplay /> -->

	<main id="main-content" class="listen-card" aria-labelledby="page-title">
		<h1 id="page-title">🎵 Listen to MIDI</h1>
		<p class="description">
			Upload a MIDI file and control LED visualization playback.
		</p>

		<!-- Upload Section -->
		{#if !songInfo.filename}
			<div class="upload-section">
				<!-- Hidden file input -->
				<input 
					bind:this={fileInput}
					type="file"
					accept=".mid,.midi"
					id="midi-file"
					on:change={handleFileSelect}
					class="sr-only"
					aria-label="Select MIDI file"
				/>

				{#if $shouldShowTooltips}
				<Tooltip text="Click to browse or drag and drop MIDI files (.mid, .midi)" position="bottom" delay={$tooltipDelay}>
					<div 
						bind:this={dropZone}
						class="drop-zone interactive file-label" 
						class:drag-over={isDragOver}
						class:has-file={selectedFile}
						class:disabled={uploadStatus === 'uploading'}
						on:dragenter={handleDragEnter}
						on:dragleave={handleDragLeave}
						on:dragover={handleDragOver}
						on:drop={handleDrop}
						on:click={() => fileInput.click()}
						on:keydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								fileInput.click();
							}
						}}
						role="button"
						aria-label="Click to select MIDI file or drag and drop"
						aria-describedby="drop-zone-help"
						tabindex="0"
					>
						<!-- Hidden help text for screen readers -->
						<div id="drop-zone-help" class="sr-only">
							Select a MIDI file by clicking this area or dragging and dropping a file. Supported formats: .mid, .midi (max 1MB)
						</div>
						
						<div class="drop-zone-content">
							<svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
								<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
								<polyline points="7,10 12,15 17,10" />
								<line x1="12" y1="15" x2="12" y2="3" />
							</svg>
							<div class="upload-text">
								{#if isDragOver}
									<h3>Drop MIDI file here</h3>
								{:else if selectedFile}
									<h3>{selectedFile.name}</h3>
									<p class="file-size">{formatFileSize(selectedFile.size)}</p>
								{:else}
									<h3>Drag & drop MIDI file or click to browse</h3>
									<p class="supported-formats">Supported formats: .mid, .midi (max 1MB)</p>
								{/if}
							</div>
						</div>
						
						{#if isDragOver}
							<div class="drag-overlay">
								<div class="drag-indicator">
									<svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
										<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
										<polyline points="7,10 12,15 17,10" />
										<line x1="12" y1="15" x2="12" y2="3" />
									</svg>
									<p>Drop your MIDI file here</p>
								</div>
							</div>
						{/if}
					</div>
				</Tooltip>
			{:else}
				<div 
					bind:this={dropZone}
					class="drop-zone interactive file-label" 
					class:drag-over={isDragOver}
					class:has-file={selectedFile}
					class:disabled={uploadStatus === 'uploading'}
					on:dragenter={handleDragEnter}
					on:dragleave={handleDragLeave}
					on:dragover={handleDragOver}
					on:drop={handleDrop}
					on:click={() => fileInput.click()}
					on:keydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							fileInput.click();
						}
					}}
					role="button"
					aria-label="Click to select MIDI file or drag and drop"
					aria-describedby="drop-zone-help"
					tabindex="0"
				>
					<!-- Hidden help text for screen readers -->
					<div id="drop-zone-help" class="sr-only">
						Select a MIDI file by clicking this area or dragging and dropping a file. Supported formats: .mid, .midi (max 1MB)
					</div>
					
					<div class="drop-zone-content">
						<svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
							<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
							<polyline points="7,10 12,15 17,10" />
							<line x1="12" y1="15" x2="12" y2="3" />
						</svg>
						<div class="upload-text">
							{#if isDragOver}
								<h3>Drop MIDI file here</h3>
							{:else if selectedFile}
								<h3>{selectedFile.name}</h3>
								<p class="file-size">{formatFileSize(selectedFile.size)}</p>
							{:else}
								<h3>Drag & drop MIDI file or click to browse</h3>
								<p class="supported-formats">Supported formats: .mid, .midi (max 1MB)</p>
							{/if}
						</div>
					</div>
					
					{#if isDragOver}
						<div class="drag-overlay">
							<div class="drag-indicator">
								<svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
									<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
									<polyline points="7,10 12,15 17,10" />
									<line x1="12" y1="15" x2="12" y2="3" />
								</svg>
								<p>Drop your MIDI file here</p>
							</div>
						</div>
					{/if}
				</div>
			{/if}

				{#if fileMetadata}
				<section class="file-metadata card-interactive" aria-labelledby="file-preview-title">
					<div class="metadata-header">
						<svg class="file-icon pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
							<path d="M9 12l2 2 4-4" />
							<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
							<path d="M3 5c0-1.66 4-3 9-3s9 1.34 9 3" />
							<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
						</svg>
						<h3 id="file-preview-title">File Preview</h3>
					</div>
						<div class="metadata-grid" role="list" aria-label="File properties">
							<div class="metadata-item" role="listitem">
								<span class="metadata-label">Name:</span>
								<span class="metadata-value" aria-label="File name: {fileMetadata.name}">{fileMetadata.name}</span>
							</div>
							<div class="metadata-item" role="listitem">
								<span class="metadata-label">Size:</span>
								<span class="metadata-value" aria-label="File size: {fileMetadata.size}">{fileMetadata.size}</span>
							</div>
							<div class="metadata-item" role="listitem">
								<span class="metadata-label">Type:</span>
								<span class="metadata-value" aria-label="File type: {fileMetadata.type}">{fileMetadata.type}</span>
							</div>
							<div class="metadata-item" role="listitem">
								<span class="metadata-label">Modified:</span>
								<span class="metadata-value" aria-label="Last modified: {fileMetadata.lastModified}">{fileMetadata.lastModified}</span>
							</div>
						</div>
					</section>
				{/if}

				<div class="upload-actions" role="group" aria-labelledby="upload-actions-title">
					<h3 id="upload-actions-title" class="sr-only">Upload Actions</h3>
					{#if $shouldShowTooltips}
						<Tooltip text={selectedFile ? 'Upload your MIDI file for LED visualization' : 'Select a MIDI file first'} position="top" delay={$tooltipDelay}>
						<InteractiveButton 
							variant="primary"
							size="lg"
							disabled={!selectedFile || uploadStatus === 'uploading'}
							loading={uploadStatus === 'uploading'}
							className="upload-btn"
							on:click={handleUpload}
						>
							{uploadStatus === 'uploading' ? 'Uploading...' : 'Upload File'}
						</InteractiveButton>
					</Tooltip>
				{:else}
					<InteractiveButton 
						variant="primary"
						size="lg"
						disabled={!selectedFile || uploadStatus === 'uploading'}
						loading={uploadStatus === 'uploading'}
						className="upload-btn"
						on:click={handleUpload}
					>
						{uploadStatus === 'uploading' ? 'Uploading...' : 'Upload File'}
					</InteractiveButton>
				{/if}

					{#if uploadStatus === 'uploading'}
						<div class="progress-section">
							<ProgressBar 
								progress={uploadProgress} 
								label="Upload Progress"
								showPercentage={true}
								size="md"
								variant="default"
								animated={true}
							/>
						</div>
						<InteractiveButton 
							variant="ghost"
							size="md"
							className="cancel-btn"
							on:click={() => { uploadStatus = 'idle'; uploadProgress = 0; uploadMessage = ''; }}
						>
							Cancel Upload
						</InteractiveButton>
					{/if}

					{#if uploadStatus === 'success'}
						{#if $shouldShowTooltips}
						<Tooltip text="Start the LED visualization with your uploaded MIDI file" position="top" delay={$tooltipDelay}>
							<a href="#playback" class="play-btn" role="button" aria-label="Navigate to play section">Start Playback</a>
						</Tooltip>
					{:else}
						<a href="#playback" class="play-btn" role="button" aria-label="Navigate to play section">Start Playback</a>
					{/if}
							{#if $shouldShowTooltips}
								<Tooltip text="Upload another MIDI file" position="top" delay={$tooltipDelay}>
								<InteractiveButton 
									variant="ghost"
									size="md"
									ariaLabel="Reset form to upload another MIDI file"
									on:click={resetUpload}
								>
									Upload Another
								</InteractiveButton>
							</Tooltip>
						{:else}
							<InteractiveButton 
								variant="ghost"
								size="md"
								className="reset-btn"
								ariaLabel="Reset form to upload another MIDI file"
								on:click={resetUpload}
							>
								Upload Another
							</InteractiveButton>
						{/if}
					{:else if uploadStatus === 'error'}
						{#if $shouldShowTooltips}
						<Tooltip text="Clear the error and try uploading again" position="top" delay={$tooltipDelay}>
							<InteractiveButton 
								variant="ghost"
								size="md"
								className="reset-btn"
								ariaLabel="Clear error and reset form to try uploading again"
								on:click={resetUpload}
							>
								Try Again
							</InteractiveButton>
						</Tooltip>
					{:else}
						<InteractiveButton 
							variant="ghost"
							size="md"
							ariaLabel="Clear error and reset form to try uploading again"
							on:click={resetUpload}
						>
							Try Again
						</InteractiveButton>
					{/if}
					{/if}
				</div>
			</div>
		{/if}

		<!-- Playback Section -->
		{#if songInfo.filename}
			<div id="playback" class="playback-section">
				<!-- Connection Status -->
				<div class="connection-status">
					<div class="status-row">
						{#if connectionStatus === 'connected'}
							<span class="status-indicator connected">🔗 Real-time</span>
						{:else if connectionStatus === 'connecting'}
							<span class="status-indicator connecting">🔄 Connecting...</span>
						{:else if connectionStatus === 'polling'}
							<span class="status-indicator polling">📡 Polling mode</span>
						{:else}
							<span class="status-indicator disconnected">❌ Disconnected</span>
						{/if}
						
						{#if midiEventRate > 0}
							<span class="performance-indicator">🎹 {midiEventRate.toFixed(1)}/s</span>
						{/if}
					</div>
				</div>
				
				<!-- Song Information -->
				<div class="song-info">
					<h2>Now Playing</h2>
					<div class="song-details">
						<p class="song-title">{songInfo.originalFilename || 'Unknown Song'}</p>
						<div class="song-meta-grid">
							<div class="meta-item">
								<span class="meta-label">Duration:</span>
								<span class="meta-value">{formatTime(totalDuration)}</span>
							</div>
							{#if songInfo.size > 0}
								<div class="meta-item">
									<span class="meta-label">Size:</span>
									<span class="meta-value">{formatFileSize(songInfo.size)}</span>
								</div>
							{/if}
							{#if songInfo.metadata}
								{#if songInfo.metadata.tempo}
									<div class="meta-item">
										<span class="meta-label">Tempo:</span>
										<span class="meta-value">{songInfo.metadata.tempo} BPM</span>
									</div>
								{/if}
								{#if songInfo.metadata.tracks}
									<div class="meta-item">
										<span class="meta-label">Tracks:</span>
										<span class="meta-value">{songInfo.metadata.tracks}</span>
									</div>
								{/if}
								{#if songInfo.metadata.type !== undefined}
									<div class="meta-item">
										<span class="meta-label">Type:</span>
										<span class="meta-value">MIDI {songInfo.metadata.type}</span>
									</div>
								{/if}
								{#if songInfo.metadata.title}
									<div class="meta-item">
										<span class="meta-label">Title:</span>
										<span class="meta-value">{songInfo.metadata.title}</span>
									</div>
								{/if}
							{/if}
						</div>
					</div>
				</div>

				<!-- Interactive Timeline -->
				<div class="timeline-section">
					<div class="time-display">
						<span class="current-time">{formatTime(currentTime)}</span>
						<span class="total-time">{formatTime(totalDuration)}</span>
					</div>
					<div 
					class="timeline" 
					bind:this={timelineElement}
					role="slider"
					tabindex="0"
					aria-label="Timeline scrubber"
					aria-valuemin="0"
					aria-valuemax={totalDuration}
					aria-valuenow={currentTime}
					on:click={handleTimelineClick}
					on:keydown={handleTimelineKeydown}
					on:mousedown={handleTimelineDragStart}
					on:mousemove={handleTimelineDrag}
					on:mouseup={handleTimelineDragEnd}
					on:mouseleave={handleTimelineDragEnd}
					on:touchstart={handleTimelineDragStart}
					on:touchmove={handleTimelineDrag}
					on:touchend={handleTimelineDragEnd}
					on:touchcancel={handleTimelineDragEnd}
						class:dragging={isDragging}
						aria-valuetext="{formatTime(currentTime)}"
					>
						<div class="timeline-track">
							<div class="timeline-progress" style="width: {progressPercentage}%"></div>
							{#if loopEnabled}
								<div 
									class="loop-region" 
									style="left: {(loopStart / totalDuration) * 100}%; width: {((loopEnd - loopStart) / totalDuration) * 100}%"
								></div>
							{/if}
							<div class="timeline-handle" style="left: {progressPercentage}%"></div>
						</div>
					</div>
					<div class="progress-info">
						<span class="time">{formatTime(currentTime)} / {formatTime(totalDuration)}</span>
						<span class="percentage">{Math.round(progressPercentage)}%</span>
					</div>
				</div>

				<!-- Playback Controls -->
				<div class="controls">
					<button 
						on:click={handlePlay} 
						disabled={playbackState === 'playing' || isLoading}
						class="control-btn play-btn"
						class:active={playbackState === 'playing'}
						aria-label="Play"
					>
						<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
							<path d="M8 5v14l11-7z"/>
						</svg>
						<span class="btn-text">Play</span>
					</button>

					<button 
						on:click={handlePause} 
						disabled={playbackState === 'idle' || playbackState === 'stopped'}
						class="control-btn pause-btn"
						class:active={playbackState === 'paused'}
						aria-label="{playbackState === 'paused' ? 'Resume' : 'Pause'}"
					>
						<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
							<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
						</svg>
						<span class="btn-text">{playbackState === 'paused' ? 'Resume' : 'Pause'}</span>
					</button>

					<button 
						on:click={handleStop} 
						disabled={playbackState === 'idle' || playbackState === 'stopped'}
						class="control-btn stop-btn"
						aria-label="Stop"
					>
						<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
							<path d="M6 6h12v12H6z"/>
						</svg>
						<span class="btn-text">Stop</span>
					</button>
				</div>

				<!-- Enhanced Controls -->
				<div class="enhanced-controls">
					<!-- Tempo Control -->
					<div class="control-group">
						<div class="slider-header">
							<label for="tempo-slider">Tempo: {Math.round(tempoMultiplier * 100)}%</label>
							<div class="slider-buttons">
								<button 
								class="slider-btn" 
								on:click={() => {
									tempoMultiplier = Math.max(0.25, tempoMultiplier - 0.05);
									handleTempoChange(tempoMultiplier);
								}}
								aria-label="Decrease tempo"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M19 13H5v-2h14v2z"/>
								</svg>
							</button>
							<button 
								class="slider-btn" 
								on:click={() => {
									tempoMultiplier = 1;
									handleTempoChange(tempoMultiplier);
								}}
								aria-label="Reset tempo to 1x"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
								</svg>
							</button>
							<button 
								class="slider-btn" 
								on:click={() => {
									tempoMultiplier = Math.min(2.0, tempoMultiplier + 0.05);
									handleTempoChange(tempoMultiplier);
								}}
								aria-label="Increase tempo"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
								</svg>
							</button>
							</div>
						</div>
						<input 
						id="tempo-slider"
						type="range" 
						min="0.25" 
						max="2.0" 
						step="0.05" 
						bind:value={tempoMultiplier}
						on:input={() => handleTempoChange(tempoMultiplier)}
						class="slider tempo-slider"
						aria-label="Adjust tempo"
					/>
						<div class="slider-labels">
							<span>0.25x</span>
							<span>1x</span>
							<span>2x</span>
						</div>
					</div>

					<!-- Volume Control -->
					<div class="control-group">
						<div class="slider-header">
							<label for="volume-slider">Volume: {Math.round(volumeMultiplier * 100)}%</label>
							<div class="slider-buttons">
								<button 
								class="slider-btn" 
								on:click={() => {
									volumeMultiplier = Math.max(0, volumeMultiplier - 0.1);
									handleVolumeChange(volumeMultiplier);
								}}
								aria-label="Decrease volume"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M19 13H5v-2h14v2z"/>
								</svg>
							</button>
							<button 
								class="slider-btn" 
								on:click={() => {
									volumeMultiplier = 0.5;
									handleVolumeChange(volumeMultiplier);
								}}
								aria-label="Set volume to 50%"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
								</svg>
							</button>
							<button 
								class="slider-btn" 
								on:click={() => {
									volumeMultiplier = Math.min(1, volumeMultiplier + 0.1);
									handleVolumeChange(volumeMultiplier);
								}}
								aria-label="Increase volume"
							>
								<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
									<path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
								</svg>
							</button>
							</div>
						</div>
						<input 
						id="volume-slider"
						type="range" 
						min="0" 
						max="1" 
						step="0.01" 
						bind:value={volumeMultiplier}
						on:input={() => handleVolumeChange(volumeMultiplier)}
						class="slider volume-slider"
						aria-label="Adjust volume"
					/>
						<div class="slider-labels">
							<span>0%</span>
							<span>50%</span>
							<span>100%</span>
						</div>
					</div>

					<!-- Loop Control -->
					<div class="control-group loop-control">
						<button 
							on:click={handleLoopToggle}
							class="control-btn loop-btn"
							class:active={loopEnabled}
							aria-label="Toggle loop {loopEnabled ? 'off' : 'on'}"
						>
							<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
								<path d="M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"/>
							</svg>
							<span class="btn-text">Loop {loopEnabled ? 'On' : 'Off'}</span>
						</button>
						{#if loopEnabled}
							<div class="loop-info">
								<span>Loop: {formatTime(loopStart)} - {formatTime(loopEnd)}</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Status Display -->
				<div class="status-section">
					<div class="status-indicator" class:playing={playbackState === 'playing'} class:paused={playbackState === 'paused'}>
						<div class="status-dot"></div>
						<span class="status-text">
							{#if playbackState === 'playing'}
								Playing
							{:else if playbackState === 'paused'}
								Paused
							{:else if playbackState === 'stopped'}
								Stopped
							{:else}
								Ready
							{/if}
						</span>
					</div>
				</div>

				<!-- Navigation -->
				<div class="navigation">
					<a href="/settings" class="nav-link">Settings</a>
					<a href="/" class="nav-link">Home</a>
				</div>
			</div>
		{/if}

		<!-- Validation Preview Modal -->
		{#if showValidationPreview && previewFiles.length > 0}
			<ValidationPreview
				files={previewFiles}
				on:proceed={handleValidationProceed}
				on:cancel={handleValidationCancel}
				on:fix={handleValidationFix}
			/>
		{/if}

		
		{#if uploadMessage}
			<div class="upload-status" class:success={uploadStatus === 'success'} class:error={uploadStatus === 'error'}>
				{#if uploadStatus === 'uploading'}
					<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
						<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
						<polyline points="17,8 12,3 7,8" />
						<line x1="12" y1="3" x2="12" y2="15" />
					</svg>
					<div class="status-content">
						<h4>Uploading MIDI File</h4>
						<p>{selectedFile?.name} • {uploadProgress}% complete</p>
						<div class="progress-bar">
							<div class="progress-fill" style="width: {uploadProgress}%"></div>
							<div class="progress-text">{uploadProgress}%</div>
						</div>
					</div>
				{:else if uploadStatus === 'success'}
					<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
						<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
						<polyline points="22,4 12,14.01 9,11.01" />
					</svg>
					<div class="status-content">
						<h4>Upload Successful</h4>
						<p>{uploadMessage}</p>
					</div>
				{:else}
					<p>{uploadMessage}</p>
				{/if}
			</div>
		{/if}

		<!-- Enhanced Error Recovery Panel -->
		{#if currentError}
			<ErrorRecoveryPanel 
				errorContext={currentError}
				on:action={(event) => {
					const { action } = event.detail;
					action.action();
				}}
				on:dismiss={() => {
					currentError = null;
					uploadStatus = 'idle';
					uploadMessage = '';
				}}
			/>
		{/if}
	</main>
	
	<!-- Onboarding Tour -->
	{#if showOnboardingTour}
		<OnboardingTour 
			on:complete={handleTourComplete}
			on:skip={handleTourSkip}
		/>
	{/if}

	<!-- Preferences Modal -->
	{#if showPreferencesModal}
		<PreferencesModal
			on:close={closePreferences}
		/>
	{/if}
	
	<!-- Live regions for screen readers -->
	<div aria-live="polite" aria-atomic="true" class="sr-only">
		{#if uploadMessage && uploadStatus !== 'error'}
			{uploadMessage}
		{/if}
	</div>
	
	<div aria-live="assertive" aria-atomic="true" class="sr-only">
		{#if uploadStatus === 'success'}
			File uploaded successfully! You can now play your song.
		{:else if uploadStatus === 'error'}
			Upload failed: {uploadMessage}
		{/if}
	</div>
</div>

<style>
	.listen-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 100vh;
		padding: 2rem;
		position: relative;
	}

	.listen-container :global(.undo-redo-controls) {
		position: absolute;
		top: 1rem;
		right: 1rem;
		z-index: 10;
	}

	.preferences-button-container {
		position: absolute;
		top: 1rem;
		left: 1rem;
		z-index: 10;
	}

	.preferences-button-container :global(.preferences-btn) {
		padding: 0.5rem;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.9);
		border: 1px solid #e2e8f0;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		transition: all 0.2s ease;
	}

	.preferences-button-container :global(.preferences-btn:hover) {
		background: white;
		border-color: #cbd5e0;
		transform: translateY(-1px);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
	}

	.preferences-icon {
		width: 1.25rem;
		height: 1.25rem;
		stroke-width: 2;
		color: #4a5568;
	}

	.listen-card {
		background: white;
		border-radius: 12px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
		padding: 2rem;
		max-width: 600px;
		width: 100%;
		text-align: center;
	}

	h1 {
		text-align: center;
		color: #1f2937;
		margin-bottom: 0.5rem;
		font-size: 2rem;
		font-weight: 700;
	}

	.description {
		text-align: center;
		color: #6b7280;
		margin-bottom: 2rem;
		line-height: 1.5;
	}

	.upload-section {
		margin-bottom: 2rem;
	}

	.drop-zone {
		position: relative;
		width: 100%;
		max-width: 400px;
		margin: 0 auto 2rem auto;
		border: 2px dashed #cbd5e0;
		border-radius: 12px;
		padding: 2rem;
		transition: all 0.3s ease;
		background: #f8fafc;
		overflow: hidden;
	}

	.drop-zone::before {
		content: '';
		position: absolute;
		top: 0;
		left: -100%;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, transparent, rgba(66, 153, 225, 0.1), transparent);
		transition: left 0.6s ease;
		pointer-events: none;
	}

	.drop-zone:hover {
		border-color: #4299e1;
		background: #ebf8ff;
		transform: translateY(-2px);
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.drop-zone:hover::before {
		left: 100%;
	}

	.drop-zone.drag-over {
		border-color: #3182ce;
		background: #bee3f8;
		box-shadow: 0 0 0 4px rgba(66, 153, 225, 0.1);
		transform: scale(1.02);
		animation: pulse 1s ease-in-out infinite;
	}

	.drop-zone:active {
		transform: translateY(0) scale(0.98);
		transition: transform 0.1s ease;
	}

	.drop-zone.disabled {
		border-color: #e2e8f0;
		background: #f7fafc;
		opacity: 0.6;
		pointer-events: none;
	}

	.drop-zone-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		text-align: center;
		pointer-events: none;
	}

	.upload-icon {
		width: 3rem;
		height: 3rem;
		stroke-width: 2;
		color: #4299e1;
		transition: all 0.2s ease;
	}

	.drop-zone:hover .upload-icon {
		color: #3182ce;
		transform: scale(1.1);
	}

	.upload-text {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.upload-text h3 {
		margin: 0;
		color: #2d3748;
		font-size: 1.125rem;
		font-weight: 600;
		line-height: 1.4;
	}

	.upload-text p {
		margin: 0;
		color: #6b7280;
		font-size: 0.875rem;
		line-height: 1.4;
	}

	.file-size {
		color: #4299e1 !important;
		font-weight: 500;
	}

	.supported-formats {
		color: #9ca3af !important;
	}

	.drag-overlay {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(66, 153, 225, 0.1);
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		pointer-events: none;
		z-index: 10;
	}

	.drag-indicator {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		color: #3182ce;
		font-weight: 600;
		text-align: center;
	}

	.drop-icon {
		width: 3rem;
		height: 3rem;
		stroke-width: 2;
		animation: bounce 1s infinite;
	}

	@keyframes bounce {
		0%, 20%, 53%, 80%, 100% {
			transform: translate3d(0, 0, 0);
		}
		40%, 43% {
			transform: translate3d(0, -8px, 0);
		}
		70% {
			transform: translate3d(0, -4px, 0);
		}
		90% {
			transform: translate3d(0, -2px, 0);
		}
	}

	.file-metadata {
		background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
		transition: all 0.2s ease;
	}

	.file-metadata:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
		border-color: #cbd5e0;
	}

	.metadata-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.file-icon {
		width: 1.5rem;
		height: 1.5rem;
		stroke: #4299e1;
		stroke-width: 2;
		transition: all 0.2s ease;
	}

	.file-metadata:hover .file-icon {
		transform: scale(1.1) rotate(5deg);
		stroke: #3182ce;
	}

	.metadata-header h3 {
		margin: 0;
		color: #2d3748;
		font-size: 1.125rem;
		font-weight: 600;
	}

	.metadata-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 0.75rem;
		margin-top: 0.75rem;
	}

	.metadata-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0;
	}

	.metadata-label {
		font-weight: 500;
		color: #4a5568;
		font-size: 0.875rem;
	}

	.metadata-value {
		color: #2d3748;
		font-size: 0.875rem;
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
		background: #ffffff;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		border: 1px solid #e2e8f0;
		max-width: 60%;
		text-align: right;
		word-break: break-all;
		transition: all 0.2s ease;
		cursor: help;
	}

	.metadata-value:hover {
		background: #ebf8ff;
		border-color: #4299e1;
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(66, 153, 225, 0.1);
	}

	.upload-actions {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		align-items: center;
		justify-content: center;
		margin-top: 1.5rem;
	}

	.progress-section {
		width: 100%;
		margin-top: 1rem;
	}

	.play-btn {
		display: inline-block;
		background: #10b981;
		color: white;
		border: none;
		border-radius: 6px;
		padding: 0.75rem 1.5rem;
		font-weight: 500;
		text-decoration: none;
		cursor: pointer;
		transition: background-color 0.2s ease;
		min-width: 120px;
		text-align: center;
	}

	.play-btn:hover {
		background: #059669;
	}

	.upload-status {
		margin-top: 1rem;
		padding: 1rem;
		border-radius: 8px;
		font-weight: 500;
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.upload-status.success {
		background: #d1fae5;
		color: #065f46;
		border: 1px solid #a7f3d0;
	}

	.upload-status.error {
		background: #fee2e2;
		color: #991b1b;
		border: 1px solid #fca5a5;
		box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.1);
	}

	.upload-status p {
		margin: 0;
		font-weight: 500;
	}

	.progress-bar {
		position: relative;
		width: 100%;
		height: 12px;
		background: #e5e7eb;
		border-radius: 6px;
		overflow: hidden;
		margin-top: 0.75rem;
		box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #3b82f6, #1d4ed8);
		transition: width 0.3s ease;
		border-radius: 6px;
		position: relative;
		box-shadow: 0 1px 2px rgba(59, 130, 246, 0.3);
	}

	.progress-text {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		font-size: 0.75rem;
		font-weight: 600;
		color: #374151;
		text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
		pointer-events: none;
	}

	/* Playback Section Styles */
	.playback-section {
		border-top: 1px solid #e5e7eb;
		padding-top: 2rem;
		margin-top: 2rem;
	}

	.song-info {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: #f8fafc;
		border-radius: 12px;
	}

	.song-info h2 {
		color: #374151;
		margin-bottom: 1rem;
		font-size: 1.25rem;
		font-weight: 600;
	}

	.song-title {
		font-size: 1.5rem;
		font-weight: 700;
		color: #1f2937;
		margin-bottom: 0.5rem;
	}

	.song-meta-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 0.75rem;
		margin-top: 0.75rem;
	}

	.meta-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.75rem;
		background: white;
		border-radius: 8px;
		border: 1px solid #e5e7eb;
	}

	.meta-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.meta-value {
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
	}

	/* Timeline Section */
	.timeline-section {
		margin-bottom: 2rem;
	}

	.time-display {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		color: #6b7280;
		font-weight: 500;
	}

	.timeline {
		width: 100%;
		height: 44px; /* Increased height for better touch target */
		padding: 15px 0; /* Increased padding for better touch target */
		cursor: pointer;
		user-select: none;
		touch-action: none; /* Prevent browser handling of touch events */
	}

	.timeline.dragging {
		cursor: grabbing;
	}

	.timeline-track {
		position: relative;
		width: 100%;
		height: 12px; /* Increased height for better visibility */
		background: #e5e7eb;
		border-radius: 6px;
		overflow: visible;
	}

	.timeline-progress {
		height: 100%;
		background: linear-gradient(90deg, #3b82f6, #1d4ed8);
		transition: width 0.1s ease;
		border-radius: 6px;
	}

	.timeline-handle {
		position: absolute;
		top: -6px;
		width: 24px; /* Increased size for touch */
		height: 24px; /* Increased size for touch */
		background: #1d4ed8;
		border: 2px solid white;
		border-radius: 50%;
		transform: translateX(-50%);
		cursor: grab;
		box-shadow: 0 2px 4px rgba(0,0,0,0.2);
		transition: all 0.1s ease;
	}

	.timeline-handle:hover,
	.timeline-handle:active {
		transform: translateX(-50%) scale(1.2);
		box-shadow: 0 4px 8px rgba(0,0,0,0.3);
	}

	.timeline.dragging .timeline-handle {
		cursor: grabbing;
		transform: translateX(-50%) scale(1.3);
	}
	
	/* Add active state for touch devices */
	@media (hover: none) {
		.timeline:active .timeline-handle {
			transform: translateX(-50%) scale(1.3);
			box-shadow: 0 4px 8px rgba(0,0,0,0.3);
		}
	}

	.loop-region {
		position: absolute;
		top: 0;
		height: 100%;
		background: rgba(34, 197, 94, 0.3);
		border: 2px solid #22c55e;
		border-radius: 4px;
		pointer-events: none;
	}

	.progress-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 8px;
		font-size: 0.9em;
		color: #666;
	}

	.time {
		font-family: 'Courier New', monospace;
	}

	.percentage {
		font-weight: bold;
	}

	.controls {
		display: flex;
		justify-content: center;
		gap: 1rem;
		margin-bottom: 2rem;
		flex-wrap: wrap;
	}

	.control-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		border: none;
		border-radius: 8px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
		min-width: 100px;
	}

	.control-btn svg {
		width: 20px;
		height: 20px;
	}

	.play-btn {
		background: #10b981;
		color: white;
	}

	.play-btn:hover:not(:disabled) {
		background: #059669;
	}

	.play-btn.active {
		background: #065f46;
	}

	.pause-btn {
		background: #f59e0b;
		color: white;
	}

	.pause-btn:hover:not(:disabled) {
		background: #d97706;
	}

	.pause-btn.active {
		background: #92400e;
	}

	.stop-btn {
		background: #ef4444;
		color: white;
	}

	.stop-btn:hover:not(:disabled) {
		background: #dc2626;
	}

	.control-btn:disabled {
		background: #9ca3af;
		cursor: not-allowed;
		opacity: 0.6;
	}

	/* Enhanced Controls */
	.enhanced-controls {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: #f8fafc;
		border-radius: 12px;
		display: grid;
		gap: 1.5rem;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
	}

	.control-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.control-group label {
		font-weight: 600;
		color: #374151;
		font-size: 0.875rem;
	}

	.slider {
		width: 100%;
		height: 6px;
		border-radius: 3px;
		background: #e5e7eb;
		outline: none;
		cursor: pointer;
		-webkit-appearance: none;
		appearance: none;
	}

	.slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #3b82f6;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0,0,0,0.2);
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.slider::-webkit-slider-thumb:hover {
		transform: scale(1.2);
		box-shadow: 0 4px 8px rgba(0,0,0,0.3);
	}

	.slider::-moz-range-thumb {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #3b82f6;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0,0,0,0.2);
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.tempo-slider::-webkit-slider-thumb {
		background: #8b5cf6;
	}

	.volume-slider::-webkit-slider-thumb {
		background: #10b981;
	}

	.slider-labels {
		display: flex;
		justify-content: space-between;
		font-size: 0.75rem;
		color: #6b7280;
		margin-top: 0.25rem;
	}

	.loop-control {
		align-items: flex-start;
	}

	.loop-btn {
		background: #6366f1;
		color: white;
		margin-bottom: 0.5rem;
	}

	.loop-btn:hover:not(:disabled) {
		background: #4f46e5;
	}

	.loop-btn.active {
		background: #22c55e;
	}

	.loop-btn.active:hover {
		background: #16a34a;
	}

	.loop-info {
		padding: 0.5rem;
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid #22c55e;
		border-radius: 6px;
		font-size: 0.875rem;
		color: #166534;
		font-weight: 500;
	}

	.status-section {
		margin-bottom: 2rem;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.status-dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: #9ca3af;
		transition: background-color 0.2s ease;
	}

	.status-indicator.playing .status-dot {
		background: #10b981;
		animation: pulse 2s infinite;
	}

	.status-indicator.paused .status-dot {
		background: #f59e0b;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	.status-text {
		font-weight: 600;
		color: #374151;
	}

	/* Connection Status Styles */
	.connection-status {
		margin-bottom: 1rem;
		display: flex;
		justify-content: center;
	}
	
	.status-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
		justify-content: center;
	}

	.status-indicator {
		padding: 0.5rem 1rem;
		border-radius: 20px;
		font-size: 0.875rem;
		font-weight: 500;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		transition: all 0.3s ease;
	}

	.status-indicator.connected {
		background-color: #dcfce7;
		color: #166534;
		border: 1px solid #bbf7d0;
	}

	.status-indicator.connecting {
		background-color: #fef3c7;
		color: #92400e;
		border: 1px solid #fde68a;
		animation: pulse 2s infinite;
	}

	.status-indicator.polling {
		background-color: #dbeafe;
		color: #1e40af;
		border: 1px solid #bfdbfe;
	}

	.status-indicator.disconnected {
		background-color: #fee2e2;
		color: #dc2626;
		border: 1px solid #fecaca;
	}

	.performance-indicator {
		padding: 0.25rem 0.75rem;
		border-radius: 15px;
		font-size: 0.75rem;
		font-weight: 600;
		background-color: #f3f4f6;
		color: #374151;
		border: 1px solid #d1d5db;
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		transition: all 0.3s ease;
	}
	
	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.7;
		}
	}

	.navigation {
		display: flex;
		justify-content: center;
		gap: 2rem;
		padding-top: 1.5rem;
		border-top: 1px solid #e5e7eb;
	}

	.nav-link {
		color: #3b82f6;
		text-decoration: none;
		font-weight: 500;
		transition: color 0.2s ease;
	}

	.nav-link:hover {
		color: #1d4ed8;
		text-decoration: underline;
	}


	/* Screen Reader Only */
	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
	
	/* Focus Management */
	.drop-zone:focus {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
		box-shadow: 0 0 0 4px rgba(var(--color-primary-rgb), 0.1);
	}
	
	.file-label:focus-within {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	
	/* Skip to content link for keyboard users */
	.skip-link {
		position: absolute;
		top: -40px;
		left: 6px;
		background: var(--color-primary);
		color: white;
		padding: 8px;
		text-decoration: none;
		border-radius: 4px;
		z-index: 1000;
		transition: top 0.3s;
	}
	
	.skip-link:focus {
		top: 6px;
	}

	/* Mobile and Touch-Friendly Responsive Styles */
	@media (max-width: 768px) {
		.listen-container {
			padding: 0.75rem;
		}

		.listen-card {
			padding: 1.25rem;
			margin: 0.5rem;
			border-radius: 12px;
		}

		.file-label {
			padding: 2.5rem 1rem;
			min-height: 200px;
			/* Larger touch target for mobile */
			-webkit-tap-highlight-color: transparent;
		}

		.drop-icon {
			width: 2.5rem;
			height: 2.5rem;
		}

		h1 {
			font-size: 1.5rem;
			margin-bottom: 1rem;
		}

		.file-metadata {
			padding: 1rem;
			margin-bottom: 1rem;
		}

		.metadata-grid {
			gap: 0.5rem;
			grid-template-columns: 1fr;
		}

		.metadata-item {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.25rem;
		}

		.metadata-value {
			max-width: 100%;
			text-align: left;
			word-break: break-word;
		}

		.upload-actions {
			flex-direction: column;
			gap: 0.75rem;
		}

		.play-btn {
			padding: 0.875rem 1.5rem;
			font-size: 1rem;
			min-height: 48px; /* iOS recommended touch target */
			width: 100%;
			/* Enhanced touch feedback */
			-webkit-tap-highlight-color: transparent;
			transform: scale(1);
			transition: transform 0.1s ease, background-color 0.2s ease;
		}

		.play-btn:active {
			transform: scale(0.98);
		}

		.progress-bar {
			height: 16px; /* Larger for better visibility on mobile */
		}

		.progress-text {
			font-size: 0.875rem;
		}
	}

	@media (max-width: 640px) {
		.listen-container {
			padding: 0.5rem;
		}

		.listen-card {
			padding: 1rem;
			margin: 0.25rem;
		}

		h1 {
			font-size: 1.25rem;
		}

		.file-metadata {
			padding: 0.75rem;
		}

		.metadata-header h3 {
			font-size: 1rem;
		}
	}

	/* Touch device specific enhancements */
	@media (hover: none) and (pointer: coarse) {
		.file-label {
			/* Remove hover effects on touch devices */
			transition: border-color 0.2s ease, background-color 0.2s ease;
		}

		.file-label:hover {
			border-color: #e5e7eb;
			background: #f9fafb;
		}

		/* Enhanced active state for touch */
		.file-label:active {
			border-color: #3b82f6;
			background: #eff6ff;
			transform: scale(0.99);
		}
	}
</style>