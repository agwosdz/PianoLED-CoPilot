# LED Trim Integration - Architecture & Data Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Svelte)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CalibrationSection3.svelte                                      │
│  ├─ User selects LEDs from allocation                            │
│  ├─ Calculate left/right trim from selection                     │
│  ├─ Save: POST /api/calibration/key-offset                       │
│  ├─ Load: GET /api/calibration/key-led-mapping                   │
│  └─ Display: Show adjusted LED range with trims                  │
│                                                                   │
│  calibrationState:                                               │
│  ├─ key_offsets: {21: 2, 22: 0, ...}                            │
│  └─ key_led_trims: {21: {left: 1, right: 1}, ...}              │
│                                                                   │
└─────────────────────┬──────────────────────────────────────────┘
                      │ HTTP API
          ┌───────────┴───────────┐
          │                       │
    POST: Save                  GET: Load
    Offset + Trim              Mapping
          │                       │
          ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Flask/Python)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  api/calibration.py                                              │
│                                                                   │
│  POST /key-offset/<midi_note>                                   │
│  ├─ Receive: offset, left_trim, right_trim                      │
│  └─ Store: key_offsets, key_led_trims (in SQLite)              │
│                                                                   │
│  GET /status                                                     │
│  └─ Return: key_offsets ✅, key_led_trims ✅                   │
│                                                                   │
│  GET /key-led-mapping                                            │
│  ├─ Get base mapping (physics/piano allocation)                  │
│  ├─ Get key_offsets & key_led_trims from SQLite                 │
│  ├─ Call: apply_calibration_offsets_to_mapping()               │
│  └─ Return: final_mapping with trims applied ✅                 │
│                                                                   │
└─────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              config.py - Mapping Logic (NEW!)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  apply_calibration_offsets_to_mapping(                          │
│      mapping,                  # Base allocation                 │
│      key_offsets,              # Per-key LED shifts             │
│      key_led_trims,            # NEW: Per-key trim values       │
│      ...                                                          │
│  )                                                                │
│                                                                   │
│  For each key:                                                   │
│    1. Apply offset:  leds = [base_led + offset for each]       │
│    2. Apply trim:    leds = leds[left_trim : -right_trim]      │
│    3. Return:        final mapping with trims applied           │
│                                                                   │
└─────────────────────┬──────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  settings table                                                  │
│  ├─ category: 'calibration'                                     │
│  ├─ key: 'key_offsets'                                          │
│  └─ value: {21: 2, 22: 0, ...}                                 │
│                                                                   │
│  settings table                                                  │
│  ├─ category: 'calibration'                                     │
│  ├─ key: 'key_led_trims'                                        │
│  └─ value: {21: {left_trim: 1, right_trim: 1}, ...}           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow - Complete Sequence

```
STEP 1: User Action
┌──────────────────────────────────────┐
│ Frontend: User selects 2 of 4 LEDs   │
│ From [49, 50, 51] → Select [50, 51] │
└──────────┬───────────────────────────┘
           │ Calculate trim
           ▼
┌──────────────────────────────────────┐
│ Frontend: Calculate trims             │
│ First selected: 50 (index 1)          │
│ Last selected: 51 (index 2)           │
│ Left trim: 1 (skip first LED 49)      │
│ Right trim: 0 (include to end)        │
└──────────┬───────────────────────────┘

STEP 2: Save to Backend
┌──────────────────────────────────────┐
│ POST /api/calibration/key-offset/50  │
│ {                                    │
│   "offset": 0,                       │
│   "left_trim": 1,                    │
│   "right_trim": 0                    │
│ }                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Backend: Save to Database            │
│ key_offsets: {50: 0}                 │
│ key_led_trims: {50: {L:1, R:0}}     │
└──────────┬───────────────────────────┘

STEP 3: Refresh Mapping
┌──────────────────────────────────────┐
│ Frontend: Call updateLedMapping()    │
│ GET /api/calibration/key-led-mapping │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Backend: Generate Final Mapping      │
│                                      │
│ 1. Get base mapping (physics):       │
│    key 49 → [48, 49]                 │
│    key 50 → [49, 50, 51]             │
│    key 51 → [51, 52, 53]             │
│                                      │
│ 2. Get key_offsets: {50: 0}         │
│    Apply: No change (offset = 0)    │
│                                      │
│ 3. Get key_led_trims: {50: {L:1, R}}│
│    Apply trim to key 50:             │
│    Before: [49, 50, 51]              │
│    After:  [49, 50, 51][1:]          │
│    Result: [50, 51] ✅              │
│                                      │
│ Final mapping:                       │
│ {                                    │
│   "49": [48, 49],                   │
│   "50": [50, 51],      ← Trimmed!   │
│   "51": [51, 52, 53]                │
│   ...                               │
│ }                                    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Frontend: Display Updated Mapping    │
│ Key 50: "Adjusted LEDs: 50 - 51"    │
│         "Trim: L1 R0"                │
└──────────────────────────────────────┘
```

## Offset + Trim Interaction

