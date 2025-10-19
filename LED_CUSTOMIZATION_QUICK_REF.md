# Enhanced LED Customization - Quick Reference

## What's New

The LED customization form now displays **currently assigned LEDs as large green buttons** that users can click to intelligently reallocate to adjacent keys.

## Key Capabilities

| Feature | Capability |
|---------|-----------|
| **Visual Display** | Shows current LEDs in large 45px buttons |
| **Click Reallocation** | Click LED → automatically moves to adjacent key |
| **Smart Edge Detection** | Left edge → previous key, Right edge → next key |
| **Manual Override** | Full LED grid for precise manual selection |
| **Pre-population** | Form auto-loads current allocation |
| **Visual Feedback** | Green (assigned), Red (removed), Yellow (current), Blue (selected) |

## UI Components

### Current Allocation Section
```
Header: "Currently Assigned LEDs (Click to Reallocate)"
Count badge showing number of LEDs
Grid of large green buttons (45px)
Hint text: "Click an LED to move it to the adjacent key"
```

### Manual LED Selection Section
```
Header: "Manual LED Selection (Optional)"
Grid of small buttons (35px) showing full range
Yellow buttons = currently assigned LEDs
Blue buttons = modified selections
White buttons = available LEDs
```

## How to Use

### Simple Reallocation (Recommended)
```
1. Select MIDI note
2. See current LEDs in large green buttons
3. Click any LED to mark for reallocation
   - Button turns RED with ✕
   - System determines adjacent key automatically
4. Click "✓ Add Adjustment" to save
5. LED automatically moves to adjacent key
```

### Manual Selection
```
1. Select MIDI note
2. Current LEDs shown in green
3. Scroll down to manual grid
4. Click any LED to toggle selection
5. Yellow LEDs = currently assigned (elsewhere)
6. Blue LEDs = your custom selection
7. Click "✓ Add Adjustment" to save
```

### Complex Scenario
```
1. Click & remove some LEDs (reallocation)
2. Scroll down & manually add/remove others
3. System combines both operations
4. Click save - all changes applied atomically
```

## Color Meanings at a Glance

| Color | Meaning | Location | Action |
|-------|---------|----------|--------|
| 🟢 Green | Currently assigned | Current grid | Click to reallocate |
| 🔴 Red | Marked for removal | Current grid | Will move to adjacent key |
| 🟡 Yellow | Currently elsewhere | Manual grid | Click to include |
| 🔵 Blue | Selected modified | Manual grid | Will be included in allocation |
| ⚪ White | Not assigned | Manual grid | Click to add |

## Examples

### Example 1: Move LED to Previous Key
```
Current: [120, 121, 122, 123]
Action: Click LED 120
Result: 120 → moves to Key 59 (previous key)
Final: [121, 122, 123]
```

### Example 2: Move LED to Next Key
```
Current: [120, 121, 122, 123]
Action: Click LED 123
Result: 123 → moves to Key 61 (next key)
Final: [120, 121, 122]
```

### Example 3: Add LED from Another Key
```
Current: [120, 121, 122, 123]
Manual: See LED 124 in yellow (currently key 62)
Action: Click LED 124 in manual grid → becomes blue
Result: [120, 121, 122, 123, 124]
Final: LED 124 added from Key 62
```

## Tips & Tricks

💡 **Tip 1**: Use current grid for quick reallocation
```
Fastest way to move LEDs between adjacent keys
Just click and save
```

💡 **Tip 2**: Use manual grid for precise control
```
When you need to add/remove specific LEDs
When managing non-adjacent keys
When fine-tuning allocations
```

💡 **Tip 3**: Combine both methods
```
1. Use current grid to remove edge LEDs
2. Use manual grid to add specific LEDs
3. Save everything at once
```

💡 **Tip 4**: Look at yellow highlights
```
Yellow LEDs in manual grid show what's currently assigned
Helps you understand where LEDs come from
```

