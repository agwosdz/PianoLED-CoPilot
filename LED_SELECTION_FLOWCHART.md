# Visual Flowchart: Piano LED Selection Interaction

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Clicks Piano Key                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │    handleKeyClick(midiNote)        │
        │  (async function)                  │
        └────────────────────────────────────┘
                         │
                         ▼
            ┌─────────────────────────────┐
            │ selectedNote === midiNote?  │
            └────────┬──────────────┬─────┘
                 YES │              │ NO
                     ▼              ▼
            ┌──────────────┐  ┌──────────────────────┐
            │  Deselect    │  │ selectedNote != null?│
            │  Logic       │  └────────┬────────┬────┘
            └──┬───────────┘      YES  │        │ NO
               │                       ▼        ▼
               │                ┌────────────┐ ┌─────────┐
               │                │ Turn off   │ │ First   │
               │                │ previous   │ │ select  │
               │                │ LEDs       │ └────┬────┘
               │                └────┬───────┘      │
               │                     │              │
               │                     ▼              ▼
               │            ┌────────────────────────────┐
               │            │  lightUpLedRange()         │
               │            │  (new LED indices)         │
               │            └────────┬───────────────────┘
               │                     │
               └─────────────┬───────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │ For Each LED Index in Range:               │
        │ POST /api/calibration/led-on/{led_index}   │
        └────────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
              ┌─────────────┐   ┌──────────────┐
              │ LEDs Turn   │   │ Error        │
              │ On (White)  │   │ (console)    │
              └─────────────┘   └──────────────┘
                    │                 │
                    └────────┬────────┘
                             ▼
              ✅ LED Selection Complete
```

## Detailed State Machine

```
                      ┌─────────────────────────────┐
                      │   NO KEY SELECTED           │
                      │  (selectedNote = null)      │
                      └────────────┬────────────────┘
                                   │
                         Click Key A│
                                   ▼
                      ┌─────────────────────────────┐
                      │   KEY A SELECTED            │
                      │  (selectedNote = A)         │
                      │  LEDs for A: ON (white)     │
                      └────────────┬────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
          Click A   │      Click B │      Click C │
          (again)   │              │              │
                    ▼              ▼              ▼
         ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
         │ Deselect:     │ │ Switch:      │ │ Switch:      │
         │ A's LEDs OFF  │ │ A's LEDs OFF │ │ A's LEDs OFF │
         │ A unselected  │ │ B's LEDs ON  │ │ C's LEDs ON  │
         └───────────────┘ │ B selected   │ │ C selected   │
             │             └──────────────┘ └──────────────┘
             │                    │              │
             └───────────┬────────┴────────┬─────┘
                         │                 │
                    (same flow)      (same flow)
                         │                 │
                         ▼                 ▼
        Repeats until user clicks different/same key
```

## Request Sequence Diagram

```
User                Frontend              Backend
 │                    │                     │
 │ Click Key A        │                     │
 ├───────────────────>│                     │
 │                    │ handleKeyClick(A)   │
 │                    │─ Validate state     │
 │                    │                     │
 │                    │ lightUpLedRange()   │
 │                    │─ Get LEDs [1,2,3]   │
 │                    │                     │
 │                    │ POST /led-on/1      │
 │                    ├────────────────────>│
 │                    │                     │ Turn on LED 1
 │                    │<────────────────────┤
 │                    │                     │
 │                    │ POST /led-on/2      │
 │                    ├────────────────────>│
 │                    │                     │ Turn on LED 2
 │                    │<────────────────────┤
 │                    │                     │
 │                    │ POST /led-on/3      │
 │                    ├────────────────────>│
 │                    │                     │ Turn on LED 3
 │                    │<────────────────────┤
 │<───────────────────┤                     │
 │ ✅ LEDs Lit        │                     │
 │                    │                     │
 │ Click Key B        │                     │
 ├───────────────────>│                     │
 │                    │ handleKeyClick(B)   │
 │                    │─ Turn off prev      │
 │                    │                     │
 │                    │ POST /api/led/off   │
 │                    ├────────────────────>│
 │                    │                     │ Turn off all
 │                    │<────────────────────┤
 │                    │                     │
 │                    │ lightUpLedRange()   │
 │                    │─ Get LEDs [4,5]     │
 │                    │                     │
 │                    │ POST /led-on/4      │
 │                    ├────────────────────>│
 │                    │                     │ Turn on LED 4
 │                    │<────────────────────┤
 │                    │                     │
 │                    │ POST /led-on/5      │
 │                    ├────────────────────>│
 │                    │                     │ Turn on LED 5
 │                    │<────────────────────┤
 │<───────────────────┤                     │
 │ ✅ LEDs Switched   │                     │
