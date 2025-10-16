# Auto Mapping Improvement Recommendations

## Priority 1: Add Validation & Warnings (QUICK WIN)

### Issue
Currently, the system silently accepts invalid configurations that might not work as expected.

### Implementation

Add to `backend/config.py`:

```python
def validate_auto_mapping_config(piano_size, led_count, leds_per_key=None, base_offset=0):
    """
    Validate mapping configuration and return warnings/recommendations.
    
    Returns:
        {
            'valid': bool,
            'warnings': [str],
            'recommendations': [str],
            'stats': {
                'key_count': int,
                'available_leds': int,
                'leds_per_key_calc': float,
                'remaining_leds': int
            }
        }
    """
    specs = get_piano_specs(piano_size)
    key_count = specs['keys']
    available_leds = led_count - base_offset
    
    warnings = []
    recommendations = []
    stats = {
        'key_count': key_count,
        'available_leds': available_leds,
        'leds_per_key_calc': 0.0,
        'remaining_leds': 0
    }
    
    # Check 1: Negative available LEDs
    if available_leds <= 0:
        return {
            'valid': False,
            'warnings': [f'No available LEDs: {led_count} total - {base_offset} offset = {available_leds}'],
            'recommendations': ['Reduce mapping_base_offset or increase led_count'],
            'stats': stats
        }
    
    # Check 2: LEDs per key calculation
    calc_leds_per_key = available_leds / key_count
    stats['leds_per_key_calc'] = calc_leds_per_key
    stats['remaining_leds'] = available_leds % key_count
    
    if calc_leds_per_key < 1:
        warnings.append(f'Not enough LEDs: {available_leds} / {key_count} = {calc_leds_per_key:.2f} LEDs/key')
        recommendations.append('Increase led_count or use smaller piano size')
        return {
            'valid': False,
            'warnings': warnings,
            'recommendations': recommendations,
            'stats': stats
        }
    
    # Check 3: Uneven distribution
    if calc_leds_per_key != int(calc_leds_per_key):
        remainder = available_leds % key_count
        warnings.append(
            f'Uneven distribution: {remainder} keys get {int(calc_leds_per_key)+1} LEDs, '
            f'{key_count - remainder} keys get {int(calc_leds_per_key)} LEDs'
        )
        recommendations.append(f'Consider using a multiple of {key_count} LEDs')
    
    # Check 4: Specified leds_per_key vs available
    if leds_per_key:
        mappable_keys = available_leds // leds_per_key
        if mappable_keys < key_count:
            warnings.append(
                f'With {leds_per_key} LEDs/key, only {mappable_keys}/{key_count} keys can be mapped'
            )
            unmapped_keys = key_count - mappable_keys
            start_midi = specs['midi_start']
            end_midi = specs['midi_end']
            first_unmapped = start_midi + mappable_keys
            recommendations.append(
                f'Keys {first_unmapped} to {end_midi} ({unmapped_keys} keys) will be unmapped'
            )
    
    # Check 5: Very small LED allocation
    if calc_leds_per_key < 2:
        warnings.append('Very low LED count per key - lighting may be subtle')
        recommendations.append('Consider increasing led_count for brighter visualization')
    
    return {
        'valid': True,
        'warnings': warnings,
        'recommendations': recommendations,
        'stats': stats
    }
```

### Usage in API

```python
@calibration_bp.route('/mapping-validate', methods=['POST'])
def validate_mapping_config():
    """Validate a proposed mapping configuration before applying it"""
    try:
        data = request.get_json()
        piano_size = data.get('piano_size', '88-key')
        led_count = data.get('led_count', 300)
        leds_per_key = data.get('leds_per_key')
        base_offset = data.get('mapping_base_offset', 0)
        
        validation = validate_auto_mapping_config(
            piano_size=piano_size,
            led_count=led_count,
            leds_per_key=leds_per_key,
            base_offset=base_offset
        )
        
        logger.info(f"Mapping validation: {validation}")
        return jsonify(validation), 200
        
    except Exception as e:
        logger.error(f"Error validating mapping: {e}")
        return jsonify({'error': str(e)}), 500
```

---

## Priority 2: Add Mapping Information Endpoint

### Issue
No way to see LED distribution details without inspecting the mapping.

### Implementation

