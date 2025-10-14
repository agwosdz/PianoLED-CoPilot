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

  const handleMapping = (payload: unknown) => {
    console.groupCollapsed('[midi-debug] debug_midi_mapping');
    console.log(payload);
    console.groupEnd();
  };

  const handleMidiInput = (payload: unknown) => {
    console.groupCollapsed('[midi-debug] midi_input');
    console.log(payload);
    console.groupEnd();
  };

  socket.on('debug_midi_mapping', handleMapping);
  socket.on('midi_input', handleMidiInput);

  const cleanup = () => {
    socket.off('debug_midi_mapping', handleMapping);
    socket.off('midi_input', handleMidiInput);
    window.removeEventListener('beforeunload', cleanup);
    enabled = false;
  };

  window.addEventListener('beforeunload', cleanup);

  (window as any).__midiDebug = {
    socket,
    cleanup,
    detach: cleanup
  };

  console.info('[midi-debug] Console logging enabled. Inspect window.__midiDebug for controls.');
  enabled = true;
}
