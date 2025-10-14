import { getSocket } from '$lib/socket';

let enabled = false;

export function enableMidiConsoleDebug(): void {
  if (enabled) return;
  if (typeof window === 'undefined') return;

  const socket = getSocket();
  if (!socket) {
    console.warn('[midi-debug] Socket.IO client not ready');
    return;
  }

  console.debug('[midi-debug] attaching listeners', {
    connected: socket.connected,
    id: socket.id,
    listeners: socket.listeners?.('debug_midi_mapping')?.length ?? 'n/a'
  });

  const handleMapping = (payload: any) => {
    if (!payload || typeof payload !== 'object') {
      return;
    }
    
    const eventType = payload?.event_type ?? payload?.eventType ?? payload?.type;
    console.log('[midi-debug] debug_midi_mapping raw', payload);
  };

  socket.on('debug_midi_mapping', handleMapping);

  socket.on('connect', () => {
    console.info('[midi-debug] socket connected', socket.id);
  });
  socket.on('disconnect', (reason: unknown) => {
    console.warn('[midi-debug] socket disconnected', reason);
  });
  socket.on('connect_error', (err: unknown) => {
    console.error('[midi-debug] socket connect error', err);
  });

  const cleanup = () => {
    socket.off('debug_midi_mapping', handleMapping);
    window.removeEventListener('beforeunload', cleanup);
    enabled = false;
  };

  window.addEventListener('beforeunload', cleanup);

  console.debug('[midi-debug] debug hooks attached for mapping diagnostics');

  (window as any).__midiDebug = {
    socket,
    cleanup,
    detach: cleanup
  };

  console.info('[midi-debug] Console logging enabled. Inspect window.__midiDebug for controls.');
  enabled = true;
}
