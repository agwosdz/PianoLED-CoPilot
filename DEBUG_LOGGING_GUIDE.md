# Debugging Guide: Identifying Duplicate LED Updates

I've added comprehensive logging to identify exactly where the duplication is happening.

## How to Use This Debug Build

### 1. Deploy to Pi

```bash
git push
# On Pi:
cd /home/pi/PianoLED-CoPilot
git pull
sudo systemctl restart piano-led-visualizer.service
```

### 2. Connect USB MIDI keyboard and play a note

### 3. Check the logs with this command:

```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 100 --no-pager | grep -E 'MIDI_PROCESSOR|service initialized'"
```

## What to Look For

### Single Processor (Correct):
```
USB MIDI service initialized (exclusive instance) [service_id=140123456789, processor_id=140123456800]
USB MIDI processing loop started (processor_id=140123456800)
MIDI_PROCESSOR[140123456800]: NOTE_ON note=60 velocity=100 led_count=25 leds=[...] 
MIDI_PROCESSOR[140123456800]: NOTE_OFF note=60 led_count=25 leds=[...]
```

All processor IDs are the SAME → ✅ NO DUPLICATION

### Dual Processors (Problem):
```
USB MIDI service initialized (exclusive instance) [service_id=140123456789, processor_id=140123456800]
USB MIDI service initialized (exclusive instance) [service_id=140123457890, processor_id=140123457900]  ← DUPLICATE!
...
MIDI_PROCESSOR[140123456800]: NOTE_ON note=60 velocity=100 led_count=25 leds=[12,13,14]
MIDI_PROCESSOR[140123457900]: NOTE_ON note=60 velocity=100 led_count=25 leds=[12,13,14]  ← SAME NOTE, DIFFERENT PROCESSOR!
```

Different processor IDs → ❌ DUPLICATION CONFIRMED

---

## Key Info From the Log Output

### Service Initialization:
- `service_id=XXXX` - The Python object ID of the USBMIDIInputService
- `processor_id=YYYY` - The Python object ID of the MidiEventProcessor

### Note Processing:
- `MIDI_PROCESSOR[XXXX]` - Shows which processor handled the note
- `note=60` - MIDI note number
- `velocity=100` - Velocity value
- `led_count=25` - Number of LEDs this processor thinks exist
- `leds=[12,13,14]` - Which LED indices are being updated

---

## What To Send Me

Once you've deployed and played a note, send me:

```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 200 --no-pager | head -100"
```

This will show:
1. How many USB services are created
2. How many processors exist
3. Whether they have the same or different IDs
4. Which processor is actually updating LEDs

---

## Expected Output Examples

### Good (Single path):
```
Oct 16 08:00:00 - USB MIDI service initialized [service_id=140200000000, processor_id=140200000100]
Oct 16 08:00:00 - USB MIDI processing loop started (processor_id=140200000100)
Oct 16 08:01:00 - MIDI_PROCESSOR[140200000100]: NOTE_ON note=60 velocity=64 led_count=25 leds=[12]
Oct 16 08:01:05 - MIDI_PROCESSOR[140200000100]: NOTE_OFF note=60 led_count=25 leds=[12]
```

### Bad (Dual path):
```
Oct 16 08:00:00 - USB MIDI service initialized [service_id=140200000000, processor_id=140200000100]
Oct 16 08:00:01 - USB MIDI service initialized [service_id=140200001000, processor_id=140200001100]  ← PROBLEM!
Oct 16 08:01:00 - MIDI_PROCESSOR[140200000100]: NOTE_ON note=60 velocity=64 led_count=25 leds=[12]
Oct 16 08:01:00 - MIDI_PROCESSOR[140200001100]: NOTE_ON note=60 velocity=64 led_count=25 leds=[12]  ← DUPLICATE!
```

---

## Next Steps Based on Results

**If Good (Single IDs):**
- The code fix worked
- Need to investigate why user still sees duplicates
- Could be:
  - Effects/animations running alongside
  - Firmware/hardware issue
  - Timing/visual lag misinterpreted as duplication

**If Bad (Dual IDs):**
- There's STILL another place where USB service is being created
- Search for: `USBMIDIInputService(` in code
- Or: Something is reloading/restarting the services
- Or: Multiple processes running (old systemd instance + new one)

---

Please deploy this and share the log output. The processor IDs will tell us exactly what's happening!
