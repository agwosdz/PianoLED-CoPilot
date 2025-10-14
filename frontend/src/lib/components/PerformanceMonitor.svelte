<script>
	import { onMount, onDestroy } from 'svelte';

		// Props (primary shape)
		/**
		 * @type {{ update_frequency: number; latency_ms: number; connection_health: string }}
		 */
		export let performanceMetrics = {
			update_frequency: 0,
			latency_ms: 0,
			connection_health: 'unknown'
		};

		// Backwards-compatible legacy props (some tests and callers still use these)
		/** @type {number|undefined} */
		export let updateFrequency = undefined;
		/** @type {number|undefined} */
		export let latency = undefined;
		/** @type {string|{ color: string; text: string; icon: string }|undefined} */
		export let connectionHealth = undefined;
		/** @type {number|undefined} */
		export let lastUpdateTime = undefined;

		// Historical data for charts
		/** @type {{ timestamp: number; value: number }[]} */
		let frequencyHistory = [];
		/** @type {{ timestamp: number; value: number }[]} */
		let latencyHistory = [];
		/** @type {number} */
		const maxHistoryLength = 60; // Keep last 60 data points

		// Performance thresholds
		const thresholds = {
			frequency: {
				good: 30,
				warning: 15
			},
			latency: {
				good: 50,
				warning: 100
			}
		};

		// Update history when metrics change
		// If legacy flat props are provided, map them into the canonical performanceMetrics shape
		$: {
			if (updateFrequency !== undefined || latency !== undefined || connectionHealth !== undefined) {
				const healthStr = typeof connectionHealth === 'string' ? connectionHealth : performanceMetrics.connection_health;
				performanceMetrics = {
					update_frequency: updateFrequency ?? performanceMetrics.update_frequency,
					latency_ms: latency ?? performanceMetrics.latency_ms,
					connection_health: healthStr
				};
			}

			if (performanceMetrics.update_frequency !== undefined) {
				updateHistory();
			}
		}

		function updateHistory() {
			const timestamp = Date.now();
        
			// Add new data points
			frequencyHistory = [...frequencyHistory, {
				timestamp,
				value: performanceMetrics.update_frequency || 0
			}].slice(-maxHistoryLength);
        
			latencyHistory = [...latencyHistory, {
				timestamp,
				value: performanceMetrics.latency_ms || 0
			}].slice(-maxHistoryLength);
		}

		// Get status color based on value and thresholds
		/**
		 * @param {number} value
		 * @param {'frequency'|'latency'} type
		 */
		function getStatusColor(value, type) {
			const threshold = thresholds[type];
			if (!threshold) return 'gray';
        
			if (type === 'frequency') {
				if (value >= threshold.good) return 'green';
				if (value >= threshold.warning) return 'orange';
				return 'red';
			} else if (type === 'latency') {
				if (value <= threshold.good) return 'green';
				if (value <= threshold.warning) return 'orange';
				return 'red';
			}
			return 'gray';
		}

		// Get connection health status
		/**
		 * @param {string|undefined} health
		 */
		function getConnectionHealthStatus(health) {
			switch (health) {
				case 'connected':
					return { color: 'green', text: 'Healthy', icon: '\u2705' };
				case 'reconnecting':
					return { color: 'orange', text: 'Reconnecting', icon: '\ud83d\udd04' };
				case 'disconnected':
					return { color: 'red', text: 'Disconnected', icon: '\u274c' };
				case 'error':
					return { color: 'red', text: 'Error', icon: '\u26a0\ufe0f' };
				case 'failed':
					return { color: 'red', text: 'Failed', icon: '\ud83d\udca5' };
				default:
					return { color: 'gray', text: 'Unknown', icon: '\u2753' };
			}
		}

		// Calculate average values
		$: avgFrequency = frequencyHistory.length > 0 
			? Math.round(frequencyHistory.reduce((sum, item) => sum + item.value, 0) / frequencyHistory.length)
			: 0;
    
		$: avgLatency = latencyHistory.length > 0 
			? Math.round(latencyHistory.reduce((sum, item) => sum + item.value, 0) / latencyHistory.length)
			: 0;

		// Get min/max values for scaling
		$: frequencyRange = {
			min: Math.min(...frequencyHistory.map(h => h.value), 0),
			max: Math.max(...frequencyHistory.map(h => h.value), 60)
		};
    
		$: latencyRange = {
			min: Math.min(...latencyHistory.map(h => h.value), 0),
			max: Math.max(...latencyHistory.map(h => h.value), 200)
		};

		// compute connectionHealthObj from legacy prop or canonical performanceMetrics
		/** @type {{ color: string; text: string; icon: string }} */
		let connectionHealthObj = { color: 'gray', text: 'Unknown', icon: '?' };

		$: {
			if (connectionHealth && typeof connectionHealth === 'object') {
				connectionHealthObj = connectionHealth;
			} else {
				const healthStr = typeof connectionHealth === 'string' ? connectionHealth : performanceMetrics.connection_health;
				connectionHealthObj = getConnectionHealthStatus(healthStr);
			}
		}

		// Computed SVG points and threshold Y positions for charts
		/** @type {string} */
		let frequencyPoints = '';
		/** @type {string} */
		let latencyPoints = '';
		/** @type {number} */
		let frequencyThresholdGoodY = 0;
		/** @type {number} */
		let frequencyThresholdWarningY = 0;
		/** @type {number} */
		let latencyThresholdGoodY = 0;
		/** @type {number} */
		let latencyThresholdWarningY = 0;

		/**
		 * Computed connection health object used in templates
		 * Renamed to avoid clashing with exported legacy prop `connectionHealth`
		 * @type {{ color: string; text: string; icon: string }}
		 */
		let connectionHealthComputed = { color: 'gray', text: 'Unknown', icon: '?' };

		$: {
			const count = frequencyHistory.length;
			if (count > 0) {
				const denom = (frequencyRange.max - frequencyRange.min) || 1;
				const step = count > 1 ? 300 / (count - 1) : 0;
				frequencyPoints = frequencyHistory.map((h, i) => {
					const x = step * i;
					const y = 100 - ((h.value - frequencyRange.min) / denom) * 100;
					return `${x},${y}`;
				}).join(' ');
				frequencyThresholdGoodY = 100 - ((thresholds.frequency.good - frequencyRange.min) / denom) * 100;
				frequencyThresholdWarningY = 100 - ((thresholds.frequency.warning - frequencyRange.min) / denom) * 100;
			} else {
				frequencyPoints = '';
				frequencyThresholdGoodY = frequencyThresholdWarningY = 0;
			}
		}

		$: {
			const count = latencyHistory.length;
			if (count > 0) {
				const denom = (latencyRange.max - latencyRange.min) || 1;
				const step = count > 1 ? 300 / (count - 1) : 0;
				latencyPoints = latencyHistory.map((h, i) => {
					const x = step * i;
					const y = 100 - ((h.value - latencyRange.min) / denom) * 100;
					return `${x},${y}`;
				}).join(' ');
				latencyThresholdGoodY = 100 - ((thresholds.latency.good - latencyRange.min) / denom) * 100;
				latencyThresholdWarningY = 100 - ((thresholds.latency.warning - latencyRange.min) / denom) * 100;
			} else {
				latencyPoints = '';
				latencyThresholdGoodY = latencyThresholdWarningY = 0;
			}
		}

	// consume legacy exported props to avoid unused-export warning when they're intentionally provided by parents
	// this reference is intentionally side-effect free
	// @ts-ignore
	const _exported_refs = { updateFrequency, latency, connectionHealth, lastUpdateTime };

	</script>
