// Shared MIDI related types for the frontend
export type UsbMidiStatus = {
  connected: boolean;
  deviceName?: string | null;
  lastActivity?: string | null;
  messageCount: number;
};

export type NetworkMidiStatus = {
  connected: boolean;
  activeSessions: any[];
  lastActivity?: string | null;
  messageCount: number;
};

export type MidiStatusUpdate = {
  type: 'usb_midi_status' | 'network_midi_status';
  status: Partial<UsbMidiStatus & NetworkMidiStatus>;
};
