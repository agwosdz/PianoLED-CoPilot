# Auto Mapping Process Visualization

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Settings (Database)                      │
├─────────────────────────────────────────────────────────────────┤
│  piano.size = "88-key"                                           │
│  led.led_count = 300                                             │
│  led.leds_per_key = null (auto-calculate)                        │
│  led.mapping_base_offset = 0                                     │
│  calibration.global_offset = 0                                   │
│  calibration.key_offsets = {48: +1, 50: +2}                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ /api/calibration/key-led-mapping
        │ (Fetch all settings)
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼────────────────┐
        │  generate_auto_key_mapping()  │
        │  (Generate base mapping)      │
        └──────────────┬───────────────┘
                       │
                       ▼
   ┌──────────────────────────────────────┐
   │  Result: 88 keys × 3-4 LEDs each    │
   │  Total: 300 LEDs distributed        │
   └──────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ apply_calibration_offsets_to_mapping()  │
│ (Apply global + cascading offsets)      │
└──────────────┬────────────────────────────┘
               │
               ▼
      ┌────────────────────┐
      │  Final Mapping     │
      │  With Offsets      │
      │  Applied           │
      └────────────────────┘
               │
               ▼
      ┌────────────────────┐
      │   Return to        │
      │   Frontend         │
      └────────────────────┘
```

---

## Detailed: Generate Auto Mapping

```
Piano Specs (88-key):
  - 88 keys total
  - MIDI range: 21 to 108 (A0 to C8)

Available LEDs: 300 - 0 = 300

Calculate Distribution:
  leds_per_key = 300 ÷ 88 = 3 (integer division)
  remaining_leds = 300 % 88 = 36

Distribution:
  ✓ Keys 21-56 (36 keys): 3+1 = 4 LEDs each → 144 LEDs
  ✓ Keys 57-108 (52 keys): 3 LEDs each → 156 LEDs
  Total: 144 + 156 = 300 ✓

Mapping Generation:
  LED Index    0  1  2  3  4  5  6  7  8  9 ...
              ┌─────┬─────┬─────┬─────┬─────┐
              │ Key │ Key │ Key │ Key │ Key │
              │ 21  │ 22  │ 23  │ 24  │ 25  │
              │ A0  │ A#0 │ B0  │ C1  │ C#1 │
              │ 4🟣 │ 4🔵 │ 4🟡 │ 4🟢 │ 4🟠 │
              └─────┴─────┴─────┴─────┴─────┘

Result Dictionary:
  {
    21: [0, 1, 2, 3],      # A0 → 4 LEDs (gets extra)
    22: [4, 5, 6, 7],      # A#0 → 4 LEDs
    23: [8, 9, 10, 11],    # B0 → 4 LEDs
    ...
    56: [140, 141, 142, 143],  # G#3 → 4 LEDs (last of first 36 keys)
    57: [144, 145, 146],   # A3 → 3 LEDs (back to 3)
    ...
    108: [297, 298, 299]   # C8 → 3 LEDs (last key)
  }
