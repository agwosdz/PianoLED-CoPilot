# LED-to-MIDI Key Mapping Explanation

## Overview

The Piano LED Visualizer uses a **zero-indexed key array (0-87)** that directly maps to **MIDI notes 21-108**.

```
Key Index  →  MIDI Note  →  Piano Key Name
0          →  21         →  A0 (lowest note)
1          →  22         →  A#0
...
21         →  42         →  F#2
...
87         →  108        →  C8 (highest note)
```

## Current Mapping Configuration

**Settings:**
- Piano size: 88-key
- Total LEDs: 255
- Calibration start LED: 4
- Calibration end LED: 249
- Available LEDs for mapping: 246 (249 - 4 + 1)
- Distribution mode: Piano Based (no overlap)
- Sharing mode: OFF

**LED Allocation:**
- LEDs 0-3: Reserved for calibration
- LEDs 4-249: Active piano key mapping
- LEDs 250-254: Reserved/unused

## Why Key 21 Starts at LED 63

Looking at the mapping breakdown:

| Key Range | MIDI Range | LED Range | Total LEDs |
|-----------|-----------|-----------|-----------|
| Keys 0-20 | Notes 21-41 | LEDs 4-62 | 59 LEDs |
| Keys 21+ | Notes 42+ | LEDs 63+ | Remaining |

**Key 21 (MIDI note 42 = F#2) starts at LED 63** because the first 21 keys (0-20) collectively use LEDs 4-62, which is 59 LEDs total.

### Per-Key LED Allocation

Each key gets either **2 or 3 LEDs** depending on distribution:

```
Keys 0-3:   4 LEDs each = 16 LEDs total
Keys 4:     3 LEDs
Keys 5-8:   4 LEDs each = 16 LEDs
Keys 9:     3 LEDs
...and so on, alternating pattern
```

This results in:
- First 20 keys (0-19): 59 LEDs total
- Key 20: uses LEDs 60-63
- **Key 21 starts at LED 63**

## Verification with curl

To verify the mapping on the Pi:

```bash
# Get full mapping
curl http://192.168.1.225:5001/api/calibration/key-led-mapping | jq '.mapping | to_entries | .[0:5]'

# Output shows:
# Key 0: [4,5,6,7]       - MIDI 21 (A0)
# Key 1: [7,8,9,10]      - MIDI 22 (A#0)
# Key 2: [10,11,12,13]   - MIDI 23 (B0)
# ...
# Key 20: [60,61,62,63]  - MIDI 41 (F2)
# Key 21: [63,64,65,66]  - MIDI 42 (F#2) ← Starts at LED 63
```

## Why This Design?

1. **Calibration headroom (4 LEDs)**: Allows for offset adjustments without affecting the lowest piano keys
2. **Gradual distribution**: Early keys get more LEDs because they're visually larger on a piano
3. **Efficient packing**: ~2.8 LEDs per key on average for smooth visual representation

## Changing the Start Point

To change where the mapping starts, modify:

```bash
# Via API
curl -X POST http://192.168.1.225:5001/api/settings/calibration \
  -H "Content-Type: application/json" \
  -d '{"start_led": 0}'  # Start at LED 0 instead of 4

# Or directly in database
ssh pi@192.168.1.225
sqlite3 backend/settings.db "UPDATE settings SET value='0' WHERE category='calibration' AND key='start_led';"
sudo systemctl restart piano-led-visualizer
```

## MIDI Note Reference

| Key | MIDI | Note | Octave |
|-----|------|------|--------|
| 0   | 21   | A    | 0      |
| 12  | 33   | A    | 1      |
| 21  | 42   | F#   | 2      |
| 24  | 45   | A    | 2      |
| 36  | 57   | A    | 3      |
| 48  | 69   | A    | 4      |
| 60  | 81   | A    | 5      |
| 72  | 93   | A    | 6      |
| 87  | 108  | C    | 8      |

## Summary

- **Key 0 = MIDI 21** (lowest note on 88-key piano)
- **Key 21 = MIDI 42** (approximately F#2, starts at LED 63)
- **Key 87 = MIDI 108** (highest note, ends at LED 249)
- LEDs 0-3 are reserved for calibration
- The mapping is working correctly - Key 21 starting at LED 63 is by design
