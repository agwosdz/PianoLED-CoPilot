# Device Selection Fix Verification

## Issue
The device selection dropdown in the Play tab was not showing any devices or allowing selection.

## Root Cause
The `/api/midi-input/devices` endpoint was returning raw device objects without the `is_current` field that the frontend expected.

Frontend code (play/+page.svelte):
```svelte
<select bind:value={selectedMidiInputDevice} on:change={(e) => connectMidiInput(e.currentTarget.value)}>
  {#each midiInputDevices as device (device.id)}
    <option value={device.name} selected={device.is_current}>
      {device.name}
    </option>
  {/each}
</select>
```

The frontend was expecting `device.is_current` but the backend was only providing `device.status`.

## Solution
Updated `/api/midi-input/devices` endpoint in `backend/app.py` to:

1. Extract USB devices and rtpMIDI sessions from the manager
2. Determine which device is currently being listened to (from `_usb_service.current_device` or active rtpMIDI session)
3. Format both USB and rtpMIDI devices with required fields:
   - `name`: Device name
   - `id`: Device ID (hash for rtpMIDI)
   - `type`: 'usb' or 'network'
   - `status`: 'connected' or 'available' or other status
   - `is_current`: Boolean indicating if this device is currently being listened to

4. Return both a flat `devices` list (for simple iteration) and separate `usb_devices`/`rtpmidi_sessions` lists

## Response Format
```json
{
  "status": "success",
  "devices": [
    {
      "name": "Device Name",
      "id": 0,
      "type": "usb",
      "status": "available",
      "is_current": false
    }
  ],
  "usb_devices": [...],
  "rtpmidi_sessions": [...],
  "current_device": "Currently listening device or null"
}
```

## Testing
To verify the fix:

1. Start the Flask backend
2. Navigate to the Play page
3. Enable "Receive MIDI from USB Keyboard"
4. The device dropdown should now populate with available devices
5. Devices can now be selected
6. The selected device's `is_current` field should be true

## Files Modified
- `backend/app.py` - Updated `get_midi_devices()` endpoint

## Frontend Already Correct
The frontend code in `frontend/src/routes/play/+page.svelte` is already correctly implemented to handle the fixed response format. No frontend changes needed.
