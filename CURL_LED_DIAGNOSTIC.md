# LED Settings API Diagnostic Guide

## Issue
Getting `{"error":"Internal Server Error","message":"Failed to set setting \"led.enabled\""}` when trying to enable LEDs via curl.

## Solution Steps

### Step 1: Test GET (Read) First
```bash
curl http://192.168.1.225:5001/api/settings/led/enabled
```

Expected response: `true`

If this works, the settings API is accessible.

### Step 2: Test Setting a Different Property
```bash
curl -X PUT http://192.168.1.225:5001/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.5}'
```

Expected response: `{"message":"Setting updated successfully"}`

This tells us if it's specific to the 'enabled' key or a general issue.

### Step 3: Test with Verbose Output
```bash
curl -v -X PUT http://192.168.1.225:5001/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": true}'
```

Look for the actual HTTP response and body.

### Step 4: Check Backend Logs
```bash
ssh user@192.168.1.225
tail -100 /var/log/piano-led-visualizer.log
```

Or if running directly:
```bash
systemctl status piano-led-visualizer
journalctl -u piano-led-visualizer -n 50
```

### Step 5: Check Database Directly on Pi
```bash
ssh user@192.168.1.225
sqlite3 ~/piano-led-visualizer/backend/settings.db "SELECT * FROM settings WHERE category='led' AND key='enabled'"
```

Expected output: `1|led|enabled|true|boolean|...|...`

### Step 6: Try with Different Data Types
```bash
# Try as string
curl -X PUT http://192.168.1.225:5001/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": "true"}'

# Try as number (0 or 1)
curl -X PUT http://192.168.1.225:5001/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": 1}'
```

### Step 7: Restart Backend Service
If none of the above work, restart:
```bash
ssh user@192.168.1.225
systemctl restart piano-led-visualizer

# Wait 5 seconds, then test again
sleep 5
curl http://192.168.1.225:5001/api/settings/led/enabled
```

## Common Issues and Fixes

### Issue: "Connection refused"
**Solution:** Backend not running or port 5001 not accessible
```bash
# Check if running
ssh user@192.168.1.225 systemctl status piano-led-visualizer

# Start if not running
ssh user@192.168.1.225 systemctl start piano-led-visualizer
```

### Issue: "400 Bad Request"
**Solution:** JSON syntax error
```bash
# Make sure JSON is valid
echo '{"value": true}' | jq .

# Should output: { "value": true }
```

### Issue: "404 Not Found"
**Solution:** Wrong endpoint path
```bash
# Correct path format:
# /api/settings/<category>/<key>

# Right:
/api/settings/led/enabled
/api/settings/led/brightness
/api/settings/calibration/start_led

# Wrong:
/api/settings (missing category/key)
/api/settings/led (missing key)
/api/settings led enabled (spaces, not slashes)
```

### Issue: "500 Internal Server Error"
**Solutions:**
1. Backend exception - check logs:
   ```bash
   ssh user@192.168.1.225 journalctl -u piano-led-visualizer -n 100
   ```

2. Database locked:
   ```bash
   ssh user@192.168.1.225 lsof | grep settings.db
   # Kill if multiple processes have it open
   ```

3. Validation error - try alternate format:
   ```bash
   # Try with explicit type
   curl -X PUT http://192.168.1.225:5001/api/settings/led/enabled \
     -H "Content-Type: application/json" \
     -d '{"value": 1}'  # 1 for true, 0 for false
   ```

## Quick Test Suite

Run this bash script to test all at once:

```bash
#!/bin/bash
PI="192.168.1.225"
PORT="5001"

echo "=== LED Settings API Test Suite ==="
echo ""

# Test 1: GET LED enabled
echo "[1] GET LED enabled status"
curl -s http://$PI:$PORT/api/settings/led/enabled
echo ""

# Test 2: GET all LED settings
echo "[2] GET all LED settings"
curl -s http://$PI:$PORT/api/settings/led | jq .
echo ""

# Test 3: PUT LED brightness
echo "[3] PUT LED brightness to 0.8"
curl -s -X PUT http://$PI:$PORT/api/settings/led/brightness \
  -H "Content-Type: application/json" \
  -d '{"value": 0.8}'
echo ""

# Test 4: PUT LED enabled TRUE
echo "[4] PUT LED enabled to true"
curl -s -X PUT http://$PI:$PORT/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": true}'
echo ""

# Test 5: Verify enabled is true
echo "[5] Verify LED enabled is now true"
curl -s http://$PI:$PORT/api/settings/led/enabled
echo ""

# Test 6: PUT LED enabled FALSE
echo "[6] PUT LED enabled to false"
curl -s -X PUT http://$PI:$PORT/api/settings/led/enabled \
  -H "Content-Type: application/json" \
  -d '{"value": false}'
echo ""

# Test 7: Verify enabled is false
echo "[7] Verify LED enabled is now false"
curl -s http://$PI:$PORT/api/settings/led/enabled
echo ""

echo "=== Test Suite Complete ==="
```

Save as `test_led_api.sh` and run:
```bash
chmod +x test_led_api.sh
./test_led_api.sh
```

## If Everything Fails

Contact support with:
1. Output from: `curl -v http://192.168.1.225:5001/api/settings/led/enabled`
2. Last 50 lines of: `journalctl -u piano-led-visualizer -n 50`
3. Result of: `sqlite3 ~/piano-led-visualizer/backend/settings.db "SELECT * FROM settings WHERE category='led'"`

## Alternative: Set via Web UI

If curl doesn't work, try the web UI:
1. Open browser: `http://192.168.1.225:5000` (frontend)
2. Go to Settings → LED
3. Toggle "LED Enable"
4. Save

This uses the same API but through the web interface.
