# LED Calibration System - Documentation Index

## 📚 Complete Documentation Set

### Quick Start
Start here if you're new to the calibration system:
- **[CALIBRATION_QUICK_REF.md](CALIBRATION_QUICK_REF.md)** ⭐ START HERE
  - Quick reference card
  - Common API calls
  - MIDI note reference
  - Basic workflow
  - 2-minute read

### Executive Summary
- **[CALIBRATION_SUMMARY.md](CALIBRATION_SUMMARY.md)**
  - What was implemented
  - Files modified/created
  - All 14 API endpoints
  - WebSocket events
  - Next steps
  - 10-minute read

### Implementation Details
- **[CALIBRATION_IMPLEMENTATION.md](CALIBRATION_IMPLEMENTATION.md)**
  - Technical architecture
  - Component breakdown
  - Settings schema
  - Data storage structure
  - Offset application flow
  - 15-minute read

### Usage Guide
- **[CALIBRATION_USAGE_GUIDE.md](CALIBRATION_USAGE_GUIDE.md)** 📖
  - Complete API reference
  - Every endpoint documented
  - Usage examples with curl
  - Calibration workflow steps
  - WebSocket event reference
  - Troubleshooting section
  - 30-minute read

### Architecture & Diagrams
- **[CALIBRATION_ARCHITECTURE.md](CALIBRATION_ARCHITECTURE.md)** 📊
  - System overview diagram
  - Data flow diagrams
  - Settings hierarchy
  - Offset application order
  - State transitions
  - Integration points table
  - 20-minute read

### Frontend Integration
- **[FRONTEND_INTEGRATION_CALIBRATION.md](FRONTEND_INTEGRATION_CALIBRATION.md)** 💻
  - Complete code examples
  - TypeScript/JavaScript patterns
  - Svelte component example
  - State management
  - WebSocket integration
  - Error handling
  - 30-minute read

### Implementation Checklist
- **[CALIBRATION_CHECKLIST.md](CALIBRATION_CHECKLIST.md)** ✅
  - Backend implementation status
  - Frontend tasks
  - Future enhancements
  - Deployment checklist
  - Known issues
  - Success criteria

---

## 🗂️ Code Files

### Backend API
- **`backend/api/calibration.py`** (330+ lines)
  - 14 REST endpoints
  - Status, control, offset, import/export
  - Error handling and validation
  - WebSocket event broadcasting

### MIDI Processing
- **`backend/midi/midi_event_processor.py`** (modified)
  - Calibration offset fields added
  - Settings loading updated
  - `_map_note_to_leds()` enhanced
  - Per-key offset application logic

### Settings
- **`backend/services/settings_service.py`** (modified)
  - `calibration` category added
  - LED mapping fields added
  - Validation rules

- **`backend/config.py`** (modified)
  - `apply_calibration_offsets_to_mapping()` helper

### App Configuration
- **`backend/app.py`** (modified)
  - Calibration blueprint registered

### Tests
- **`backend/tests/test_calibration.py`** (new)
  - 15 unit tests
  - Offset logic validation
  - Settings loading tests

---

## 📊 What Each Document Contains

### For Developers

| Role | Document | Focus |
|------|----------|-------|
| **Backend Dev** | CALIBRATION_IMPLEMENTATION.md | Architecture, implementation details |
| **Backend Dev** | CALIBRATION_USAGE_GUIDE.md | API endpoints, testing |
| **Frontend Dev** | FRONTEND_INTEGRATION_CALIBRATION.md | Code examples, integration |
| **QA/Tester** | CALIBRATION_CHECKLIST.md | Test cases, deployment |
| **DevOps** | CALIBRATION_CHECKLIST.md | Deployment checklist |
| **Everyone** | CALIBRATION_QUICK_REF.md | Quick lookup, common tasks |

### For Understanding

| Question | Document |
|----------|----------|
| What was implemented? | CALIBRATION_SUMMARY.md |
| How does it work? | CALIBRATION_ARCHITECTURE.md |
| How do I use the API? | CALIBRATION_USAGE_GUIDE.md |
| How do I integrate in frontend? | FRONTEND_INTEGRATION_CALIBRATION.md |
| What do I need to do? | CALIBRATION_CHECKLIST.md |
| Quick lookup? | CALIBRATION_QUICK_REF.md |
| Technical details? | CALIBRATION_IMPLEMENTATION.md |

