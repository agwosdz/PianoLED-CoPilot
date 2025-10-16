# Architecture: Before & After the Duplicate LED Fix

## BEFORE FIX: Two Independent USB MIDI Services

```
┌─────────────────────────────────────────────────────────────────┐
│                     Piano LED Visualizer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              app.py (Main Application)              │        │
│  ├─────────────────────────────────────────────────────┤        │
│  │                                                     │        │
│  │  SettingsService                                    │        │
│  │       │                                             │        │
│  │       ├─→ LED Controller (SHARED)                   │        │
│  │       │                                             │        │
│  │       ├─→ USBMIDIInputService #1  ◄─ PROBLEM      │        │
│  │            │                                        │        │
│  │            └─→ MidiEventProcessor #1                │        │
│  │                 (Cached: 255 LEDs, normal)          │        │
│  │                                                     │        │
│  │       └─→ MIDIInputManager                          │        │
│  │            │                                        │        │
│  │            ├─→ USBMIDIInputService #2  ◄─ PROBLEM  │        │
│  │            │   (DUPLICATE!)                         │        │
│  │            │   │                                    │        │
│  │            │   └─→ MidiEventProcessor #2            │        │
│  │            │        (Cached: 25 LEDs, reversed)     │        │
│  │            │                                        │        │
│  │            └─→ RtpMIDIService                       │        │
│  │                                                     │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  When USB MIDI input arrives:                                    │
│  ┌──────────────────────────────────────────────────┐           │
│  │  MIDI Note On                                    │           │
│  ├──────────────────────────────────────────────────┤           │
│  │  ├─→ Processor #1: Map to 255 LEDs (old cache)  │           │
│  │  │   └─→ LED Controller: Light 0-255           │           │
│  │  │                                               │           │
│  │  └─→ Processor #2: Map to 25 LEDs (new cache)  │           │
│  │      └─→ LED Controller: Light 0-25            │           │
│  │                                                 │           │
│  │  RESULT: TWO OVERLAPPING LED PATTERNS ✗         │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## AFTER FIX: Single Shared USB MIDI Service

```
┌─────────────────────────────────────────────────────────────────┐
│                     Piano LED Visualizer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              app.py (Main Application)              │        │
│  ├─────────────────────────────────────────────────────┤        │
│  │                                                     │        │
│  │  SettingsService                                    │        │
│  │       │                                             │        │
│  │       ├─→ LED Controller (SHARED)                   │        │
│  │       │                                             │        │
│  │       ├─→ USBMIDIInputService (SINGLE) ✓           │        │
│  │       │   │                                         │        │
│  │       │   └─→ MidiEventProcessor                    │        │
│  │       │        (Fresh cache every event)            │        │
│  │       │        (Always: current settings)           │        │
│  │       │                                             │        │
│  │       └─→ MIDIInputManager                          │        │
│  │            │                                        │        │
│  │            ├─→ References SAME USBMIDIService ✓    │        │
│  │            │   (No duplicate creation)              │        │
│  │            │                                        │        │
│  │            └─→ RtpMIDIService                       │        │
│  │                                                     │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  When USB MIDI input arrives:                                    │
│  ┌──────────────────────────────────────────────────┐           │
│  │  MIDI Note On                                    │           │
│  ├──────────────────────────────────────────────────┤           │
│  │  ├─→ Processor (shared): Reads fresh cache       │           │
│  │  │   ├─→ LED Count: 25 LEDs (current)           │           │
│  │  │   ├─→ Orientation: reversed (current)         │           │
│  │  │   │                                            │           │
│  │  │   └─→ LED Controller: Light ONLY 0-25        │           │
│  │  │       (reversed mapping)                       │           │
│  │  │                                               │           │
│  │  RESULT: SINGLE LED PATTERN ✓                    │           │
│  │  SETTINGS APPLY IMMEDIATELY ✓                    │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Flow

### Before Fix
```
USB MIDI Input
    │
    ├─→ [Service #1 Thread]─→ [Cache: 255, normal]─→ LED Update
    │
    └─→ [Service #2 Thread]─→ [Cache: 25, reversed]─→ LED Update
    
Result: Concurrent threads, different caches → DUPLICATE LEDs
```

### After Fix
```
USB MIDI Input
    │
    └─→ [Single Service Thread]
         │
         ├─→ [Refresh cache from DB]
         │
         ├─→ [Cache: 25, reversed] ← Current settings
         │
         └─→ [Single LED Update]

Result: One thread, fresh cache, single update → CORRECT
```

---

## Settings Change Propagation

### Before Fix (Race Condition)
```
User changes: 255 LEDs → 25 LEDs

Settings Service broadcasts change
    ├─→ Service #1 cache refreshed: 255 → 25 ✓
    │
    └─→ Service #2 cache refreshed: 255 → 25 ✓

BUT: Service #1 MIDI events in flight
    ├─→ Process with NEW cache (25 LEDs) ✓
    
AND: Service #2 MIDI events in flight  
    ├─→ Process with OLD cache? (possibly 255 LEDs) ✗
    
Result: GHOST PATTERN - Two overlapping LED sets
```

### After Fix (Clean Propagation)
```
User changes: 255 LEDs → 25 LEDs

Settings Service broadcasts change
    └─→ Single cache refreshed: 255 → 25 ✓

All MIDI events process with SAME cache
    └─→ All use 25 LEDs ✓

Result: CLEAN TRANSITION - Only new pattern visible
```

---

## Implementation: Shared Instance

### Data Flow
```
┌─────────────────┐
│  app.py         │
├─────────────────┤
│  Creates:       │
│  usb_midi_svc ──┐
└─────────────────┘ │
                    │ Passes reference
                    ↓
┌──────────────────────────────┐
│  MIDIInputManager            │
├──────────────────────────────┤
│  __init__(usb_midi_service=) │
│  {                           │
│    self._usb_service = ✓     │
│    # Same reference!         │
│  }                           │
└──────────────────────────────┘

No duplicate creation!
Single instance shared by both!
```

---

## Testing Verification Checklist

```
┌─ Initialization ─────────────────────────┐
│ ☑ app.py creates USBMIDIInputService    │
│ ☑ MIDIInputManager receives via param   │
│ ☑ initialize_services() skips creation  │
│ ☑ Both reference SAME object            │
└──────────────────────────────────────────┘

┌─ Settings Change ────────────────────────┐
│ ☑ User changes LED count 255 → 25       │
│ ☑ One cache update (not two)            │
│ ☑ One LED output update (not two)       │
│ ☑ No ghost/duplicate patterns           │
└──────────────────────────────────────────┘

┌─ Orientation Change ─────────────────────┐
│ ☑ User changes orientation normal → rev │
│ ☑ New mapping applied immediately       │
│ ☑ Only one LED pattern responds         │
│ ☑ No overlay or flicker                 │
└──────────────────────────────────────────┘

┌─ MIDI Input ─────────────────────────────┐
│ ☑ Connect USB MIDI keyboard             │
│ ☑ Play notes → Only ONE set lights      │
│ ☑ Settings change → Response immediate  │
│ ☑ No latency or lag                     │
└──────────────────────────────────────────┘
```

---

## Performance Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| USB MIDI Instances | 2 | 1 | -50% |
| Event Processor Threads | 2 | 1 | -50% |
| Settings Caches | 2 | 1 | -50% |
| CPU Usage | Higher | Lower | ↓ |
| Memory Usage | Higher | Lower | ↓ |
| LED Latency | Variable | Consistent | ✓ |
| Duplicate LEDs | YES ✗ | NO ✓ | ✓ |

