import { readable } from 'svelte/store';

export interface ToastData {
	id: string;
	type: 'success' | 'error' | 'warning' | 'info';
	title?: string;
	message: string;
	duration?: number;
	dismissible?: boolean;
	persistent?: boolean;
	position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

const emptyStore = readable<ToastData[]>([]);

function generateId(): string {
	return Math.random().toString(36).substr(2, 9);
}

function addToast(_toast: Omit<ToastData, 'id'>): string {
	return generateId();
}

function removeToast(_id: string): void {
	// No-op: toast notifications are disabled
}

function clearAll(): void {
	// No-op: toast notifications are disabled
}

function success(message: string, _options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>): string {
	console.info('[status] success:', message);
	return addToast({ type: 'success', message });
}

function error(message: string, _options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>): string {
	console.error('[status] error:', message);
	return addToast({ type: 'error', message });
}

function warning(message: string, _options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>): string {
	console.warn('[status] warning:', message);
	return addToast({ type: 'warning', message });
}

function info(message: string, _options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>): string {
	console.info('[status] info:', message);
	return addToast({ type: 'info', message });
}

function loading(message: string, _options?: Partial<Omit<ToastData, 'id' | 'type' | 'message'>>): string {
	console.info('[status] loading:', message);
	return addToast({ type: 'info', message, persistent: true, dismissible: false });
}

function updateToast(_id: string, _updates: Partial<Omit<ToastData, 'id'>>): void {
	// No-op: toast notifications are disabled
}

export const toastStore = {
	subscribe: emptyStore.subscribe,
	addToast,
	removeToast,
	clearAll,
	success,
	error,
	warning,
	info,
	loading,
	updateToast
};

// Helper function for async operations with loading states
export async function withLoadingToast<T>(
	promise: Promise<T>,
	_loadingMessage: string,
	successMessage?: string,
	errorMessage?: string
): Promise<T> {
	try {
		const result = await promise;
		if (successMessage) {
			console.info('[status] success:', successMessage);
		}
		return result;
	} catch (error) {
		const message = errorMessage || (error instanceof Error ? error.message : 'An error occurred');
		console.error('[status] error:', message, error);
		throw error;
	}
}