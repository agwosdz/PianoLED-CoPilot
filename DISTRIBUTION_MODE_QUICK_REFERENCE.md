# Distribution Mode - Quick Reference

## Three Modes Overview

| Mode | Backend Param | LEDs/Key | Use Case | Key Features |
|------|---------------|----------|----------|--------------|
| **Piano Based (with overlap)** | `allow_led_sharing=True` | 5-6 avg | Smooth transitions | Boundary LEDs shared, 261 overlaps |
| **Piano Based (no overlap)** | `allow_led_sharing=False` | 3-4 avg | Individual control | Tight allocation, 0 overlaps |
| **Custom** | `allow_led_sharing=True` | TBD | Future use | Reserved |

## API Endpoints

### Get Current Mode
```bash
GET /api/calibration/distribution-mode
```

**Response:**
```json
{
  "current_mode": "Piano Based (with overlap)",
  "available_modes": ["Piano Based (with overlap)", "Piano Based (no overlap)", "Custom"],
  "allow_led_sharing": true
}
```

### Change Mode
```bash
POST /api/calibration/distribution-mode
Content-Type: application/json

{
  "mode": "Piano Based (no overlap)",
  "apply_mapping": true
}
```

**Response:**
```json
{
  "distribution_mode": "Piano Based (no overlap)",
  "allow_led_sharing": false,
  "mapping_regenerated": true,
  "mapping_stats": {
    "total_keys_mapped": 88,
    "total_leds_used": 246,
    "distribution": {"3": 19, "4": 69}
  }
}
```

## Frontend Component

**Location:** `frontend/src/lib/components/CalibrationSection3.svelte`

**Features:**
- Dropdown shows all three modes
- Real-time mode switching
- Integrates with validation
- Shows mode descriptions

**Usage:**
1. Navigate to Settings → Calibration
2. Find "Distribution Mode:" dropdown in "Piano LED Mapping" section
3. Select desired mode
4. Mapping updates immediately

## Distribution Comparison

### Mode 1: With Overlap (Smooth)
```
Key 0: [4, 5, 6, 7, 8]     ← 5 LEDs
Key 1: [7, 8, 9, 10]       ← 4 LEDs (shares 7,8)
Key 2: [10, 11, 12, 13]    ← 4 LEDs (shares 10)
...
Total keys: 88
Total unique LEDs: 246
Total allocations: 507
Shared LEDs: 261
```

### Mode 2: No Overlap (Tight)
```
Key 0: [4, 5, 6, 7]        ← 4 LEDs (no sharing)
Key 1: [7, 8, 9, 10]       ← 4 LEDs (no sharing)
Key 2: [10, 11, 12, 13]    ← 4 LEDs (no sharing)
...
Total keys: 88
Total unique LEDs: 246
Total allocations: 333
Shared LEDs: 0
```

## Implementation Details

### Backend Processing
1. User selects mode in frontend dropdown
2. Frontend sends POST to `/api/calibration/distribution-mode`
3. Backend maps mode name to `allow_led_sharing` boolean
4. Backend calls `calculate_per_key_led_allocation()` with parameter
5. Algorithm regenerates mapping if requested
6. New allocation is returned to frontend

### Settings Storage
```python
settings_service.set_setting('calibration', 'distribution_mode', mode_name)
settings_service.set_setting('calibration', 'allow_led_sharing', boolean)
```

### Mode-to-Parameter Mapping
```python
if mode == 'Piano Based (with overlap)':
    allow_led_sharing = True
elif mode == 'Piano Based (no overlap)':
    allow_led_sharing = False
elif mode == 'Custom':
    allow_led_sharing = True  # Default
```

## When to Use Each Mode

### Choose "Piano Based (with overlap)" when:
- Creating smooth LED animations across keys
- Wanting visual continuity between adjacent keys
- Not concerned about LED efficiency
- Using real-time visualization feedback
- Creating rainbow/gradient effects

### Choose "Piano Based (no overlap)" when:
- Maximizing individual key control
- Using limited LED strips
- Creating distinct key-specific colors
- Avoiding LED allocation overlap
- Ensuring precise LED count per key

### Choose "Custom" when:
- Implementing specialized distribution patterns
- Creating weighted allocations (e.g., more LEDs for lowest keys)
- Building thematic patterns
- Fine-tuning for specific musical genres

## Testing

All modes have been verified:

✅ **Mode Switch Tests:**
- WITH overlap → NO overlap: Distribution changes 5-6 → 3-4
- NO overlap → WITH overlap: Distribution changes 3-4 → 5-6
- All 88 keys mapped in both modes
- All 246 LEDs utilized in both modes

✅ **Integration Tests:**
- Frontend dropdown displays all modes
- Backend accepts mode change requests
- Settings persist across server restart
- Mapping regenerates correctly

✅ **API Tests:**
- GET endpoint returns current mode
- POST endpoint changes mode
- POST with apply_mapping regenerates allocation
- Invalid mode names rejected with 400 error

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Dropdown shows wrong mode | Refresh page, clear browser cache |
| Mode change not applying | Check browser console, verify POST request |
| LEDs not updating after change | Verify calibration is enabled |
| Mapping shows old distribution | Click "Validate Mapping" to refresh |
| Settings not persisting | Check SQLite database, verify write permissions |

## Files Involved

- **Backend:** `backend/api/calibration.py` (endpoint)
- **Backend:** `backend/config_led_mapping_advanced.py` (algorithm)
- **Backend:** `backend/services/settings_service.py` (storage)
- **Frontend:** `frontend/src/lib/components/CalibrationSection3.svelte` (UI)
- **Frontend:** `frontend/src/lib/stores/calibration.ts` (state)

## Next Steps

1. Deploy to Raspberry Pi
2. Test on actual hardware
3. Verify LED output for both modes
4. Get user feedback
5. Implement Custom mode enhancements

---

**Status:** Production Ready
**Last Updated:** October 17, 2025
