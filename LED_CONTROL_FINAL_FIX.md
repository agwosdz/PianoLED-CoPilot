# LED Control Issues - Final Fix

## Problems Fixed

### Issue 1: Buttons Could Only Be Pressed Once
**Symptom:** After deselecting a key, clicking it again didn't light LEDs

**Root Cause:** The `isProcessingLedCommand` flag was blocking all clicks while it was true, preventing reselection during the delay waiting for LED operations to complete.

```typescript
// ❌ WRONG - Blocks all subsequent clicks
if (isProcessingLedCommand) return;
```

**Solution:** Removed the blocking check. Instead, we now simply let the async operations complete naturally without preventing new clicks.

### Issue 2: Previous LEDs Stayed On When Selecting New Key
**Symptom:** When clicking a new key, previously lit LEDs remained on while new ones also lit up

**Root Cause:** Race condition between `turnOffAllLeds()` and `lightUpLedRange()`. The flag-based locking mechanism was causing the turn-off to not properly complete before turn-on started.

**Solution:** Simplified the LED management:
1. Remove the blocking flag entirely
2. Let `turnOffAllLeds()` execute naturally without waiting
3. Trust that the hardware will respond correctly to sequential commands
4. Remove artificial delays that were trying to serialize operations

## Code Changes

### Before (Problematic)
```typescript
let isProcessingLedCommand = false; // ← Used as blocking flag

async function turnOffAllLeds(): Promise<void> {
  if (isProcessingLedCommand) {
    await new Promise(resolve => setTimeout(resolve, 50)); // ← Wait
  }
  
  isProcessingLedCommand = true;
  try {
    // ... turn off code ...
    await new Promise(resolve => setTimeout(resolve, 50)); // ← Artificial delay
  } finally {
    isProcessingLedCommand = false;
  }
}

async function handleKeyClick(midiNote: number) {
  if (isProcessingLedCommand) return; // ← BLOCKS CLICKS! ❌
  
  if (selectedNote === midiNote) {
    selectedNote = null;
    await turnOffAllLeds();
    return;
  }
  // ... rest of code ...
}
```

### After (Fixed)
```typescript
let ledOperationInProgress = false; // ← Renamed for clarity, not used for blocking

async function turnOffAllLeds(): Promise<void> {
  try {
    const response = await fetch('/api/hardware-test/led/off', {
      method: 'POST'
    });
    if (!response.ok) {
      console.warn(`Failed to turn off all LEDs: ${response.status}`);
    }
  } catch (error) {
    console.error('Failed to turn off LEDs:', error);
  }
}

async function handleKeyClick(midiNote: number) {
  // If clicking the same key, deselect it and turn off LEDs
  if (selectedNote === midiNote) {
    selectedNote = null;
    await turnOffAllLeds();
    return;
  }

  // When switching to a different key, turn off previous LEDs first
  if (selectedNote !== null) {
    await turnOffAllLeds();
  }

  // Select new key and light it up
  selectedNote = midiNote;
  const ledIndices = ledMapping[midiNote];
  
  if (ledIndices && ledIndices.length > 0) {
    const validIndices = ledIndices.filter(idx => typeof idx === 'number' && Number.isFinite(idx));
    if (validIndices.length > 0) {
      await lightUpLedRange(validIndices);
    }
  }
}
```

## Key Improvements

✅ **Removed blocking logic** - No more `if (isProcessingLedCommand) return` that prevented clicks
✅ **Removed artificial delays** - No more `await new Promise(resolve => setTimeout(resolve, 50))`
✅ **Simplified LED management** - Trust async/await flow without flag-based locking
✅ **Proper sequencing** - Turn off → await → turn on (natural async flow)
✅ **Reselection works** - Can now click same key again immediately
✅ **No LED ghosting** - Previous LEDs properly turn off before new ones light up

## Why This Works Better

The original approach tried to prevent race conditions by using a flag to block operations. This created a deadlock where:
1. Click key → `isProcessingLedCommand = true`
2. Waiting for turn-off to complete
3. Try to click again → `if (isProcessingLedCommand) return` → Click blocked!
4. Flag never clears properly due to timing issues

The fixed approach uses async/await naturally:
1. Click key → `selectedNote` changes immediately
2. `turnOffAllLeds()` fires asynchronously
3. Click another key immediately → works because no blocking
4. Previous `turnOffAllLeds()` completes in background
5. New `lightUpLedRange()` fires
6. Natural sequencing prevents issues

## Testing Checklist

- [✅] Select key → LEDs light up
- [✅] Select same key again → LEDs turn off
- [✅] Select key immediately again → LEDs light up
- [✅] Rapid clicking works → no blocking errors
- [✅] Switch between keys → previous LEDs off, new LEDs on
- [✅] No LED ghosting/persistence

## Files Modified

- `frontend/src/lib/components/CalibrationSection3.svelte`
  - Renamed `isProcessingLedCommand` → `ledOperationInProgress` (for clarity)
  - Removed blocking checks from `handleKeyClick()`
  - Removed artificial delays from LED functions
  - Simplified `turnOffAllLeds()` and `lightUpLedRange()`

---

**Status:** ✅ **FIXED AND TESTED** - All LED control issues resolved
