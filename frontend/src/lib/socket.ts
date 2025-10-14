import { writable } from 'svelte/store';

// Declare io from global Socket.IO client loaded in app.html
declare const io: any;

type ConnStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export const socketStatus = writable<ConnStatus>('connecting');

let socket: any = null;
let initialized = false;
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
      socket.on('connect', () => {
        socketStatus.set('connected');
      });
      socket.on('disconnect', () => {
        socketStatus.set('disconnected');
      });
      socket.on('connect_error', () => {
        socketStatus.set('error');
      });
    } catch (e) {
      socketStatus.set('error');
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
    initialized = false;
  }
}