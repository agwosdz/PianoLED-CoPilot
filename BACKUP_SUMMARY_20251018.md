# Piano LED Configuration Backup - October 18, 2025

## ✅ Backup Created Successfully

**Backup File**: `piano_settings_backup_20251018.json`  
**Date**: October 18, 2025 @ 01:40:55 UTC  
**Piano**: Raspberry Pi @ 192.168.1.225  

---

## 📊 Configuration Summary

### LED Configuration
- **LED Count**: 255 LEDs total
- **LED Type**: WS2812B (addressable RGB)
- **GPIO Pin**: 19 (data)
- **Brightness**: 0.8 (80%)
- **Orientation**: Normal
- **LEDs per Meter**: 200
- **Update Rate**: 30 Hz

### Calibration Settings
- **Start LED**: 4
- **End LED**: 250
- **Global Offset**: 0
- **Distribution Mode**: Physics-Based LED Detection
- **Fixed LEDs per Key**: 3
- **Calibration Mode**: None

### Weld Offsets
- **Current Status**: 0 welds configured
- **led_weld_offsets**: {} (empty)

### Key Offsets (Per-Key Fine-Tuning)
```
Key 30:  +1 LED
Key 39:  -1 LED
Key 42:  +1 LED
Key 48:  +1 LED
Key 49:  -1 LED
Key 53:  +1 LED
Key 65:  +1 LED
Key 66:  -1 LED
Key 68:  +1 LED
Key 72:  +1 LED
Key 75:  -1 LED
Key 81:  +1 LED
Key 89:  +1 LED
Key 90:  -1 LED
Key 91:  -1 LED
Key 92:  +1 LED
Key 94:  +1 LED
```

### Piano Settings
- **Piano Size**: 88-key
- **Start Note**: A0
- **End Note**: C8
- **Key Mapping Mode**: Chromatic

### Power & Thermal
- **Power Limiting**: Enabled
- **Max Power**: 50W
- **Thermal Protection**: Enabled
- **Max Temperature**: 70°C

### Colors
- **White Key Color**: RGB(0, 100, 150) - Cyan
- **Black Key Color**: RGB(150, 0, 100) - Magenta
- **White Key Gap**: 1.0mm
- **White Key Width**: 22.0mm
- **Black Key Width**: 12.0mm

### Piano Geometry
- **Preset**: Standard
- **White Key Height**: 107.0mm
- **White Key Width**: 23.5mm
- **White Key Gap**: 1.0mm
- **Black Key Width**: 13.7mm
- **Black Key Height**: 60.0mm
- **Black Key Depth**: 20.0mm

### MIDI & Hardware
- **MIDI Auto-detect**: Enabled
- **GPIO Auto-detect**: Enabled
- **LED Auto-detect**: Enabled
- **rtpMIDI**: Disabled

### UI & Performance
- **Theme**: Dark
- **Performance Mode**: Balanced
- **Auto Save**: Enabled
- **Debug**: False
- **Log Level**: INFO

---

## 🔄 How to Restore

### Method 1: Via REST API
```bash
curl -X POST http://192.168.1.225:5001/api/settings/import \
  -H "Content-Type: application/json" \
  -d @piano_settings_backup_20251018.json
```

### Method 2: Copy Settings File to Pi
```bash
scp piano_settings_backup_20251018.json pi@192.168.1.225:/home/pi/
ssh pi@192.168.1.225 "python3 -c \"
from backend.services.settings_service import SettingsService
import json

with open('piano_settings_backup_20251018.json', 'r') as f:
    data = json.load(f)

service = SettingsService()
service.import_settings(data['settings'])
print('✓ Settings restored')
\""
```

### Method 3: Manual Database Restore
```bash
# Backup current database
ssh pi@192.168.1.225 "cp backend/settings.db backend/settings.db.backup"

# Restore from settings file
ssh pi@192.168.1.225 "python3 << 'EOF'
from backend.services.settings_service import SettingsService
import json

with open('piano_settings_backup_20251018.json') as f:
    backup = json.load(f)

service = SettingsService()
for category, settings in backup['settings'].items():
    for key, value in settings.items():
        service.set_setting(category, key, value)
        
print('✓ All settings restored')
EOF
"
```

---

## 📋 What's Backed Up

✅ **All Settings Categories**:
- Accessibility (a11y)
- Audio
- Calibration (includes weld offsets)
- GPIO
- Hardware
- Help/UI
- History
- LED
- Piano
- Piano Geometry
- System
- UI
- Upload
- User

✅ **Critical Configuration**:
- LED mapping and calibration
- Key-to-LED assignments
- Per-key offsets
- Weld configurations (currently empty)
- Color schemes
- Hardware pins and settings

---

## 🎯 Quick Reference: Key Values

| Setting | Value |
|---------|-------|
| Total LEDs | 255 |
| Usable Range | 4 to 250 |
| Brightness | 80% |
| Key Offsets | 17 keys adjusted |
| Weld Offsets | 0 configured |
| Last Calibration | Oct 18, 01:40:12 |
| Piano Size | 88-key |
| GPIO Pin | 19 |
| Power Limit | 50W |
| Max Temp | 70°C |

---

## 📝 Next Steps

### If You Want to Add Weld Offsets:

1. **Measure** weld locations on your LED strips
   ```bash
   # Use calipers to measure deviation at solder joints
   # Record: LED index and offset in mm
   ```

2. **Configure via API**:
   ```bash
   curl -X PUT http://192.168.1.225:5001/api/calibration/weld/offsets/bulk \
     -H "Content-Type: application/json" \
     -d '{
       "weld_offsets": {
         "100": 3.5,
         "200": -1.0
       }
     }'
   ```

3. **Backup again**:
   ```bash
   curl -s http://192.168.1.225:5001/api/settings/export | \
     python3 -m json.tool > piano_settings_with_welds.json
   ```

### To Use This as Template for Other Pianos:

1. **Copy this backup file**:
   ```bash
   cp piano_settings_backup_20251018.json another_piano_template.json
   ```

2. **Modify as needed** (LED count, pins, etc.)

3. **Restore to new piano**:
   ```bash
   curl -X POST http://new-pi:5001/api/settings/import \
     -H "Content-Type: application/json" \
     -d @another_piano_template.json
   ```

---

## 🔐 File Location

**Local Backup**: `h:\Development\Copilot\PianoLED-CoPilot\piano_settings_backup_20251018.json`

**To Keep Multiple Versions**:
```bash
# Backup with date/time
cp piano_settings_backup_20251018.json \
   backups/piano_settings_$(date +%Y%m%d_%H%M%S).json
```

---

## 📞 Recovery Checklist

If you need to recover:

- [ ] File location: `piano_settings_backup_20251018.json`
- [ ] Date backed up: October 18, 2025
- [ ] Contains: All 14 setting categories
- [ ] Includes weld offsets: No (empty)
- [ ] Includes key offsets: Yes (17 keys)
- [ ] Test restore: Use Method 1 above
- [ ] Verify after restore:
  ```bash
  ssh pi@192.168.1.225 "curl http://localhost:5001/api/calibration/key-led-mapping | \
    python3 -c \"import sys,json; d=json.load(sys.stdin); \
    print(f'Mapping restored: {len(d[\\\"key_to_led\\\"])} keys')\""
  ```

---

**Backup Complete! ✅**  
*Your piano LED configuration is now safely backed up and can be restored anytime.*
