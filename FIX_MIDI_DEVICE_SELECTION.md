# 🎛️ Fix: MIDI Input Selection Wonky

## Problem
MIDI input device selection was defaulting to "MIDI Through Port" instead of showing physical devices first.

## Root Cause
1. **Frontend**: The `selected={device.is_current}` attribute in HTML options doesn't work in Svelte - must let `bind:value` handle selection
2. **Backend**: The device list included virtual/loopback ports like "MIDI Through Port" without filtering, causing them to appear first

## Solution Applied

### Frontend Fix (play/+page.svelte, line 450-460)
- ✅ Removed the non-functional `selected={device.is_current}` attribute
- ✅ Let `bind:value` properly manage selection
- ✅ Added visual indicator "(current)" to show which device is selected

### Backend Fix (backend/midi/usb_port_manager.py)
Updated `list_devices()` method to:

1. **Separate** devices into two categories:
   - Physical devices (keyboards, interfaces, controllers)
   - Virtual devices (MIDI Through Port, RtMidOut, USB-USB, Loopback, Virtual)

2. **Return physical devices first**, followed by virtual devices
   - This ensures real MIDI controllers appear at the top
   - Virtual ports are still available if user wants them

3. **Filter keywords detected**:
   - "Through" → MIDI Through Port
   - "RtMidOut" → rtMIDI virtual outputs
   - "USB-USB" → Self-loops
   - "Loopback" → Jack loopback ports
   - "Virtual" → Explicitly virtual ports

## Behavior Changes
✅ Physical MIDI devices now appear first in the dropdown
✅ Virtual ports appear at the end (still usable but not default)
✅ Selection now properly tracks current device
✅ Visual feedback shows which device is currently selected with "(current)" label

## Testing
1. Load the UI
2. Check MIDI input device dropdown
3. Should see physical keyboard/interface first
4. "MIDI Through Port" should appear at the very end
5. Selecting a device should immediately connect to it

## Example Device Order
**Before**: MIDI Through Port, KeyStation, ...
**After**: KeyStation, ..., MIDI Through Port
