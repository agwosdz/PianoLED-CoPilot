# Getting Weld Offsets into Configuration

## Overview

There are **multiple ways** to get weld offsets into your system. Choose the method that best fits your workflow:

1. **REST API** (Recommended for users) - Easiest, real-time updates
2. **Settings Export/Import** - Backup and restore configurations
3. **Direct SQLite** - Advanced, direct database access
4. **Config JSON** - File-based configuration
5. **Bulk Scripts** - Programmatic setup

---

## Method 1: REST API (Recommended ✨)

### Quickest Way to Add Welds

```bash
# Add a single weld at LED 100 with 3.5mm offset
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5}'

# Response:
# {
#   "success": true,
#   "message": "Weld offset updated",
#   "led_index": 100,
#   "offset_mm": 3.5
# }
```

### Add Multiple Welds (Bulk)

```bash
# Add multiple welds in one request
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "150": -1.0,
      "200": 2.0
    }
  }'

# Response:
# {
#   "success": true,
#   "message": "Bulk operation completed",
#   "created": 0,
#   "updated": 3,
#   "total": 3
# }
```

### Validate Before Saving

```bash
# Pre-validate configuration without committing
curl -X POST http://localhost:5001/api/calibration/weld/validate \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "150": -1.0,
      "200": 2.0
    }
  }'

# Response:
# {
#   "valid": true,
#   "warnings": [],
#   "errors": [],
#   "statistics": {
#     "weld_count": 3,
#     "average_offset": 1.5,
#     "max_offset": 3.5,
#     "min_offset": -1.0
#   }
# }
```

### Get Current Welds

```bash
# List all configured welds
curl http://localhost:5001/api/calibration/weld/offsets

# Response:
# {
#   "success": true,
#   "weld_offsets": {
#     "100": 3.5,
#     "150": -1.0,
#     "200": 2.0
#   },
#   "count": 3,
#   "statistics": {...}
# }
```

### Python Helper Script

```python
#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:5001/api/calibration/weld"

class WeldManager:
    def add_weld(self, led_index: int, offset_mm: float):
        """Add or update a weld"""
        url = f"{BASE_URL}/offset/{led_index}"
        data = {"offset_mm": offset_mm}
        response = requests.post(url, json=data)
        return response.json()
    
    def add_multiple(self, welds: dict):
        """Add multiple welds: {led_index: offset_mm, ...}"""
        url = f"{BASE_URL}/offsets/bulk"
        data = {"weld_offsets": welds}
        response = requests.put(url, json=data)
        return response.json()
    
    def get_all(self):
        """Get all configured welds"""
        url = f"{BASE_URL}/offsets"
        response = requests.get(url)
        return response.json()
    
    def validate(self, welds: dict):
        """Pre-validate configuration"""
        url = f"{BASE_URL}/validate"
        data = {"weld_offsets": welds}
        response = requests.post(url, json=data)
        return response.json()
    
    def delete_weld(self, led_index: int):
        """Delete a specific weld"""
        url = f"{BASE_URL}/offset/{led_index}"
        response = requests.delete(url)
        return response.json()
    
    def clear_all(self):
        """Clear all welds"""
        url = f"{BASE_URL}/offsets"
        response = requests.delete(url)
        return response.json()

# Usage example
if __name__ == "__main__":
    manager = WeldManager()
    
    # Add welds
    result = manager.add_multiple({
        100: 3.5,
        200: -1.0,
        250: 2.0
    })
    print("Added welds:", result)
    
    # Get all
    all_welds = manager.get_all()
    print("Current welds:", all_welds)
```

---

## Method 2: Settings Export/Import

### Export Current Settings (Including Welds)

```bash
# Export all settings to JSON
curl http://localhost:5001/api/settings \
  -H "Accept: application/json" > my_config.json

# The exported file includes:
# {
#   "calibration": {
#     "led_weld_offsets": {
#       "100": 3.5,
#       "150": -1.0,
#       "200": 2.0
#     },
#     ...other calibration settings...
#   }
# }
```

### Create Config File with Welds

```json
{
  "calibration": {
    "led_weld_offsets": {
      "100": 3.5,
      "150": -1.0,
      "200": 2.0
    },
    "key_offsets": {21: 1, 22: -1},
    "global_offset": 0
  },
  "piano": {
    "piano_size": "88-key"
  }
}
```

### Import Settings

```bash
# Import from file
curl -X POST http://localhost:5001/api/settings/import \
  -H "Content-Type: application/json" \
  -d @my_config.json

# Or via form data
curl -X POST http://localhost:5001/api/settings/import \
  -F "file=@my_config.json"
```

### Python Export/Import