```
Example: Key with Offset AND Trim

Base Allocation:        [0, 1, 2, 3]
                          (4 LEDs)
              │
              ├─ Apply Offset (+2)
              │
Offset Phase:           [2, 3, 4, 5]
                          (still 4 LEDs, shifted right)
              │
              ├─ Apply Trim (L1, R1)
              │  [left_trim : len - right_trim]
              │  [1 : 4 - 1]
              │  [1 : 3]
              │
Trim Phase:             [3, 4]
                          (2 LEDs, trimmed from both sides)
```

## Trim Calculation in Frontend

```javascript
// Frontend: CalibrationSection3.svelte

// User selection: [50, 51] from [49, 50, 51]
const allocation = [49, 50, 51];
const selected = [50, 51];

// Find first/last selected indices
const firstSelectedIdx = 0;  // In allocation[0] = 49... wait
const firstSelectedIdx = allocation.indexOf(50) = 1;    // LED 50 is at index 1
const lastSelectedIdx = allocation.indexOf(51) = 2;     // LED 51 is at index 2

// Calculate trims from position in allocation
const leftTrim = firstSelectedIdx;        // = 1
const rightTrim = allocation.length - lastSelectedIdx - 1;  // = 3 - 2 - 1 = 0

// Result: [1, 0]
// Backend receives: {left_trim: 1, right_trim: 0}
```

## Backend Trim Application

```python
# Backend: config.py

for midi_note, led_indices in mapping.items():
    # Apply offset first
    adjusted_indices = [led + cascading_offset for led in led_indices]
    
    # Apply trim AFTER offset
    if midi_note in normalized_key_led_trims:
        trim = normalized_key_led_trims[midi_note]
        left = trim['left_trim']
        right = trim['right_trim']
        
        # Slice: [left : len - right]
        if right > 0:
            adjusted_indices = adjusted_indices[left:-right]
        else:
            adjusted_indices = adjusted_indices[left:]
    
    mapping[midi_note] = adjusted_indices
```

## Parameter Conversions

### MIDI Note ↔ Key Index

```
Frontend uses MIDI notes (21-108):
  Middle C = 60
  A1 = 21
  C8 = 108

Backend mapping uses key indices (0-87):
  A1 (MIDI 21) = index 0
  C (middle) = index 39
  C8 (MIDI 108) = index 87

Conversion:
  key_index = midi_note - 21
  midi_note = key_index + 21

Applied in:
  - get_key_led_mapping(): convert trims MIDI→index before passing to function
  - apply_calibration_offsets_to_mapping(): use index form throughout
```

### Trim Dict Structure

```python
# Frontend sends (MIDI format)
POST /api/calibration/key-offset/50
{
  "offset": 2,
  "left_trim": 1,
  "right_trim": 0
}

# Backend stores (MIDI note as key)
settings.set_setting('calibration', 'key_led_trims', {
  '50': {
    'left_trim': 1,
    'right_trim': 0
  }
})

# Backend uses (index format for mapping)
apply_calibration_offsets_to_mapping(
    key_led_trims={
        29: {'left_trim': 1, 'right_trim': 0}  # MIDI 50 → index 29
    }
)
```

## Logging Output Example

```
INFO: Applying calibration offsets to mapping with 88 entries. 
      start_led=4, end_led=249, key_offsets_count=1, 
      key_led_trims_count=1, weld_offsets_count=0, led_count=300

DEBUG: Normalized 1 key offsets. Notes: [50], Offsets: [2]
DEBUG: Normalized 1 key LED trims. Notes with trims: [50]

DEBUG: Note 50: LED 49 → 51 (led_offset=2, weld_compensation=0 LEDs, 
       contributing_offsets=[(50, 2, 'led')], clamped=False)
DEBUG: Note 50: LED 50 → 52 (led_offset=2, weld_compensation=0 LEDs, 
       contributing_offsets=[(50, 2, 'led')], clamped=False)
DEBUG: Note 50: LED 51 → 53 (led_offset=2, weld_compensation=0 LEDs, 
       contributing_offsets=[(50, 2, 'led')], clamped=False)

DEBUG: Note 50: Applied trim L1/R0 → 3 LEDs became 2 LEDs 
       (LEDs: [52, 53])

INFO: Offset and trim application complete. Adjusted 88 notes. 
      Clamped 0 LED indices (bounds: 4-249). 
      Applied 1 LED offsets, 1 LED trims, and 0 weld compensations. 
      Adjusted mapping now has 256 total LED assignments
```

## Response Format

```json
GET /api/calibration/key-led-mapping

{
  "mapping": {
    "21": [10, 11, 12],
    "22": [13, 14, 15],
    ...
    "50": [50, 51],        ← Trimmed result
    ...
    "108": [245, 246]
  },
  "piano_size": "88-key",
  "led_count": 300,
  "start_led": 4,
  "end_led": 249,
  "key_offsets_count": 1,
  "key_led_trims_count": 1,    ← NEW: Shows trim count
  "distribution_mode": "Physics-Based LED Detection",
  "allow_led_sharing": true,
  "timestamp": "2025-10-19T14:30:00.123456"
}
```

---

**Key Takeaway:** Trims are now integrated into the backend mapping logic, applied AFTER offsets, and returned as part of the final mapping response. Frontend can use the trimmed mapping for accurate LED visualization.
