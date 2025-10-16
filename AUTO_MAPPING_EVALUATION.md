# Auto Mapping Function Evaluation

## Overview
The auto mapping system automatically generates a key-to-LED mapping based on piano size and LED count. This document provides a comprehensive evaluation of the current implementation.

---

## 1. Core Function: `generate_auto_key_mapping()`

**Location:** `backend/config.py` (lines 657-717)

### Parameters
```python
def generate_auto_key_mapping(
    piano_size,              # "88-key", "61-key", "49-key", etc.
    led_count,               # Total LEDs available
    led_orientation="normal", # "normal" or "reversed" (note: applied in LEDController, not here)
    leds_per_key=None,       # Optional: fixed LEDs per key
    mapping_base_offset=None # Optional: offset from start of LED strip
)
```

### Algorithm

1. **Retrieve Piano Specs**
   - Gets key count and MIDI range for piano size
   - Example: 88-key piano = 88 keys, MIDI 21-108

2. **Calculate Base Parameters**
   ```
   available_leds = led_count - mapping_base_offset
   ```
   - Default offset = 0 (use all LEDs)
   - Can reserve LEDs at start of strip

3. **Distribute LEDs to Keys**
   - **If `leds_per_key` is None (calculated mode):**
     ```
     leds_per_key = available_leds // key_count  (integer division)
     remaining_leds = available_leds % key_count  (remainder)
     ```
     - Remaining LEDs are distributed to first N keys
     - Example: 250 LEDs ÷ 88 keys = 2 LEDs/key + 74 remaining
     - First 74 keys get 3 LEDs, remaining 14 keys get 2 LEDs

   - **If `leds_per_key` is specified:**
     ```
     max_mappable_keys = available_leds // leds_per_key
     If max_mappable_keys < key_count:
         key_count = max_mappable_keys  (truncate mapping)
     ```
     - Only maps keys that have enough LEDs
     - Example: If you specify 3 LEDs/key with 250 LEDs:
       - Can map 250 ÷ 3 = 83 keys (last 5 keys unmapped)

4. **Build Mapping Dictionary**
   ```python
   mapping = {
       21: [0, 1, 2],        # A0 → LEDs 0-2
       22: [3, 4, 5],        # A#0 → LEDs 3-5
       ...
       108: [255, 256, 257]  # C8 → LEDs 255-257
   }
   ```
   - MIDI note → list of LED indices (logical, not physical)

### Key Design Decisions

✅ **Pros:**
- Simple and predictable
- Distributes remaining LEDs fairly to early keys
- Supports flexible LED allocation
- Handles partial mappings gracefully

⚠️ **Potential Issues:**
1. **Remaining LED Distribution:** First keys get extra LEDs, might cause visual inconsistency
   - Key 21 (A0) gets 3 LEDs
   - Key 95 (B7) gets 2 LEDs
   - Inconsistent across keyboard

2. **Unequal LED Per Key:** If 250 LEDs and 88 keys:
   - 74 keys with 3 LEDs
   - 14 keys with 2 LEDs
   - Visual brightness inconsistency

3. **Truncation Mode Silent:** When `leds_per_key` specified, keys beyond available LEDs are silently dropped
   - No warning logged
   - Last keys unmapped with no feedback

---

## 2. Integration: `/api/calibration/key-led-mapping` Endpoint

**Location:** `backend/api/calibration.py` (lines 505-561)

### Request Flow
```
GET /api/calibration/key-led-mapping
  ↓
Fetch settings:
  - piano.size (default: 88-key)
  - led.led_count (default: 300)
  - led.led_orientation (default: "normal")
  - led.mapping_base_offset (default: 0)
  - led.leds_per_key (default: None)
  ↓
generate_auto_key_mapping()
  ↓
Fetch calibration offsets:
  - calibration.global_offset
  - calibration.key_offsets
  ↓
apply_calibration_offsets_to_mapping()
  ↓
Return mapping with offsets applied
```

