# Falling Notes Timing Synchronization

## Overview
The falling notes visualization is synchronized with the backend playback timer via:
1. **100ms polling** - `fetchPlaybackStatus()` polls `/api/playback-status` every 100ms
2. **Reactive updates** - All note positions recalculate when `currentTime` changes
3. **Look-ahead window** - Notes visible 4 seconds before playback

## Timing Calculation

### Current Implementation
```javascript
// Backend provides currentTime in seconds
const currentTime = playbackStatus.current_time;

// For each note:
const timeUntilNote = note.startTime - currentTime;

// Only render if within look-ahead window:
if (timeUntilNote < LOOK_AHEAD_TIME && timeUntilNote > -(note.duration))

// Position calculation (0% = top, 100% = keyboard):
const noteTopPercent = ((LOOK_AHEAD_TIME - timeUntilNote) / LOOK_AHEAD_TIME) * 100
```

### Position Mapping
- **timeUntilNote = 4.0s** → `noteTopPercent = 0%` (top of screen)
- **timeUntilNote = 2.0s** → `noteTopPercent = 50%` (middle of screen)
- **timeUntilNote = 0.0s** → `noteTopPercent = 100%` (reaches keyboard)
- **timeUntilNote < 0** → Hidden (already played)

### Falling Speed
With `LOOK_AHEAD_TIME = 4` seconds and container height = 600px:
- Notes fall at constant speed: **600px / 4s = 150px/s**
- Update rate: 100ms → 15px per update

## Synchronization Points

### 1. Playback Status Updates (100ms)
```typescript
const statusInterval = setInterval(async () => {
    await fetchPlaybackStatus();
    // currentTime is updated with backend's current_time
}, 100);
```

### 2. Reactive Position Recalculation
When `currentTime` changes, all `{@const timeUntilNote = note.startTime - currentTime}` 
expressions recalculate, triggering DOM updates.

### 3. CSS Smooth Transitions
```css
.falling-note-bar {
    transition: top 0.05s linear, background-color 0.2s ease;
}
```
- Linear interpolation over 50ms between positions
- Creates smooth falling animation even at 100ms update intervals

## Verification Checklist

- [ ] Console logs show consistent time increments (≈0.1s per poll)
- [ ] Note positions smoothly progress from top (0%) to bottom (100%)
- [ ] Notes reach keyboard exactly when `currentTime >= note.startTime`
- [ ] Blue highlight appears when note should be playing
- [ ] Hand detection correct: Orange (< 54), Yellow (≥ 54)
- [ ] No timing drift over long playback sessions

## Potential Issues & Solutions

### Issue: Notes don't reach keyboard on time
**Cause**: `LOOK_AHEAD_TIME` mismatch with container height
**Solution**: Adjust `LOOK_AHEAD_TIME` constant (currently 4 seconds)

### Issue: Choppy animation
**Cause**: CSS transition too fast for 100ms polling
**Solution**: Increase transition time or polling rate
**Current**: `transition: top 0.05s linear` (smooth enough)

### Issue: Timing drift
**Cause**: Backend time not synced with frontend
**Solution**: Verify backend playback service provides accurate `current_time`

### Issue: Notes appear/disappear suddenly
**Cause**: Conditional rendering based on `timeUntilNote` window
**Solution**: Extend look-ahead slightly or add fade-in/out effects

## Next Steps

1. **Test with actual MIDI playback** - Load piano.mid and observe timing
2. **Measure sync accuracy** - Compare expected vs actual note arrival times
3. **Adjust `LOOK_AHEAD_TIME`** - Based on preferred visual appearance
4. **Monitor polling consistency** - Ensure 100ms interval holds steady
5. **Test long sessions** - Verify no drift over several minutes

## Architecture Summary

```
Backend Playback Service
    ↓ (100ms polling)
fetchPlaybackStatus() → currentTime updated
    ↓ (reactive)
Note position recalculates: timeUntilNote = startTime - currentTime
    ↓
CSS applies transition smoothly
    ↓
User sees smooth falling animation synchronized with audio
```

**Status**: Implementation complete, ready for testing
