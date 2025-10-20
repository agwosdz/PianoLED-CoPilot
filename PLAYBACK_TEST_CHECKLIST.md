# Playback Animation Test Checklist

## Phase 1: Play Button Interaction ✅→📋

- [ ] **Click Play**
  - Expected: Button changes to "⏸ Pause"
  - Check: Debug shows "Playing: true"
  - Check: Progress bar starts filling

- [ ] **Time Advancement**
  - Expected: Debug time advances (0.00s → 0.10s → 0.20s...)
  - Check: Updates every 100ms in frontend
  - Check: No freezing or jumps

- [ ] **Progress Bar**
  - Expected: Fills from 0% to 100% over 240 seconds
  - Check: Shows correct duration (4:00)
  - Check: Shows correct current time (0:00 → 0:04 → ...)

## Phase 2: Note Animation ✅→📋

- [ ] **Initial Position**
  - Expected: Yellow notes at 100% (bottom, at keyboard)
  - Check: Visible in the viewport
  - Check: Multiple notes stacked above

- [ ] **Falling Motion**
  - Expected: topPercent decreases over time (100% → 75% → 50% → 25% → 0%)
  - Check: Smooth animation (no jumps)
  - Check: Notes move upward visually (higher on screen = earlier in time)

- [ ] **Window Scrolling**
  - Expected: New notes enter from top (100%) as old ones exit bottom (0%)
  - Check: Always ~15 notes visible
  - Check: No gaps or duplicates

- [ ] **Colors**
  - Expected: Yellow notes (right hand, MIDI ≥ 54)
  - Expected: Orange notes (left hand, MIDI < 54)
  - Check: Can see both colors during playback

## Phase 3: Piano Keyboard Highlighting 📋

- [ ] **Note Reaching Keyboard**
  - Expected: When topPercent reaches 0%, that note plays
  - Check: Piano key highlights/animates
  - Check: Timing matches visual animation

- [ ] **Multiple Notes**
  - Expected: Handle overlapping notes correctly
  - Check: All notes highlighted when they reach keyboard
  - Check: No visual artifacts

## Phase 4: Playback Controls 📋

- [ ] **Pause Button**
  - Click: "⏸ Pause" button
  - Expected: Animation stops
  - Check: Time value freezes
  - Check: Notes stop falling

- [ ] **Resume**
  - Click: "⏸ Pause" button again (should be "▶ Play" now)
  - Expected: Animation resumes from paused position
  - Check: Time continues advancing
  - Check: Notes continue falling

- [ ] **Stop Button**
  - Click: "Stop" button
  - Expected: Animation stops and resets
  - Check: Time resets to 0:00
  - Check: Notes return to starting positions
  - Check: File selection cleared

## Phase 5: Edge Cases 📋

- [ ] **Very Fast Notes**
  - Expected: Multiple notes in same column (same MIDI time)
  - Check: All render correctly
  - Check: No visual overlap issues

- [ ] **Long Notes**
  - Expected: Notes with long duration span multiple timeframes
  - Check: Bar extends from top to bottom
  - Check: Duration property correct

- [ ] **File Switching**
  - Select new file while playing
  - Expected: Current playback stops
  - Check: New file loads when Play is clicked

## Phase 6: Performance 📋

- [ ] **Smooth Animation**
  - Expected: 60fps rendering
  - Check: No stuttering
  - Check: No frame drops

- [ ] **Memory Usage**
  - Expected: Stable memory during playback
  - Check: No memory leaks
  - Check: Performance consistent after 1 minute

- [ ] **CPU Usage**
  - Expected: Reasonable CPU (~20-30% on Pi)
  - Check: Pi doesn't overheat
  - Check: Other processes responsive

## Recording Instructions

### For Video Capture
1. Open Developer Tools (F12)
2. Switch to Console tab
3. Click Play
4. Record for 10 seconds
5. Save video as `playback_animation_test.mp4`

### For Screenshot Sequence
1. Take screenshot at t=0s (before play)
2. Click Play
3. Take screenshot at t=1s
4. Take screenshot at t=2s
5. Take screenshot at t=3s
6. Compare note positions

### Key Metrics to Log
- Time at start: `0:00`
- Time at 1 second mark: `0:01`
- Time at 2 second mark: `0:02`
- Number of visible notes: Should stay ~15
- First note topPercent: Should decrease by ~25% per second

---

## Success Definition
✅ **All tests pass when:**
- Notes fall smoothly from top to keyboard
- Timing is accurate to within 100ms
- Colors display correctly (yellow/orange)
- Pause/resume/stop work correctly
- Performance is smooth (no stuttering)
- Piano keyboard highlights notes at correct time
