import { writable } from 'svelte/store';
import { toastStore } from '$lib/stores/toastStore';

// Declare io from global Socket.IO client loaded in app.html
declare const io: any;

type ConnStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export const socketStatus = writable<ConnStatus>('connecting');

let socket: any = null;
let initialized = false;
let lastToastStatus: ConnStatus | null = null;
let toastId: string | null = null;
let toastTimer: any = null;

function emitStatusToast(status: ConnStatus) {
  if (lastToastStatus === status) return;
  lastToastStatus = status;
  // Debounce rapid status changes to avoid overlay spam
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    // Clear previous toast if any
    if (toastId) {
      toastStore.removeToast(toastId);
      toastId = null;
    }
    if (status === 'connected') {
      toastId = toastStore.success('Connected to backend', { duration: 2000, dismissible: true, position: 'top-right' });
    } else if (status === 'disconnected') {
      toastId = toastStore.warning('Disconnected from backend', { duration: 2500, dismissible: true, position: 'top-right' });
    } else if (status === 'error') {
      toastId = toastStore.error('Backend socket error', { dismissible: true, position: 'top-right' });
    } else if (status === 'connecting') {
      toastId = toastStore.info('Connecting to backend…', { duration: 1500, dismissible: true, position: 'top-right' });
    }
  }, 200);
}

export function getSocket(): any {
  if (socket && socket.connected) return socket;

  const backendUrl = (typeof window !== 'undefined' && (window as any).socketIOBackendUrl) || undefined;
  const isDev = typeof import.meta !== 'undefined' && (import.meta as any)?.env?.DEV;
  const config = (typeof window !== 'undefined' && (window as any).socketIOConfig) || {
    forceNew: false,
    reconnection: true,
    timeout: 10000,
    transports: ['polling', 'websocket']
  };

  socket = (!isDev && backendUrl) ? io(backendUrl, config) : io(config);
  if (!initialized) {
    initialized = true;
    try {
      socketStatus.set('connecting');
      emitStatusToast('connecting');
      socket.on('connect', () => {
        socketStatus.set('connected');
        emitStatusToast('connected');
      });
      socket.on('disconnect', () => {
        socketStatus.set('disconnected');
        emitStatusToast('disconnected');
      });
      socket.on('connect_error', () => {
        socketStatus.set('error');
        emitStatusToast('error');
      });
    } catch (e) {
      socketStatus.set('error');
      emitStatusToast('error');
    }
  }
  return socket;
}

export function disconnectSocket(): void {
  try {
    if (socket) {
      socket.disconnect();
      socket = null;
    }
  } finally {
    socketStatus.set('disconnected');
    emitStatusToast('disconnected');
    initialized = false;
  }
}