```python
from backend.services.settings_service import SettingsService

settings_service = SettingsService()

# Export
exported = settings_service.export_settings()
print(json.dumps(exported, indent=2))

# Save to file
with open("config_backup.json", "w") as f:
    json.dump(exported, f, indent=2)

# Import from file
with open("config_backup.json", "r") as f:
    config = json.load(f)

settings_service.import_settings(config)
```

---

## Method 3: Direct SQLite Access

### View Settings Database

```bash
# Connect to SQLite database
sqlite3 backend/settings.db

# View all weld offsets
SELECT category, key, value FROM settings 
WHERE category = 'calibration' 
AND key = 'led_weld_offsets';

# View all settings
SELECT * FROM settings;
```

### Insert/Update Welds Directly

```sql
-- Insert weld offsets
INSERT INTO settings (category, key, value, type, description)
VALUES ('calibration', 'led_weld_offsets', 
  '{"100": 3.5, "150": -1.0, "200": 2.0}', 
  'object', 
  'LED weld offsets')
ON CONFLICT(category, key) 
DO UPDATE SET value = excluded.value;

-- Verify
SELECT value FROM settings 
WHERE category = 'calibration' 
AND key = 'led_weld_offsets';
```

### Python Direct Database Access

```python
import sqlite3
import json
from pathlib import Path

db_path = Path("backend/settings.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current welds
cursor.execute("""
  SELECT value FROM settings 
  WHERE category = 'calibration' 
  AND key = 'led_weld_offsets'
""")
result = cursor.fetchone()
current_welds = json.loads(result[0]) if result else {}

# Add new weld
current_welds[100] = 3.5
current_welds[200] = -1.0

# Update database
cursor.execute("""
  INSERT INTO settings (category, key, value, type)
  VALUES ('calibration', 'led_weld_offsets', ?, 'object')
  ON CONFLICT(category, key) 
  DO UPDATE SET value = excluded.value
""", (json.dumps(current_welds),))

conn.commit()
conn.close()
```

---

## Method 4: Config JSON File

### Add to config.json (Legacy)

The newer settings service uses SQLite, but you can still use config.json:

```json
{
  "led_count": 254,
  "brightness": 0.5,
  "led_weld_offsets": {
    "100": 3.5,
    "200": -1.0,
    "250": 2.0
  }
}
```

**Note**: This method is for reference. The current system uses the Settings Service with SQLite for persistence.

---

## Method 5: Bulk Configuration Script

### Setup Multiple Welds from Measurements

```python
#!/usr/bin/env python3
"""
Bulk weld configuration from measurements file.
Usage: python setup_welds.py measurements.txt
"""

import sys
import json
import requests

def parse_measurements(filename):
    """Parse measurements file
    
    Format:
    # LED strip measurements (mm from start)
    100, 3.5
    150, -1.0
    200, 2.0
    """
    welds = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = [p.strip() for p in line.split(',')]
            if len(parts) == 2:
                try:
                    led_idx = int(parts[0])
                    offset = float(parts[1])
                    welds[led_idx] = offset
                except ValueError:
                    print(f"Skipping invalid line: {line}")
    
    return welds

def configure_welds(welds):
    """Configure welds via API"""
    url = "http://localhost:5001/api/calibration/weld/offsets/bulk"
    
    data = {"weld_offsets": welds}
    response = requests.put(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Successfully configured {result['total']} welds")
        print(f"  Created: {result['created']}")
        print(f"  Updated: {result['updated']}")
        return True
    else:
        print(f"✗ Failed to configure welds: {response.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_welds.py <measurements_file>")
        sys.exit(1)
    
    measurements_file = sys.argv[1]
    welds = parse_measurements(measurements_file)
    
    print(f"Parsed {len(welds)} welds from {measurements_file}")
    print(json.dumps(welds, indent=2))
    
    configure_welds(welds)
```

### Example Measurements File

```
# LED Strip Weld Measurements
# Format: led_index, offset_mm
# Measured with calipers at each solder joint

# First joint (100-110 range)
105, 3.5

# Second joint (195-210 range)
205, -1.0

# Third joint (250-260 range)
255, 2.0
```

### Usage

```bash
python setup_welds.py measurements.txt
```

---

## Integration with Calibration Workflow

### Complete Calibration Flow

```
1. Start backend server
   └─> Settings Service initializes
   └─> Creates SQLite database if needed
   └─> Loads default settings (including led_weld_offsets: {})

2. Measure weld locations and offsets
   └─> Use calipers to measure deviation at each solder joint
   └─> Record LED index and offset in mm

3. Configure welds (via REST API)
   └─> POST /api/calibration/weld/offset/{led}
   └─> Settings Service updates SQLite
   └─> WebSocket broadcasts change event

4. Verify in LED mapping
   └─> GET /api/calibration/key-led-mapping
   └─> Returns mapping with weld compensation applied

5. Test on hardware
   └─> Connect to LED strip
   └─> Play keys and verify alignment

6. Export configuration
   └─> POST /api/settings/export
   └─> Save to file for backup/transfer
```