```

---

## Detailed: Apply Cascading Offsets

```
Base Mapping (before offsets):
  MIDI 48 (C3):  [0, 1, 2]
  MIDI 49 (C#3): [3, 4, 5]
  MIDI 50 (D3):  [6, 7, 8]
  MIDI 51 (D#3): [9, 10, 11]
  MIDI 52 (E3):  [12, 13, 14]
  ...

Settings:
  global_offset = 0
  key_offsets = {
    48: +1,    # C3: add 1
    50: +2     # D3: add 2 more (cascades with C3's +1)
  }

Processing:

  ╔════════════════════════════════════════════════════╗
  ║ MIDI 48 (C3)                                       ║
  ║ Cascading offset = 0 + 1 = 1  ✓                   ║
  ║ Result: [0,1,2] + 1 = [1, 2, 3]                   ║
  ╚════════════════════════════════════════════════════╝

  ╔════════════════════════════════════════════════════╗
  ║ MIDI 49 (C#3)                                      ║
  ║ Cascading offset = 1 (from C3)  ✓                 ║
  ║ Result: [3,4,5] + 1 = [4, 5, 6]                   ║
  ╚════════════════════════════════════════════════════╝

  ╔════════════════════════════════════════════════════╗
  ║ MIDI 50 (D3)                                       ║
  ║ Cascading offset = 1 (from C3) + 2 (from D3) = 3 ║
  ║ Result: [6,7,8] + 3 = [9, 10, 11]                 ║
  ╚════════════════════════════════════════════════════╝

  ╔════════════════════════════════════════════════════╗
  ║ MIDI 51 (D#3)                                      ║
  ║ Cascading offset = 1 + 2 = 3 (inherited)          ║
  ║ Result: [9,10,11] + 3 = [12, 13, 14]              ║
  ╚════════════════════════════════════════════════════╝

Final Mapping (with offsets):
  MIDI 48 (C3):  [1, 2, 3]         ← shifted by +1
  MIDI 49 (C#3): [4, 5, 6]         ← shifted by +1 (cascaded)
  MIDI 50 (D3):  [9, 10, 11]       ← shifted by +3 (1+2)
  MIDI 51 (D#3): [12, 13, 14]      ← shifted by +3 (cascaded)
  MIDI 52 (E3):  [15, 16, 17]      ← unchanged
  ...
```

---

## Scenario: Uneven Distribution Problem

```
Example: 250 LEDs for 88 keys

Calculation:
  250 ÷ 88 = 2 LEDs/key with 74 remaining
  
Distribution:
  ┌─────────────────────────────────────────────┐
  │ Keys 21-94 (74 keys):                        │
  │ Get 2+1 = 3 LEDs each → 222 LEDs            │
  │ 🟣🔵🟡 🟣🔵🟡 🟣🔵🟡 ...                   │
  └─────────────────────────────────────────────┘
  
  ┌─────────────────────────────────────────────┐
  │ Keys 95-108 (14 keys):                       │
  │ Get 2 LEDs each → 28 LEDs                    │
  │ 🟣🔵 🟣🔵 🟣🔵 ...                          │
  └─────────────────────────────────────────────┘

Visual Problem on Piano:
  High Keys (C7-C8):    🟣🔵 🟣🔵  ← 2 LEDs (dimmer)
  Mid Keys (C4-C5):     🟣🔵🟡 🟣🔵🟡  ← 3 LEDs (brighter)
  
Result: Brightness inconsistency across keyboard
```

---

## API Response Example

```json
{
  "mapping": {
    "21": [0, 1, 2, 3],
    "22": [4, 5, 6, 7],
    "23": [8, 9, 10, 11],
    ...
    "56": [140, 141, 142, 143],
    "57": [144, 145, 146],
    ...
    "108": [297, 298, 299]
  },
  "piano_size": "88-key",
  "led_count": 300,
  "mapping_base_offset": 0,
  "leds_per_key": null,
  "global_offset": 0,
  "key_offsets_count": 2,
  "timestamp": "2025-10-16T14:30:45.123456"
}
```

---

## Comparison: Distribution Modes

### Current (First-Keys Distribution)
```
Keys 21-94:  🟣🔵🟡  (3 LEDs)
Keys 95-108: 🟣🔵   (2 LEDs)

Pro: Simple to implement
Con: Visual inconsistency
```

### Proposed: Spread Distribution
```
Keys 21-40:  🟣🔵🟡  (3 LEDs)
Keys 41-54:  🟣🔵   (2 LEDs)
Keys 55-68:  🟣🔵🟡  (3 LEDs)
Keys 69-82:  🟣🔵   (2 LEDs)
Keys 83-108: 🟣🔵🟡  (3 LEDs)

Pro: More even distribution
Con: More complex logic
```

### Proposed: End-Keys Extra
```
Keys 21-94:  🟣🔵   (2 LEDs)
Keys 95-108: 🟣🔵🟡  (3 LEDs)

Pro: High keys (where user looks) get more LEDs
Con: Unintuitive to configure
```

---

## Configuration Examples

### Example 1: 88-Key with Auto Distribution
```
Settings:
  piano_size = "88-key"
  led_count = 300
  leds_per_key = null
  
Result: 74 keys × 3 LEDs + 14 keys × 2 LEDs
```

### Example 2: 88-Key with Fixed Distribution
```
Settings:
  piano_size = "88-key"
  led_count = 300
  leds_per_key = 3
  
Result: 88 keys × 3 LEDs = 264 LEDs used, 36 LEDs unused
```

### Example 3: Partial Keyboard Mapping
```
Settings:
  piano_size = "88-key"
  led_count = 150
  leds_per_key = 2
  
Calculation: 150 ÷ 2 = 75 keys max
Result: Only first 75 keys mapped (MIDI 21-95)
        Last 13 keys unmapped (MIDI 96-108)
```

### Example 4: With Base Offset
```
Settings:
  piano_size = "88-key"
  led_count = 300
  mapping_base_offset = 50  ← Skip first 50 LEDs
  
Result: Map to LEDs 50-299 (250 LEDs available)
        Distribution: 74 keys × 2 LEDs + 14 keys × 3 LEDs
```

