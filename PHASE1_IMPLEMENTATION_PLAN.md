# Phase 1 Implementation Plan: Hybrid Physical Geometry Integration

## Scope

Integrate your piano.py's **physical key geometry** and **symmetry analysis** into our current system while maintaining full backward compatibility.

## Architecture

### New Files to Create

#### 1. `backend/config_led_mapping_physical.py`
Extracted from your piano.py with integration points:

```python
# Constants from your script
WHITE_KEY_WIDTH = 23.5
WHITE_KEY_GAP = 1.0
BLACK_KEY_WIDTH = 13.7
CUT_VALUES = {...}

# Functions to extract:
- calculate_all_key_geometries()           # Your exact geometry calc
- analyze_led_placement_on_top()           # Physical overlap detection
- perform_symmetry_analysis()              # Quality scoring
- run_single_key_analysis()                # Per-key detailed analysis (optional)

# New integration function:
- generate_physical_mapping_stats(key_led_mapping)
  Input: Current system's mapping output
  Output: Enhanced with physical geometry analysis
```

#### 2. Enhanced `backend/schemas/settings_schema.py`
```python
# Add new settings categories and keys for piano geometry
# Add validation for LED physical parameters
# Keep defaults matching your script's values
```

#### 3. Enhanced `backend/services/settings_service.py`
```python
# Add new default settings for piano/led physical parameters
# Ensure they're persisted in settings.db
```

## Implementation Steps

### Step 1: Extract and Adapt piano.py Functions

**File**: `backend/config_led_mapping_physical.py` (NEW)

```python
#!/usr/bin/env python3
"""
Physical geometry-based LED mapping analysis
Extracted and adapted from piano.py
"""

import logging
from typing import Dict, List, Any, Tuple
from backend.logging_config import get_logger

logger = get_logger(__name__)

# Constants (configurable via settings later)
DEFAULT_WHITE_KEY_WIDTH = 23.5
DEFAULT_BLACK_KEY_WIDTH = 13.7
DEFAULT_WHITE_KEY_GAP = 1.0
DEFAULT_LED_PHYSICAL_WIDTH = 3.5
DEFAULT_LED_STRIP_OFFSET = DEFAULT_LED_PHYSICAL_WIDTH / 2
DEFAULT_LED_OVERHANG_THRESHOLD = 1.5

class PhysicalKeyGeometry:
    """Calculate exact piano key geometry"""
    
    @staticmethod
    def calculate_all_key_geometries(
        white_key_width=DEFAULT_WHITE_KEY_WIDTH,
        black_key_width=DEFAULT_BLACK_KEY_WIDTH,
        white_key_gap=DEFAULT_WHITE_KEY_GAP
    ) -> List[Dict[str, Any]]:
        """
        Calculate exact positions of all 88 piano keys with white/black key cuts.
        
        Returns:
            List of geometry dicts with positions for each key
        """
        # ... Your implementation ...
        pass

class LEDPlacementAnalyzer:
    """Analyze physical LED placement on keyboard"""
    
    @staticmethod
    def analyze_led_placement_on_top(
        key_data: Dict[str, float],
        led_spacing_mm: float,
        led_width: float = DEFAULT_LED_PHYSICAL_WIDTH,
        led_offset: float = DEFAULT_LED_STRIP_OFFSET,
        threshold: float = DEFAULT_LED_OVERHANG_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Determine which LEDs physically overlay this key.
        
        Args:
            key_data: Key geometry from calculate_all_key_geometries()
            led_spacing_mm: LED spacing (1000/leds_per_meter)
            led_width: Physical LED width in mm
            led_offset: Global strip offset in mm
            threshold: Allowed overhang in mm
            
        Returns:
            List of LEDs on this key with center positions
        """
        # ... Your implementation ...
        pass

class SymmetryAnalyzer:
    """Analyze and score LED placement symmetry"""
    
    @staticmethod
    def perform_symmetry_analysis(
        key_data: Dict[str, float],
        led_analysis: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze symmetry of LED placement on key.
        
        Returns:
            Classification: "Excellent Center Alignment", "Symmetrical", "Centered", "Asymmetrical"
            Details with distance measurements
        """
        # ... Your implementation ...
        pass

def generate_physical_mapping_analysis(
    all_geometries: List[Dict],
    key_led_mapping: Dict[int, List[int]],
    settings_service: Any
) -> Dict[str, Any]:
    """
    INTEGRATION POINT: Take current mapping and enhance with physical analysis.
    
    This function:
    1. Gets key geometries (exact positions)
    2. Analyzes LED placement for each key
    3. Scores symmetry/alignment quality
    4. Detects gaps and neighbor sharing
    
    Returns:
        {
            "mapping": key_led_mapping,  # Current mapping
            "physical_analysis": {
                0: {  # Per key
                    "symmetry": "Excellent Center Alignment",
                    "symmetry_score": 0.95,
                    "leds": [4, 5, 6],
                    "placement_quality": "Optimal"
                },
                ...
            },
            "quality_metrics": {
                "avg_symmetry": 0.92,
                "keys_with_gaps": [],
                "keys_with_asymmetry": [15, 42, ...],
                "overall_score": 0.88
            }
        }
    """
    # Get settings (LED width, offset, threshold, key dimensions)
    # For each key in mapping:
    #   - Get key geometry
    #   - Analyze LED placement
    #   - Score symmetry
    # Return enhanced mapping with quality metrics
    pass
```

