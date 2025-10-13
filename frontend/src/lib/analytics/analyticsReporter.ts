import { errorAnalytics } from './errorAnalytics';
import type { AnalyticsReport, ErrorEvent } from './errorAnalytics';

/**
 * Analytics Reporter
 * Provides methods to generate and export analytics reports
 */
export class AnalyticsReporter {
	/**
	 * Generate comprehensive analytics report
	 */
	generateReport(): AnalyticsReport {
		return errorAnalytics.generateReport();
	}

	/**
	 * Export analytics data as JSON
	 */
	exportAsJSON(): string {
		const report = this.generateReport();
		return JSON.stringify(report, null, 2);
	}

	/**
	 * Export analytics data as CSV
	 */
	exportAsCSV(): string {
		const lines: string[] = [];
		lines.push('Piano LED Analytics Report');
		lines.push('Generated: ' + new Date().toISOString());
		lines.push('');

		// Get error events from analytics directly since they're not in the report
		const errorEvents = errorAnalytics.getEvents().filter(e => e.type === 'error');
		const recoveryEvents = errorAnalytics.getEvents().filter(e => e.type === 'recovery');
		const preventionEvents = errorAnalytics.getEvents().filter(e => e.type === 'prevention');

		// Error events CSV
		lines.push('Error Events');
		lines.push('Type,Severity,Message,Code,Timestamp,Context');
		
		errorEvents.forEach(event => {
			const contextStr = JSON.stringify(event.context).replace(/"/g, '""');
			lines.push(`"${event.type}","${event.severity}","${event.message}","${event.errorCode || ''}","${new Date(event.timestamp).toISOString()}","${contextStr}"`);
		});

		lines.push('');
		lines.push('Recovery Events');
		lines.push('Error ID,Method,Success,Timestamp');
		
		recoveryEvents.forEach(event => {
			const success = event.resolution?.successful ? 'true' : 'false';
			const method = event.resolution?.method || 'unknown';
			lines.push(`"${event.id}","${method}","${success}","${new Date(event.timestamp).toISOString()}"`);
		});

		lines.push('');
		lines.push('Prevention Events');
		lines.push('Type,Action,Timestamp,Context');
		
		preventionEvents.forEach(event => {
			const contextStr = JSON.stringify(event.context).replace(/"/g, '""');
			const action = event.userAction || 'unknown';
			lines.push(`"${event.type}","${action}","${new Date(event.timestamp).toISOString()}","${contextStr}"`);
		});

		return lines.join('\n');
	}

	/**
	 * Get error patterns summary
	 */
	getErrorPatternsSummary(): string {
		const report = this.generateReport();
		const lines: string[] = [];

		lines.push('Error Patterns Summary');
		lines.push('===================');
		lines.push('');

		report.topErrorPatterns.forEach(pattern => {
			lines.push(`Pattern: ${pattern.category}`);
			lines.push(`Frequency: ${pattern.frequency}`);
			lines.push(`Success Rate: ${Math.round(pattern.successRate * 100)}%`);
			lines.push(`Avg Time to Resolve: ${Math.round(pattern.avgTimeToResolve / 1000)}s`);
			lines.push(`Common Causes:`);
			pattern.commonCauses.forEach(cause => lines.push(`  - ${cause}`));
			lines.push(`Suggested Improvements:`);
			pattern.suggestedImprovements.forEach(improvement => lines.push(`  - ${improvement}`));
			lines.push('');
		});

		return lines.join('\n');
	}

	/**
	 * Clear all analytics data
	 */
	clearData(): void {
		errorAnalytics.cleanup();
	}

	/**
	 * Download report as file
	 */
	downloadReport(format: 'json' | 'csv' = 'json'): void {
		const data = format === 'json' ? this.exportAsJSON() : this.exportAsCSV();
		const blob = new Blob([data], { type: format === 'json' ? 'application/json' : 'text/csv' });
		const url = URL.createObjectURL(blob);
		
		const a = document.createElement('a');
		a.href = url;
		a.download = `error-analytics-${new Date().toISOString().split('T')[0]}.${format}`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}
}

export const analyticsReporter = new AnalyticsReporter();