#!/usr/bin/env python3
try:
    import mido
    MIDO_AVAILABLE = True
    print("✓ mido library available")
except ImportError as e:
    print(f"✗ mido library not available: {e}")
    print("This test requires mido to be installed")
    print("Install with: pip3 install mido python-rtmidi")
    exit(1)

import time

print("Available MIDI devices:")
for i, name in enumerate(mido.get_input_names()):
    print(f"  {i}: {name}")

device_name = "CASIO USB-MIDI:CASIO USB-MIDI MIDI 1 20:0"
print(f"\nTesting device: {device_name}")

try:
    port = mido.open_input(device_name)
    print("\nListening for 10 seconds, press keys on CASIO keyboard...")
    
    start = time.time()
    count = 0
    
    while time.time() - start < 10:
        msg = port.poll()
        if msg:
            print(f"MIDI: {msg}")
            count += 1
        time.sleep(0.001)
    
    port.close()
    print(f"\nReceived {count} messages")
    
except Exception as e:
    print(f"Error: {e}")