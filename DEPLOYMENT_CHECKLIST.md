# DEPLOYMENT CHECKLIST: LED Controller Fix

## Pre-Deployment (Local Machine)

- [ ] Review `backend/app.py` line 101-105 (singleton reset code)
- [ ] Verify `start_wrapper.sh` has been updated
- [ ] Understand the fix: Reset `_initialized` flag to force fresh init
- [ ] Read documentation if needed (see DOCUMENTATION_INDEX.md)

## Deployment Steps

### Step 1: Copy Files to Pi
```bash
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/
```
- [ ] Command executed
- [ ] Check for errors

### Step 2: Copy Wrapper Script
```bash
scp start_wrapper.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/
```
- [ ] Command executed
- [ ] Check for errors

### Step 3: Make Script Executable
```bash
ssh pi@192.168.1.225 "chmod +x /home/pi/PianoLED-CoPilot/start_wrapper.sh"
```
- [ ] Command executed
- [ ] Check for errors

### Step 4: Restart Service
```bash
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
```
- [ ] Command executed
- [ ] Wait 5 seconds for service to fully start

## Post-Deployment Verification

### Check 1: Singleton Reset Message
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep singleton"
```
- [ ] Command executed
- [ ] Output shows: `LED Controller singleton reset - will initialize with current settings.db`
- [ ] If not found: See troubleshooting section below

### Check 2: Hardware Loaded (Not Simulation)
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 30 | grep rpi_ws281x"
```
- [ ] Command executed
- [ ] Output shows: `rpi_ws281x library loaded successfully`
- [ ] If not found: Hardware may not be installed

### Check 3: LED Controller Initialized
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 30 | grep 'LED controller initialized'"
```
- [ ] Command executed
- [ ] Output shows: `LED controller initialized with 255 pixels on pin 18`
- [ ] Verify pixel count and pin match your hardware

### Check 4: API Responsive
```bash
curl http://192.168.1.225:5001/api/midi-input/status
```
- [ ] Command executed
- [ ] Returns JSON response (API working)
- [ ] If timeout: Service may not be fully started, wait 10 seconds

### Check 5: Automated Verification
```bash
scp verify_led_fix.sh pi@192.168.1.225:/home/pi/PianoLED-CoPilot/
ssh pi@192.168.1.225 "bash /home/pi/PianoLED-CoPilot/verify_led_fix.sh"
```
- [ ] Script copied
- [ ] Script executed
- [ ] All 5 checks show green ✓

## Functional Testing

### Test 1: Change Setting
```bash
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.9}'
```
- [ ] Command executed
- [ ] Returns success response

### Test 2: Restart Service with New Settings
```bash
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5
```
- [ ] Service restarted
- [ ] Waited for initialization

### Test 3: Verify New Setting Applied
```bash
curl http://192.168.1.225:5001/api/settings/led/brightness
```
- [ ] New brightness value (0.9) is being used
- [ ] LEDs respond with new brightness (visual check)
- [ ] If old value: Settings not being read (problem!)

### Test 4: Multiple Push-Restart Cycle
Repeat the setting change 3 more times to verify consistency:
- [ ] Cycle 1: Change setting → Restart → Verify ✓
- [ ] Cycle 2: Change setting → Restart → Verify ✓
- [ ] Cycle 3: Change setting → Restart → Verify ✓
- [ ] All cycles worked consistently

## If All Checks Pass ✅

Congratulations! The fix is working. You can now:

- [ ] Push new `settings.db` files without losing LED functionality
- [ ] Change settings and have them apply on service restart
- [ ] Confidently deploy configuration updates to the Pi

## If Something Fails ⚠️

### Singleton Reset Message Not Found

**Problem**: Output doesn't show "singleton reset"

**Causes**:
- Files not deployed correctly
- Service not restarted
- Old service process still running

**Solutions**:
```bash
# 1. Verify file was copied
ssh pi@192.168.1.225 "grep -n 'reset_singleton' /home/pi/PianoLED-CoPilot/backend/app.py"
# Should return the line number

# 2. If not found, redeploy:
scp backend/app.py pi@192.168.1.225:/home/pi/PianoLED-CoPilot/backend/

