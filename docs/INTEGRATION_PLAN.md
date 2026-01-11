# Integration Plan: WSPR Beacon + FT8 Tools

## Overview

This repository contains two related but separate tool sets:
1. **WSPR Beacon Control** (main directory) - Serial control of BG6JJI WSPR beacon
2. **FT8 Analysis Tools** (prior-ft8-work/) - Antenna comparison, propagation analysis, WSJT-X automation

**Goal**: Integrate these into a unified HF propagation toolkit while maintaining modularity.

## Current State

### WSPR Beacon Tools (Root)
- `wspr_band.py` - Band switching via serial (✓ PEP 723 + uv)
- `test_wspr_band.py` - Test suite (✓ PEP 723 + uv)
- `Makefile` - Quick band switching targets
- `README.md` - WSPR beacon documentation
- `RECOVERY.md` - GPS auto-grid recovery guide
- **Status**: Production ready, actively tested

### FT8 Tools (prior-ft8-work/)
- `antenna.py` - Antenna A/B comparison, bearing analysis, PSKReporter integration
- `antenna_web.py` - Flask web UI with azimuthal projection maps
- `wsjtx_control.py` - UDP control of WSJT-X from WSL2 ⚠️ **Non-working, on hold**
- `ft8tool.py` - Interactive TUI menu
- `split_adi_by_gridsquare.py` - Multi-QTH log management ⚠️ **Works but ad-hoc, no established workflow**
  - Use case: Same laptop used at CM98kq (Folsom) and CN88ra (Freeland), contacts intermingled in single WSJT-X log
  - Needs workflow integration for regular splitting and upload to QRZ/LoTW
- `check_qrz_settings.py` - QRZ profile validation
- **Status**: Mostly working but needs modernization (no uv/PEP 723)

### Planned Dashboard (wspr_dashboard_spec.md)
- PSKReporter polling for WSPR/FT8 spots
- SQLite database for spots, worked DXCC/grids
- Streamlit dashboard with "what's open now?"
- Pushover alerts for new DXCCs/grids
- **Status**: Spec only, not implemented

## Key Synergies Identified

### 1. Azimuthal Visualization (DONE in FT8, PLANNED for WSPR)
- **Existing**: `antenna_web.py` has full azimuthal projection map
  - SVG-based rendering with continent outlines
  - Plots stations by bearing/distance from QTH
  - Color-coded by SNR, filterable by band
  - Located in `templates/analysis.html` lines 1355-1500
- **Reuse**: Extract azimuthal projection code for WSPR dashboard
- **Integration**: Create shared `geo_utils.py` module

### 2. PSKReporter API Integration
- **Existing**: `antenna.py` already queries PSKReporter for TX analysis
- **Reuse**: Same API calls work for WSPR spots
- **Integration**: Unified PSKReporter client module

### 3. Grid/Distance/Bearing Calculations
- **Existing**: `antenna.py` has:
  - `grid_to_latlon()` - Maidenhead conversion
  - `calc_bearing()` - Great circle bearing
  - `haversine_distance()` - Distance calculation
  - Band frequency mapping
- **Reuse**: Move to shared `geo_utils.py`

### 4. Solar Data Integration
- **Existing**: `antenna.py` fetches from HamQSL solar XML
- **Reuse**: Dashboard can use same source
- **Enhancement**: Track solar conditions during beacon tests

### 5. Automation Potential
- **WSPR beacon**: `wspr_band.py` enables programmatic band switching
- **WSJT-X control**: `wsjtx_control.py` (⚠️ currently non-working) could enable frequency/grid changes
- **Future**: Coordinated testing across both modes (pending WSJT-X control fixes)

## Integration Strategy

### Phase 1: Modernization (Immediate)
**Goal**: Update FT8 tools to match WSPR tool quality

1. **Add PEP 723 metadata to all Python scripts**
   - `antenna.py` → uv inline script metadata
   - `antenna_web.py` → flask, dependencies
   - `wsjtx_control.py` → minimal deps
   - `ft8tool.py` → curses/TUI deps
   - Other scripts as needed

2. **Create shared modules**
   - `lib/geo_utils.py` - Grid, bearing, distance calculations
   - `lib/pskreporter.py` - PSKReporter API client
   - `lib/solar.py` - Solar data fetching
   - `lib/band_utils.py` - Frequency/band mapping

3. **Update README structure**
   - Main README covers both WSPR and FT8 tools
   - Separate docs: `docs/wspr-beacon.md`, `docs/ft8-tools.md`
   - Keep current README content, reorganize

4. **Standardize configuration**
   - Move to `~/.config/ak6mj-hf/config.yaml`
   - Unified config for callsign, grids, device paths
   - Backwards compatible with existing configs

