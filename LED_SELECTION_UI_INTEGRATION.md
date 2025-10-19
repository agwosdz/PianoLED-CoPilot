# LED Selection Override UI Integration

## Overview
The LED Selection Override feature has been integrated into the Calibration panel in the Settings page. Users can now adjust which specific LEDs are assigned to each piano key directly from the calibration interface.

## What Was Integrated

### Component Integration
- **Component**: `LEDSelectionPanel.svelte`
- **Location**: `frontend/src/lib/components/LEDSelectionPanel.svelte`
- **Integration Point**: Settings → Calibration section (after Individual Key Offsets)

### Changes Made

#### 1. Settings Page (`frontend/src/routes/settings/+page.svelte`)
```svelte
// Added import
import LEDSelectionPanel from '$lib/components/LEDSelectionPanel.svelte';

// Added to calibration section
<div class="led-selection-wrapper">
  <LEDSelectionPanel />
</div>
```

#### 2. Styling
Added visual hierarchy with dashed border and gradient background:
```css
.led-selection-wrapper {
  border: 2px dashed #2563eb;
  border-radius: 12px;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f0f7ff 0%, #e0eaff 100%);
}
```

## UI Workflow

### Complete Per-Key Adjustment Panel
Users now have **two complementary tools** in the Calibration section:

1. **Section 2 - LED Range Selection**
   - Choose which LED indices to use globally
   - Set start and end LED for the entire keyboard

2. **Section 3 - Individual Key Offsets**
   - Add timing/positioning offsets for specific keys
   - Measured in LED units

3. **LED Selection Override** (NEW)
   - Select which specific LEDs attach to each key
   - Fine-tune LED allocation per key
   - Override auto-mapping on a per-key basis
   - Removed LEDs auto-reallocate to neighbors

## Feature Breakdown

### Step 1: Select a Piano Key
- Interactive grid showing all 88 piano keys
- Highlights:
  - **Blue**: Currently selected key
  - **Green**: Keys with active overrides
  - Shows MIDI note info in tooltips

### Step 2: Select LEDs for That Key
- Available LED range displayed (e.g., "120 - 246")
- LED grid with toggle buttons
- Real-time counter: "Selected: X LEDs"

### Step 3: Apply or Cancel
- **✓ Apply Selection**: Save the override for this key
- **Clear This Key**: Remove override for this key only
- **Cancel**: Exit without saving

### Active Overrides Summary
- Shows all keys with active overrides
- Displays LED allocation: `[120, 121, 122]`
- Quick delete buttons per override
- "Clear All Overrides" button to reset

## Data Flow

### API Endpoints Used
```
GET    /api/led-selection/all              # Fetch all overrides on mount
PUT    /api/led-selection/key/<midi_note>  # Save override for a key
DELETE /api/led-selection/key/<midi_note>  # Clear override for a key
DELETE /api/led-selection/all              # Clear all overrides
```

### State Management
- **Store**: `$lib/stores/ledSelection.ts`
- **State**: Stores valid LED range, current overrides, loading state
- **API Layer**: Encapsulated in `ledSelectionAPI` store

## Visual Hierarchy

The integration fits seamlessly into the Calibration workflow:

```
Calibration Section
├── Calibration Section 2 (LED Range Selection)
├── Calibration Section 3 (Individual Key Offsets)
└── LED Selection Override [NEW]
    ├── Step 1: Select a Piano Key
    ├── Step 2: Select LEDs for That Key
    ├── Step 3: Apply/Save
    └── Active Overrides Summary
```

## User Experience Enhancements

### Error Handling
- Displays error messages from API failures
- Shows success messages on apply
- Disabled buttons during loading

### Responsive Design
- Mobile-friendly grid layouts
- Adjusts column counts based on screen size
- Touch-friendly button sizes

### Accessibility
- Descriptive button labels and tooltips
- MIDI note display with octave info
- Section hints explaining valid ranges

## Backend Integration

No new backend endpoints needed - uses existing API:
- `backend/api/led_selection.py` - RESTful endpoints
- `backend/services/led_selection_service.py` - Core logic
- `backend/models/led_selection.py` - Data models

## Testing Checklist

- [ ] Navigate to Settings → Calibration
- [ ] See LED Selection Override panel below Individual Key Offsets
- [ ] Click a key in the piano grid
- [ ] Toggle LEDs on/off in the grid
- [ ] Apply selection - verify success message
- [ ] Check "Active Overrides" section updates
- [ ] Edit override by selecting same key again
- [ ] Clear individual override
- [ ] Clear all overrides
- [ ] Verify changes persist on page reload

## Next Steps (Optional Enhancements)

1. **Visual Preview**: Show physical LED positions for selected key
2. **Bulk Operations**: Select multiple keys at once
3. **Import/Export**: Save and load LED configurations
4. **Visualization**: Live piano display showing LED-to-key mapping
5. **Undo/Redo**: History of changes with restore options

## Files Modified
- `frontend/src/routes/settings/+page.svelte` - Added component import and integrated into UI

## Files Already Existed (No Changes Needed)
- `frontend/src/lib/components/LEDSelectionPanel.svelte` - Ready to use
- `frontend/src/lib/stores/ledSelection.ts` - State management
- `backend/api/led_selection.py` - API endpoints
- `backend/services/led_selection_service.py` - Business logic
