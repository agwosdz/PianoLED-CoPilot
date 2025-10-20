# Play and Learn - Backend API Implementation

## API Endpoints

### 1. Get Learning Options

**Endpoint:** `GET /api/learning/options`

**Purpose:** Retrieve current learning mode settings from the database

**Response:**
```json
{
  "success": true,
  "wait_for_notes_enabled": false,
  "timing_window_ms": 500,
  "left_hand_white": "#ff0000",
  "left_hand_black": "#cc0000",
  "right_hand_white": "#0000ff",
  "right_hand_black": "#0000cc"
}
```

**Implementation Location:** `backend/app.py`

```python
@app.route('/api/learning/options', methods=['GET'])
def get_learning_options():
    """Get current learning mode options"""
    try:
        options = {
            'success': True,
            'wait_for_notes_enabled': settings_service.get_setting('learning_mode', 'wait_for_notes_enabled', False),
            'timing_window_ms': settings_service.get_setting('learning_mode', 'timing_window_ms', 500),
            'left_hand_white': settings_service.get_setting('learning_mode', 'left_hand_white', '#ff0000'),
            'left_hand_black': settings_service.get_setting('learning_mode', 'left_hand_black', '#cc0000'),
            'right_hand_white': settings_service.get_setting('learning_mode', 'right_hand_white', '#0000ff'),
            'right_hand_black': settings_service.get_setting('learning_mode', 'right_hand_black', '#0000cc')
        }
        return jsonify(options)
    except Exception as e:
        logger.error(f"Error getting learning options: {e}")
        return jsonify({'error': str(e)}), 500
```

### 2. Update Learning Options

**Endpoint:** `POST /api/learning/options`

**Purpose:** Save learning mode settings to the database

**Request Body:**
```json
{
  "wait_for_notes_enabled": boolean,
  "timing_window_ms": number,
  "left_hand_white": "#rrggbb",
  "left_hand_black": "#rrggbb",
  "right_hand_white": "#rrggbb",
  "right_hand_black": "#rrggbb"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Learning options saved"
}
```

**Implementation Location:** `backend/app.py`

```python
@app.route('/api/learning/options', methods=['POST'])
def update_learning_options():
    """Update learning mode options"""
    try:
        data = request.get_json()
        
        # Validate input
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid request format'}), 400
        
        # Save settings
        if 'wait_for_notes_enabled' in data:
            settings_service.set_setting('learning_mode', 'wait_for_notes_enabled', data['wait_for_notes_enabled'])
        
        if 'timing_window_ms' in data:
            timing = data['timing_window_ms']
            if not isinstance(timing, (int, float)) or timing < 100 or timing > 2000:
                return jsonify({'error': 'timing_window_ms must be between 100 and 2000'}), 400
            settings_service.set_setting('learning_mode', 'timing_window_ms', timing)
        
        # Validate and save colors
        color_keys = ['left_hand_white', 'left_hand_black', 'right_hand_white', 'right_hand_black']
        for color_key in color_keys:
            if color_key in data:
                color_value = data[color_key]
                # Validate hex color format
                if not isinstance(color_value, str) or not re.match(r'^#[0-9a-fA-F]{6}$', color_value):
                    return jsonify({'error': f'{color_key} must be valid hex color (e.g., #ff0000)'}), 400
                settings_service.set_setting('learning_mode', color_key, color_value)
        
        logger.info("Learning options updated")
        return jsonify({'success': True, 'message': 'Learning options saved'})
    
    except Exception as e:
        logger.error(f"Error updating learning options: {e}")
        return jsonify({'error': str(e)}), 500
```

## Settings Integration

### 1. Add to Default Settings Schema

**File:** `backend/services/settings_service.py`

```python
DEFAULT_SETTINGS = {
    # ... existing settings ...
    
    'learning_mode': {
        'wait_for_notes_enabled': False,
        'timing_window_ms': 500,
        'left_hand_white': '#ff0000',
        'left_hand_black': '#cc0000',
        'right_hand_white': '#0000ff',
        'right_hand_black': '#0000cc'
    }
}
```

### 2. Initialize in _get_default_settings_schema()

```python
def _get_default_settings_schema(self) -> Dict[str, Dict[str, Any]]:
    """Generate default settings schema with all categories and keys"""
    return {
        # ... existing categories ...
        
        'learning_mode': {
            'wait_for_notes_enabled': {
                'type': 'boolean',
                'default': False,
                'description': 'Enable pause-for-notes learning mode'
            },
            'timing_window_ms': {
                'type': 'integer',
                'default': 500,
                'min': 100,
                'max': 2000,
                'description': 'Timing tolerance for note matching in milliseconds'
            },
            'left_hand_white': {
                'type': 'string',
                'default': '#ff0000',
                'description': 'Color for left hand white keys (hex format)'
            },
            'left_hand_black': {
                'type': 'string',
                'default': '#cc0000',
                'description': 'Color for left hand black keys (hex format)'
            },
            'right_hand_white': {
                'type': 'string',
                'default': '#0000ff',
                'description': 'Color for right hand white keys (hex format)'
            },
            'right_hand_black': {
                'type': 'string',
                'default': '#0000cc',
                'description': 'Color for right hand black keys (hex format)'
            }
        }
    }
```

## Modifications to Existing Services

### PlaybackService Changes (Future - Phase 2)

