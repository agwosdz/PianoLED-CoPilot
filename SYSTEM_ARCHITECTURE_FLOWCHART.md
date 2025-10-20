# 📊 System Architecture & Data Flow

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Svelte/TS)                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Play Page Component                                │  │
│  │  +page.svelte                                       │  │
│  │                                                      │  │
│  │  ├─ File Browser (5 files)                          │  │
│  │  ├─ Play Controls (Play/Pause/Stop)               │  │
│  │  ├─ Progress Bar (real-time)                       │  │
│  │  ├─ Debug Display (timing info)                    │  │
│  │  └─ Visualization Viewport                         │  │
│  │     ├─ Falling Notes (yellow/orange bars)         │  │
│  │     └─ Piano Keyboard (white/black keys)          │  │
│  └─────────────────────────────────────────────────────┘  │
│                           ↕ (Polling every 100ms)          │
└─────────────────────────────────────────────────────────────┘
                            |
                            | HTTP REST
                            |
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼─────────────────────────────────────────▼──┐
│         BACKEND (Flask + SocketIO)                 │
│                                                    │
│  API Endpoints (Fixed ✅):                       │
│  ├─ GET  /api/uploaded-midi-files                │
│  ├─ GET  /api/midi-notes                         │
│  ├─ GET  /api/playback-status  ← Polled 10x/sec │
│  ├─ POST /api/play                               │
│  ├─ POST /api/pause                              │
│  └─ POST /api/stop                               │
│                          ↕                        │
│  ┌─────────────────────────────────┐            │
│  │  PlaybackService (Backend)      │            │
│  │  - load_midi_file()             │            │
│  │  - start_playback()             │            │
│  │  - pause_playback()             │            │
│  │  - stop_playback()              │            │
│  │  - state (PLAYING/IDLE/etc)     │            │
│  │  - current_time (advancing)     │            │
│  │  - total_duration               │            │
│  │  - filename                     │            │
│  └─────────────────────────────────┘            │
└────────────────────────────────────────────────────┘
```

---

## Data Flow: Playing a File

```
Step 1: FILE SELECTION
  User clicks file in browser
    ↓
  Frontend sends: GET /api/midi-notes?filename=song.mid
    ↓
  Backend response: { notes: [...], total_duration: 240.39 }
    ↓
  Frontend stores: notes array (453 items)
    ↓
  Visualization renders: Yellow/orange bars at starting positions

Step 2: CLICK PLAY
  User clicks "▶ Play" button
    ↓
  Frontend sends: POST /api/play { filename: "song.mid" }
    ↓
  Backend:
    1. playback_service.load_midi_file("song.mid")
       - Parses MIDI file
       - Sets total_duration
    2. playback_service.start_playback()
       - Starts playback thread
       - Begins advancing current_time
       - Emits WebSocket updates
    ↓
  Backend responds: { success: true }

Step 3: POLLING LOOP (Every 100ms)
  Frontend: GET /api/playback-status
    ↓
  Backend responds:
  {
    state: "playing",
    current_time: 0.23,      ← Advancing!
    total_duration: 240.39,
    filename: "song.mid",
    progress_percentage: 0.096,
    error_message: null
  }
    ↓
  Frontend updates:
    - currentTime = 0.23
    - totalDuration = 240.39
    - isPlaying = true
    - Progress bar fills
    - Debug display updates
    ↓
  Animation loop (Svelte reactivity):
    For each note in notes array:
      timeUntilNote = note.startTime - currentTime
      topPercent = ((4 - timeUntilNote) / 4) * 100
      Render note bar at computed position
    ↓
  Visual result: Notes fall from 100% → 0%

Step 4: PAUSE
  User clicks "⏸ Pause" button
    ↓
  Frontend sends: POST /api/pause
    ↓
  Backend: playback_service.pause_playback()
    - Pauses playback thread
    - current_time frozen
    - state = PAUSED
    ↓
  Frontend detects: state = "paused"
    - Animation stops
    - Button changes to "▶ Play"

Step 5: RESUME
  User clicks "▶ Play" button (while paused)
    ↓
  Frontend sends: POST /api/pause (toggles)
    ↓
  Backend: playback_service.pause_playback()
    - Resumes from paused position
    - current_time continues advancing
    - state = PLAYING
    ↓
  Frontend detects: state = "playing"
    - Animation resumes smoothly
    - No time jump

