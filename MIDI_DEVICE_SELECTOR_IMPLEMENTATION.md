# MIDI USB Device Selection - Implementation Guide

## Overview

The original `MidiDeviceSelector.svelte` component displays available MIDI devices but doesn't actually connect to them. The improved version (`MidiDeviceSelectorImproved.svelte`) adds the missing connect/disconnect functionality.

## Current Status

### ✅ What's Done
- Backend APIs fully implemented and working
- Improved component created with full connection management
- Connect/disconnect buttons with proper state management
- Error handling and loading states
- Real-time connection status display

### 📋 What Needs to Be Done
1. Replace or update the original component in your listen page
2. Test connection/disconnection flow
3. Integrate with WebSocket status updates (optional enhancement)

## Changes to Original Component

### New State Variables
```typescript
// Connection state
let isConnecting = false;
let connectionError: string | null = null;
let isCurrentlyConnected = false;
let connectedDeviceName: string | null = null;
```

### New Functions
```typescript
// Connects to the selected device via API
async function handleConnect()

// Disconnects from the currently connected device
async function handleDisconnect()
```

### New UI Section
```svelte
<!-- Connection actions at the bottom -->
<div class="connection-actions">
  {#if connectionError}
    <!-- Error message with dismiss button -->
  {/if}
  
  {#if isCurrentlyConnected}
    <!-- Connected state with device name and disconnect button -->
  {:else}
    <!-- Connect button -->
  {/if}
</div>
```

### New Styles
- `.connection-actions` - Container for connection controls
- `.connection-error` - Error message styling
- `.btn-connect` - Blue gradient connect button
- `.btn-disconnect` - Red disconnect button
- `.connected-state` - Shows "Connected to [Device]" with pulse indicator
- `.pulse-dot` - Animated indicator showing active connection

## Integration Steps

### Option 1: Direct Component Replacement (Simplest)

**File**: `frontend/src/lib/components/MidiDeviceSelector.svelte`

Replace the entire component with the improved version:

```bash
cp frontend/src/lib/components/MidiDeviceSelectorImproved.svelte \
   frontend/src/lib/components/MidiDeviceSelector.svelte
```

**Pros**: 
- Single update everywhere it's used
- Clean, non-breaking change
- All existing code continues to work

**Cons**: 
- Overwrites original (back it up first if you want to keep it)

### Option 2: Import Both (Keep Existing)

Use the improved version selectively:

```svelte
<!-- In your listen page -->
<script>
  import MidiDeviceSelectorImproved from '$lib/components/MidiDeviceSelectorImproved.svelte';
</script>

<MidiDeviceSelectorImproved 
  bind:selectedDevice
  on:connected={(e) => console.log('Connected to', e.detail.deviceName)}
  on:disconnected={() => console.log('Disconnected')}
/>
```

**Pros**:
- Can test both side-by-side
- Gradually migrate to improved version
- Keep original as fallback

**Cons**:
- Maintains two versions
- Needs manual updating of imports

## Usage

### Basic Usage

```svelte
<script>
  import MidiDeviceSelector from '$lib/components/MidiDeviceSelector.svelte';
  
  let selectedDevice: number | null = null;
</script>

<MidiDeviceSelector 
  bind:selectedDevice
  autoRefresh={true}
  refreshInterval={5000}
  on:connected={(event) => {
    console.log('Device connected:', event.detail.deviceName);
  }}
  on:disconnected={() => {
    console.log('Device disconnected');
  }}
  on:deviceSelected={(event) => {
    console.log('Device selected:', event.detail);
  }}
/>
```

### Events

| Event | Detail | Description |
|-------|--------|-------------|
| `connected` | `{ deviceId: number, deviceName: string }` | Fired when successfully connected to a device |
| `disconnected` | (none) | Fired when successfully disconnected from device |
| `deviceSelected` | MidiDevice object | Fired when user selects a device (before connecting) |
| `devicesUpdated` | DeviceResponse | Fired when device list is updated |

### Exported Props

```typescript
export let selectedDevice: number | null = null;
export let autoRefresh = false;
export let refreshInterval = 5000;
```

## API Calls Made

### Connect Device

```http
POST /api/midi-input/start
Content-Type: application/json

{
  "device_name": "USB Device Name",
  "enable_usb": true,
  "enable_rtpmidi": false
}
```

### Disconnect Device

```http
POST /api/midi-input/stop
```

## Testing Guide

### 1. Component Loads
```
✓ Device list displays
✓ USB and Network sections visible
✓ Connect button is disabled until device selected
✓ Auto-refresh toggle works
```

### 2. Device Selection
```
✓ Clicking device highlights it
✓ Selected device info shows
✓ Connect button becomes enabled
```

### 3. Connection
```
✓ Click Connect button
✓ Button shows "🔄 Connecting..."
✓ Connection succeeds
✓ UI shows "Connected to [Device Name]"
✓ Disconnect button appears
✓ Backend receives /api/midi-input/start call
```

### 4. Disconnection
```
✓ Click Disconnect button
✓ Button shows "🔄 Disconnecting..."
✓ Disconnection succeeds
✓ UI returns to disconnected state
✓ Connect button reappears
✓ Can select another device
```