```python
@calibration_bp.route('/mapping-info', methods=['GET'])
def get_mapping_info():
    """Get detailed information about current LED mapping"""
    try:
        settings_service = get_settings_service()
        
        piano_size = settings_service.get_setting('piano', 'size', '88-key')
        led_count = settings_service.get_setting('led', 'led_count', 300)
        base_offset = settings_service.get_setting('led', 'mapping_base_offset', 0)
        leds_per_key = settings_service.get_setting('led', 'leds_per_key', None)
        
        # Generate mapping
        mapping = generate_auto_key_mapping(
            piano_size=piano_size,
            led_count=led_count,
            leds_per_key=leds_per_key,
            mapping_base_offset=base_offset
        )
        
        # Analyze distribution
        led_counts = {}
        for midi_note, led_indices in mapping.items():
            count = len(led_indices)
            if count not in led_counts:
                led_counts[count] = 0
            led_counts[count] += 1
        
        specs = get_piano_specs(piano_size)
        
        info = {
            'piano_size': piano_size,
            'total_keys': specs['keys'],
            'mapped_keys': len(mapping),
            'unmapped_keys': specs['keys'] - len(mapping),
            'total_leds': led_count,
            'available_leds': led_count - base_offset,
            'leds_used': sum(len(indices) for indices in mapping.values()),
            'leds_unused': led_count - sum(len(indices) for indices in mapping.values()),
            'distribution': {
                f'{count}_leds': count_keys 
                for count, count_keys in sorted(led_counts.items())
            },
            'min_leds_per_key': min(led_counts.keys()) if led_counts else 0,
            'max_leds_per_key': max(led_counts.keys()) if led_counts else 0,
            'avg_leds_per_key': (
                sum(len(indices) for indices in mapping.values()) / len(mapping)
                if mapping else 0
            ),
            'first_unmapped_key': (
                specs['midi_start'] + len(mapping) 
                if len(mapping) < specs['keys'] else None
            ),
            'validation': validate_auto_mapping_config(
                piano_size=piano_size,
                led_count=led_count,
                leds_per_key=leds_per_key,
                base_offset=base_offset
            )
        }
        
        return jsonify(info), 200
        
    except Exception as e:
        logger.error(f"Error getting mapping info: {e}")
        return jsonify({'error': str(e)}), 500
```

### Example Response

```json
{
  "piano_size": "88-key",
  "total_keys": 88,
  "mapped_keys": 88,
  "unmapped_keys": 0,
  "total_leds": 300,
  "available_leds": 300,
  "leds_used": 300,
  "leds_unused": 0,
  "distribution": {
    "3_leds": 74,
    "2_leds": 14
  },
  "min_leds_per_key": 2,
  "max_leds_per_key": 3,
  "avg_leds_per_key": 3.41,
  "first_unmapped_key": null,
  "validation": {
    "valid": true,
    "warnings": [
      "Uneven distribution: 36 keys get 3 LEDs, 52 keys get 2 LEDs"
    ],
    "recommendations": [
      "Consider using 264 or 352 LEDs for even distribution"
    ],
    "stats": {
      "key_count": 88,
      "available_leds": 300,
      "leds_per_key_calc": 3.41,
      "remaining_leds": 36
    }
  }
}
```

---

## Priority 3: Improve Logging

### Issue
Silent failures and truncations make debugging difficult.

### Implementation

```python
def generate_auto_key_mapping(piano_size, led_count, led_orientation="normal", 
                              leds_per_key=None, mapping_base_offset=None):
    """Generate automatic key-to-LED mapping with improved logging"""
    
    specs = get_piano_specs(piano_size)
    key_count = specs["keys"]
    
    if key_count == 0:
        logger.warning(f"Piano size '{piano_size}' has 0 keys, returning empty mapping")
        return {}
    
    if mapping_base_offset is None:
        mapping_base_offset = 0
    
    available_leds = led_count - mapping_base_offset
    
    if available_leds <= 0:
        logger.error(
            f"Invalid LED count: total={led_count}, base_offset={mapping_base_offset}, "
            f"available={available_leds}"
        )
        return {}
    
    logger.info(f"Generating mapping for {piano_size} ({key_count} keys) with {available_leds} LEDs")
    
    # Calculate or use provided leds_per_key
    if leds_per_key is None:
        leds_per_key = available_leds // key_count
        remaining_leds = available_leds % key_count
        logger.info(
            f"Auto-calculated: {leds_per_key} LEDs/key with {remaining_leds} remaining "
            f"({remaining_leds} keys will get +1 LED)"
        )
    else:
        max_mappable_keys = available_leds // leds_per_key
        if max_mappable_keys < key_count:
            logger.warning(
                f"Requested {leds_per_key} LEDs/key, but only {max_mappable_keys}/{key_count} "
                f"keys can be mapped. Keys {specs['midi_start'] + max_mappable_keys} to "
                f"{specs['midi_end']} will be unmapped."
            )
            key_count = max_mappable_keys
        remaining_leds = available_leds - (key_count * leds_per_key)
    
    # Build mapping
    mapping = {}
    led_index = mapping_base_offset
    
    for key_num in range(key_count):
        midi_note = specs["midi_start"] + key_num
        key_led_count = leds_per_key + (1 if key_num < remaining_leds else 0)
        led_range = list(range(led_index, led_index + key_led_count))
        mapping[midi_note] = led_range
        led_index += key_led_count
    
    logger.info(
        f"Mapping complete: {len(mapping)} keys mapped, "
        f"LED range {mapping_base_offset} to {led_index - 1}"
    )
    
    return mapping
```

