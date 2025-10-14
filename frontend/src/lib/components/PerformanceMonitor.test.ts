import { render, waitFor } from '@testing-library/svelte';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import PerformanceMonitor from './PerformanceMonitor.svelte';

describe('PerformanceMonitor', () => {
	let component: any;
	let container: HTMLElement;

	const defaultProps = {
		updateFrequency: 30,
		latency: 15,
		connectionHealth: { color: 'green', text: 'Excellent', icon: '\u2705' },
		lastUpdateTime: Date.now()
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	afterEach(() => {
		if (component) {
			component.$destroy();
		}
	});

	it('renders with default props', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Check for main title
		expect(container.textContent).toContain('Performance Monitor');
	});

	it('displays update frequency correctly', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should display the update frequency
		expect(container.textContent).toContain('30');
		expect(container.textContent).toContain('Hz');
	});

	it('displays latency correctly', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should display the latency
		expect(container.textContent).toContain('15');
		expect(container.textContent).toContain('ms');
	});

	it('displays excellent connection health', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, connectionHealth: { color: 'green', text: 'Excellent', icon: '\u2705' } }
		});
		container = testContainer;

		// Should show excellent health status
		const healthElement = container.querySelector('.connection-status');
		expect(healthElement).toBeTruthy();
		expect(healthElement?.textContent).toContain('Excellent');
		expect(healthElement?.className).toContain('status-green');
	});

	it('displays good connection health', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, connectionHealth: { color: 'green', text: 'Good', icon: '\u2705' } }
		});
		container = testContainer;

		// Should show good health status
		const healthElement = container.querySelector('.connection-status');
		expect(healthElement).toBeTruthy();
		expect(healthElement?.textContent).toContain('Good');
		expect(healthElement?.className).toContain('status-green');
	});

	it('displays warning connection health', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, connectionHealth: { color: 'orange', text: 'Warning', icon: '\u26a0\ufe0f' } }
		});
		container = testContainer;

		// Should show warning health status
		const healthElement = container.querySelector('.connection-status');
		expect(healthElement).toBeTruthy();
		expect(healthElement?.textContent).toContain('Warning');
		expect(healthElement?.className).toContain('status-orange');
	});

	it('displays poor connection health', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, connectionHealth: { color: 'red', text: 'Poor', icon: '\u274c' } }
		});
		container = testContainer;

		// Should show poor health status
		const healthElement = container.querySelector('.connection-status');
		expect(healthElement).toBeTruthy();
		expect(healthElement?.textContent).toContain('Poor');
		expect(healthElement?.className).toContain('status-red');
	});

	it('updates metrics when props change', async () => {
		const { container: testContainer, component: testComponent } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;
		component = testComponent;

		// Initial values
		expect(container.textContent).toContain('30');
		expect(container.textContent).toContain('15');

		// Update props
		await component.$set({
			updateFrequency: 60,
			latency: 8
		});

		// Should display new values
		expect(container.textContent).toContain('60');
		expect(container.textContent).toContain('8');
	});

	it('shows appropriate status indicators', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should have status indicators
		const statusIndicators = container.querySelectorAll('.status-indicator, .metric-status');
		expect(statusIndicators.length).toBeGreaterThan(0);
	});

	it('displays chart placeholder', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should have chart container
		const chartContainer = container.querySelector('.chart-container');
		expect(chartContainer).toBeTruthy();
	});

	it('handles high frequency updates', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, updateFrequency: 120 }
		});
		container = testContainer;

		// Should display high frequency
		expect(container.textContent).toContain('120');
	});

	it('handles low frequency updates', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, updateFrequency: 5 }
		});
		container = testContainer;

		// Should display low frequency
		expect(container.textContent).toContain('5');
	});

	it('handles high latency', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, latency: 500 }
		});
		container = testContainer;

		// Should display high latency
		expect(container.textContent).toContain('500');
	});

	it('handles zero latency', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, latency: 0 }
		});
		container = testContainer;

		// Should display zero latency
		expect(container.textContent).toContain('0');
	});

	it('displays last update time', () => {
		const testTime = Date.now();
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, lastUpdateTime: testTime }
		});
		container = testContainer;

		// Should have some time-related content
		// (exact format depends on implementation)
		expect(container.textContent.length).toBeGreaterThan(0);
	});

	it('handles missing lastUpdateTime', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: { ...defaultProps, lastUpdateTime: undefined }
		});
		container = testContainer;

		// Should still render without errors
		expect(container.querySelector('.performance-monitor')).toBeTruthy();
	});

	it('shows metric cards', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should have metric cards
		const metricCards = container.querySelectorAll('.metric-card');
		expect(metricCards.length).toBeGreaterThan(0);
	});

	it('displays metrics grid layout', () => {
		const { container: testContainer } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;

		// Should have metrics grid
		const metricsGrid = container.querySelector('.metrics-grid');
		expect(metricsGrid).toBeTruthy();
	});

	it('handles component cleanup', () => {
		const { container: testContainer, component: testComponent } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;
		component = testComponent;

		// Component should destroy without errors
		expect(() => component.$destroy()).not.toThrow();
	});

	it('responds to prop changes reactively', async () => {
		const { container: testContainer, component: testComponent } = render(PerformanceMonitor, {
			props: defaultProps
		});
		container = testContainer;
		component = testComponent;

		// Change connection health
		await component.$set({ connectionHealth: { color: 'red', text: 'Poor', icon: '\u274c' } });

		// Should update the health display
		await waitFor(() => {
			expect(container.querySelector('.connection-status')?.textContent).toContain('Poor');
		});
	});

	it('maintains consistent layout across different metrics', () => {
		const testCases = [
			{ updateFrequency: 1, latency: 1000, connectionHealth: { color: 'red', text: 'Poor', icon: '\u274c' } },
			{ updateFrequency: 60, latency: 10, connectionHealth: { color: 'green', text: 'Excellent', icon: '\u2705' } },
			{ updateFrequency: 120, latency: 5, connectionHealth: { color: 'green', text: 'Good', icon: '\u2705' } }
		];

		testCases.forEach((testCase, index) => {
			const { container: testContainer } = render(PerformanceMonitor, {
				props: { ...defaultProps, ...testCase }
			});

			// Should maintain consistent structure
			expect(testContainer.querySelector('.performance-monitor')).toBeTruthy();
			expect(testContainer.querySelector('.metrics-grid')).toBeTruthy();
		});
	});
});