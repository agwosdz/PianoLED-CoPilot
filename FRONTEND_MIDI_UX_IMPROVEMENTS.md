# Frontend MIDI USB Device Selection UX - Improvement Analysis

## Current State Analysis

### ✅ What's Working

1. **Device Discovery**: `MidiDeviceSelector.svelte` properly fetches and displays USB devices
2. **Device Selection**: Users can click to select a device
3. **Visual Feedback**: Selected device is highlighted
4. **Device Status**: Shows status (available, connected, error)
5. **Connection Status**: `MidiConnectionStatus.svelte` shows USB MIDI connected state
6. **Auto-refresh**: Can enable periodic device list refresh

### ❌ Issues Identified

1. **No Device Disconnect Function**
   - Users can SELECT a device, but cannot DESELECT/DISCONNECT it
   - No way to "clear" the selected device without selecting another one
   - No "Disconnect" button in the UI

2. **Incomplete Device Selection UX**
   - `MidiDeviceSelector.svelte` has `selectedDevice` variable but never sends the selection to backend
   - No API call to `/api/midi-input/start` with the selected device
   - Selection is local UI state only - backend doesn't know what device was picked

3. **Missing Integration Between Components**
   - `MidiDeviceSelector.svelte` and `MidiConnectionStatus.svelte` don't communicate
   - No unified MIDI control panel that ties selection to start/stop listening

4. **No Status Reflection of Device Selection**
   - After selecting a device, status doesn't update to show it's now active
   - User has no feedback that the selection took effect

5. **Missing Visual Connection Flow**
   - No clear "Apply" or "Connect" button after selecting device
   - No confirmation of device change
   - No indication of when the manager is starting to listen

## Backend API Available

✅ All necessary endpoints exist:

```
GET  /api/midi-input/devices       - Get available devices (USB + network)
POST /api/midi-input/start         - Start listening on device
POST /api/midi-input/stop          - Stop listening (disconnect)
GET  /api/midi-input/status        - Get current listening status
```

### Start Listening Endpoint

```http
POST /api/midi-input/start
Content-Type: application/json

{
  "device_name": "USB Device Name",
  "enable_usb": true,
  "enable_rtpmidi": true
}
```

Response:
```json
{
  "status": "success",
  "message": "MIDI input started successfully",
  "services": {
    "usb": true,
    "rtpmidi": false
  }
}
```

### Stop Listening Endpoint

```http
POST /api/midi-input/stop
```

Response:
```json
{
  "status": "success",
  "message": "MIDI input stopped successfully"
}
```

## Recommended UX Improvements

### 1. Add Action Buttons to Device Selector

**Current**: Just clicking a device (local-only selection)

**Proposed**: 
- Keep the click-to-select interaction
- Add "Connect" button (blue, primary)
- Add "Disconnect" button (gray, secondary, only visible when something connected)
- Show connection state in real-time

```svelte
<div class="device-actions">
  {#if selectedDevice}
    <button class="btn-primary" on:click={handleConnect}>
      🎵 Connect Device
    </button>
    {#if isConnected}
      <button class="btn-secondary" on:click={handleDisconnect}>
        ✕ Disconnect
      </button>
    {/if}
  {:else}
    <button class="btn-primary" disabled>
      Select a device first
    </button>
  {/if}
</div>
```

### 2. Integrate Device Selector with Connection Status

Create a unified **"MIDI Device Manager"** component that contains:
- Device selector (left side)
- Connection status (right side)
- Bidirectional state updates

When device connects:
- Status indicator goes green
- Shows device name in status
- Disable other device options (prevent mid-stream switching)

When device disconnects:
- Status indicator goes red
- Clear device name
- Enable other device options

### 3. Add Connection State Management

Track three states:
1. **Listening** - Service is started and ready
2. **Connected** - Specific device is actively streaming MIDI
3. **Disconnected** - No device connected (default state)

```typescript
type MidiConnectionState = 'disconnected' | 'listening' | 'connected';

export let connectionState: MidiConnectionState = 'disconnected';
```

### 4. Real-time Status Updates via WebSocket

Backend already broadcasts `midi_manager_status` events. Frontend should:
- Listen for status updates
- Update device connection indicator
- Show "Last activity" timestamp
- Display message count

```typescript
socket.on('midi_manager_status', (data) => {
  if (data.sources.USB.connected) {
    connectionState = 'connected';
    connectedDevice = data.sources.USB.device_name;
  } else {
    connectionState = 'disconnected';
    connectedDevice = null;
  }
});
```

### 5. Handle Device Switching

When user wants to switch devices while one is connected:
- Show confirmation dialog
- Stop listening on current device
- Wait for disconnect confirmation
- Start listening on new device
- Provide feedback at each step

```
"Switch from [Device A] to [Device B]?"
✓ Switching will disconnect current device and connect to new one
✓ Any active MIDI playback will continue from the newly connected device
```

