# Layout Visualization Auto-Restore Feature ✅

## Feature Description
When "Show Layout" visualization is active and you click on a key to add/edit an adjustment, the layout will automatically restore after successfully saving the adjustment.

## Problem it Solves
Previously:
1. User has "Show Layout" turned on (all keys illuminated)
2. User clicks a key to fine-tune it
3. Layout visualization turns off so you can see the form
4. User adds adjustment and saves
5. Layout visualization stays OFF - user has to manually click "Show Layout" again

Now:
1. User has "Show Layout" turned on
2. User clicks a key to fine-tune it
3. Layout visualization auto-saves its state and turns off
4. User adds adjustment and saves
5. Layout visualization **automatically restores** with updated mapping ✨

## Implementation Details

### New Variable
```typescript
let shouldRestoreLayoutAfterAdjustment = false;
```
Tracks whether layout visualization should be re-enabled after adding an adjustment.

### Modified Function: `openAddOffsetForm()`
When a user clicks on a key to add/edit an adjustment:
1. Save the current state of `layoutVisualizationActive` to `shouldRestoreLayoutAfterAdjustment`
2. Turn off layout visualization (if it was on)
3. Close all LEDs with `turnOffAllLeds()`
4. Open the adjustment form

```typescript
function openAddOffsetForm(midiNote: number) {
  // Remember if layout visualization is currently active
  shouldRestoreLayoutAfterAdjustment = layoutVisualizationActive;
  
  // Turn off layout visualization while editing
  if (layoutVisualizationActive) {
    console.log('[LED] Saving layout visualization state for later restoration');
    layoutVisualizationActive = false;
    showingLayoutVisualization = false;
    turnOffAllLeds();
  }
  
  showAddForm = true;
  // ... rest of function
}
```

### Modified Function: `handleAddKeyOffset()`
After successfully adding an adjustment:
1. Check if `shouldRestoreLayoutAfterAdjustment` is true
2. If yes, re-trigger the layout visualization with the **updated LED mapping**
3. The updated mapping includes the new offset and trim adjustments!

```typescript
// Restore layout visualization if it was active before opening the form
if (shouldRestoreLayoutAfterAdjustment) {
  console.log('[LED] Restoring layout visualization after adjustment');
  shouldRestoreLayoutAfterAdjustment = false;
  
  // Re-trigger the layout visualization with the updated mapping
  try {
    showingLayoutVisualization = true;
    layoutVisualizationActive = true;
    
    // Collect LEDs for all white and black keys using UPDATED ledMapping
    const whiteKeyLeds: number[] = [];
    const blackKeyLeds: number[] = [];
    
    for (const note of whiteKeyNotes) {
      const indices = ledMapping[note];  // ← Uses updated mapping!
      if (indices && indices.length > 0) {
        whiteKeyLeds.push(...indices);
      }
    }
    
    // Light them up with updated indices
    if (whiteKeyLeds.length > 0) {
      await lightUpLedRangeWithColor(whiteKeyLeds, WHITE_KEY_COLOR);
    }
    // ...
  } catch (error) {
    // Handle error gracefully
  }
}
```

## User Experience Flow

### Scenario: Fine-tuning a key while visualizing layout

```
1. Click "🎹 Show Layout" button
   → All piano keys light up (white and black keys)

2. Visually notice: "Key 35 (C#2) seems too long on the right"

3. Click on Key 35 (C#2) in the piano to select it
   → Layout visualization turns OFF
   → Form opens to add/edit adjustment for this key
   → LEDs turn off

4. Adjust the right trim to reduce LED coverage
   → Slide trim slider or customize LED selection

5. Click "✓ Add Adjustment"
   → Adjustment saves to database
   → LED mapping reloads with new trim applied
   → Layout visualization automatically restores
   → You can NOW see the adjusted piano with the new mapping!

6. Visually verify: "Key 35 now looks better aligned"

7. Continue fine-tuning other keys without turning layout off/on manually
```

## Benefits

✅ **Faster Workflow** - No manual turning on/off of visualization
✅ **Visual Feedback** - Immediately see the effect of your adjustment
✅ **Reduced Friction** - One less button click per adjustment
✅ **Non-intrusive** - Only restores if it was on before (doesn't force it on)

## Technical Details

### State Preservation
- Uses `shouldRestoreLayoutAfterAdjustment` flag
- Only set when entering form, only used when exiting
- Automatically cleared after restoration
- Won't interfere with manual Show Layout toggle

### LED Mapping Updates
- Uses the `updateLedMapping()` call that's already in the success path
- Restores with fresh mapping that includes:
  - New offsets
  - New trims
  - Trim redistributions to adjacent keys
  - All other adjustments

### Error Handling
- If restoration fails, gracefully sets `layoutVisualizationActive = false`
- Doesn't crash the UI
- User can manually toggle layout if needed

## Files Modified

- `frontend/src/lib/components/CalibrationSection3.svelte`
  - Added `shouldRestoreLayoutAfterAdjustment` variable (line ~36)
  - Updated `openAddOffsetForm()` to save/restore state (lines ~700-730)
  - Updated `handleAddKeyOffset()` to re-trigger visualization (lines ~295-340)

## Testing Checklist

- [ ] Show Layout ON → Click key → Form opens → Layout OFF
- [ ] Add adjustment → Form closes → Layout AUTO-RESTORES
- [ ] Check that restored layout shows updated mapping
- [ ] Turn Show Layout OFF → Click key → Form opens → Layout stays OFF
- [ ] Add adjustment → Form closes → Layout stays OFF (not forced on)
- [ ] Cancel adding adjustment → Form closes → Layout stays OFF
- [ ] Multiple adjustments in sequence → All work smoothly
- [ ] Verify trim redistribution shows in restored layout

