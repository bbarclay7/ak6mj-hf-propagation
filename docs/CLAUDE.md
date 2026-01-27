# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FT8 tools for amateur radio operator AK6MJ. Manages QRZ profile synchronization across multiple QTHs and provides antenna/propagation analysis tools.

## Quick Start

```bash
python3 ft8tool.py      # Interactive TUI - recommended for new users
```

## Key Files

- `ft8tool.py` - Interactive TUI frontend (start here)
- `antenna.py` - CLI for antenna comparison and propagation analysis
- `split_adi_by_gridsquare.py` - Splits WSJTX log by MY_GRIDSQUARE
- `check_qrz_settings.py` - Validates QRZ profile against IP location
- `Makefile` - Common operations (check, go, folsom, freeland)

## Use Cases

### 1. QRZ Profile & Log Management

**Problem:** Operating from two QTHs (CN88ra Freeland WA, CM98kq Folsom CA) requires keeping QRZ profile in sync and uploading separate logs.

```bash
make check    # Verify QRZ profile matches current IP location
make go       # Split log by gridsquare, copy to WSJT-X folder
make folsom   # Show settings for CM98kq, open QRZ edit page
make freeland # Show settings for CN88ra, open QRZ edit page
```

### 2. Antenna Comparison

**Problem:** Scientifically compare antenna performance by analyzing received signal strengths.

```bash
python3 antenna.py define A "40m EFHW, 30ft"
python3 antenna.py define B "Vertical, ground-mounted"
python3 antenna.py start      # Captures solar conditions
python3 antenna.py use A      # Switch to antenna A
# ... operate 10-15 min ...
python3 antenna.py use B      # Switch to antenna B
# ... operate 10-15 min ...
python3 antenna.py stop
python3 antenna.py analyze CM98kq   # Compare by band and bearing
```

### 3. Time-of-Day Propagation Analysis

**Problem:** Find propagation patterns across different times of day.

```bash
python3 antenna.py tod 06:00-09:00 18:00-21:00 CM98kq
```

### 4. Solar/Propagation Conditions

```bash
python3 antenna.py solar   # Current SFI, K-index, A-index from N0NBH
```

## Environment

- **Host OS:** Windows 11 (runs WSJT-X)
- **Dev environment:** Debian WSL2 container
- **Cross-OS access:** WSL2 mounts Windows filesystem at `/mnt/c/`

## External Dependencies

- WSJTX log: symlinked as `wsjtx_log.adi` → `/mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi`
- ALL.TXT: `/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT`
- QRZ credentials: `~/.qrz_credentials` (username=CALL, password=PASS)
- Solar data: https://www.hamqsl.com/solarxml.php

## WSJT-X Automation

WSJT-X on Windows can be controlled via UDP from WSL2 using `wsjtx_control.py`.

### Setup (one-time in WSJT-X)

1. File -> Settings -> Reporting
2. Check "Accept UDP requests"
3. Set UDP Server to `0.0.0.0` (accept from WSL2)
4. UDP Server port: `2237`

### Band Switching via Configurations

WSJT-X doesn't have a direct "change frequency" UDP message, but you can:

1. Create named configurations in WSJT-X (File -> Settings -> Configurations)
2. Name them by band: `20m`, `40m`, `15m`, etc.
3. Set each config's frequency in the Working Frequencies table
4. Switch remotely: `python3 wsjtx_control.py switch 20m`

### Commands

```bash
python3 wsjtx_control.py status          # Show connection info
python3 wsjtx_control.py test            # Test by clearing Band Activity
python3 wsjtx_control.py switch <config> # Switch to named configuration
python3 wsjtx_control.py grid <locator>  # Set grid locator
```

### Automation Ideas

- Schedule band sweeps across time of day
- Coordinate with antenna.py for automated A/B testing
- Sync grid locator when switching QTH

See: [WSJT-X NetworkMessage.hpp](https://github.com/roelandjansen/wsjt-x/blob/master/NetworkMessage.hpp)

## QTH Reference

| QTH | Grid | County | IOTA | Description |
|-----|------|--------|------|-------------|
| CN88ra | CN88 | Island | NA-065 | Freeland, WA |
| CM98kq | CM98 | Sacramento | (none) | Folsom, CA |

## Future Enhancements

### WSPR Antenna Comparison

The current WSPR comparison (`/hf/wspr/compare`) is hardcoded to compare two specific antennas (80ef1 vs ryb) with a fixed switch time. To match the flexibility of the FT8 antenna comparison system:

1. **Multiple antennas** - Allow defining and comparing any number of antennas, not just two
2. **Dynamic antenna selection** - UI dropdown to select which antennas to compare
3. **Multiple QTH support** - Filter comparison data by grid square (tx_loc from wspr.live)
   - CM98 = Folsom QTH
   - CN88 = Freeland QTH
4. **Antenna history from file** - Read time periods from `antenna_history.json` instead of hardcoded switch times
5. **Multiple switches** - Support A→B→A→C patterns over time
6. **Solar condition normalization** - Weight/group comparisons by K-index, SFI to account for propagation variability

### Data Model

```
QTH (grid)
  └── Antenna
        └── Time periods active
              └── Spots (from wspr.live, filtered by tx_loc)
```

This would allow questions like:
- "Compare ryb vs efhw at CM98 during quiet conditions (K≤2)"
- "Compare same antenna at CM98 vs CN88"
- "Show all antennas tested at Freeland"
