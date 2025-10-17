# Advanced Settings UI - Quick Start

## What's New?

When you select **"Physics-Based LED Detection"** from the Distribution Mode dropdown, a new **"Advanced Physics Parameters"** section appears with sliders to fine-tune your piano's keyboard geometry.

## The 5 Parameters

| Parameter | What It Controls | Typical Range |
|-----------|------------------|----------------|
| **White Key Width** | Width of white keys (mm) | 23-24.5 mm |
| **Black Key Width** | Width of black keys (mm) | 13.5-14.5 mm |
| **Key Gap** | Space between keys (mm) | 0.8-1.5 mm |
| **LED Width** | Physical width of each LED (mm) | 3-4 mm |
| **Overhang Threshold** | Sensitivity of LED-key overlap detection (mm) | 1-2 mm |

## How to Use It

### 1️⃣ Enable Physics-Based Mode
```
Distribution Mode: [Physics-Based LED Detection] ▼
```

### 2️⃣ Adjust Parameters
Use sliders or type exact values:
```
White Key Width: [========●========] 23.5 mm
```

### 3️⃣ Apply or Save
- **Apply Changes** (green button) → Save + regenerate LED mapping
- **Save Only** (orange button) → Save without regenerating
- **Reset to Defaults** → Restore factory settings

### 4️⃣ View Results
After applying, see preview stats:
```
Keys Mapped: 88
LEDs Used: 245
Avg LEDs/Key: 2.78
```

## Why Adjust These?

Different piano models have slightly different key dimensions. By adjusting these parameters, you optimize the LED-to-key mapping for your specific piano, ensuring:
- ✅ Better LED coverage
- ✅ Reduced gaps between key zones
- ✅ More accurate visual feedback

## Before/After Example

**Before (default settings):**
```
C3:  LEDs 4-6    (Gap to D3)  ← 2 LEDs
C#3: LEDs 6-7    (Gap to D3)
```

**After (tuned for your piano):**
```
C3:  LEDs 4-7    (Better coverage)  ← 3 LEDs
C#3: LEDs 7-8    (Improved)
```

## Tips

1. **Start with defaults** - They work for standard 88-key pianos
2. **Adjust gradually** - Change one parameter at a time
3. **Preview often** - Click Apply to see real-time changes
4. **Note units** - All dimensions in millimeters (mm)
5. **Settings persist** - Changes saved automatically to database

## Keyboard Dimensions Reference

| Piano Type | White Width | Black Width | Gap |
|------------|-------------|------------|-----|
| Standard Grand | 24.0-24.5 | 14.0-14.5 | 1.2-1.5 |
| Upright | 23.0-23.5 | 13.5-14.0 | 1.0-1.2 |
| Digital Keyboard | 23.5-24.0 | 13.5-14.0 | 0.8-1.0 |
| Narrower Keys | 22.0-23.0 | 12.5-13.5 | 0.8-1.0 |

## Troubleshooting

**Q: "Advanced Settings tab doesn't appear"**
A: Make sure you selected "Physics-Based LED Detection" mode in the Distribution Mode dropdown.

**Q: "LEDs not evenly distributed"**
A: Try adjusting `LED Width` and `Overhang Threshold` to match your LED strip specifications.

**Q: "Some keys have gaps in LED coverage"**
A: Adjust `White Key Width` and `Black Key Width` to match your piano's exact dimensions.

**Q: "Too many LEDs on some keys"**
A: Decrease `White Key Width` or increase `Overhang Threshold` to be more selective.

## API Reference (Developers)

### Get Current Parameters
```bash
GET /api/calibration/physics-parameters
```

### Update Parameters
```bash
POST /api/calibration/physics-parameters
Content-Type: application/json

{
  "white_key_width": 24.0,
  "black_key_width": 14.0,
  "white_key_gap": 1.2,
  "led_physical_width": 3.5,
  "overhang_threshold_mm": 1.5,
  "apply_mapping": true
}
```

---

**Last Updated:** Oct 17, 2024  
**Status:** Ready for Testing