### 5. Error Handling
```
✓ Disconnect USB device physically
✓ Error message appears
✓ Can dismiss error with ✕ button
✓ Can retry connection
```

### 6. State Management
```
✓ Cannot connect two devices simultaneously
✓ Cannot select while connecting
✓ Settings persist after disconnect
✓ Device name shows correctly
```

## Manual Testing Checklist

- [ ] Component displays without errors
- [ ] Device list refreshes correctly
- [ ] Can select a USB device
- [ ] "Connect Device" button works
- [ ] Connection status updates in UI
- [ ] Pulse indicator shows on connection
- [ ] Can disconnect device
- [ ] Disconnect button hidden after disconnect
- [ ] Can select and connect a different device
- [ ] Error messages display and dismiss properly
- [ ] Loading state shows during connection
- [ ] Auto-refresh works
- [ ] Device list updates when devices added/removed

## Integration with Listen Page

### Current File
`frontend/src/routes/listen/+page.svelte`

### Suggested Position
Add MIDI device selector before or alongside the upload section:

```svelte
<div class="midi-control-area">
  <section class="midi-selector-card">
    <MidiDeviceSelector 
      bind:selectedDevice
      on:connected={(e) => {
        // Optional: Show toast notification
        showNotification(`Connected to ${e.detail.deviceName}`);
      }}
      on:disconnected={() => {
        showNotification('MIDI device disconnected');
      }}
    />
  </section>
  
  <!-- Rest of listen page content -->
</div>
```

## Future Enhancements (Phase 2+)

### 1. WebSocket Integration
Update connection status in real-time from backend:

```typescript
import { getSocket } from '$lib/socket';

const socket = getSocket();
socket.on('midi_manager_status', (data) => {
  if (data.sources?.USB?.connected) {
    isCurrentlyConnected = true;
    connectedDeviceName = data.sources.USB.device_name;
  }
});
```

### 2. Device Switching
Allow switching devices mid-session:

```typescript
async function handleDeviceSwitch() {
  // Show confirmation dialog
  // Disconnect from current device
  // Wait for confirmation
  // Connect to new device
}
```

### 3. Connection History
Remember recently used devices:

```typescript
const recentDevices = JSON.parse(
  localStorage.getItem('recentMidiDevices') || '[]'
);
```

### 4. Auto-reconnect
Automatically reconnect if device disconnects unexpectedly:

```typescript
socket.on('midi_device_disconnected', async () => {
  if (shouldAutoReconnect) {
    await new Promise(r => setTimeout(r, 1000)); // Wait 1s
    await handleConnect();
  }
});
```

## Troubleshooting

### Component Not Showing Connect Button
- **Issue**: Connect button disabled even after selecting device
- **Solution**: Check that `selectedDevice` is being set. Add console.log to verify:
  ```typescript
  function selectDevice(device: MidiDevice) {
    selectedDevice = device.id;
    console.log('Selected device:', selectedDevice);
  }
  ```

### Connection Fails Silently
- **Issue**: Click Connect but nothing happens, no error shown
- **Solution**: Check browser console for errors. Ensure backend endpoint is accessible:
  ```bash
  curl -X POST http://localhost:5001/api/midi-input/start \
    -H "Content-Type: application/json" \
    -d '{"device_name":"Test Device","enable_usb":true}'
  ```

### Connected Status Doesn't Update
- **Issue**: UI shows "Connecting..." then goes back to normal
- **Solution**: Check if backend is actually receiving the request and what it's returning:
  ```typescript
  console.log('API Response:', data);
  ```

### Device List Not Updating
- **Issue**: New devices not shown when plugged in
- **Solution**: Click the refresh button or enable auto-refresh. Check backend device enumeration:
  ```bash
  curl http://localhost:5001/api/midi-input/devices
  ```

## File Locations

- **Component**: `frontend/src/lib/components/MidiDeviceSelectorImproved.svelte`
- **Usage**: `frontend/src/routes/listen/+page.svelte`
- **Backend**: `backend/app.py` (routes starting with `/api/midi-input/`)
- **API Handler**: `backend/midi_input_manager.py`

## Related Documentation

- `FRONTEND_MIDI_UX_IMPROVEMENTS.md` - Analysis of UX gaps and design decisions
- `backend/app.py` - API endpoint implementations
- `backend/midi_input_manager.py` - MIDI manager logic

---

## Quick Start

1. **Copy improved component**:
   ```bash
   cp frontend/src/lib/components/MidiDeviceSelectorImproved.svelte \
      frontend/src/lib/components/MidiDeviceSelector.svelte
   ```

2. **Update listen page to use it** (if not auto-imported):
   ```svelte
   import MidiDeviceSelector from '$lib/components/MidiDeviceSelector.svelte';
   ```

3. **Test**:
   - Connect a USB MIDI device
   - Navigate to listen page
   - Device should appear in list
   - Select device
   - Click "Connect Device"
   - See connection status update
   - Play a MIDI note
   - LEDs should light up
   - Click "Disconnect"
   - Select different device
   - Click "Connect Device" again

4. **Verify in logs**:
   ```bash
   ssh pi@192.168.1.225
   sudo journalctl -u piano-led-visualizer.service -f | grep MIDI_PROCESSOR
   ```

That's it! The component should now provide a complete device connection experience.