### Response Example
```json
{
  "mapping": {
    "21": [0, 1, 2],
    "22": [3, 4, 5],
    ...
  },
  "piano_size": "88-key",
  "led_count": 300,
  "global_offset": 0,
  "key_offsets_count": 5,
  "timestamp": "2025-10-16T..."
}
```

---

## 3. Calibration Offset Application: `apply_calibration_offsets_to_mapping()`

**Location:** `backend/config.py` (lines 719-792)

### Two Types of Offsets

#### 1. Global Offset
- Applies to ALL LEDs equally
- Shifts entire mapping forward/backward
- Use case: Align mapping to LEDs

#### 2. Per-Key Cascading Offsets
- Applied individually to specific notes
- **Cascading:** Offset at note N affects notes N, N+1, N+2, ...
- Cumulative: Multiple offsets stack
- Use case: Fine-tune individual notes

### Example: Cascading Offset Behavior
```
Settings:
  global_offset = 0
  key_offsets = {
    48: +1,    # C3: +1 LED
    50: +2,    # D3: +2 MORE LEDs (total +3 for D3)
    55: +3     # G3: +3 MORE LEDs (total +6 from C3)
  }

Mapping Results:
  C3  (MIDI 48): base[0, 1, 2] → offset +1 → [1, 2, 3]
  C#3 (MIDI 49): base[3, 4, 5] → offset +1 → [4, 5, 6]      (cascades from C3)
  D3  (MIDI 50): base[6, 7, 8] → offset +3 → [9, 10, 11]    (C3's +1 + D3's +2)
  D#3 (MIDI 51): base[9, 10, 11] → offset +3 → [12, 13, 14] (cascades from D3)
  ...
  G3  (MIDI 55): base[...] → offset +6 → [...] (accumulated from C3, D3, G3)
```

### Implementation Details

1. **Type Normalization**
   - Converts string keys/values to integers
   - Handles mixed types from database storage

2. **Bounds Checking**
   - Clamps adjusted indices to [0, led_count-1]
   - Prevents invalid LED access

3. **Error Handling**
   - Skips invalid entries silently
   - Returns what it can process

---

## 4. Evaluation Metrics

### Current Test Coverage

**Location:** `backend/tests/test_calibration.py`

Tests verify:
✅ Offsets disabled → no change  
✅ Global offset applied  
✅ Per-key offset applied  
✅ Combined offsets  
✅ Negative offsets  
✅ Clamping to bounds  
✅ Lower bound clamping  

### What's NOT Tested
❌ Cascading offset logic (only individual offsets tested)  
❌ Edge cases: LEDs < keys  
❌ Multiple leds_per_key with offsets  
❌ String key normalization  
❌ Invalid MIDI note handling  

---

## 5. Suggested Improvements

### 1. Better LED Distribution
**Current Issue:** Uneven LED distribution to keys

**Option A: Distribute Remaining LEDs More Evenly**
```python
# Spread remaining LEDs across entire keyboard
# Instead of first 74 keys get 3, rest get 2
# Make it more like: alternating or distributed pattern
```

**Option B: Make Distribution Mode Configurable**
```python
def generate_auto_key_mapping(..., distribution_mode="even"):
    # "even": current behavior (first keys get extra)
    # "spread": distribute extra LEDs evenly
    # "end": put extra LEDs at end of keyboard
    # "custom": user specifies which keys get extra
```

### 2. Better Truncation Handling
**Current Issue:** Silent key truncation when LEDs insufficient

**Improvement:**
```python
if max_mappable_keys < key_count:
    logger.warning(f"Cannot map all {key_count} keys with {leds_per_key} LEDs/key")
    logger.warning(f"Only {max_mappable_keys} keys can be mapped")
    logger.info(f"Keys {specs['midi_start'] + max_mappable_keys} to {specs['midi_end']} unmapped")
```

