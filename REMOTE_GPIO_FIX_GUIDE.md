# Remote GPIO Fix via SSH

## What This Script Does

The `scripts/remote-gpio-fix.sh` script automates the entire GPIO fix process on your Raspberry Pi from your local machine:

1. ✅ Checks SSH connectivity to Pi
2. ✅ Runs GPIO diagnostic script on Pi
3. ✅ Stops the LED service
4. ✅ Backs up settings.db
5. ✅ Updates GPIO pin in settings.db
6. ✅ Restarts the service
7. ✅ Verifies health endpoint
8. ✅ Checks for errors

## Quick Start

### From Your Local Machine

**Option 1: Try GPIO 12 (most common)**
```bash
bash scripts/remote-gpio-fix.sh 192.168.1.225 12
```

**Option 2: Try GPIO 13 (if 12 doesn't work)**
```bash
bash scripts/remote-gpio-fix.sh 192.168.1.225 13
```

**Option 3: Try GPIO 19**
```bash
bash scripts/remote-gpio-fix.sh 192.168.1.225 19
```

That's it! The script will:
- Run diagnostics
- Ask for confirmation
- Apply the fix
- Verify success
- Show results

## What Happens

### Step-by-Step

1. **Connectivity Check** (5 sec)
   - Verifies SSH connection to Pi
   - Shows connection status

2. **GPIO Diagnostic** (10 sec)
   - Runs diagnostic script on Pi
   - Shows available GPIO pins
   - Identifies conflicts

3. **Confirmation** (manual)
   - You confirm the GPIO pin choice
   - Type 'y' or 'n'

4. **Service Stop** (2 sec)
   - Stops piano-led-visualizer service
   - Ensures safe update

5. **Settings Backup** (1 sec)
   - Backs up settings.db
   - Creates settings.db.backup

6. **GPIO Pin Update** (1 sec)
   - Updates settings.db with new GPIO pin
   - Verifies update succeeded

7. **Service Restart** (5 sec)
   - Restarts piano-led-visualizer
   - Waits for initialization

8. **Health Verification** (2 sec)
   - Checks /api/calibration/health endpoint
   - Verifies LED controller status
   - Shows controller details

9. **Log Check** (2 sec)
   - Reviews recent service logs
   - Checks for errors

### Total Time: ~2-3 minutes

## Success Indicators

✅ **Script completes successfully when:**
- SSH connection works
- Diagnostic runs without errors
- Service stops cleanly
- GPIO pin updates successfully
- Service restarts without errors
- Health endpoint returns "status": "OK"
- No critical errors in logs

✅ **You'll see:**
```
✓ Connected to 192.168.1.225
✓ Diagnostic completed
✓ Service stopped
✓ Settings backed up
✓ GPIO pin updated to 12
✓ Service restarted
✓ Health check PASSED
✓ GPIO FIX SUCCESSFUL!
```

## If GPIO Pin Fails

If the script completes but health check doesn't return "OK":

1. Note the GPIO pin that didn't work
2. Run script again with different GPIO pin:
   ```bash
   bash scripts/remote-gpio-fix.sh 192.168.1.225 13
   ```

3. Try in this order:
   - GPIO 12 → 13 → 19 → 21

## Requirements

✅ **Local Machine:**
- Bash shell (Linux, macOS, or Git Bash on Windows)
- SSH access to Pi
- curl installed (or Python for JSON parsing - optional)

✅ **Raspberry Pi:**
- Service at /home/pi/PianoLED-CoPilot
- Diagnostic script at scripts/diagnose-gpio.sh
- sqlite3 installed (usually pre-installed)
- systemctl available (standard on Pi OS)

## Troubleshooting

### "Could not connect to 192.168.1.225"

Make sure:
1. Pi is powered on and connected to network
2. IP address is correct (check your router or run `ping 192.168.1.225`)
3. SSH is enabled on Pi
4. You have network connectivity

**Fix:** Verify connection first:
```bash
ssh pi@192.168.1.225 "echo 'Connected'"
```

### SSH asks for password every time

Set up passwordless SSH:
```bash
# On your local machine
ssh-keygen -t ed25519 -f ~/.ssh/pi_key -N ""
ssh-copy-id -i ~/.ssh/pi_key pi@192.168.1.225

# Then use:
ssh -i ~/.ssh/pi_key pi@192.168.1.225 "echo 'Connected'"
```

### "Diagnostic script not found!"

Make sure scripts/diagnose-gpio.sh exists on Pi:
```bash
ssh pi@192.168.1.225 "ls -la /home/pi/PianoLED-CoPilot/scripts/"
```

### Health check still not OK after trying multiple pins

1. Check Pi logs directly:
   ```bash
   ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 30"
   ```

2. Check which GPIO pins actually work on your Pi:
   ```bash
   ssh pi@192.168.1.225 "sudo bash /home/pi/PianoLED-CoPilot/scripts/diagnose-gpio.sh"
   ```

3. Verify settings.db was updated:
   ```bash
   ssh pi@192.168.1.225 "sqlite3 /home/pi/PianoLED-CoPilot/backend/settings.db 'SELECT value FROM settings WHERE category=\"led\" AND key=\"gpio_pin\";'"
   ```

## Manual Alternative

If the script doesn't work, run commands manually:

```bash
ssh pi@192.168.1.225

# 1. Run diagnostics
cd /home/pi/PianoLED-CoPilot
sudo bash scripts/diagnose-gpio.sh

# 2. Stop service
sudo systemctl stop piano-led-visualizer

# 3. Update GPIO pin (replace 12 with your chosen pin)
sqlite3 backend/settings.db "UPDATE settings SET value='12' WHERE category='led' AND key='gpio_pin';"

# 4. Restart service
sudo systemctl start piano-led-visualizer
sleep 5

# 5. Verify
curl http://localhost:5001/api/calibration/health | jq .
```

## Expected Success Output

```
╔════════════════════════════════════════════════════════════════╗
║          REMOTE GPIO FIX - Piano LED Visualizer               ║
╚════════════════════════════════════════════════════════════════╝

Configuration:
  Pi Address: 192.168.1.225
  GPIO Pin: 12
  Service: piano-led-visualizer

Step 1: Checking connectivity to Pi...
✓ Connected to 192.168.1.225

Step 2: Running GPIO diagnostic on Pi...
✓ Diagnostic completed

Step 3: Confirming GPIO pin choice...
  Selected GPIO pin: 12
  Continue with GPIO 12? (y/n) y

Step 4: Stopping piano-led-visualizer service...
✓ Service stopped

Step 5: Backing up settings.db...
✓ Settings backed up

Step 6: Updating GPIO pin to 12 in settings.db...
✓ GPIO pin updated to 12

Step 7: Restarting piano-led-visualizer service...
✓ Service restarted

Step 8: Verifying LED health status...
✓ Health check PASSED

LED Controller Status:
{
  "status": "OK",
  "led_controller_exists": true,
  "led_enabled": true,
  "num_pixels": 255,
  "pin": 12,
  "pixels_initialized": true,
  "brightness": 0.3,
  "message": "LED controller is responsive"
}

✓ LED controller is responsive!

Step 9: Checking service logs for errors...
✓ No critical errors in logs

╔════════════════════════════════════════════════════════════════╗
║                 ✅ GPIO FIX SUCCESSFUL!                       ║
║                                                                ║
║  • GPIO pin updated to: 12                                    ║
║  • Service is running                                         ║
║  • LED controller is responsive                               ║
║                                                                ║
║  Next steps:                                                  ║
║  1. Test LED control via web interface                        ║
║  2. Verify physical LED strip responds                        ║
║  3. Test MIDI input processing                                ║
╚════════════════════════════════════════════════════════════════╝
```

## Next Steps After Successful Fix

1. **Test LED Control:**
   ```bash
   curl -X POST http://192.168.1.225:5001/api/calibration/test-led \
     -H "Content-Type: application/json" \
     -d '{"index": 0, "color": [255, 0, 0], "duration_ms": 1000}'
   ```

2. **Verify Physical Response:**
   - Watch your LED strip
   - First LED should blink red for 1 second

3. **Test Full Strip:**
   ```bash
   curl -X POST http://192.168.1.225:5001/api/calibration/test-leds-batch \
     -H "Content-Type: application/json" \
     -d '{"start_index": 0, "end_index": 255, "color": [0, 255, 0], "duration_ms": 2000}'
   ```

4. **Access Web Interface:**
   - Open: http://192.168.1.225:5001
   - Navigate to calibration section
   - Test LED controls

## Support

If you have issues:

1. Check the troubleshooting section above
2. Review GPIO_ERROR_11_QUICK_FIX.md
3. Read GPIO_INITIALIZATION_ERROR_FIX.md for detailed help
4. Check service logs: `ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 50"`

---

**One-liner to try GPIO 12:**
```bash
bash scripts/remote-gpio-fix.sh 192.168.1.225 12
```

**That's all you need!**
