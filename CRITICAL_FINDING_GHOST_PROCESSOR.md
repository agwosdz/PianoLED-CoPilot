# CRITICAL FINDING: Two MidiEventProcessor Instances!

## The Evidence

From the logs, we see TWO processors handling EVERY note:

```
MIDI_PROCESSOR[548625315360]: NOTE_ON (led_count=25)   ← New processor
MIDI_PROCESSOR[548624280272]: NOTE_ON (led_count=255)  ← OLD processor!
```

Processor IDs:
- `548625315360` = Created during this boot (matches service_id=548625314688... wait that's different!)
- `548624280272` = **GHOST PROCESSOR from previous boot!**

## Why TWO Processors?

There are **NOT two USB services**. There's only one service (as the logs confirm).

**But there ARE two processors**, which means:
1. **One processor** was created on current boot with correct settings (25 LEDs)
2. **One processor** is still running from a PREVIOUS boot with old settings (255 LEDs)

This could only happen if:
- Old Python process still running
- Old threading.Thread still active
- Device file handle still open to first device

## How to Fix

The service on the Pi is showing **single USB MIDI service initialized**, but somehow TWO threads are processing.

**Hypothesis**: The old `_processing_loop()` thread from a previous restart is still running in the background!

Kill all Python processes and restart fresh:
```bash
ssh pi@192.168.1.225
sudo killall -9 python3  # Kill all python
sudo systemctl restart piano-led-visualizer.service
# Wait 10 seconds
sudo journalctl -u piano-led-visualizer.service -n 20 --no-pager
```

Then check if there's still duplication in the logs.