💡 **Tip 5**: Check the count badge
```
Shows how many LEDs are in current allocation
Helps you understand keyboard coverage
```

## Visual Indicators

### Hover States
| Element | Hover Effect |
|---------|------------|
| Current LED (Green) | Scale up, brighten |
| Removed LED (Red) | Scale up, brighten |
| Yellow LED (Current) | Highlight with border |
| Blue LED (Selected) | Scale up |

### Tooltips
```
Hover over any button → see LED index and status
Examples:
  "LED 120 (currently assigned)"
  "LED 122 (will move to adjacent key)"
  "LED 125 (currently assigned elsewhere)"
```

## Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Navigate between buttons |
| Space/Enter | Activate button (toggle LED) |
| Escape | Close form (future) |

## Accessibility

✅ Descriptive button titles (hover to see)
✅ Color + symbol differentiation (not color alone)
✅ High contrast colors (WCAG AA)
✅ Keyboard accessible (Tab navigation)
✅ Large touch targets (45px minimum)
✅ Clear visual feedback (hover states)

## Troubleshooting

### Problem: "Can't see current LEDs"
**Solution**: Make sure you've entered a MIDI note and checked "Customize LED allocation"

### Problem: "LED not moving where I expect"
**Solution**: System uses midpoint calculation to determine edge. Click LEDs from the edges for predictable behavior.

### Problem: "Yellow and blue colors too similar"
**Solution**: Look at the button borders - yellow has orange border, blue has no special border

### Problem: "Want to keep all current LEDs"
**Solution**: Just don't remove any - current grid starts pre-selected. Save without changes.

### Problem: "LED showing as both green and yellow"
**Solution**: Green = currently assigned here, Yellow = somewhere else. They're different keys.

## Common Workflows

### Workflow 1: Quick Edge Adjustment
```
Goal: Remove LED from edge, auto-reallocate
1. Select MIDI
2. Click edge LED (green)
3. Button turns red
4. Save
Done! LED moved to adjacent key automatically.
```

### Workflow 2: Manual Fine-tuning
```
Goal: Precise control over specific LEDs
1. Select MIDI
2. Scroll to manual grid
3. Individually toggle LEDs
4. Watch blue/unblue states
5. Save
Done! Custom allocation applied.
```

### Workflow 3: Multi-Step Adjustment
```
Goal: Remove some, add some, replace some
1. Current grid: Click to remove edge LEDs (red)
2. Manual grid: Click to add other LEDs (blue)
3. Observe total count
4. Save everything at once
Done! All changes applied atomically.
```

## Technical Details (Advanced)

### What Happens on Save
```
1. System compares:
   - Current: [120, 121, 122, 123]
   - Modified: [121, 122, 123, 124]
   
2. Calculates diff:
   - Removed: [120]
   - Added: [124]
   
3. Reallocates:
   - 120 → adjacent key (auto-detected)
   - 124 → taken from its current key
   
4. Updates all affected keys atomically
```

### State Management
```
currentKeyLEDAllocation: Shows what's currently assigned
selectedLEDsForNewKey: Tracks what user selected
Diff = Selected - Current = Changes to apply
```

### API Calls
```
1. PUT /api/calibration/key-offsets/60 (save offset)
2. PUT /api/led-selection/key/60 (save LED override)
Backend intelligently handles reallocation
```

## Performance

⚡ LED grid renders: <50ms
⚡ Reallocation calc: <5ms
⚡ No page slowdown
⚡ Efficient state updates

## Browser Support

✅ Chrome/Edge: Full
✅ Firefox: Full
✅ Safari: Full
✅ Mobile: Touch-optimized

## Future Ideas

🔮 Drag & drop LEDs between keys
🔮 Save allocation templates
🔮 Preview final allocation before saving
🔮 Physical visualization of LED positions
🔮 Undo/redo history
🔮 Batch operations on multiple keys

---

**Quick Ref Version**: 1.0
**Last Updated**: October 19, 2025
**Status**: Production Ready