---

## 🎯 Common Tasks

### "I want to understand the system quickly"
1. Read: CALIBRATION_QUICK_REF.md (2 min)
2. Read: CALIBRATION_SUMMARY.md (10 min)
3. Check: CALIBRATION_ARCHITECTURE.md diagrams (5 min)

### "I need to implement the frontend"
1. Read: FRONTEND_INTEGRATION_CALIBRATION.md (30 min)
2. Reference: CALIBRATION_USAGE_GUIDE.md (as needed)
3. Use: Code examples provided
4. Check: CALIBRATION_CHECKLIST.md for tasks

### "I need to debug an issue"
1. Check: CALIBRATION_USAGE_GUIDE.md troubleshooting
2. Read: CALIBRATION_IMPLEMENTATION.md for details
3. Reference: CALIBRATION_ARCHITECTURE.md for flow

### "I need to deploy this"
1. Read: CALIBRATION_CHECKLIST.md deployment section
2. Check: Code files for configuration
3. Run: Tests in backend/tests/test_calibration.py

### "I need to extend this"
1. Read: CALIBRATION_IMPLEMENTATION.md architecture
2. Read: CALIBRATION_CHECKLIST.md future enhancements
3. Check: Code for patterns

---

## 🔗 Document Relationships

```
CALIBRATION_QUICK_REF.md
  ↓ (references)
  ├─→ CALIBRATION_USAGE_GUIDE.md (full API details)
  ├─→ CALIBRATION_SUMMARY.md (what was built)
  └─→ CALIBRATION_CHECKLIST.md (what to do)

CALIBRATION_SUMMARY.md
  ↓ (details explained in)
  ├─→ CALIBRATION_IMPLEMENTATION.md (technical)
  ├─→ CALIBRATION_ARCHITECTURE.md (visual)
  └─→ FRONTEND_INTEGRATION_CALIBRATION.md (integration)

CALIBRATION_IMPLEMENTATION.md
  ↓ (illustrated by)
  └─→ CALIBRATION_ARCHITECTURE.md (diagrams)

FRONTEND_INTEGRATION_CALIBRATION.md
  ↓ (uses)
  ├─→ CALIBRATION_USAGE_GUIDE.md (API reference)
  └─→ CALIBRATION_QUICK_REF.md (common calls)

CALIBRATION_CHECKLIST.md
  ↓ (tracks)
  ├─→ CALIBRATION_IMPLEMENTATION.md (backend)
  ├─→ FRONTEND_INTEGRATION_CALIBRATION.md (frontend)
  └─→ CALIBRATION_USAGE_GUIDE.md (API testing)
```

---

## 📈 Implementation Status

### Backend ✅ COMPLETE
- [x] API implementation (14 endpoints)
- [x] Settings integration
- [x] MIDI offset logic
- [x] Database persistence
- [x] WebSocket events
- [x] Export/import
- [x] Error handling
- [x] Unit tests (15 tests)
- [x] Documentation (5 docs)

### Frontend 📋 READY FOR IMPLEMENTATION
- [ ] UI components
- [ ] API integration
- [ ] WebSocket connection
- [ ] Test mode
- [ ] User experience

### Phase 2 🔮 PLANNED
- [ ] Assisted calibration
- [ ] Calibration profiles
- [ ] Drift compensation
- [ ] Smart learning

---

## 🚀 Getting Started

### 1. Understand the System (10 minutes)
```
Read: CALIBRATION_QUICK_REF.md
Read: CALIBRATION_SUMMARY.md
```

### 2. Backend Development (already done!)
```
Files: backend/api/calibration.py
Status: ✅ COMPLETE & TESTED
```

### 3. Frontend Development
```
Read: FRONTEND_INTEGRATION_CALIBRATION.md
Reference: CALIBRATION_USAGE_GUIDE.md
Code: Implement UI components
```