```

## State Transitions with Timing

```
Time 0ms:  IDLE (no key selected, no LEDs)
           ↓
Time 10ms: User clicks Key A
           ↓
Time 20ms: Frontend detects click
           ├─ turnOffAllLeds() [only if prev selected]
           ├─ selectedNote = A
           ├─ lightUpLedRange([1,2,3])
           ↓
Time 30ms: POST /led-on/1, /led-on/2, /led-on/3 (async)
           ↓
Time 50ms: LEDs 1, 2, 3 light up (white)
           ↓
Time 100ms: User clicks Key B
            ↓
Time 110ms: Frontend detects click
            ├─ turnOffAllLeds() [turn off A's LEDs]
            │  POST /api/led/off
            ├─ selectedNote = B
            ├─ lightUpLedRange([4,5])
            ↓
Time 120ms: POST /led/off returns
            ├─ LEDs turn off
            ↓
Time 130ms: POST /led-on/4, /led-on/5 (async)
            ↓
Time 150ms: LEDs 4, 5 light up (white)
            ↓
Time 200ms: User clicks Key B again (deselect)
            ├─ selectedNote = null
            ├─ turnOffAllLeds()
            │  POST /api/led/off
            ↓
Time 210ms: POST /api/led/off returns
            ├─ All LEDs turn off
            ↓
Time 220ms: IDLE (all LEDs off)
```

## Color Timeline

```
Physical LEDs:

Time:      0ms         50ms        100ms       150ms       200ms
           │           │           │           │           │
LEDs 1,2,3: BLACK ────> WHITE ────> BLACK
LEDs 4,5:   BLACK ───────────────> WHITE ────────────────>
            
Legend:
 BLACK = Off (0, 0, 0)
 WHITE = On for key selection (255, 255, 255)
 CYAN  = Used for global offset testing (0, 255, 255)
```

## Error Handling Paths

```
Normal Path:
  handleKeyClick()
        ↓
  lightUpLedRange()
        ↓
  POST /led-on/{index} × N
        ↓
  ✅ Success

Error Path 1 - Network Error:
  handleKeyClick()
        ↓
  lightUpLedRange()
        ↓
  POST /led-on/{index} → Network Error
        ├─ console.warn() logged
        ├─ Graceful degradation
        └─ Component remains responsive
        ↓
  ⚠️  LEDs may not light (partial state)

Error Path 2 - Invalid LED Index:
  POST /led-on/{index} → 400 Bad Request
        ├─ Backend validation catches it
        ├─ Returns error response
        ├─ console.warn() logged
        └─ No LEDs affected
        ↓
  ⚠️  Single LED fails, others may work

Error Path 3 - No LED Controller:
  POST /led-on/{index} → 200 OK (unavailable)
        ├─ Graceful degradation
        ├─ Works in simulation mode
        ├─ console.error() logged
        └─ API still responsive
        ↓
  ℹ️  Works in dev/sim mode
```

## Key Guarantees

✅ **Atomicity**: Either all LEDs for a key light up, or failure logged
✅ **Isolation**: Selecting new key always turns off previous
✅ **Consistency**: Frontend state matches backend LED state
✅ **Error Handling**: No unrecoverable failures
✅ **Responsiveness**: Async calls don't block UI