### Phase 2: Code Extraction (Near-term)
**Goal**: Extract reusable components

1. **Extract azimuthal projection**
   - From: `prior-ft8-work/templates/analysis.html` (JavaScript)
   - To: Python implementation in `lib/geo_utils.py`
   - To: JavaScript library in `static/js/azimuthal.js` for web UIs
   - Include continent outline data

2. **Extract PSKReporter client**
   - From: `antenna.py` PSKReporter functions
   - To: `lib/pskreporter.py` with class-based API
   - Support both TX (who heard me) and RX (who I heard) queries
   - Add caching, rate limiting

3. **Create test suite for shared libs**
   - `test_geo_utils.py` - Grid conversions, distance, bearing
   - `test_pskreporter.py` - API mocking, parsing
   - Use pytest framework

### Phase 3: Dashboard Implementation (Future)
**Goal**: Build unified propagation dashboard

1. **Implement wspr_dashboard_spec.md**
   - SQLite database schema
   - `wspr_ingest.py` - PSKReporter poller
   - `wspr_log_sync.py` - ADIF parser
   - Streamlit dashboard UI

2. **Add azimuthal visualization to dashboard**
   - Reuse extracted azimuthal projection code
   - Show WSPR spots on polar map
   - Color-code by SNR, filter by band/time

3. **Integrate beacon control**
   - Dashboard shows current beacon band
   - Optional: Manual band switching from UI
   - Logs band changes with timestamps

4. **Alerts and automation**
   - Pushover notifications per spec
   - Optional: Automated band switching based on propagation
   - Coordinate WSPR beacon + FT8 operating

### Phase 4: Advanced Integration (Long-term)
**Goal**: Unified toolkit with automation

1. **Unified web UI**
   - Combine `antenna_web.py` Flask app with dashboard
   - Single port, tabbed interface
   - WSPR tab, FT8 tab, Antenna Comparison tab

2. **Cross-mode analysis**
   - Compare WSPR beacon reports vs FT8 QSOs
   - "Which mode works better on this band/time?"
   - Correlation with solar conditions

3. **Automated testing**
   - Script: "Test 40m, 20m, 15m for 15 min each"
   - Auto-switch beacon bands
   - Collect PSKReporter data
   - Generate comparison report

4. **Multi-QTH support**
   - Track CM98kq (Folsom) vs CN88ra (Freeland)
   - Separate logs, configs, analysis
   - Propagation differences by location

## Directory Structure (Proposed)

```
wspr/                           # Repository root
├── README.md                   # Overview of all tools
├── INTEGRATION_PLAN.md         # This file
├── RECOVERY.md                 # WSPR beacon recovery
├── Makefile                    # WSPR beacon shortcuts
├── wspr_band.py                # WSPR beacon control (PEP 723)
├── test_wspr_band.py           # WSPR tests (PEP 723)
│
├── docs/                       # Detailed documentation
│   ├── wspr-beacon.md          # WSPR beacon guide (from main README)
│   ├── ft8-tools.md            # FT8 tools guide (from prior-ft8-work README)
│   ├── dashboard-spec.md       # Dashboard specification
│   └── automation.md           # Automation recipes
│
├── lib/                        # Shared Python modules (PEP 723)
│   ├── __init__.py
│   ├── geo_utils.py            # Grid, bearing, distance, azimuthal projection
│   ├── pskreporter.py          # PSKReporter API client
│   ├── solar.py                # Solar data fetching
│   ├── band_utils.py           # Frequency/band mapping
│   └── config.py               # Unified config loader
│
├── ft8/                        # FT8 tools (modernized)
│   ├── antenna.py              # Antenna comparison (PEP 723)
│   ├── antenna_web.py          # Web UI (PEP 723)
│   ├── wsjtx_control.py        # WSJT-X UDP control (⚠️ non-working)
│   ├── ft8tool.py              # Interactive TUI (PEP 723)
│   ├── split_adi.py            # Log splitter (PEP 723)
│   ├── check_qrz.py            # QRZ validator (PEP 723)
│   ├── templates/              # Flask templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── analysis.html       # With azimuthal map
│   └── static/                 # CSS, JS
│       ├── css/
│       └── js/
│           └── azimuthal.js    # Extracted projection code
│
├── dashboard/                  # Unified propagation dashboard (future)
│   ├── wspr_ingest.py          # PSKReporter poller (PEP 723)
│   ├── wspr_log_sync.py        # ADIF parser (PEP 723)
│   ├── wspr_dashboard.py       # Streamlit app (PEP 723)
│   └── schema.sql              # SQLite schema
│
├── tests/                      # Test suite
│   ├── test_geo_utils.py
│   ├── test_pskreporter.py
│   ├── test_wspr_band.py       # Move here
│   └── fixtures/
│
└── prior-ft8-work/             # KEEP for reference during migration
    └── ... (original files preserved until migration complete)
```