### Step 2: Update Settings Schema

**File**: `backend/schemas/settings_schema.py`

Add to the schema dictionary:

```python
'piano': {
    'type': 'object',
    'required': [],
    'properties': {
        'white_key_width': {
            'type': 'number',
            'minimum': 20,
            'maximum': 30,
            'default': 23.5,
            'description': 'Width of white keys in mm'
        },
        'black_key_width': {
            'type': 'number',
            'minimum': 10,
            'maximum': 20,
            'default': 13.7,
            'description': 'Width of black keys in mm'
        },
        'white_key_gap': {
            'type': 'number',
            'minimum': 0.5,
            'maximum': 2.0,
            'default': 1.0,
            'description': 'Gap between adjacent white keys in mm'
        }
    }
},

'calibration': {
    'type': 'object',
    'required': [],
    'properties': {
        'use_physical_geometry': {
            'type': 'boolean',
            'default': True,
            'description': 'Use physical geometry analysis for mapping quality'
        },
        'symmetry_tolerance': {
            'type': 'number',
            'minimum': 0.1,
            'maximum': 2.0,
            'default': 0.8,
            'description': 'Tolerance for symmetry detection in mm'
        },
        'led_physical_width': {
            'type': 'number',
            'minimum': 2,
            'maximum': 6,
            'default': 3.5,
            'description': 'Physical width of LED in mm'
        },
        'led_strip_offset': {
            'type': 'number',
            'minimum': 0.5,
            'maximum': 5,
            'default': 1.75,
            'description': 'LED strip vertical offset in mm'
        },
        'led_overhang_threshold': {
            'type': 'number',
            'minimum': 0.5,
            'maximum': 3.0,
            'default': 1.5,
            'description': 'Maximum allowed LED overhang outside key in mm'
        }
    }
}
```

### Step 3: Update Settings Service Defaults

**File**: `backend/services/settings_service.py`

Update `_get_default_settings_schema()`:

```python
def _get_default_settings_schema(self):
    return {
        # ... existing categories ...
        
        'piano': {
            'white_key_width': {'type': 'number', 'default': 23.5},
            'black_key_width': {'type': 'number', 'default': 13.7},
            'white_key_gap': {'type': 'number', 'default': 1.0},
        },
        
        'calibration': {
            'use_physical_geometry': {'type': 'boolean', 'default': True},
            'symmetry_tolerance': {'type': 'number', 'default': 0.8},
            'led_physical_width': {'type': 'number', 'default': 3.5},
            'led_strip_offset': {'type': 'number', 'default': 1.75},
            'led_overhang_threshold': {'type': 'number', 'default': 1.5},
        }
    }
```

### Step 4: Enhance Calibration API Endpoint

**File**: `backend/api/calibration.py`

Add new endpoint:

