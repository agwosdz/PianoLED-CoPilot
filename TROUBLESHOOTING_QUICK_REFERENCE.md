# 🔧 LED System - Troubleshooting Quick Reference

## Common Issues & Solutions

### ❌ Problem: "LEDs are disabled in settings - running in simulation mode"

**Cause**: Database has `led.enabled = False`

**Quick Fix**:
```bash
ssh pi@192.168.1.225 "python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')
from backend.services.settings_service import SettingsService
s = SettingsService()
s.set_setting('led', 'enabled', True)
print('LEDs enabled')
PYEOF
"

# Restart service
ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer.service"
```

**Verification**:
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 3 --no-pager | grep -i 'initialized'"
```

Expected output: `LED controller initialized with 255 pixels on pin 12`

---

### ❌ Problem: "ws2811_init failed with code -11"

**Cause**: GPIO pin conflict

**Affected Pins**: 18, 19 (have I2S/PWM conflicts on Pi Zero 2W)  
**Solution**: Use GPIO 12

**Quick Fix**:
```bash
ssh pi@192.168.1.225 "python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')
from backend.services.settings_service import SettingsService
s = SettingsService()
s.set_setting('led', 'gpio_pin', 12)
print('GPIO pin changed to 12')
PYEOF
"

ssh pi@192.168.1.225 "sudo systemctl restart piano-led-visualizer.service"
```

**Working GPIO Pins** (Pi Zero 2W):
- GPIO 12 ✅ (recommended)
- GPIO 13
- GPIO 21
- GPIO 26

---

### ❌ Problem: API endpoint returns "LED controller not initialized"

**Cause**: LED controller couldn't initialize or isn't accessible

**Quick Debug**:
```bash
# Check service status
ssh pi@192.168.1.225 "sudo systemctl status piano-led-visualizer.service"

# Check logs
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 20 --no-pager | grep -i error"

# Check settings
ssh pi@192.168.1.225 "python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')
from backend.services.settings_service import SettingsService
s = SettingsService()
print('LED enabled:', s.get_setting('led', 'enabled'))
print('GPIO pin:', s.get_setting('led', 'gpio_pin'))
print('LED count:', s.get_setting('led', 'led_count'))
PYEOF
"
```

---

### ❌ Problem: Only 1-2 LEDs respond, not all 88 keys

**Cause**: MIDI processor using wrong calibration range or mapping issue

**Quick Check**:
```bash
# Check calibration mapping
curl -s http://192.168.1.225:5001/api/calibration/mapping-info | \
  python -c "import sys, json; d = json.load(sys.stdin); print('Keys:', d['mapping_statistics']['mapped_keys'], '/ 88'); print('LEDs:', d['mapping_statistics']['leds_used'], '/ 246')"

# Check specific key mapping
curl -s http://192.168.1.225:5001/api/calibration/key-led-mapping | \
  python -c "import sys, json; d = json.load(sys.stdin); m = d.get('mapping', {}); print('MIDI 21:', m.get('21')); print('MIDI 60:', m.get('60')); print('MIDI 108:', m.get('108'))"
```

Expected:
```
Keys: 88 / 88
LEDs: 246 / 246
MIDI 21: [4, 5, 6]
MIDI 60: [121, 122, 123]
MIDI 108: [248, 249]
```

If not matching, check `backend/midi/midi_event_processor.py` calibration logic.

---

### ❌ Problem: Service won't start after reboot

**Quick Fix**:
```bash
# Check if service is running
ssh pi@192.168.1.225 "sudo systemctl status piano-led-visualizer.service"

# Start service
ssh pi@192.168.1.225 "sudo systemctl start piano-led-visualizer.service"

# Check logs
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -n 50 --no-pager"
```

Common causes:
- Port 5001 already in use
- Settings database corrupted
- Hardware not initialized on boot

---

## Testing Commands

### Test LED On
```bash
curl -X POST http://192.168.1.225:5001/api/calibration/leds-on \
  -H "Content-Type: application/json" \
  -d '{
    "leds": [
      {"index": 0, "r": 255, "g": 0, "b": 0},
      {"index": 100, "r": 0, "g": 255, "b": 0},
      {"index": 200, "r": 0, "g": 0, "b": 255}
    ]
  }'
```

### Test LED Off
```bash
curl -X POST http://192.168.1.225:5001/api/hardware-test/led/off
```

### Check Calibration Mapping
```bash
curl -s http://192.168.1.225:5001/api/calibration/mapping-info | python -m json.tool
```

### Check Key-LED Mapping
```bash
curl -s http://192.168.1.225:5001/api/calibration/key-led-mapping | python -m json.tool
```

### Check MIDI Input Status
```bash
curl -s http://192.168.1.225:5001/api/midi-input/status | python -m json.tool
```

### Live Service Logs
```bash
ssh pi@192.168.1.225 "sudo journalctl -u piano-led-visualizer.service -f"
```

---

## Critical Settings

Location: Raspberry Pi SQLite database (`settings.db`)

**Must Be Correct**:
```
led.enabled = True
led.gpio_pin = 12 (or working pin)
led.led_count = 255
led.brightness = 0.8
```

**Calibration Settings**:
```
calibration.start_led = 4
calibration.end_led = 249
```

To check all:
```bash
ssh pi@192.168.1.225 "python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')
from backend.services.settings_service import SettingsService
s = SettingsService()
for key, val in s.get_all_settings()['led'].items():
    print(f'{key}: {val}')
print('\nCalibration:')
for key, val in s.get_all_settings()['calibration'].items():
    print(f'{key}: {val}')
PYEOF
"
```

---

## Emergency Restart

```bash
# Full restart sequence
ssh pi@192.168.1.225 << 'BASH'
echo "Stopping service..."
sudo systemctl stop piano-led-visualizer.service

echo "Checking settings..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/pi/PianoLED-CoPilot')
from backend.services.settings_service import SettingsService
s = SettingsService()
print(f"LED enabled: {s.get_setting('led', 'enabled')}")
print(f"GPIO pin: {s.get_setting('led', 'gpio_pin')}")
PYEOF

echo "Starting service..."
sudo systemctl start piano-led-visualizer.service

echo "Checking status..."
sleep 2
sudo systemctl status piano-led-visualizer.service
BASH
```

---

## Success Indicators

✅ Service logs show: `LED controller initialized with 255 pixels on pin 12`

✅ Calibration info shows: `88 keys mapped, 246 LEDs used, valid: true`

✅ LED endpoints respond with HTTP 200

✅ Settings database has: `enabled=True, gpio_pin=12`

✅ No errors in `journalctl` output

---

## When All Else Fails

1. **Check hardware connection**: LED strip GPIO pin properly connected
2. **Check power**: 5V @ 10A available
3. **Check permissions**: Service runs as `root` (should be fine)
4. **Verify Python packages**: `pip list | grep rpi-ws281x`
5. **Reset database**: Delete `settings.db`, service will recreate with defaults
6. **Check syslog**: `grep piano-led /var/log/syslog | tail -20`

---

Generated: 2025-10-16  
Updated: During LED MIDI fix session