### 3. Offset Application Improvements
**Current Issue:** Cascading offsets might not be intuitive

**Improvement: Add Offset Mode Selection**
```python
def apply_calibration_offsets_to_mapping(
    ...,
    offset_mode="cascading"  # "cascading" or "independent"
):
    # cascading: offset at N affects N, N+1, N+2, ... (current)
    # independent: offset at N affects only N
```

### 4. Validation & Warnings
**Add Pre-mapping Validation:**
```python
def validate_mapping_config(piano_size, led_count, leds_per_key, base_offset):
    """Check if mapping is feasible and warn of issues"""
    specs = get_piano_specs(piano_size)
    available_leds = led_count - base_offset
    
    warnings = []
    
    if available_leds < specs['keys']:
        warnings.append(f"Not enough LEDs ({available_leds}) for all keys ({specs['keys']})")
    
    if leds_per_key and (available_leds // leds_per_key) < specs['keys']:
        warnings.append(f"With {leds_per_key} LEDs/key, only {available_leds // leds_per_key} keys can be mapped")
    
    if available_leds < specs['keys'] * 2:
        warnings.append("LED distribution might be uneven")
    
    return warnings
```

### 5. Add Mapping Visualization Endpoint
```python
@calibration_bp.route('/mapping-info', methods=['GET'])
def get_mapping_info():
    """Get detailed info about current mapping"""
    return {
        "total_keys": 88,
        "mapped_keys": 88,
        "unmapped_keys": 0,
        "leds_distribution": {
            "keys_with_2_leds": 14,
            "keys_with_3_leds": 74
        },
        "first_key_distribution": [3, 3, 3, ...],  # LED counts per key
        "warning": "Uneven distribution: first 74 keys get 3 LEDs, last 14 get 2"
    }
```

---

## 6. Testing Recommendations

### Unit Tests to Add
1. **Cascading Offset Tests**
   ```python
   def test_cascading_offset_accumulation():
       """Multiple offsets at different notes stack correctly"""
   
   def test_cascading_offset_single():
       """Single offset cascades to all subsequent notes"""
   ```

2. **Edge Case Tests**
   ```python
   def test_more_leds_than_keys():
       """500 LEDs, 88 keys - proper distribution"""
   
   def test_fewer_leds_than_keys():
       """50 LEDs, 88 keys - graceful handling"""
   
   def test_exactly_matching():
       """88 LEDs, 88 keys - 1 LED per key"""
   ```

3. **Configuration Tests**
   ```python
   def test_leds_per_key_specified():
       """Fixed LEDs per key ignores remainder distribution"""
   
   def test_base_offset_applied():
       """mapping_base_offset correctly skips first LEDs"""
   ```

### Integration Tests
1. Test full flow: settings → mapping generation → offset application → API response
2. Test with actual piano sizes (25, 37, 49, 61, 76, 88 key)
3. Test with various LED counts (50, 100, 150, 200, 300, 500)

---

## 7. Summary

### What Works Well ✅
- Simple, predictable algorithm
- Handles various piano sizes
- Cascading offset system is elegant
- Type normalization prevents crashes
- Bounds checking prevents invalid LEDs

### What Needs Improvement ⚠️
- Uneven LED distribution to keys
- Silent truncation of unmapped keys
- Limited logging/warnings
- Cascading offset might confuse users
- No validation of feasibility

### Recommended Priority
1. **High:** Add validation and warnings (easy, high value)
2. **High:** Improve cascading offset documentation
3. **Medium:** Add mapping-info endpoint for debugging
4. **Medium:** Add tests for edge cases and cascading
5. **Low:** Make distribution mode configurable

---

## Testing Script

To test the auto mapping:

```bash
# Run calibration tests
pytest backend/tests/test_calibration.py -v

# Test endpoint
curl -X GET http://localhost:5000/api/calibration/key-led-mapping

# Test with specific settings
# (Requires settings API to modify piano size, LED count, etc.)
```