```python
@calibration_bp.route('/physical-analysis', methods=['GET'])
def get_physical_analysis():
    """Get physical geometry analysis of current mapping"""
    try:
        settings_service = get_settings_service()
        key_led_mapping = get_key_led_mapping()
        
        # Import new module
        from backend.config_led_mapping_physical import (
            PhysicalKeyGeometry,
            generate_physical_mapping_analysis
        )
        
        # Get piano geometry
        white_key_width = settings_service.get_setting('piano', 'white_key_width', 23.5)
        black_key_width = settings_service.get_setting('piano', 'black_key_width', 13.7)
        white_key_gap = settings_service.get_setting('piano', 'white_key_gap', 1.0)
        
        geometries = PhysicalKeyGeometry.calculate_all_key_geometries(
            white_key_width, black_key_width, white_key_gap
        )
        
        # Generate analysis
        analysis = generate_physical_mapping_analysis(
            geometries,
            key_led_mapping,
            settings_service
        )
        
        return jsonify(analysis), 200
    except Exception as e:
        logger.error(f"Error getting physical analysis: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

# Enhance existing endpoint
@calibration_bp.route('/mapping-quality', methods=['GET'])
def get_mapping_quality():
    """Get mapping quality metrics (enhanced with symmetry)"""
    # ... existing code ...
    # Add physical analysis if enabled
    use_physical = settings_service.get_setting('calibration', 'use_physical_geometry', True)
    if use_physical:
        physical_analysis = get_physical_analysis_data()
        result['physical_analysis'] = physical_analysis
    # ... return ...
```

### Step 5: Database Migration

Run on first startup (in `app.py` or migration script):

```python
def ensure_settings_initialized():
    """Ensure all settings are in database"""
    settings_service = get_settings_service()
    
    # Piano geometry defaults
    settings_service.set_setting('piano', 'white_key_width', 23.5)
    settings_service.set_setting('piano', 'black_key_width', 13.7)
    settings_service.set_setting('piano', 'white_key_gap', 1.0)
    
    # Calibration defaults
    settings_service.set_setting('calibration', 'use_physical_geometry', True)
    settings_service.set_setting('calibration', 'symmetry_tolerance', 0.8)
    settings_service.set_setting('calibration', 'led_physical_width', 3.5)
    settings_service.set_setting('calibration', 'led_strip_offset', 1.75)
    settings_service.set_setting('calibration', 'led_overhang_threshold', 1.5)
```

## Testing Plan

### Unit Tests
```
tests/test_physical_geometry.py
├── test_calculate_all_key_geometries
│   └── Verify key positions match expected values
├── test_analyze_led_placement
│   └── Verify LED detection with various thresholds
└── test_symmetry_analysis
    └── Verify quality scoring

tests/test_settings_integration.py
├── test_settings_schema_piano
├── test_settings_schema_calibration
└── test_settings_persistence
```

### Integration Tests
```
tests/test_mapping_physical_integration.py
├── test_physical_analysis_endpoint
│   └── Call /physical-analysis, verify response format
├── test_enhanced_quality_endpoint
│   └── Verify /mapping-quality includes physical data
└── test_settings_configuration
    └── Verify all new settings readable/writable
```

### Manual Testing
1. Start service with defaults
2. Call `/api/calibration/physical-analysis`
3. Verify response contains symmetry data
4. Update settings via `/api/settings`
5. Verify physical analysis updates accordingly

## Rollout Strategy

1. ✅ Merge new code (backward compatible)
2. ✅ Deploy to test environment
3. ✅ Verify endpoints work
4. ✅ Deploy to Pi with clean database (auto-initializes)
5. ✅ Verify settings populated
6. ✅ Frontend optionally displays symmetry data

## Benefits After Implementation

✅ Per-key symmetry scores available
✅ Physical geometry exactly matches piano
✅ Gap detection warnings
✅ Quality metrics based on real physics
✅ User-adjustable parameters for tuning
✅ Foundation for Phase 2 (better algorithm)

## Risk Assessment

**Risk Level**: LOW

- ✅ Backward compatible (adds data, doesn't change existing)
- ✅ Non-breaking changes (new settings optional)
- ✅ Isolated module (physical analysis separate)
- ✅ Current mapping unchanged
- ✅ Can be disabled with feature flag

## Timeline Estimate

- **Phase 1 Implementation**: 4-6 hours
- **Testing**: 2-3 hours
- **Documentation**: 1 hour
- **Total**: ~1 day work
