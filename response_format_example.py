#!/usr/bin/env python3
"""
Example of the fixed /api/midi-input/devices response
Demonstrates the correct format with is_current field
"""

# Before Fix - BROKEN
BEFORE_RESPONSE = {
    "status": "success",
    "devices": {
        "usb_devices": [
            {
                "name": "USB Keyboard",
                "id": 0,
                "status": "available",
                "type": "usb"
                # ❌ MISSING: is_current field - BREAKS FRONTEND!
            }
        ],
        "rtpmidi_sessions": [
            {
                "name": "192.168.1.100",
                "ip_address": "192.168.1.100",
                "port": 5004,
                "status": "available"
                # ❌ MISSING: is_current field - BREAKS FRONTEND!
            }
        ]
    }
}

# After Fix - WORKING
AFTER_RESPONSE = {
    "status": "success",
    "devices": [
        # ✅ Flat list combining USB and rtpMIDI
        {
            "name": "USB Keyboard",
            "id": 0,
            "type": "usb",
            "status": "available",
            "is_current": True  # ✅ NOW HAS is_current field!
        },
        {
            "name": "192.168.1.100",
            "id": 1234567890,
            "type": "network",
            "status": "available",
            "is_current": False  # ✅ NOW HAS is_current field!
        }
    ],
    "usb_devices": [
        # ✅ USB-only list for advanced clients
        {
            "name": "USB Keyboard",
            "id": 0,
            "type": "usb",
            "status": "available",
            "is_current": True
        }
    ],
    "rtpmidi_sessions": [
        # ✅ rtpMIDI-only list for advanced clients
        {
            "name": "192.168.1.100",
            "id": 1234567890,
            "type": "network",
            "status": "available",
            "is_current": False
        }
    ],
    "current_device": "USB Keyboard"  # ✅ Useful reference
}

# Frontend will now work correctly:
# 
# {#each midiInputDevices as device (device.id)}
#   <option value={device.name} selected={device.is_current}>
#     {device.name}
#   </option>
# {/each}
#
# Results in HTML:
# <option value="USB Keyboard" selected>USB Keyboard</option>
# <option value="192.168.1.100">192.168.1.100</option>

if __name__ == "__main__":
    import json
    print("BEFORE FIX (BROKEN):")
    print(json.dumps(BEFORE_RESPONSE, indent=2))
    print("\n" + "="*60 + "\n")
    print("AFTER FIX (WORKING):")
    print(json.dumps(AFTER_RESPONSE, indent=2))
