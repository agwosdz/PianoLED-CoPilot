# LED Index Bounds Checking Implementation

## Problem Statement
With a 255-LED setup (valid indices 0-254) and a +4 global offset, the last LED indices should not exceed 254. For example:
- Last key base index: 251
- With +4 offset: would be 255, but should clamp to 254 (the maximum valid index)

## Solution
Added bounds validation to `apply_calibration_offsets_to_mapping()` in `backend/config.py`:

### Updated Function Signature
```python
def apply_calibration_offsets_to_mapping(mapping, global_offset=0, key_offsets=None, led_count=None):
    """Apply calibration offsets with optional bounds checking
    
    Args:
        mapping: Base key-to-LED mapping dict
        global_offset: Global offset to apply to all LEDs
        key_offsets: Per-key offset dict {midi_note: offset}
        led_count: Total LED count for bounds checking (optional, no bounds if None)
    
    Returns:
        dict: Adjusted mapping with offsets applied (LED indices clamped to [0, led_count-1])
    """
```

### Implementation Details
- For each LED index after applying offsets: `clamped_index = max(0, min(adjusted_index, led_count - 1))`
- Backward compatible: If `led_count=None`, no bounds checking is applied (existing behavior)
- Applies bounds checking to both list and single index mappings

### Updated Callers
1. **backend/api/calibration.py** - `/api/calibration/key-led-mapping` endpoint now passes `led_count`:
   ```python
   final_mapping = apply_calibration_offsets_to_mapping(
       mapping=auto_mapping,
       global_offset=global_offset,
       key_offsets=key_offsets,
       led_count=led_count  # Enables bounds checking
   )
   ```

## Test Results
With 255 LEDs (valid indices 0-254) and +4 global offset:

| Test Case | Base Index | After +4 Offset | Result |
|-----------|-----------|-----------------|--------|
| First key | 0 | 4 | ✅ 4 (within bounds) |
| Last key | 251 | 254 | ✅ 254 (clamped from 255) |
| Last 5 keys | [250-254] | [254×5] | ✅ All clamped to 254 |

## Benefits
1. **Prevents Out-of-Bounds Access**: LED indices always stay within [0, led_count-1]
2. **Hardware Safe**: Prevents attempting to light non-existent LEDs
3. **Graceful Degradation**: If offset is too large, keys map to last available LED instead of failing
4. **Backward Compatible**: Existing code without `led_count` parameter works unchanged

## Frontend Impact
The piano visualization in CalibrationSection3.svelte now displays accurate, bounded LED indices from the backend, ensuring visual representation matches hardware constraints.