<div class="performance-monitor">
	<!-- Real-time Metrics -->
	<div class="metrics-grid">
		<div class="metric-card">
			<div class="metric-header">
				<h4>Update Frequency</h4>
				<span class="metric-status status-{getStatusColor(performanceMetrics.update_frequency, 'frequency')}"></span>
			</div>
			<div class="metric-value">
				<span class="value">{performanceMetrics.update_frequency || 0}</span>
				<span class="unit">FPS</span>
			</div>
			<div class="metric-details">
				<small>Avg: {avgFrequency} FPS</small>
				<small>Target: ≥30 FPS</small>
			</div>
		</div>

		<div class="metric-card">
			<div class="metric-header">
				<h4>Latency</h4>
				<span class="metric-status status-{getStatusColor(performanceMetrics.latency_ms, 'latency')}"></span>
			</div>
			<div class="metric-value">
				<span class="value">{performanceMetrics.latency_ms || 0}</span>
				<span class="unit">ms</span>
			</div>
			<div class="metric-details">
				<small>Avg: {avgLatency} ms</small>
				<small>Target: ≤50 ms</small>
			</div>
		</div>

		<div class="metric-card connection-card">
			<div class="metric-header">
				<h4>Connection Health</h4>
				<span class="connection-icon">{connectionHealthObj.icon}</span>
			</div>
			<div class="metric-value">
				<span class="connection-status status-{connectionHealthObj.color}">
					{connectionHealthObj.text}
				</span>
			</div>
			<div class="metric-details">
				<small>Data Points: {frequencyHistory.length}</small>
			</div>
		</div>
	</div>

	<!-- Performance Charts -->
	<div class="charts-section">
		<div class="chart-container">
			<h4>Update Frequency History</h4>
			<div class="chart frequency-chart">
				{#if frequencyHistory.length > 1}
					<svg viewBox="0 0 300 100" class="chart-svg">
						<!-- Grid lines -->
						<defs>
							<pattern id="grid" width="30" height="20" patternUnits="userSpaceOnUse">
								<path d="M 30 0 L 0 0 0 20" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
							</pattern>
						</defs>
						<rect width="300" height="100" fill="url(#grid)" />
						
						<!-- Threshold lines -->
						<line x1="0" y1="{frequencyThresholdGoodY}" x2="300" y2="{frequencyThresholdGoodY}" stroke="green" stroke-width="1" stroke-dasharray="5,5" opacity="0.5" />
						<line x1="0" y1="{frequencyThresholdWarningY}" x2="300" y2="{frequencyThresholdWarningY}" stroke="orange" stroke-width="1" stroke-dasharray="5,5" opacity="0.5" />
						
						<!-- Data line -->
						<polyline points={frequencyPoints} fill="none" stroke="#007bff" stroke-width="2" />
					</svg>
				{:else}
					<div class="no-data">Collecting data...</div>
				{/if}
			</div>
		</div>

		<div class="chart-container">
			<h4>Latency History</h4>
			<div class="chart latency-chart">
				{#if latencyHistory.length > 1}
					<svg viewBox="0 0 300 100" class="chart-svg">
						<!-- Grid lines -->
						<rect width="300" height="100" fill="url(#grid)" />
						
						<!-- Threshold lines -->
						<line x1="0" y1="{latencyThresholdGoodY}" x2="300" y2="{latencyThresholdGoodY}" stroke="green" stroke-width="1" stroke-dasharray="5,5" opacity="0.5" />
						<line x1="0" y1="{latencyThresholdWarningY}" x2="300" y2="{latencyThresholdWarningY}" stroke="orange" stroke-width="1" stroke-dasharray="5,5" opacity="0.5" />
						
						<!-- Data line -->
						<polyline points={latencyPoints} fill="none" stroke="#dc3545" stroke-width="2" />
					</svg>
				{:else}
					<div class="no-data">Collecting data...</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Performance Summary -->
	<div class="performance-summary">
		<h4>Performance Summary</h4>
		<div class="summary-grid">
			<div class="summary-item">
				<span class="label">Status:</span>
				<span class="value status-{connectionHealthObj.color}">{connectionHealthObj.text}</span>
			</div>
			<div class="summary-item">
				<span class="label">Avg FPS:</span>
				<span class="value">{avgFrequency}</span>
			</div>
			<div class="summary-item">
				<span class="label">Avg Latency:</span>
				<span class="value">{avgLatency}ms</span>
			</div>
			<div class="summary-item">
				<span class="label">Data Points:</span>
				<span class="value">{frequencyHistory.length}/{maxHistoryLength}</span>
			</div>
		</div>
	</div>
</div>

<style>
	.performance-monitor {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		padding: 1rem;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: white;
		font-family: 'Courier New', monospace;
	}



	.metrics-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.metric-card {
		padding: 1rem;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: white;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		min-height: 80px;
		display: flex;
		flex-direction: column;
		justify-content: center;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.metric-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 8px rgba(0,0,0,0.1);
	}

	.metric-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.metric-header h4 {
		margin: 0;
		font-size: 0.9rem;
		font-weight: 600;
		color: #555;
	}

	.status-indicator {
		display: inline-block;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		margin-right: 0.75rem;
		box-shadow: 0 2px 4px rgba(0,0,0,0.2);
	}

	.metric-status {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		display: inline-block;
	}

	.status-green {
		background-color: #28a745;
		box-shadow: 0 0 5px rgba(40, 167, 69, 0.5);
	}

	.status-orange {
		background-color: #ffc107;
		box-shadow: 0 0 5px rgba(255, 193, 7, 0.5);
	}

	.status-red {
		background-color: #dc3545;
		box-shadow: 0 0 5px rgba(220, 53, 69, 0.5);
	}

	.status-gray {
		background-color: #6c757d;
	}

	.status-good {
		background-color: #28a745;
	}

	.status-warning {
		background-color: #ffc107;
	}

	.status-error {
		background-color: #dc3545;
	}

	.metric-label {
		font-size: 0.85rem;
		color: #666;
		margin-bottom: 0.5rem;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		font-weight: 500;
	}

	.metric-value {
		display: flex;
		align-items: baseline;
		gap: 0.25rem;
		margin-bottom: 0.5rem;
	}

	.metric-value .value {
		font-size: 1.8rem;
		font-weight: 700;
		color: #333;
		line-height: 1.2;
	}

	.metric-value .unit {
		font-size: 1rem;
		color: #666;
		font-weight: normal;
	}

	.metric-details {
		display: flex;
		justify-content: space-between;
		font-size: 0.8rem;
		color: #666;
	}

	.connection-card .connection-icon {
		font-size: 1.2rem;
	}

	.connection-status {
		font-size: 1.2rem;
		font-weight: 600;
	}

	.charts-section {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: 1rem;
	}

	.chart-container {
		padding: 1rem;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: white;
		height: 200px;
		display: flex;
		flex-direction: column;
	}

	.chart-container h4 {
		margin: 0 0 1rem 0;
		font-size: 0.9rem;
		font-weight: 600;
		color: #555;
	}

	.chart {
		height: 100px;
		border: 1px solid #f0f0f0;
		border-radius: 4px;
		background: #fafafa;
		position: relative;
	}

	.chart-svg {
		width: 100%;
		height: 100%;
	}

	.no-data {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #999;
		font-size: 0.9rem;
	}

	.performance-summary {
		padding: 1rem;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		background: #f8f9fa;
	}

	.health-status {
		padding: 1rem;
		border-radius: 8px;
		margin-top: 1rem;
		font-weight: 500;
		font-size: 1rem;
		display: flex;
		align-items: center;
		min-height: 44px;
	}

	.health-excellent {
		background-color: #d4edda;
		color: #155724;
		border: 1px solid #c3e6cb;
	}

	.health-good {
		background-color: #d1ecf1;
		color: #0c5460;
		border: 1px solid #bee5eb;
	}

	.health-warning {
		background-color: #fff3cd;
		color: #856404;
		border: 1px solid #ffeaa7;
	}

	.health-poor {
		background-color: #f8d7da;
		color: #721c24;
		border: 1px solid #f5c6cb;
	}

	.performance-summary h4 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: #333;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 0.5rem;
	}

	.summary-item {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem;
		background: white;
		border-radius: 4px;
		border: 1px solid #e9ecef;
	}

	.summary-item .label {
		font-weight: 500;
		color: #666;
		font-size: 0.9rem;
	}

	.summary-item .value {
		font-weight: 600;
		color: #333;
		font-size: 0.9rem;
	}

	/* Mobile-specific optimizations */
	@media (max-width: 768px) {
		.performance-monitor {
			padding: 0.75rem;
		}
		
		.metrics-grid {
			grid-template-columns: repeat(2, 1fr);
			gap: 0.75rem;
		}
		
		.metric-card {
			padding: 0.75rem;
			min-height: 70px;
		}
		
		.metric-value .value {
			font-size: 1.5rem;
		}
		
		.chart-container {
			height: 150px;
			padding: 0.75rem;
		}
		
		.charts-section {
			grid-template-columns: 1fr;
		}
		
		.summary-grid {
			grid-template-columns: 1fr 1fr;
		}
		
		.health-status {
			padding: 0.75rem;
			font-size: 0.9rem;
		}
	}

	@media (max-width: 480px) {
		.performance-monitor {
			padding: 0.5rem;
		}
		

		
		.metrics-grid {
			grid-template-columns: 1fr;
			gap: 0.5rem;
		}
		
		.metric-card {
			padding: 0.5rem;
			min-height: 60px;
		}
		
		.metric-label {
			font-size: 0.75rem;
			margin-bottom: 0.25rem;
		}
		
		.metric-value .value {
			font-size: 1.3rem;
		}
		
		.metric-value .unit {
			font-size: 0.85rem;
		}
		
		.chart-container {
			height: 120px;
			padding: 0.5rem;
		}
		
		.health-status {
			padding: 0.5rem;
			font-size: 0.85rem;
			min-height: 40px;
		}
		
		.status-indicator {
			width: 12px;
			height: 12px;
			margin-right: 0.5rem;
		}
	}
</style>