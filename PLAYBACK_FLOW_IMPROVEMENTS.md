# Playback Flow Improvements

## Changes Made

### 1. File Selection No Longer Auto-Plays ✅

**Before:**
- Clicking a file immediately started playback
- Could lead to confusion about which file was selected

**After:**
```javascript
async function handleSelectFile(filePath: string) {
    // Stop any currently playing file first
    try {
        await fetch('/api/stop', { method: 'POST' });
    } catch (error) {
        console.warn('Failed to stop previous playback:', error);
    }

    // Select file and load notes, but DON'T auto-play
    selectedFile = filePath;
    await loadMIDINotes();
    console.log(`✓ Selected ${filePath} - click Play to start`);
}
```

**Benefits:**
- User must explicitly click Play to start
- Clears any previous playback
- Console shows what file was selected

### 2. Only One File Can Play At A Time ✅

**Before:**
- Selecting a new file while one is playing could cause conflicts

**After:**
```javascript
async function handlePlayPause() {
    if (!selectedFile) return;

    try {
        // If we're not currently playing, stop any other file first
        if (!isPlaying) {
            console.log(`▶ Playing: ${selectedFile}`);
            // Stop any other playback first (to ensure only one file plays)
            try {
                await fetch('/api/stop', { method: 'POST' });
            } catch (e) {
                // Ignore errors when stopping (nothing might be playing)
            }
        } else {
            console.log(`⏸ Pausing`);
        }

        const method = isPlaying ? 'pause' : 'play';
        const response = await fetch(`/api/${method}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: selectedFile })
        });

        if (response.ok) {
            await fetchPlaybackStatus();
        } else {
            console.error(`Failed to ${method}: ${response.status}`);
        }
    } catch (error) {
        console.error('Failed to control playback:', error);
    }
}
```

**Benefits:**
- When playing a file, any other playback stops first
- Prevents multiple files playing simultaneously
- Better error handling with status logging

## Workflow Now

1. **User selects a file**
   - File loads into memory
   - Notes are fetched and displayed
   - Console: "✓ Selected filename.mid - click Play to start"

2. **User clicks Play**
   - Any other playback stops first
   - Selected file begins playing
   - Console: "▶ Playing: filename.mid"
   - Debug display updates with advancing currentTime

3. **User clicks Pause**
   - Playback pauses
   - Console: "⏸ Pausing"

4. **User clicks Stop**
   - Playback stops completely
   - Selection cleared
   - Ready to select new file

5. **User selects different file while one is playing**
   - Previous playback stops
   - New file loads
   - Must click Play again to start

## Expected Behavior Now

When testing the falling notes:

1. Upload or select a MIDI file
2. Console should show: `✓ Selected piano.mid - click Play to start`
3. Click **Play** button
4. Console should show: `▶ Playing: piano.mid`
5. Debug display should show advancing currentTime
6. Notes should fall from top to keyboard

## Robustness Improvements

✅ **Prevents race conditions** - Ensures only one file plays
✅ **Clear user intent** - Must explicitly click Play
✅ **Better logging** - Console shows what's happening
✅ **Error resilience** - Handles failures gracefully

## Testing

Try these scenarios:

1. **Normal playback:**
   - Select file → Click Play → Watch time advance → Click Stop

2. **Multiple selections:**
   - Select file A
   - Click Play
   - While playing, select file B
   - File A should stop, file B loads
   - Click Play to start file B

3. **Pause/Resume:**
   - Play file
   - Click Pause (should pause)
   - Click Play again (should resume from same position)

4. **Visual feedback:**
   - Watch debug display for advancing currentTime
   - Watch notes fall from top to keyboard
   - Watch colors change (orange/yellow/blue)