---

## Priority 4: Add Distribution Mode Configuration

### Issue
First-key distribution might not be ideal for all use cases.

### Implementation

Add to settings schema:

```python
'led': {
    ...
    'led_distribution_mode': {
        'type': 'string', 
        'default': 'even',
        'enum': ['even', 'spread', 'end']
    }
}
```

Implement in mapping function:

```python
def generate_auto_key_mapping(
    piano_size, led_count, led_orientation="normal",
    leds_per_key=None, mapping_base_offset=None,
    distribution_mode="even"  # NEW PARAMETER
):
    """
    distribution_mode options:
    - "even": Extra LEDs given to first keys (current behavior)
    - "spread": Extra LEDs spread throughout keyboard
    - "end": Extra LEDs given to last keys (high keys brighter)
    """
    
    # ... setup code ...
    
    if distribution_mode == "even":
        # Current behavior: first N keys get extra LED
        for key_num in range(key_count):
            midi_note = specs["midi_start"] + key_num
            key_led_count = leds_per_key + (1 if key_num < remaining_leds else 0)
            # ...
    
    elif distribution_mode == "spread":
        # Spread extra LEDs evenly across keyboard
        step = key_count // remaining_leds if remaining_leds > 0 else 1
        for key_num in range(key_count):
            midi_note = specs["midi_start"] + key_num
            key_led_count = leds_per_key + (1 if (key_num % step) < (key_num % step + 1) else 0)
            # ...
    
    elif distribution_mode == "end":
        # Extra LEDs go to last keys (where user looks)
        for key_num in range(key_count):
            midi_note = specs["midi_start"] + key_num
            key_led_count = leds_per_key + (1 if key_num >= (key_count - remaining_leds) else 0)
            # ...
```

---

## Priority 5: Add Offset Mode Selection

### Issue
Cascading offsets might be unintuitive for some users.

### Implementation

Add to settings schema:

```python
'calibration': {
    ...
    'offset_mode': {
        'type': 'string',
        'default': 'cascading',
        'enum': ['cascading', 'independent'],
        'description': 'How per-key offsets are applied'
    }
}
```

Implement in `apply_calibration_offsets_to_mapping`:

```python
def apply_calibration_offsets_to_mapping(
    mapping, global_offset=0, key_offsets=None, led_count=None,
    offset_mode="cascading"  # NEW PARAMETER
):
    """
    offset_mode options:
    - "cascading": Offset at note N affects N, N+1, ... (current)
    - "independent": Offset at note N affects only N
    """
    
    # ... setup code ...
    
    if offset_mode == "cascading":
        # Current behavior
        for offset_note, offset_value in sorted(normalized_key_offsets.items()):
            if offset_note <= midi_note_int:
                cascading_offset += offset_value
    
    elif offset_mode == "independent":
        # Only apply offset for this specific note
        cascading_offset = normalized_key_offsets.get(midi_note_int, 0)
```

---

## Testing Checklist

- [ ] Add `test_validate_auto_mapping_config()` unit tests
- [ ] Add `test_mapping_info_endpoint()` integration tests
- [ ] Add cascading offset tests with multiple offsets
- [ ] Add edge case tests (very few LEDs, many LEDs, exactly matching)
- [ ] Test distribution modes with various LED counts
- [ ] Test offset modes (cascading vs independent)
- [ ] Test with all piano sizes (25, 37, 49, 61, 76, 88 key)

---

## Frontend Changes Needed

Add new API calls in calibration section:

```typescript
async function loadMappingInfo() {
  const response = await fetch('/api/calibration/mapping-info');
  return await response.json();
}

async function validateMappingConfig(config: any) {
  const response = await fetch('/api/calibration/mapping-validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  return await response.json();
}
```

Display mapping info in UI:
- Show number of mapped vs unmapped keys
- Display LED distribution breakdown
- Show warnings and recommendations
- Allow user to change distribution mode before applying

---

## Rollout Plan

1. **Phase 1:** Add validation endpoint (no breaking changes)
2. **Phase 2:** Add mapping-info endpoint (informational only)
3. **Phase 3:** Improve logging throughout
4. **Phase 4:** Add distribution mode configuration
5. **Phase 5:** Add offset mode configuration

Each phase can be tested independently before proceeding to the next.

