# Piano LED Visualizer - Future Roadmap

## Current State (✅ Completed)

**Phase 0 - Core Geometry & Analysis (COMPLETE)**
- ✅ Accurate piano key geometry (all 88 keys)
- ✅ Correct LED placement calculations (relative indices)
- ✅ Physical overhang/coverage metrics
- ✅ Symmetry scoring system
- ✅ Threshold-based LED filtering
- ✅ Comprehensive analysis API (`/api/calibration/physical-analysis`)

**System Status:** Production-ready geometry engine with full physical analysis

---

## Future Phases

### Phase 2: Physics-Based Detection Algorithm (1-2 weeks)

**Objective:** Replace current allocation algorithm with physics-based LED-to-key detection

**Current Approach:**
- Fixed LED-to-key assignment ratios
- Does not account for physical spacing variations
- Cannot adapt to hardware mounting variations

**Proposed Approach:**
- Use physical geometry to dynamically determine LED assignments
- Each key gets LEDs that physically overlap its exposed surface
- Threshold-based filtering (overhang ≤ 1.5mm) ensures quality
- Automatic handling of boundary conditions

**Deliverables:**
- New allocation algorithm in `backend/services/` 
- Migration from fixed ratios to physics-based mapping
- Automatic re-calibration on geometry changes
- Validation tests against current mapping

**Benefits:**
- ✅ Adapts to different LED strips/densities
- ✅ Better handles non-standard mounting
- ✅ Quality metrics drive assignments
- ✅ Less manual tuning required

**Technical Work:**
- Implement LED-to-key mapper using `PhysicalMappingAnalyzer`
- Add settings for allocation parameters (threshold, min coverage %, etc.)
- Create migration path from old to new algorithm
- Add comparison metrics (old vs new quality)

---

### Phase 3: UI Visualization & Interactive Tuning (2-3 weeks)

**Objective:** Interactive frontend for visualizing and tuning LED assignments

**Visualization Components:**

1. **Physical Layout Viewer**
   - Piano keyboard visual representation
   - LED strip overlay showing physical positions
   - Interactive zoom/pan for detail inspection
   - Real-time LED assignment highlighting

2. **Per-Key Analysis Dashboard**
   - Key selection displays detailed metrics:
     - Physical range (mm)
     - Exposed range (mm)
     - Assigned LEDs with visualization
     - Coverage %, overhang (L/R), symmetry score
     - Quality grade
   - Side-by-side key comparisons

3. **Quality Metrics Panel**
   - Overall alignment score
   - Distribution of quality grades (Excellent/Good/Acceptable/Poor)
   - Average symmetry and coverage stats
   - Problem keys highlighted (below threshold)

4. **Interactive Tuning Controls**
   - Slider: Overhang threshold adjustment (0.5-3.0mm)
   - Slider: Minimum coverage % requirement (20-100%)
   - Dropdown: Quality grade filter
   - Button: Auto-optimize allocation
   - Button: Apply/save allocation

5. **Real-Time Preview**
   - Live update of metrics as parameters change
   - Visual feedback of affected keys
   - Before/after comparison

**Technical Stack:**
- React component for layout viewer (SVG-based)
- D3.js or similar for visualization
- WebSocket for real-time updates
- Settings API integration for persistence

**Data Flow:**
```
Frontend (Interactive Controls)
    ↓
API (POST /api/calibration/allocate with params)
    ↓
Backend (PhysicalMappingAnalyzer)
    ↓
JSON Response (full analysis)
    ↓
Frontend (update visualization)
```

**File Structure:**
```
frontend/
  src/
    components/
      calibration/
        PhysicalLayoutViewer.tsx      # Main visualization
        KeyAnalysisPanel.tsx          # Per-key metrics
        QualityMetricsPanel.tsx       # Overview stats
        TuningControls.tsx            # Interactive sliders
        ComparisonView.tsx            # Before/after
    pages/
      CalibrationPhysical.tsx         # Main page
```

**Deliverables:**
- ✅ Interactive physical layout viewer
- ✅ Per-key analysis dashboard
- ✅ Quality metrics display
- ✅ Real-time tuning interface
- ✅ Allocation saving/loading UI
- ✅ Export analysis reports

**Benefits:**
- 🎨 Visual understanding of LED placement
- 🎯 Easy problem identification
- ⚙️ Interactive parameter tuning
- 📊 Data-driven optimization
- 📈 Before/after comparison

---

## Implementation Priorities

### Phase 2 Dependencies (What's Needed First)
- [ ] Finalize physics-based allocation algorithm
- [ ] Unit tests for allocation logic
- [ ] API endpoint `/api/calibration/allocate` with parameters
- [ ] Settings keys for allocation parameters
- [ ] Migration script from old → new algorithm

### Phase 3 Dependencies (Requires Phase 2)
- [ ] Phase 2 complete and stable
- [ ] Full physical analysis working
- [ ] WebSocket support for real-time updates
- [ ] Settings persistence layer

---

## Success Metrics

**Phase 2 Success:**
- Physics-based allocation produces equal/better quality than manual tuning
- All 88 keys properly assigned without overlaps
- Algorithm adapts to different LED densities
- Quality metrics validate correct assignments

**Phase 3 Success:**
- Users can visualize LED-to-key assignments
- Interactive tuning achieves >95% user satisfaction
- <5 second response time for parameter changes
- Metrics accurately reflect visual placement

---

## Risk Mitigation

**Phase 2 Risks:**
- Algorithm too rigid/specific
  - *Mitigation:* Comprehensive parameter system
- Migration breaks existing installations
  - *Mitigation:* Backwards compatibility layer

**Phase 3 Risks:**
- Visualization doesn't scale to complex layouts
  - *Mitigation:* SVG-based with infinite zoom
- Real-time updates cause performance issues
  - *Mitigation:* Debounce, WebSocket optimization

---

## Documentation Roadmap

### Phase 2 Docs
- [ ] Allocation Algorithm Design Document
- [ ] Physics-Based Detection Explanation
- [ ] Migration Guide (old → new)
- [ ] Configuration Reference

### Phase 3 Docs
- [ ] UI Component Guide
- [ ] Interactive Tuning Tutorial
- [ ] Troubleshooting Guide
- [ ] Performance Optimization Guide

---

## Quick Reference

| Phase | Duration | Complexity | Impact | Status |
|-------|----------|-----------|--------|--------|
| **0** (Current) | Complete | High | Core engine ready | ✅ Done |
| **2** | 1-2 weeks | Medium | Auto-calibration | 📋 Planned |
| **3** | 2-3 weeks | High | User experience | 📋 Planned |

---

## Related Documentation

📚 **Detailed Implementation Guide:** `IMPLEMENTATION_INDEX.md`
🚀 **Quick Reference:** `AUTO_MAPPING_QUICK_REFERENCE.md`
📊 **Visual Overview:** `FRONTEND_ARCHITECTURE_DIAGRAMS.md`
📋 **File Manifest:** See workspace structure

---

## Contact & Questions

For implementation details, refer to:
- Backend geometry: `backend/config_led_mapping_physical.py`
- Current allocation: `backend/services/` (midi_input_manager, led_controller)
- Frontend structure: `frontend/src/` (calibration components)