```python
class PlaybackMode(Enum):
    """Playback mode options"""
    NORMAL = "normal"
    LEARNING = "learning"

class PlaybackService:
    def __init__(self, ..., settings_service=None):
        # ... existing code ...
        self._settings_service = settings_service
        self._playback_mode = PlaybackMode.NORMAL
        self._learning_paused_at_event = None
        self._expected_notes_for_learning = []
    
    def set_playback_mode(self, mode: PlaybackMode):
        """Set playback mode (normal or learning)"""
        self._playback_mode = mode
    
    def is_learning_mode(self) -> bool:
        """Check if learning mode is enabled"""
        if not self._settings_service:
            return False
        return self._settings_service.get_setting('learning_mode', 'wait_for_notes_enabled', False)
```

### LEDController Changes (Future - Phase 2)

```python
def get_hand_color(self, hand: str, is_black_key: bool = False) -> Tuple[int, int, int]:
    """
    Get the color for a specific hand and key type
    
    Args:
        hand: 'right', 'left', 'both', or 'unknown'
        is_black_key: True for black keys, False for white keys
    
    Returns:
        RGB tuple (r, g, b)
    """
    if not self._settings_service:
        return (255, 255, 255)  # Default white
    
    # Map to setting keys
    if hand == 'left':
        key = 'left_hand_black' if is_black_key else 'left_hand_white'
    elif hand == 'right':
        key = 'right_hand_black' if is_black_key else 'right_hand_white'
    else:
        return (255, 255, 255)  # Unknown hand, use white
    
    # Get color from settings
    color_hex = self._settings_service.get_setting('learning_mode', key, '#ffffff')
    
    # Convert hex to RGB
    return self._hex_to_rgb(color_hex)

def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    try:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (255, 255, 255)  # Default to white on error
```

## Database Schema

### Settings Table Entry

```sql
INSERT INTO settings (category, key, value, type, description)
VALUES 
  ('learning_mode', 'wait_for_notes_enabled', 'false', 'boolean', 'Enable pause-for-notes learning mode'),
  ('learning_mode', 'timing_window_ms', '500', 'integer', 'Timing tolerance for note matching'),
  ('learning_mode', 'left_hand_white', '#ff0000', 'string', 'Color for left hand white keys'),
  ('learning_mode', 'left_hand_black', '#cc0000', 'string', 'Color for left hand black keys'),
  ('learning_mode', 'right_hand_white', '#0000ff', 'string', 'Color for right hand white keys'),
  ('learning_mode', 'right_hand_black', '#0000cc', 'string', 'Color for right hand black keys');
```

## Testing

### API Tests

```python
# test_learning_api.py

def test_get_learning_options():
    """Test retrieving learning options"""
    response = client.get('/api/learning/options')
    assert response.status_code == 200
    data = response.get_json()
    assert 'success' in data
    assert 'wait_for_notes_enabled' in data
    assert 'timing_window_ms' in data
    assert 'left_hand_white' in data
    assert 'left_hand_black' in data
    assert 'right_hand_white' in data
    assert 'right_hand_black' in data

def test_update_learning_options():
    """Test updating learning options"""
    new_options = {
        'wait_for_notes_enabled': True,
        'timing_window_ms': 750,
        'left_hand_white': '#ff0000',
        'left_hand_black': '#cc0000',
        'right_hand_white': '#0000ff',
        'right_hand_black': '#0000cc'
    }
    response = client.post('/api/learning/options', json=new_options)
    assert response.status_code == 200
    assert response.get_json()['success'] is True

def test_invalid_timing_window():
    """Test validation of timing window"""
    invalid_options = {
        'timing_window_ms': 50  # Too low
    }
    response = client.post('/api/learning/options', json=invalid_options)
    assert response.status_code == 400

def test_invalid_hex_color():
    """Test validation of hex color"""
    invalid_options = {
        'left_hand_white': 'invalid_color'
    }
    response = client.post('/api/learning/options', json=invalid_options)
    assert response.status_code == 400
```

## Implementation Priority

### Phase 1 (Current) ✅
- ✅ Frontend UI: Learning Options Card
- ✅ Frontend State Management
- ✅ Frontend Styling

### Phase 2 (Next)
- Settings schema integration
- API endpoints implementation
- Settings persistence
- Database migration (if needed)

### Phase 3 (Later)
- Playback pause logic for learning mode
- Note verification algorithm
- Color application in playback
- Full integration testing

## Integration Checklist

- [ ] Settings schema added to SettingsService
- [ ] GET /api/learning/options endpoint working
- [ ] POST /api/learning/options endpoint working
- [ ] Color values validated (hex format)
- [ ] Timing window validated (100-2000 ms)
- [ ] Settings persist across sessions
- [ ] API errors handled gracefully
- [ ] Frontend loads options on startup
- [ ] Frontend saves on every change
- [ ] Reset to defaults works
- [ ] All validation working

## Error Handling

### Common Errors

1. **Invalid Hex Color**
   - Status: 400
   - Message: "{color_key} must be valid hex color (e.g., #ff0000)"

2. **Timing Window Out of Range**
   - Status: 400
   - Message: "timing_window_ms must be between 100 and 2000"

3. **Database Error**
   - Status: 500
   - Message: "Error updating learning options: {error}"

4. **API Not Available**
   - Frontend: Uses local defaults, continues normally
   - Shows toast/error message to user

## Future Enhancements

1. **Color Presets**
   - Save favorite color combinations
   - Quick switch between presets

2. **Advanced Timing**
   - Different windows per hand
   - Adaptive timing based on difficulty

3. **Hand Detection Feedback**
   - Show which hand is currently playing
   - Display confidence scores

4. **Learning Analytics**
   - Track accuracy of note matching
   - Store learning session history
   - Progress reports

