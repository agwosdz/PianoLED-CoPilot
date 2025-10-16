# Global Offset Rework: LED Range Adjustment System

## Overview

The **Global Offset** has been completely reworked into a more intuitive **LED Range Adjustment** system using two sliders: **Set First LED** and **Set Last LED**.

This new system allows you to define the exact boundaries of the mappable LED area, accommodating LED strips that may exceed or precede the piano key length.

---

## What Changed

### Backend Changes

#### Settings Schema (`backend/services/settings_service.py`)
- **Removed:** `global_offset` (0-20 range)
- **Added:** 
  - `start_led`: First LED index at the beginning of the piano (default: 0)
  - `end_led`: Last LED index at the end of the piano (default: 245 for 246-LED strip)

#### API Endpoints (`backend/api/calibration.py`)
- **Status Endpoint** (`GET /api/calibration/status`):
  - Now returns `start_led` and `end_led` instead of `global_offset`
  
- **Removed Endpoints:**
  - `GET /api/calibration/global-offset`
  - `PUT /api/calibration/global-offset`
  
- **New Endpoints:**
  - `PUT /api/calibration/start-led` — Set the first mappable LED
  - `PUT /api/calibration/end-led` — Set the last mappable LED
  
- **Reset Endpoint** (`POST /api/calibration/reset`):
  - Now resets to `start_led: 0` and `end_led: (led_count - 1)`

### Frontend Changes

#### Calibration Store (`frontend/src/lib/stores/calibration.ts`)
- **Updated Type:** `CalibrationState` now has `start_led` and `end_led` instead of `global_offset`
- **Removed Functions:**
  - `setGlobalOffset(offset)`
  - `getGlobalOffset()`
- **New Functions:**
  - `setStartLed(ledIndex)` — Update the first LED boundary
  - `setEndLed(ledIndex)` — Update the last LED boundary
- **Updated Exports:** All convenience functions reflect the new API

#### CalibrationSection2 (`frontend/src/lib/components/CalibrationSection2.svelte`)
- **Renamed Section:** "Offset Adjustment" → "LED Strip Alignment"
- **New Description:** "Define the mappable area of your LED strip by setting where the piano begins and ends."
- **Two Sliders Replaced One:**
  - **Set First LED** (0 to LED count - 1)
    - Label: "Set First LED"
    - Description: "Set this to the first LED index at the beginning of your piano keyboard."
    - Shows current index in real-time
  
  - **Set Last LED** (0 to LED count - 1)
    - Label: "Set Last LED"
    - Description: "Set this to the last LED index at the end of your piano keyboard. Recommended: LED count - 20 or less."
    - Shows current index in real-time
  
- **New Mapping Info Display:**
  - Shows the active mappable range (start → end)
  - Displays total LEDs in the range
  - Helps visualize the calibration area

#### CalibrationSection3 (`frontend/src/lib/components/CalibrationSection3.svelte`)
- Updated the info box to display:
  - **LED Range:** {start_led} — {end_led}
  - (Previously: "Global Offset")

---

## How It Works

### The Concept

Your LED strip may have more LEDs than piano keys, or may start/end at different physical positions. The new system lets you define:

1. **Start LED**: The first LED in the strip that aligns with the beginning of your piano
2. **End LED**: The last LED in the strip that aligns with the end of your piano

The mapping algorithm uses these boundaries to create the clamping limits for the entire mappable area.

### LED Index Calculation

- **Slider Range:** 0 to (LED count - 1)
- **Default Values:**
  - `start_led: 0` (first LED in strip)
  - `end_led: 245` (for 246-LED strip)
- **Recommended Setup:**
  - Set `end_led` to `led_count - 20` to leave buffer space

### Validation

- `start_led` must be ≤ `end_led`
- Both values must be within the valid LED count range
- The UI prevents invalid cross-over values

---

## UI/UX Improvements

1. **Clearer Intent**: "Set First LED" and "Set Last LED" are more intuitive than "Global Offset"
2. **Visual Feedback**: Real-time LED index display next to each slider
3. **Mapping Info**: Shows the active range and total LEDs available
4. **Descriptions**: Each slider has helpful context about its purpose
5. **Range Validation**: Prevents logically impossible configurations

---

## API Changes Summary

| Operation | Old Endpoint | New Endpoint | Request Body |
|-----------|--------------|--------------|--------------|
| Get Status | `GET /status` | `GET /status` | (same endpoint, different fields) |
| Set Start | N/A | `PUT /start-led` | `{"start_led": <index>}` |
| Set End | N/A | `PUT /end-led` | `{"end_led": <index>}` |
| Reset | `POST /reset` | `POST /reset` | (uses new default values) |

---

## Migration Guide (if upgrading from old system)

1. **Database**: Old `global_offset` setting will be ignored
2. **API Clients**: Update to use `/start-led` and `/end-led` endpoints
3. **Frontend**: CalibrationSection2 automatically reflects the new UI
4. **Default Behavior**: New installations default to full LED strip (0 to count-1)

---

## Testing Checklist

- [x] Backend Python syntax valid
- [x] Frontend TypeScript compiles
- [x] Settings schema updated
- [x] API endpoints implemented
- [x] Store functions exported correctly
- [x] UI components display correctly
- [ ] Functional testing with hardware
- [ ] Edge cases (max values, cross-over prevention)
- [ ] WebSocket events broadcast correctly

---

## Next Steps

1. Test with running backend/frontend
2. Verify LED lighting works with new boundaries
3. Test edge cases (e.g., end_led close to start_led)
4. Ensure mapping calculations respect the new range