### 4. Integration & Testing
```
Follow: CALIBRATION_CHECKLIST.md
Reference: CALIBRATION_ARCHITECTURE.md
```

### 5. Deployment
```
Checklist: CALIBRATION_CHECKLIST.md → Deployment section
```

---

## 💡 Key Concepts

### Global Offset
- Shifts all LEDs uniformly
- Range: -100 to +100
- Use: Align LED strip position

### Per-Key Offset
- Individual key adjustments
- Range: -100 to +100 per key
- Use: Correct imperfections and drift

### Combined Effect
```
Final LED index = base_index + global_offset + key_offset
                (clamped to [0, num_leds))
```

---

## 🔍 API Overview

14 endpoints organized by function:

- **Status** (1): `/status`
- **Control** (3): `/enable`, `/disable`, `/reset`
- **Global** (2): `/global-offset` [GET/PUT]
- **Per-Key** (6): `/key-offset/*`, `/key-offsets` [GET/PUT/batch]
- **I/O** (2): `/export`, `/import`

All endpoints:
- Accept/return JSON
- Use standard HTTP methods
- Return standard status codes
- Broadcast WebSocket events

---

## 📞 Navigation Tips

- **Just need an API call?** → CALIBRATION_QUICK_REF.md
- **Need to understand something?** → CALIBRATION_SUMMARY.md
- **Need implementation details?** → CALIBRATION_IMPLEMENTATION.md
- **Need visual diagrams?** → CALIBRATION_ARCHITECTURE.md
- **Need to integrate frontend?** → FRONTEND_INTEGRATION_CALIBRATION.md
- **Need complete API docs?** → CALIBRATION_USAGE_GUIDE.md
- **Need implementation plan?** → CALIBRATION_CHECKLIST.md

---

## ✅ Verification Checklist

Before starting frontend development:

- [x] Read CALIBRATION_SUMMARY.md
- [x] Understand global vs per-key offsets
- [x] Know the 14 API endpoints
- [x] Understand WebSocket events
- [x] Review code examples in FRONTEND_INTEGRATION_CALIBRATION.md
- [x] Check existing placeholder UI locations
- [x] Plan UI components
- [x] Set up API calls
- [x] Test WebSocket connection

---

## 🎓 Learning Path

**Beginner (30 minutes)**
1. CALIBRATION_QUICK_REF.md
2. CALIBRATION_SUMMARY.md
3. CALIBRATION_ARCHITECTURE.md (diagrams)

**Intermediate (1-2 hours)**
4. CALIBRATION_USAGE_GUIDE.md
5. CALIBRATION_IMPLEMENTATION.md
6. Start coding from examples

**Advanced (2-3 hours)**
7. FRONTEND_INTEGRATION_CALIBRATION.md
8. Study code files
9. Review CALIBRATION_CHECKLIST.md

---

## 📝 Document Metadata

| Document | Lines | Type | Read Time |
|----------|-------|------|-----------|
| CALIBRATION_QUICK_REF.md | 280 | Reference | 2 min |
| CALIBRATION_SUMMARY.md | 500 | Summary | 10 min |
| CALIBRATION_IMPLEMENTATION.md | 200 | Technical | 15 min |
| CALIBRATION_USAGE_GUIDE.md | 500 | Reference | 30 min |
| CALIBRATION_ARCHITECTURE.md | 600 | Visual | 20 min |
| FRONTEND_INTEGRATION_CALIBRATION.md | 500 | Guide | 30 min |
| CALIBRATION_CHECKLIST.md | 400 | Checklist | 15 min |

**Total Documentation**: 2,980 lines of comprehensive guides

---

## 🔄 Continuous Improvement

As you implement and test:
1. Document any discoveries in implementation notes
2. Update CALIBRATION_CHECKLIST.md with actual findings
3. Add any workarounds to CALIBRATION_USAGE_GUIDE.md
4. Report issues for Phase 2 planning

---

## 📍 You Are Here

✅ Backend implementation COMPLETE
📍 You are reading the documentation
→ Next: Frontend implementation begins

**Ready to start?** → Open [CALIBRATION_QUICK_REF.md](CALIBRATION_QUICK_REF.md)