---

## Verification

### Check Welds Are Applied

```bash
# 1. Verify welds are stored
curl http://localhost:5001/api/calibration/weld/offsets | jq

# 2. Verify mapping includes welds
curl http://localhost:5001/api/calibration/key-led-mapping | jq '.key_to_led | .[0:5]'

# 3. Check in database
sqlite3 backend/settings.db "SELECT value FROM settings WHERE key='led_weld_offsets';"
```

### Example Output

```bash
# Step 1: Welds stored ✓
{
  "success": true,
  "weld_offsets": {
    "100": 3.5,
    "200": -1.0
  },
  "count": 2
}

# Step 2: Mapping applied ✓
{
  "key_to_led": {
    "0": [0, 1, 2],      # Key A0
    "1": [3, 4, 5],      # Key A#0
    ...
    "21": [100, 101],    # Key C3 (adjusted for weld at 100)
    ...
  }
}

# Step 3: Database ✓
{"100": 3.5, "200": -1.0}
```

---

## Comparison: Which Method?

| Method | Use Case | Ease | Speed | Notes |
|--------|----------|------|-------|-------|
| **REST API** | User configuration | ★★★★★ | Real-time | Best for live adjustment |
| **Export/Import** | Backup/restore | ★★★★☆ | One-time | Best for migration |
| **Direct SQLite** | Advanced debugging | ★★☆☆☆ | Direct | For troubleshooting |
| **Config JSON** | Legacy/reference | ★★★☆☆ | Static | Historical, less used |
| **Bulk Script** | Mass configuration | ★★★★☆ | Batch | Best for initial setup |

---

## Troubleshooting

### Welds Not Appearing in Mapping

```bash
# 1. Check welds are stored
curl http://localhost:5001/api/calibration/weld/offsets
# Should show your welds

# 2. Check settings service is running
curl http://localhost:5001/api/settings
# Should return all settings

# 3. Force mapping recalculation
curl -X POST http://localhost:5001/api/calibration/regenerate-mapping

# 4. Check logs
tail -f backend.log | grep -i weld
```

### Invalid Offset Error

```bash
# Error: "Offset must be between -10.0 and +10.0 mm"
# Solution: Use value in valid range
curl -X POST http://localhost:5001/api/calibration/weld/offset/100 \
  -H "Content-Type: application/json" \
  -d '{"offset_mm": 3.5}'  # Must be -10 to +10
```

### Database Locked Error

```bash
# Problem: SQLite database locked
# Solution: Wait for write operation to complete

# Check current connections
lsof backend/settings.db

# Or restart backend service
# (closes all connections)
```

### Settings Not Persisting

```bash
# Problem: Welds reset after restart
# Solution: Verify SQLite is being used

# Check database exists
ls -la backend/settings.db

# Verify settings are in DB
sqlite3 backend/settings.db "SELECT * FROM settings LIMIT 5;"

# Check permissions
chmod 666 backend/settings.db
```

---

## Complete Example: 3-Segment Strip Setup

### Scenario
You have 3 LED strips soldered together:
- Strip 1: LEDs 0-99
- Weld at 100 (3.5mm forward)
- Strip 2: LEDs 100-199  
- Weld at 200 (1.0mm backward)
- Strip 3: LEDs 200-254

### Step 1: Measure

```
Physical measurements:
- Weld at ~LED 100: +3.5mm forward
- Weld at ~LED 200: -1.0mm backward
```

### Step 2: Configure via API

```bash
# Configure both welds
curl -X PUT http://localhost:5001/api/calibration/weld/offsets/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "weld_offsets": {
      "100": 3.5,
      "200": -1.0
    }
  }'

# Response: success
```

### Step 3: Verify

```bash
# Check welds are stored
curl http://localhost:5001/api/calibration/weld/offsets
# {"weld_offsets": {"100": 3.5, "200": -1.0}, "count": 2}

# Check mapping was updated
curl http://localhost:5001/api/calibration/key-led-mapping | \
  python3 -c "import sys, json; d=json.load(sys.stdin); \
  print('LED mapping with welds applied:')"
```

### Step 4: Export for Backup

```bash
# Export configuration
curl http://localhost:5001/api/settings > my_piano_config.json

# Can restore later with:
curl -X POST http://localhost:5001/api/settings/import \
  -H "Content-Type: application/json" \
  -d @my_piano_config.json
```

---

## Next Steps

1. **REST API Method** (Recommended) - Start with this
2. Check `WELD_OFFSET_FEATURE_GUIDE.md` for complete documentation
3. Check `WELD_OFFSET_VISUAL_GUIDE.md` for diagrams
4. Review endpoint details in `backend/api/calibration_weld_offsets.py`
5. Test with your hardware when ready
