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

  const formatMapping = (mapping: any): string => {
    if (!mapping || typeof mapping !== 'object') {
      return 'mapping=<' + String(mapping) + '>';
    }
    const parts = [
      `mode=${mapping.mode ?? 'n/a'}`,
      `leds_per_key=${mapping.leds_per_key ?? 'n/a'}`,
      `base_offset=${mapping.base_offset ?? 'n/a'}`,
      `orientation=${mapping.orientation ?? 'n/a'}`
    ];
    if (Object.prototype.hasOwnProperty.call(mapping, 'manual_mapping_used')) {
      parts.push(`manual=${mapping.manual_mapping_used}`);
    }
    if (Object.prototype.hasOwnProperty.call(mapping, 'manual_entry')) {
      parts.push(`manual_entry=${mapping.manual_entry ?? 'n/a'}`);
    }
    return parts.join(' ');
  };

  const formatSummary = (prefix: string, payload: any): string => {
    const note = payload?.note;
    const velocity = payload?.velocity;
    const eventType = payload?.event_type ?? payload?.eventType ?? payload?.type ?? 'unknown';
    const ledsRaw = payload?.led_indices || payload?.ledIndices;
    const leds = Array.isArray(ledsRaw) ? ledsRaw.join(',') : ledsRaw;
    const mappingText = formatMapping(payload?.mapping);
    return `${prefix}: event=${eventType} note=${note} velocity=${velocity} leds=${leds ?? 'n/a'} ${mappingText}`;
  };

  const handleMapping = (payload: any) => {
    if (!payload || typeof payload !== 'object') {
      return;
    }

    const eventType = payload?.event_type ?? payload?.eventType ?? payload?.type;
    console.debug('[midi-debug] debug_midi_mapping raw', payload);
    if (eventType && eventType !== 'note_on') {
      return;
    }
    console.log(formatSummary('[midi-debug] debug_midi_mapping', payload));
  };

  const handleMidiInput = (payload: any) => {
    if (!payload || typeof payload !== 'object') {
      return;
    }

    const eventType = payload?.event_type ?? payload?.eventType ?? payload?.type;
    console.debug('[midi-debug] midi_input raw', payload);
    if (eventType && eventType !== 'note_on') {
      return;
    }
    console.log(formatSummary('[midi-debug] midi_input', payload));
  };

  socket.on('debug_midi_mapping', handleMapping);
  socket.on('midi_input', handleMidiInput);

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
    socket.off('midi_input', handleMidiInput);
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