### 6. Error Handling and Recovery

Show clear error messages:
- "Device disconnected unexpectedly"
- "Failed to connect to device"
- "Connection lost - attempting reconnect..."

Add auto-reconnect option:
```
"Device Connection Lost"
[Auto-reconnect in 5s...] [Reconnect Now] [Dismiss]
```

## Implementation Priority

### Phase 1 (Critical - MVP)
- [ ] Add "Connect" and "Disconnect" buttons to MidiDeviceSelector
- [ ] Wire up POST `/api/midi-input/start` when clicking Connect
- [ ] Wire up POST `/api/midi-input/stop` when clicking Disconnect
- [ ] Show loading state during connection
- [ ] Show error message on failure

### Phase 2 (Important - Polish)
- [ ] Integrate with MidiConnectionStatus for real-time updates
- [ ] Add device switching confirmation dialog
- [ ] Show connection in-progress indicator
- [ ] Add "Last connected device" memory

### Phase 3 (Nice-to-have - Advanced)
- [ ] Auto-reconnect on unexpected disconnect
- [ ] Device history/favorites
- [ ] Connection quality indicator
- [ ] Bandwidth/latency display

## File Changes Needed

### frontend/src/lib/components/MidiDeviceSelector.svelte
- Add `handleConnect()` and `handleDisconnect()` functions
- Add Connect/Disconnect action buttons
- Call `/api/midi-input/start` and `/api/midi-input/stop` endpoints
- Track `isConnecting` and `connectionError` states

### frontend/src/lib/components/MidiConnectionStatus.svelte
- Already handles status updates properly ✓
- May need to expose current connected device name for parent components

### frontend/src/routes/listen/+page.svelte
- Could integrate MIDI control into main page (or keep separate panel)
- May add MIDI status indicator in the header

### New Component (Optional): MidiDeviceManager.svelte
- Combines MidiDeviceSelector + MidiConnectionStatus
- Handles coordinated connection/disconnection flows
- Manages loading/error states for entire MIDI workflow

## Code Example: Phase 1 Implementation

```svelte
<script lang="ts">
  import { writable } from 'svelte/store';
  
  export let selectedDevice: number | null = null;
  
  let isConnecting = false;
  let connectionError: string | null = null;
  let isCurrentlyConnected = false;
  
  async function handleConnect() {
    if (!selectedDevice) return;
    
    isConnecting = true;
    connectionError = null;
    
    try {
      const response = await fetch('/api/midi-input/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_name: allDevices.find(d => d.id === selectedDevice)?.name,
          enable_usb: true,
          enable_rtpmidi: false
        })
      });
      
      const data = await response.json();
      if (response.ok) {
        isCurrentlyConnected = true;
        dispatch('connected', { deviceId: selectedDevice });
      } else {
        connectionError = data.message || 'Failed to connect device';
      }
    } catch (err) {
      connectionError = err instanceof Error ? err.message : 'Connection failed';
    } finally {
      isConnecting = false;
    }
  }
  
  async function handleDisconnect() {
    try {
      const response = await fetch('/api/midi-input/stop', { method: 'POST' });
      if (response.ok) {
        isCurrentlyConnected = false;
        dispatch('disconnected');
      }
    } catch (err) {
      connectionError = 'Failed to disconnect';
    }
  }
</script>

<!-- Buttons added to component -->
<div class="device-actions">
  <button 
    class="btn-primary" 
    on:click={handleConnect}
    disabled={!selectedDevice || isConnecting}
  >
    {#if isConnecting}
      🔄 Connecting...
    {:else if isCurrentlyConnected}
      ✓ Connected
    {:else}
      🎵 Connect Device
    {/if}
  </button>
  
  {#if isCurrentlyConnected}
    <button 
      class="btn-danger" 
      on:click={handleDisconnect}
      disabled={isConnecting}
    >
      ✕ Disconnect
    </button>
  {/if}
  
  {#if connectionError}
    <div class="error-message">{connectionError}</div>
  {/if}
</div>
```

## WebSocket Status Integration

Add to listen/+page.svelte or new MidiDeviceManager component:

```typescript
import { getSocket } from '$lib/socket';

const socket = getSocket();

socket.on('midi_manager_status', (data) => {
  // Update UI based on connection status
  const isListening = data.running;
  const usbConnected = data.sources?.USB?.connected;
  const usbDevice = data.sources?.USB?.device_name;
  
  // Reflect in device selector UI
});
```

---

## Summary

The backend already has all the necessary APIs implemented and working. The frontend needs:

1. **Connection actions** (Connect/Disconnect buttons)
2. **State management** (track connected device, connection progress)
3. **Real-time updates** (WebSocket status reflection)
4. **User feedback** (loading states, error messages)
5. **Clear UX flow** (selection → connect → use → disconnect)

This is a high-priority UX improvement that will make the MIDI device selection feature actually functional and user-friendly.