## Migration Checklist

### Phase 1 Tasks
- [ ] Create `lib/` directory structure
- [ ] Extract grid/bearing/distance to `lib/geo_utils.py`
- [ ] Extract PSKReporter client to `lib/pskreporter.py`
- [ ] Extract solar data to `lib/solar.py`
- [ ] Extract band utils to `lib/band_utils.py`
- [ ] Create unified config in `lib/config.py`
- [ ] Add PEP 723 metadata to `antenna.py`
- [ ] Add PEP 723 metadata to `antenna_web.py`
- [ ] ~~Add PEP 723 metadata to `wsjtx_control.py`~~ **Skip - non-working, needs debugging**
- [ ] Add PEP 723 metadata to `ft8tool.py`
- [ ] Add PEP 723 metadata to other FT8 scripts
- [ ] Create `docs/` directory
- [ ] Move WSPR content to `docs/wspr-beacon.md`
- [ ] Move FT8 content to `docs/ft8-tools.md`
- [ ] Update main README with integration overview
- [ ] Create `tests/` directory
- [ ] Move `test_wspr_band.py` to `tests/`
- [ ] Add tests for shared libs

### Phase 2 Tasks
- [ ] Extract azimuthal projection to Python
- [ ] Extract azimuthal projection to standalone JS
- [ ] Create continent outline data file
- [ ] Test azimuthal rendering across modes
- [ ] Refactor `antenna.py` to use shared libs
- [ ] Refactor `antenna_web.py` to use shared libs
- [ ] Update all imports to use `lib/` modules
- [ ] Verify all tests pass

### Phase 3 Tasks (Dashboard)
- [ ] Implement SQLite schema from spec
- [ ] Create `wspr_ingest.py` with PSKReporter polling
- [ ] Create `wspr_log_sync.py` with ADIF parsing
- [ ] Create Streamlit dashboard skeleton
- [ ] Add azimuthal map to dashboard
- [ ] Implement Pushover alerts
- [ ] Add beacon control integration
- [ ] Test end-to-end workflow

### Phase 4 Tasks (Advanced)
- [ ] Merge Flask apps into unified web UI
- [ ] Add cross-mode analysis features
- [ ] Create automation scripts
- [ ] Add multi-QTH tracking
- [ ] Performance optimization
- [ ] Documentation polish

## Breaking Changes & Compatibility

### Minimizing Disruption
1. **Keep `prior-ft8-work/` intact** during Phase 1-2
2. **Symlink strategy**: Create symlinks in old locations → new locations
3. **Config migration**: Auto-detect old configs, offer to migrate
4. **Gradual cutover**: Test new code alongside old before removing

### Testing Strategy
1. **Unit tests** for all shared libs
2. **Integration tests** for each tool
3. **Manual testing** with real hardware before removing old code
4. **Backup** of working tools before major refactors

## Success Criteria

### Phase 1 Complete
- ✓ All Python scripts use uv + PEP 723
- ✓ Shared libraries extracted and tested
- ✓ Documentation reorganized
- ✓ No functionality lost from prior-ft8-work/

### Phase 2 Complete
- ✓ Azimuthal projection reusable across projects
- ✓ PSKReporter client unified
- ✓ All tools use shared libs
- ✓ Test coverage >80%

### Phase 3 Complete
- ✓ Dashboard deployed and running
- ✓ Alerts working via Pushover
- ✓ WSPR + FT8 data integrated
- ✓ Azimuthal map shows live spots

### Phase 4 Complete
- ✓ Single unified web UI
- ✓ Cross-mode analysis working
- ✓ Automation scripts tested
- ✓ Multi-QTH support functional

## Next Steps

1. **Review this plan** - User feedback, adjustments
2. **Start Phase 1** - Create lib/ structure, begin extraction
3. **Iterative development** - One component at a time
4. **Continuous testing** - Don't break working code
5. **Document as we go** - Keep docs in sync with code

## Questions for User

1. **Priority**: Which phase should we tackle first?
2. **Breaking changes**: OK to reorganize directory structure?
3. **Config location**: `~/.config/ak6mj-hf/` or keep separate configs?
4. **Web UI**: Prefer Flask (like antenna_web.py) or Streamlit (like spec)?
5. **Timeline**: Quick migration or careful/gradual?
6. **WSPR beacon recovery**: Have you recovered the device yet? This is urgent!
