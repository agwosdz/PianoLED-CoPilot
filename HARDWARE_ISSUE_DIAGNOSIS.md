# Piano LED Visualizer - Hardware Issues & Solutions

## Current Status (Oct 16, 2025)

### ✅ What's Working
- Backend service running (eventlet + SocketIO configured)
- Frontend accessible (nginx proxy on port 80)
- API endpoints responding (200 OK)
- WebSocket connections stable (no more Werkzeug errors)
- MIDI input services initialized
- Settings database operational

### ❌ What's Not Working  
1. **LED Hardware Initialization** - CRITICAL
   - Error: `ws2811_init failed with code -11 (Selected GPIO not possible)`
   - Cause: GPIO pin 19 (or 12) not accessible for WS2811 library
   - Impact: No startup animation, no MIDI LED response, no calibration

2. **Hardware Test Endpoint**
   - Endpoint `/api/hardware-test/led/off` returns 503
   - Cause: LED controller not initialized (running in simulation mode)

## Root Cause Analysis

The rpi_ws281x library returns error code -11 when:
1. **GPIO Memory Access Denied** - User doesn't have /dev/mem access (but running as root)
2. **GPIO Pin Conflict** - Another process/device is using the GPIO pin
3. **Missing Device Tree Overlay** - GPIO or SPI not enabled in /boot/firmware/config.txt
4. **Hardware Not Connected** - LED strip not wired to GPIO or not powered

## Hardware Setup Check

SSH to Pi and run:
```bash
# Check if SPI/GPIO devices exist
ls -la /dev/spi* /dev/mem

# Check boot config
cat /boot/firmware/config.txt | grep -E "spi|dtoverlay|dtparam"

# Check if GPIO library can detect hardware
python3 -c "from rpi_ws281x import PixelStrip; print('rpi_ws281x loaded')"
```

## Solutions to Try (in order)

### Solution 1: Verify Hardware Connection
1. Check LED strip is physically connected to GPIO 19
2. Check LED strip has power (5V, ground)
3. Check data pin is connected to GPIO 19
4. Test with a multimeter if possible

###Solution 2: Check Device Tree Config
```bash
ssh pi@192.168.1.225
sudo nano /boot/firmware/config.txt

# Ensure these lines exist:
dtparam=spi=on
dtoverlay=gpio-ir
dtparam=gpio_pin=19

# Save (Ctrl+X, Y, Enter)
sudo reboot
```

### Solution 3: Try Different GPIO Pin
If GPIO 19 is reserved, try GPIO 18 (original rpi_ws281x default):
```bash
curl -X POST http://192.168.1.225:5001/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"led": {"gpio_pin": 18}}'

# Restart service
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer.service"
```

### Solution 4: Check for GPIO Conflicts
```bash
# SSH to Pi
ssh pi@192.168.1.225

# Check which processes are using GPIO
ps aux | grep -i gpio
ps aux | grep -i led
ps aux | grep -i ws

# Check system logs for GPIO errors
sudo journalctl -n 200 | grep -i gpio
```

### Solution 5: Reinstall rpi_ws281x Library
```bash
ssh pi@192.168.1.225
cd /home/pi/PianoLED-CoPilot
source backend/venv/bin/activate
pip uninstall rpi_ws281x -y
pip install rpi_ws281x==4.3.4 --no-cache-dir
sudo systemctl restart piano-led-visualizer.service
```

## Expected Behavior After Fix

Once GPIO initialization succeeds, you should see:
```
LED controller initialized with 255 pixels on pin 19 (freq=800000, dma=10, channel=0)
🎹 Triggering fancy startup animation...
✨ Startup animation completed successfully!
```

Then:
- ✅ Startup animation will run on boot
- ✅ LEDs will respond to MIDI input
- ✅ Calibration functions will work
- ✅ Hardware test endpoints will return 200 OK

## Status Verification Command

```bash
# Check if LEDs are enabled and initialized
curl -s http://192.168.1.225:5001/api/status | grep -A5 led

# Check for LED initialization in logs
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 50 | grep -E 'LED controller|startup animation|ws2811'"
```

## Notes

- Backend now uses eventlet async mode for stable WebSocket/SocketIO
- Frontend displays 503 errors when LED hardware unavailable
- System runs in "simulation mode" without real LED hardware
- All MIDI input logic works, just no physical LED output

## Next Steps

1. **Physical Check**: Verify LED strip is properly connected and powered
2. **Reboot Pi**: Ensure device tree overlay loaded
3. **Monitor Logs**: Watch for "LED controller initialized" message
4. **Test Hardware**: Use calibration tool to verify LED mapping