# 3. Kill old processes and restart
ssh pi@192.168.1.225 "pkill -f 'python.*app.py' || true; sleep 2; sudo systemctl start piano-led-visualizer"

# 4. Check logs again
sleep 5
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 20 | grep singleton"
```
- [ ] Verified file copied
- [ ] Restarted service cleanly
- [ ] Singleton reset message now appears

### Hardware Not Loaded (Simulation Mode)

**Problem**: `rpi_ws281x library loaded successfully` not in logs

**Causes**:
- rpi_ws281x not installed on Pi
- Hardware dependencies missing

**Solutions**:
```bash
# Check if library is installed
ssh pi@192.168.1.225 "python3 -c \"from rpi_ws281x import PixelStrip; print('OK')\""

# If error, install dependencies (on Pi):
ssh pi@192.168.1.225 "cd /home/pi/PianoLED-CoPilot && pip install -r backend/requirements.txt"

# If already installed but not showing up:
ssh pi@192.168.1.225 "python3 -m pip install --upgrade rpi-ws281x"
```
- [ ] Verified library installed
- [ ] Restarted service
- [ ] Hardware message now appears

### LED Controller Not Initializing

**Problem**: `LED controller initialized` not in logs

**Causes**:
- Exception during initialization
- Settings database corrupted
- Permission issue with settings.db

**Solutions**:
```bash
# 1. Check for errors in logs
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer -n 100 | tail -50"

# 2. Check if settings.db exists and is readable
ssh pi@192.168.1.225 "ls -la /home/pi/PianoLED-CoPilot/backend/settings.db"

# 3. Verify permissions
ssh pi@192.168.1.225 "sudo chown pi:pi /home/pi/PianoLED-CoPilot/backend/settings.db"
ssh pi@192.168.1.225 "sudo chmod 644 /home/pi/PianoLED-CoPilot/backend/settings.db"

# 4. Restart
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
```
- [ ] Checked logs for specific error
- [ ] Fixed permissions if needed
- [ ] Service started successfully

### API Not Responding

**Problem**: `curl` times out or connection refused

**Causes**:
- Service not fully started
- Service crashed during initialization
- Port 5001 blocked

**Solutions**:
```bash
# 1. Check if service is running
ssh pi@192.168.1.225 "sudo systemctl status piano-led-visualizer"

# 2. If not running, try manual start
ssh pi@192.168.1.225 "cd /home/pi/PianoLED-CoPilot/backend && source venv/bin/activate && python3 app.py 2>&1 | head -50"

# 3. Check port
ssh pi@192.168.1.225 "netstat -tlnp | grep 5001"

# 4. Wait longer for service to start (it does startup animation)
sleep 10
curl http://192.168.1.225:5001/api/midi-input/status
```
- [ ] Service is running
- [ ] Port 5001 is listening
- [ ] API responding

### Settings Not Persisting After Restart

**Problem**: Changed setting, restarted, old value came back

**Causes**:
- Singleton still has old `_initialized` flag
- Settings database not being read
- Configuration cache issue

**Solutions**:
```bash
# 1. Force complete cleanup
ssh pi@192.168.1.225 "pkill -9 -f 'python.*app.py'; pkill -9 -f 'python.*start.py'"
sleep 3

# 2. Clear cache
ssh pi@192.168.1.225 "cd /home/pi/PianoLED-CoPilot && find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null"

# 3. Restart fresh
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 5

# 4. Test again
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.8}'
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer"
sleep 3
curl http://192.168.1.225:5001/api/settings/led
```
- [ ] Killed old processes
- [ ] Cleared cache
- [ ] Restarted cleanly
- [ ] Setting now persists

## Additional Resources

- See DEPLOY_LED_FIX.md for more detailed troubleshooting
- See SINGLETON_PATTERN_EXPLANATION.md to understand the bug
- See DOCUMENTATION_INDEX.md for all available guides

## Approval & Sign-Off

Once all checks pass:
- [ ] System is working correctly
- [ ] Fix is verified
- [ ] Ready for production use
- [ ] Documented and tested

**Date Deployed**: ___________
**Deployed By**: ___________
**Status**: ✅ Ready for Use