Step 6: STOP
  User clicks "■ Stop" button
    ↓
  Frontend sends: POST /api/stop
    ↓
  Backend: playback_service.stop_playback()
    - Stops playback thread
    - current_time = 0
    - state = IDLE
    ↓
  Frontend detects:
    - state = "idle"
    - current_time = 0
    - Animation resets
    - Button shows "▶ Play"
```

---

## Position Calculation Formula

```javascript
// Constants
LOOK_AHEAD_TIME = 4.0  // seconds

// Inputs
currentTime        = 0.23          // seconds (from backend)
note.startTime     = 1.50          // seconds (from MIDI)

// Calculation
timeUntilNote = note.startTime - currentTime
              = 1.50 - 0.23
              = 1.27 seconds

topPercent = ((LOOK_AHEAD_TIME - timeUntilNote) / LOOK_AHEAD_TIME) * 100
           = ((4.0 - 1.27) / 4.0) * 100
           = (2.73 / 4.0) * 100
           = 0.6825 * 100
           = 68.25%

// Result
Note appears 68.25% down the screen
(100% = top, 0% = keyboard)

// Over time
t=0.00s: timeUntilNote = 1.50,  topPercent = 100.0% (just entered view)
t=0.30s: timeUntilNote = 1.20,  topPercent = 80.0%
t=0.60s: timeUntilNote = 0.90,  topPercent = 77.5%
t=0.90s: timeUntilNote = 0.60,  topPercent = 85.0%
t=1.20s: timeUntilNote = 0.30,  topPercent = 92.5%
t=1.50s: timeUntilNote = 0.00,  topPercent = 100.0% (plays!)
```

---

## Component Interaction Diagram

```
┌────────────────────┐
│   File Browser     │
│  (Select file)     │
└─────────┬──────────┘
          │ onClick
          │
          ▼
┌────────────────────┐      GET /midi-notes
│  Load Notes        │─────────────────────► Backend
│  (Frontend)        │◄─────────────────────
└─────────┬──────────┘    {notes[], duration}
          │
          ▼
┌────────────────────┐
│  Render Viz        │
│  (Static bars)     │
└─────────┬──────────┘
          │ onClick Play
          │
          ▼
┌────────────────────┐      POST /play
│  Start Playback    │─────────────────────► Backend
│  (Frontend)        │◄─────────────────────
└─────────┬──────────┘
          │
    ┌─────▼─────┐
    │ Polling   │  GET /playback-status
    │ Loop      │─────────────────────► Backend
    │ (100ms)   │◄─────────────────────
    └─────┬─────┘    {state, time, duration, ...}
          │
          ▼
┌────────────────────┐
│  Update State      │
│  (currentTime++)   │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Recalc Position   │
│  (topPercent)      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Render Notes      │
│  (Animate)         │
└─────────┬──────────┘
          │ (Loop continues)
          └────────┐
                   │ User clicks Pause
                   ▼
            POST /pause ──► Backend
                   │
            Animation stops
```

---

## Note Visibility & Filtering

```
LOOK_AHEAD_TIME = 4 seconds
Current time: 1.50s

