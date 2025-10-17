# QUICK START: Deploy LED Fix in 2 Minutes

## TL;DR
Your LEDs stop working after pushing `settings.db` because the singleton doesn't reinit. Fixed by calling `reset_singleton()` at startup.

## Deploy (Copy & Paste)

```bash
# Step 1: Copy files to Pi
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/
scp start_wrapper.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/
ssh pi@192.168.1.225 "chmod +x /home/pi/PianoLED-CoPilot/start_wrapper.sh"

# Step 2: Restart service
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"

# Step 3: Verify (wait 5 seconds, then check)
sleep 5
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep singleton"
```

**Expected**: Shows `"LED Controller singleton reset - will initialize with current settings.db"`

## What Changed
- **app.py**: Added 1 function call `reset_singleton()` before LED init
- **start_wrapper.sh**: Enhanced cleanup (clears cache, kills old processes)

## How It Works
1. Before init, reset the `_initialized` flag
2. LEDController reads fresh `settings.db`
3. Uses new configuration
4. Done ✅

## Verify It Works

### Check 1: Logs show reset
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 5 | grep singleton"
```
Should show: `LED Controller singleton reset`

### Check 2: Hardware loaded (not simulation)
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep rpi_ws281x"
```
Should show: `rpi_ws281x library loaded successfully`

### Check 3: LEDs initialized
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep 'LED controller initialized'"
```
Should show: `LED controller initialized with 255 pixels`

### Check 4: Test with new settings
```bash
# Change a setting
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.9}'

# Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"

# Wait for init
sleep 3

# LEDs should respond with new brightness ✅
```

## If It Doesn't Work

### Singleton reset not showing up
- Files not deployed correctly
- Restart service: `ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"`
- Check file: `ssh pi@192.168.1.225 "grep reset_singleton /home/pi/PianoLED-CoPilot/backend/app.py"`

### LEDs still don't work
- Check full logs: `ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 100" | tail -50`
- Verify API: `curl http://192.168.1.225:5001/api/midi-input/status`
- Check hardware: `ssh pi@192.168.1.225 "python3 -c \"from rpi_ws281x import PixelStrip; print('OK')\""`

## Rollback (if needed)
```bash
ssh pi@192.168.1.225 "cd /home/pi/PianoLED-CoPilot && git checkout backend/app.py start_wrapper.sh"
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
```

---

**Status**: ✅ Ready to deploy
**Downtime**: ~40 seconds
**Risk**: Very low

