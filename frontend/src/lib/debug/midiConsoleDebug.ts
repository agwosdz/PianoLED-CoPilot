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

  const formatSummary = (prefix: string, payload: any): string => {
  const note = payload?.note;
  const velocity = payload?.velocity;
    const eventType = payload?.event_type || payload?.eventType;
    const leds = payload?.led_indices || payload?.ledIndices;
    const mapping = payload?.mapping || {};
    return `${prefix}: event=${eventType} note=${note} velocity=${velocity} leds=${Array.isArray(leds) ? leds.join(',') : leds} mapping=${JSON.stringify(mapping)}`;
  };

  const handleMapping = (payload: any) => {
    if (payload && typeof payload === 'object') {
      console.log(formatSummary('[midi-debug] debug_midi_mapping', payload));
    } else {
      console.log('[midi-debug] debug_midi_mapping raw', payload);
    }
  };

  const handleMidiInput = (payload: any) => {
    if (!payload || typeof payload !== 'object') {
      console.log('[midi-debug] midi_input raw', payload);
      return;
    }

    const eventType = payload?.event_type || payload?.eventType;
    if (eventType !== 'note_on') {
      return; // Only log NOTE_ON events as requested
    }

    console.log(formatSummary('[midi-debug] midi_input', payload));
  };

  socket.on('debug_midi_mapping', handleMapping);
  socket.on('midi_input', handleMidiInput);
  socket.onAny((event: string, ...args: unknown[]) => {
    console.debug('[midi-debug] onAny event', event, args);
  });

  socket.on('connect', () => {
    console.info('[midi-debug] socket connected', socket.id);
  });
  socket.on('disconnect', (reason: unknown) => {
    console.warn('[midi-debug] socket disconnected', reason);
  });
  socket.on('connect_error', (err: unknown) => {
    console.error('[midi-debug] socket connect error', err);
  });

  const onAnyHandler = (event: string, ...args: unknown[]) => {
    console.debug('[midi-debug] onAny event', event, args);
  };
  socket.onAny(onAnyHandler);

  const cleanup = () => {
    socket.off('debug_midi_mapping', handleMapping);
    socket.off('midi_input', handleMidiInput);
    socket.offAny(onAnyHandler);
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