Notes in memory: 453 total
┌────────────────────────────────────────┐
│ Note 1: MIDI 60,  startTime: 0.00s  │ ← Past (not rendered)
│ Note 2: MIDI 62,  startTime: 0.50s  │ ← Past (not rendered)
│ ...                                    │
│ Note 50: MIDI 70, startTime: 1.20s  │ ← VISIBLE (topPercent: 80%)
│ Note 51: MIDI 72, startTime: 1.50s  │ ← VISIBLE (topPercent: 100%)
│ Note 52: MIDI 74, startTime: 1.80s  │ ← VISIBLE (topPercent: 120%)*
│ Note 53: MIDI 76, startTime: 2.10s  │ ← VISIBLE (topPercent: 140%)*
│ Note 54: MIDI 78, startTime: 2.40s  │ ← VISIBLE (topPercent: 160%)*
│ Note 55: MIDI 80, startTime: 2.70s  │ ← VISIBLE (topPercent: 180%)*
│ Note 56: MIDI 82, startTime: 3.00s  │ ← VISIBLE (topPercent: 200%)*
│ Note 57: MIDI 84, startTime: 3.30s  │ ← VISIBLE (topPercent: 220%)*
│ Note 58: MIDI 86, startTime: 3.60s  │ ← VISIBLE (topPercent: 240%)*
│ Note 59: MIDI 88, startTime: 4.00s  │ ← VISIBLE (topPercent: 280%)*
│ Note 60: MIDI 90, startTime: 4.30s  │ ← VISIBLE (topPercent: 320%)*
│ Note 61: MIDI 92, startTime: 4.60s  │ ← VISIBLE (topPercent: 360%)*
│ Note 62: MIDI 94, startTime: 4.90s  │ ← VISIBLE (topPercent: 400%)*
│ Note 63: MIDI 65, startTime: 5.20s  │ ← VISIBLE (topPercent: 440%)*
│ Note 64: MIDI 67, startTime: 5.50s  │ ← FUTURE (topPercent: 480%) - not rendered
│ ...                                    │
│ Note 453: MIDI 69, startTime: 240.39s│ ← Future (not rendered)
└────────────────────────────────────────┘

*Rendered above viewport (off-screen at top)

Visibility Algorithm:
for each note:
  timeUntilNote = note.startTime - currentTime
  timeUntilNoteEnd = (note.startTime + note.duration) - currentTime
  
  if (timeUntilNote < LOOK_AHEAD_TIME && 
      timeUntilNoteEnd > -0.5):
    // Render this note (visible in window)
  else:
    // Skip this note (not visible)

Result: ~15 notes always visible, optimized rendering ✨
```

---

## State Machine

```
┌─────────┐
│  IDLE   │ (Waiting for user to click Play)
│ (Start) │
└────┬────┘
     │
     │ User clicks Play
     │ POST /api/play
     │
     ▼
┌──────────┐
│ PLAYING  │ (Playback in progress)
│          │ currentTime advancing
└────┬─────┘
     │
     ├─────────────────────┬──────────────────────┐
     │                     │                      │
     │ User clicks Pause   │ User clicks Stop     │ User stops file
     │ POST /api/pause     │ POST /api/stop       │ (natural end)
     │                     │                      │
     ▼                     ▼                      ▼
┌──────────┐         ┌─────────┐         ┌──────────┐
│  PAUSED  │         │  IDLE   │         │ STOPPED  │
│          │         │         │         │          │
│ Can play │         └─────┬───┘         └────┬─────┘
│ again    │               │                   │
└────┬─────┘               │                   │
     │                     │                   │
     │ User clicks Play    │                   │
     │ (resume)            │                   │
     │                     │ Click Play        │ Click Play
     │                     │                   │
     └──────────┬──────────┴───────────────────┴───►(PLAYING)
                │
              (Resume from pause)
```

---

## Error Handling Flow

```
User Action
    ↓
Frontend sends API request
    ↓
┌─────────────────────┐
│  Backend processes  │
└────────┬────────────┘
         │
    ┌────┴────┐
    │          │
  Success    Error
    │          │
    ▼          ▼
┌────────┐  ┌─────────────────┐
│Return  │  │Log error        │
│status  │  │Return error     │
│data    │  │message & code   │
└────┬───┘  └────────┬────────┘
     │               │
     │               ▼
     │        ┌────────────────┐
     │        │Frontend catches│
     │        │error response  │
     │        └────────┬───────┘
     │                 │
     │                 ▼
     │        ┌────────────────────┐
     │        │Display error msg   │
     │        │to user on console  │
     │        │or UI alert         │
     │        └────────────────────┘
     │
     ▼
Frontend continues polling
```

---

## Performance Optimization

```
Frontend Rendering Optimization:
- Only render visible notes (~15 out of 453)
- Use CSS transforms for smooth animation
- Debounce status updates (100ms)
- Avoid re-rendering static elements
- Use Svelte reactivity efficiently

Backend Optimization:
- Playback in separate thread
- Minimal lock contention
- Efficient note event lookup
- Status caching between polls

Network Optimization:
- HTTP keep-alive
- Gzip compression
- Minimal payload size (~500 bytes per poll)
- 100ms update rate optimal for smooth animation
```

---

## This is the complete system architecture! 🎹✨
