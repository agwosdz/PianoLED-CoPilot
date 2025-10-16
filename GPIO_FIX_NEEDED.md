# GPIO Error -11: Selected GPIO Not Possible

## Issue
The LED controller is failing with:
```
ws2811_init failed with code -11 (Selected GPIO not possible)
```

This causes:
- ❌ No startup animation
- ❌ No MIDI LED response
- ❌ LED controller running in simulation mode only

## Root Cause
GPIO pin 12 is not properly initialized or unavailable on the Raspberry Pi Zero 2W.

## Solution

### Option 1: Use a Different GPIO Pin (Fastest Fix)
Change from GPIO 12 to GPIO 18 (default for WS2811):

```bash
# SSH into Pi
ssh pi@192.168.1.225

# Update the settings
curl -X POST http://localhost:5000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"led": {"gpio_pin": 18}}'
```

Then restart the service:
```bash
sudo systemctl restart piano-led-visualizer.service
```

### Option 2: Enable SPI/GPIO via Device Tree (If using specific pins)
If you must use GPIO 12, add to `/boot/firmware/config.txt`:

```ini
# Add this line at the end:
dtoverlay=gpio-ir,gpio_pin=12
# OR for PWM:
dtparam=gpiopin=12
```

Then reboot:
```bash
sudo reboot
```

### Option 3: Check Hardware Connection
Before changing GPIO, verify:
1. LED strip is properly powered (5V and GND)
2. Data line is connected to GPIO pin (currently pin 12)
3. Power supply has sufficient current (~0.5A minimum for 255 LEDs)

## Next Steps
1. Verify LED strip is physically connected and powered
2. Try Option 1 (GPIO 18 is the default and most compatible)
3. Restart the service and check logs for "LED controller initialized"

## Verification
After fix, you should see in logs:
```
LED controller initialized with 255 pixels on pin 18 (freq=800000, dma=10, channel=0)
🎹 Triggering fancy startup animation...
✨ Startup animation completed successfully!
```
