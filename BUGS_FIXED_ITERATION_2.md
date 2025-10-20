# Bug Fixes Applied - October 19, 2025

## Issues Identified & Fixed

### 1. ❌ Time Display Not Showing (0:00 / 0:00)

**Problem**: 
- The playbar showed "0:00 / 0:00" because `totalDuration` was never being set
- Frontend loads notes via `/api/midi-notes` which returns `total_duration`
- But this duration wasn't being captured from the response

**Fix**:
- Modified `loadMIDINotes()` to extract and store `total_duration` from API response
- Updated both `totalDuration` variable and `playbackStatus.total_duration`
- Now displays correct duration in playbar (e.g., "0:00 / 4:00")

### 2. ❌ Playing Status Shows False (Not Recognizing Play State)

**Problem**:
- Debug display shows "Playing: false" even when playing
- Could be due to:
  a) Backend not returning correct state
  b) Frontend not parsing state correctly
  c) State comparison failing

**Fix**:
- Added debug logging to track state comparison:
  ```javascript
  console.log(`[DEBUG] State from API: "${data.state}", isPlaying: ${isPlaying}`)
  ```
- This will show us if the state is being returned correctly from backend
- Will help identify if it's a parsing or comparison issue

### 3. ❌ Bars Off by One Note (Indexing Issue)

**Problem**:
- Falling note bars not aligning with correct piano keys
- Likely caused by `getWhiteKeyIndex()` starting at -1

**Fix**:
- Changed `getWhiteKeyIndex()` to start counting at 0 instead of -1
- Simplified logic: just count white keys before the given note
- Now the horizontal positioning should align notes with correct keys

**Before**:
```javascript
function getWhiteKeyIndex(note: number): number {
    let whiteKeyIndex = -1; // Start at -1
    for (let i = MIN_MIDI_NOTE; i < note; i++) {
        if (isWhiteKey(i)) {
            whiteKeyIndex++;
        }
    }
    return whiteKeyIndex;
}
```

**After**:
```javascript
function getWhiteKeyIndex(note: number): number {
    // Count how many white keys come before this note
    let whiteKeyIndex = 0;
    for (let i = MIN_MIDI_NOTE; i < note; i++) {
        if (isWhiteKey(i)) {
            whiteKeyIndex++;
        }
    }
    return whiteKeyIndex;
}
```

---

## Files Modified

- `frontend/src/routes/play/+page.svelte`
  - Updated `loadMIDINotes()` function
  - Updated `fetchPlaybackStatus()` function with debug logging
  - Fixed `getWhiteKeyIndex()` function

---

## Expected Results After Reload

### Visible Improvements:
1. **Playbar now shows duration** - "0:00 / 4:00" (or whatever song length)
2. **Better state debugging** - Console will show state from API
3. **Notes aligned correctly** - Falling note bars on correct piano keys

### To Verify:
1. Reload the page
2. Select a MIDI file
3. Check playbar shows correct duration
4. Click Play and watch for state changes
5. Notes should align with keyboard horizontally
6. Check console for "[DEBUG] State from API" messages

---

## Remaining Issues to Watch

- If "Playing: false" still shows despite clicking Play, check backend logs for state changes
- If notes still misaligned, verify piano key widths are calculated correctly
- If playbar duration shows 0, verify `/api/midi-notes` returns `total_duration` field

---

## Next Testing Steps

1. **Hard reload** browser (Ctrl+Shift+R)
2. **Select file** → verify duration shows in playbar
3. **Click Play** → observe state changes
4. **Check console** → "[DEBUG] State from API" messages
5. **Verify notes** → aligned with correct keys
