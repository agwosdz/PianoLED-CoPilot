# 🚀 Deployment Guide: Duplicate Processor Fix

## What Was Fixed

**Problem**: Two MIDI processors running simultaneously, causing LEDs to light up twice with different settings.

**Root Cause**: `initialize_services()` was not idempotent and could create duplicate `USBMIDIInputService` instances.

**Solution**: Made `initialize_services()` check if services already exist before creating new ones.

## Deployment Steps

### 1. Pull Latest Code on Raspberry Pi

```bash
ssh pi@192.168.1.225
cd ~/PianoLED-CoPilot
git pull origin main
```

### 2. Restart the Service

```bash
sudo systemctl restart piano-led-visualizer.service
```

### 3. Verify the Fix (Check for Single Processor ID)

**Monitor logs in real-time and play a MIDI note:**

```bash
# In one terminal, watch logs
sudo journalctl -u piano-led-visualizer.service -f | grep -E 'MIDI_PROCESSOR|USB MIDI service'

# In another terminal, play a MIDI note on your keyboard
```

**Expected output** (✅ GOOD - Single processor ID):
```
Oct 16 10:30:45 pi start_wrapper.sh[1234]: 2025-10-16 10:30:45,123 - midi.midi_event_processor - INFO - MIDI_PROCESSOR[548203690176]: NOTE_ON note=33 velocity=35 led_count=100 leds=[84]
Oct 16 10:30:45 pi start_wrapper.sh[1234]: 2025-10-16 10:30:45,125 - midi.midi_event_processor - INFO - MIDI_PROCESSOR[548203690176]: NOTE_OFF note=33 led_count=100 leds=[]
```

**Bad output** (❌ WRONG - Multiple processor IDs):
```
Oct 16 10:30:45 pi start_wrapper.sh[1234]: 2025-10-16 10:30:45,123 - midi.midi_event_processor - INFO - MIDI_PROCESSOR[548203690176]: NOTE_ON note=33 velocity=35 led_count=100 leds=[84]
Oct 16 10:30:45 pi start_wrapper.sh[1234]: 2025-10-16 10:30:45,124 - midi.midi_event_processor - INFO - MIDI_PROCESSOR[548204325584]: NOTE_ON note=33 velocity=35 led_count=255 leds=[3]
```

### 4. Test LED Behavior

Play several MIDI notes and verify:

- ✅ Each note lights up **ONE set of LEDs** (not duplicates)
- ✅ All LED patterns are consistent (same LED indices for same notes)
- ✅ No overlapping/conflicting patterns
- ✅ LEDs turn off cleanly when note ends

### 5. Test Settings Changes

Change settings and verify clean application:

```bash
# Via web UI or direct API call
# Change: LED count, orientation, or mapping mode

# Example: Change LED count from 100 to 50
curl -X POST http://192.168.1.225:5001/api/settings \
  -H "Content-Type: application/json" \
  -d '{"category":"led","key":"led_count","value":50}'

# Play MIDI notes and verify:
# - LEDs still light up correctly
# - No old/stale patterns from 100-LED config
# - Pattern uses new 50-LED config
```

## Verification Checklist

- [ ] Single processor ID appears in ALL MIDI_PROCESSOR log entries
- [ ] LED lights up once per note (not duplicated)
- [ ] LED patterns are consistent across multiple notes
- [ ] Settings changes apply cleanly without stale patterns
- [ ] No "already initialized" skip messages before start_listening call
- [ ] Service starts cleanly without errors

## Rollback (If needed)

If something goes wrong:

```bash
cd ~/PianoLED-CoPilot
git reset --hard HEAD~2  # Go back 2 commits
git pull origin main
sudo systemctl restart piano-led-visualizer.service
```

## Expected Log Pattern After Fix

### On Service Start
```
USB MIDI service initialized (exclusive instance) [service_id=548203690176, processor_id=548203690176]
```

### When start_listening() Called
```
Services not initialized yet, calling initialize_services()
USB MIDI service initialized (exclusive instance) [service_id=548203690176, processor_id=548203690176]
USB MIDI listening started
MIDI input manager started with 1 source(s)
```

### When Playing MIDI
```
MIDI_PROCESSOR[548203690176]: NOTE_ON note=33 velocity=35 led_count=100 leds=[84]
MIDI_PROCESSOR[548203690176]: NOTE_OFF note=33 led_count=100 leds=[]
MIDI_PROCESSOR[548203690176]: NOTE_ON note=36 velocity=40 led_count=100 leds=[87]
```

**Notice**: Always the SAME processor ID `548203690176`

## Troubleshooting

### Still seeing two processor IDs?

1. **Check service fully restarted**:
   ```bash
   sudo systemctl status piano-led-visualizer.service
   ps aux | grep python
   ```

2. **Check git pull worked**:
   ```bash
   cd ~/PianoLED-CoPilot
   git log -1 --oneline
   # Should show: "fix: Make initialize_services() idempotent..."
   ```

3. **Check no stale processes**:
   ```bash
   sudo killall -9 python3
   sleep 2
   sudo systemctl start piano-led-visualizer.service
   ```

4. **Check logs for errors**:
   ```bash
   sudo journalctl -u piano-led-visualizer.service -n 100 --no-pager | grep -i error
   ```

## Questions?

If you see any issues:
1. Capture logs with: `sudo journalctl -u piano-led-visualizer.service -n 200 --no-pager > logs.txt`
2. Share the log file for analysis

---

**Deployment Date**: October 16, 2025
**Affected Components**: Backend MIDI input manager
**Impact**: Fixes duplicate LED processing, improves MIDI responsiveness
**Status**: Ready for production
