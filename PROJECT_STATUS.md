# AK6MJ HF Propagation Tools - Project Status

**Last Updated:** 2025-01-10

## Quick Status

**Current State:**
- ✅ WSPR beacon control working (wspr_band.py)
- ✅ FT8 tools copied to prior-ft8-work/
- ✅ Artifact management strategy defined
- ✅ Integration plan created
- ⏳ Awaiting user decisions on integration approach

**Immediate Next Steps:**
1. Review integration plan (INTEGRATION_PLAN.md)
2. Decide on Phase 1 approach
3. Begin code modernization

---

## Document Map

### Planning & Strategy Documents

| Document                     | Purpose                                                        | Status       | Next Action              |
|------------------------------|----------------------------------------------------------------|--------------|--------------------------|
| **PROJECT_STATUS.md**        | This file - master index of all planning docs                  | ✅ Current   | Keep updated             |
| **INTEGRATION_PLAN.md**      | Comprehensive 4-phase integration strategy                     | ✅ Complete  | **User review needed**   |
| **ARTIFACT_STRATEGY.md**     | How to manage user-generated files (comparisons, logs, state)  | ✅ Complete  | Ready to implement       |
| **wspr_dashboard_spec.md**   | Specification for unified propagation dashboard                | ✅ Existing  | Phase 3 implementation   |

### Technical Documentation

| Document                     | Purpose                                   | Status       | Next Action                  |
|------------------------------|-------------------------------------------|--------------|------------------------------|
| **README.md**                | Main project documentation (WSPR beacon)  | ✅ Current   | Will reorganize in Phase 1   |
| **RECOVERY.md**              | WSPR beacon GPS auto-grid recovery guide  | ✅ Complete  | Reference only               |
| **prior-ft8-work/README.md** | FT8 tools documentation                   | ✅ Existing  | Will merge into unified docs |
| **prior-ft8-work/CLAUDE.md** | AI assistant context (FT8 tools)          | ✅ Existing  | Will update                  |

### Code & Tests

| Component                | Status                           | Next Action              |
|--------------------------|----------------------------------|--------------------------|
| **wspr_band.py**         | ✅ Working (PEP 723, uv)         | Stable                   |
| **test_wspr_band.py**    | ✅ Working (19 tests)            | Move to tests/ in Phase 1 |
| **prior-ft8-work/*.py**  | ✅ Working (needs modernization) | Add PEP 723 in Phase 1   |
| **local/**               | ✅ Created, artifacts moved      | Ready for use            |

---

## Integration Overview

We're combining two related tool sets into a unified HF propagation toolkit:

```
┌─────────────────────────────────────────────────────────────┐
│                  AK6MJ HF Propagation Tools                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  WSPR Beacon     │         │   FT8 Tools      │        │
│  │  Control         │         │   & Analysis     │        │
│  ├──────────────────┤         ├──────────────────┤        │
│  │ • Band switching │         │ • Antenna A/B    │        │
│  │ • Serial control │         │ • PSKReporter    │        │
│  │ • Power setting  │         │ • WSJT-X control │        │
│  │ • GPS grid       │         │ • Log management │        │
│  └──────────────────┘         └──────────────────┘        │
│           │                            │                   │
│           └────────────┬───────────────┘                   │
│                        │                                   │
│              ┌─────────▼─────────┐                        │
│              │  Shared Libraries  │                        │
│              ├───────────────────┤                        │
│              │ • Geo calculations │                        │
│              │ • PSKReporter API  │                        │
│              │ • Solar data       │                        │
│              │ • Band mapping     │                        │
│              │ • Configuration    │                        │
│              └───────────────────┘                        │
│                        │                                   │
│              ┌─────────▼─────────┐                        │
│              │  Unified Dashboard │                        │
│              ├───────────────────┤                        │
│              │ • Live propagation │                        │
│              │ • Azimuthal maps   │                        │
│              │ • DXCC/grid alerts │                        │
│              │ • Beacon control   │                        │
│              └───────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## The Four Phases

### Phase 1: Modernization & Code Extraction ⏳ NEXT
**Status:** Ready to start, awaiting user approval
**Timeline:** 1-2 sessions
**Goal:** Update FT8 tools to match WSPR tool quality

**Key Tasks:**
- [ ] Create `lib/` directory with shared modules
  - [ ] `lib/geo_utils.py` - Grid, bearing, distance, azimuthal projection
  - [ ] `lib/pskreporter.py` - PSKReporter API client
  - [ ] `lib/solar.py` - Solar data fetching
  - [ ] `lib/band_utils.py` - Frequency/band mapping
  - [ ] `lib/config.py` - Unified config loader
- [ ] Add PEP 723 metadata to all FT8 scripts
- [ ] Update code to use `local/` directory for artifacts
- [ ] Reorganize documentation (create `docs/` directory)
- [ ] Create comprehensive test suite

**Documents:** INTEGRATION_PLAN.md (Phase 1 section)

**Decision Needed:**
- Approve directory structure?
- Config location: `~/.config/ak6mj-hf/` or keep separate?

---

### Phase 2: Azimuthal Visualization Extraction ⏸️ WAITING
**Status:** Blocked by Phase 1
**Timeline:** 1 session
**Goal:** Reusable azimuthal projection code

**Key Discovery:**
The FT8 tools already have a full azimuthal projection map implementation in `prior-ft8-work/templates/analysis.html` (lines 1355-1500). This can be:
- Extracted to Python (`lib/geo_utils.py`)
- Extracted to standalone JS (`static/js/azimuthal.js`)
- Reused in WSPR dashboard

**Tasks:**
- [ ] Extract JavaScript azimuthal projection to Python
- [ ] Create standalone JS library
- [ ] Include continent outline data
- [ ] Test with WSPR and FT8 data

**Documents:** INTEGRATION_PLAN.md (Phase 2 section)

---

### Phase 3: Dashboard Implementation ⏸️ WAITING
**Status:** Blocked by Phase 1 & 2
**Timeline:** Multiple sessions
**Goal:** Build unified propagation dashboard

**Spec:** wspr_dashboard_spec.md (complete specification exists)

**Key Components:**
- SQLite database for spots, worked DXCC/grids
- `wspr_ingest.py` - PSKReporter poller (15 min cron)
- `wspr_log_sync.py` - ADIF parser (5 min cron)
- Streamlit dashboard UI
- Pushover alerts for new DXCCs/grids
- Azimuthal map visualization (from Phase 2)
- Beacon control integration

**Documents:**
- wspr_dashboard_spec.md (implementation spec)
- INTEGRATION_PLAN.md (Phase 3 section)

---

### Phase 4: Advanced Integration ⏸️ FUTURE
**Status:** Long-term vision
**Timeline:** TBD
**Goal:** Unified toolkit with automation

**Ideas:**
- Merge Flask apps into single web UI
- Cross-mode analysis (WSPR vs FT8 comparison)
- Automated band sweeps
- Multi-QTH tracking (CM98kq vs CN88ra)
- Propagation-based automation

**Documents:** INTEGRATION_PLAN.md (Phase 4 section)

---

## Artifact Management

**Strategy:** Store all user-generated files in `local/` directory

**Status:** ✅ Implemented

```
local/                      # Fully gitignored
├── comparisons/            # Antenna comparison results
├── logs/                   # ADIF logs, databases
│   ├── ALL.TXT -> /mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT
│   └── wsjtx_log.adi -> /mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi
├── state/                  # State files
│   ├── antenna_log.json
│   └── antennas.json
└── config/                 # User configs
```

**What's Done:**
- ✅ Created `local/` structure
- ✅ Updated `.gitignore`
- ✅ Moved artifacts from `prior-ft8-work/`
- ⏳ Need to update code paths in Phase 1

**Documents:** ARTIFACT_STRATEGY.md (complete strategy)

---

## Current Issues & Blockers

### RESOLVED: WSPR Beacon GPS Auto-Grid Recovery ✅
**Problem:** Device entered reboot loop when configured with GPS auto-grid without antenna
**Status:** ✅ RESOLVED - Device recovered automatically
**Actions Taken:**
- Reverted default grid from "auto" to "CM98" (commit 68fa2b2)
- Added GPS warnings to README and script docs
- Created RECOVERY.md with recovery procedures
**Outcome:** Beacon recovered and showing on PSKReporter on 12m

### PENDING: Git Push Blocked by User 🔒
**Status:** Waiting for user to push safety fixes
**Affected Commits:** 68fa2b2 (GPS auto-grid safety fixes)
**Action:** User will push when ready

---

## User Decisions Needed

### Priority 1: Integration Approach
**Question:** Which phase should we tackle first?
- **Recommended:** Phase 1 (Modernization) - Sets foundation for everything else
- Alternative: Jump to Phase 3 (Dashboard) - Get functionality quickly
- Alternative: Phase 2 only (Azimuthal extraction) - Low-hanging fruit

**Impact:** Determines next 1-3 sessions of work

### Priority 2: Directory Structure
**Question:** Approve proposed structure in INTEGRATION_PLAN.md?
```
wspr/
├── lib/           # Shared libraries
├── ft8/           # FT8 tools (moved from prior-ft8-work/)
├── dashboard/     # Dashboard (Phase 3)
├── tests/         # All tests
└── docs/          # All documentation
```

**Alternative:** Keep flatter structure, just add `lib/`

### Priority 3: Configuration Location
**Question:** Where should unified config live?
- Option A: `~/.config/ak6mj-hf/config.yaml` (XDG standard)
- Option B: `local/config/config.yaml` (stays with repo)
- Option C: Both supported, local/ takes precedence

### Priority 4: Web Framework Choice
**Question:** For unified dashboard, use:
- Flask (existing in antenna_web.py) - More control, familiar
- Streamlit (spec suggests this) - Faster prototyping, modern
- Both: Streamlit for dashboard, Flask for antenna comparison

---

## Recent Session Notes

### Session: 2025-01-10
**Accomplished:**
- Reviewed prior FT8 work
- Identified azimuthal projection in analysis.html
- Created comprehensive integration plan
- Defined artifact management strategy (local/ directory)
- Fixed GPS auto-grid safety issue
- Installed gh CLI on WSL2 Debian
- Created this master status document

**User Requests:**
- Unified planning/dev/spec document hierarchy ✅ (this file)
- `local/` directory for artifacts ✅ (implemented)
- Review integration plan ⏳ (in progress)

**Next Session:**
- Get user decisions on integration approach
- Start Phase 1 work (if approved)
- Push committed changes to remote

---

## Quick Reference

### Where to Find Things

**Want to...**
- Understand overall integration plan → **INTEGRATION_PLAN.md**
- Know what to do next → **This file (PROJECT_STATUS.md)**
- Learn about artifact management → **ARTIFACT_STRATEGY.md**
- See dashboard specification → **wspr_dashboard_spec.md**
- Recover bricked WSPR beacon → **RECOVERY.md**
- Use WSPR beacon now → **README.md**
- Use FT8 tools now → **prior-ft8-work/README.md**

### Key Concepts

**local/** - Directory containing all user-generated artifacts (gitignored)

**PEP 723** - Inline script metadata for uv dependency management

**uv** - Fast Python package manager, handles deps automatically

**Azimuthal projection** - Polar map showing bearing/distance from your QTH

**PSKReporter** - Service tracking WSPR/FT8 spots worldwide

---

## Health Check

**Code Quality:**
- WSPR beacon tools: ✅ Modern (PEP 723, uv, tested)
- FT8 tools: ⚠️ Working but needs modernization

**Documentation:**
- WSPR: ✅ Complete
- FT8: ✅ Complete
- Integration: ✅ Planned, not implemented

**Testing:**
- WSPR: ✅ 19 automated tests
- FT8: ⚠️ No automated tests
- Shared libs: ⏳ TBD in Phase 1

**Artifacts:**
- ✅ Organized in local/
- ✅ Properly gitignored
- ✅ Migration complete

**Blockers:**
- ⏳ Awaiting user decisions
- ⏳ Need Phase 1 approval to proceed

---

## Contact & Resources

**User:** Brandon (AK6MJ)
**Grid:** CM98kq (Folsom, CA) / CN88ra (Freeland, WA)
**Repository:** https://github.com/bbarclay7/ak6mj-hf-propagation

**Key External Services:**
- PSKReporter: https://pskreporter.info
- HamQSL Solar: https://www.hamqsl.com/solarxml.php
- WSJT-X: https://wsjt.sourceforge.io

**Hardware:**
- WSPR Beacon V1.06 by BG6JJI
- WSJT-X on Windows 11
- Development on Debian WSL2
