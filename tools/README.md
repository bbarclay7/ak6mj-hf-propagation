# FT8 Tools for AK6MJ

Amateur radio tools for FT8 operation, focusing on:
- Antenna A/B comparison testing
- Multi-QTH log and profile management
- WSJT-X automation

## Quick Start

```bash
python3 ft8tool.py      # Interactive TUI - recommended
```

Or use individual tools directly (see below).

## Tools

### antenna.py - Antenna Comparison & Analysis

Compare antenna performance using real-world FT8 signals. Analyzes both:
- **RX performance** - Who you heard (from WSJT-X ALL.TXT)
- **TX performance** - Who heard you (from PSKReporter)

```bash
# Define antennas
python3 antenna.py define A "40m EFHW, 30ft"
python3 antenna.py define B "Vertical, ground-mounted"

# Run A/B test
python3 antenna.py start          # Captures solar conditions
python3 antenna.py use A          # Switch to antenna A, operate 10-15 min
python3 antenna.py use B          # Switch to antenna B, operate 10-15 min
python3 antenna.py stop
python3 antenna.py analyze CM98kq # Compare by band and bearing

# Other commands
python3 antenna.py list           # Show defined antennas
python3 antenna.py solar          # Current propagation conditions
python3 antenna.py tod 06:00-09:00 18:00-21:00 CM98kq  # Time-of-day analysis
```

Analysis creates a `comparison_YYYYMMDD_HHMMSS/` directory with raw data for later review. See `comparison_README.md` for details.

**Best practice:** Alternate antennas within each band (A→B→A) rather than all bands on A then all on B. This minimizes propagation drift effects. Transmit during each interval to capture TX data.

### wsjtx_control.py - WSJT-X Remote Control

Control WSJT-X on Windows from WSL2 via UDP.

```bash
python3 wsjtx_control.py status          # Show connection info
python3 wsjtx_control.py switch 20m      # Switch to named configuration
python3 wsjtx_control.py grid CN88ra     # Set grid locator
python3 wsjtx_control.py test            # Test by clearing Band Activity
```

Requires one-time WSJT-X setup:
1. File → Settings → Reporting
2. Check "Accept UDP requests"
3. UDP Server: `0.0.0.0`, Port: `2237`

### split_adi_by_gridsquare.py - Log Splitter

Splits WSJT-X ADIF log by MY_GRIDSQUARE field for separate QTH uploads.

```bash
python3 split_adi_by_gridsquare.py
```

### check_qrz_settings.py - QRZ Profile Validator

Checks if QRZ.com profile matches current IP geolocation.

```bash
python3 check_qrz_settings.py
```

### ft8tool.py - Interactive TUI

Menu-driven interface combining all tools above.

```bash
python3 ft8tool.py
```

## Makefile Shortcuts

```bash
make check    # Verify QRZ profile matches current IP location
make go       # Split log by gridsquare, copy to WSJT-X folder
make folsom   # Show settings for CM98kq, open QRZ edit page
make freeland # Show settings for CN88ra, open QRZ edit page
```

## Environment

- **Host OS:** Windows 11 (runs WSJT-X)
- **Dev environment:** Debian WSL2
- **Cross-OS access:** WSL2 mounts Windows at `/mnt/c/`

### File Locations

| File | Path |
|------|------|
| WSJT-X log | `/mnt/c/Users/admin/AppData/Local/WSJT-X/wsjtx_log.adi` |
| ALL.TXT | `/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT` |
| QRZ credentials | `~/.qrz_credentials` |

### QRZ Credentials File

Create `~/.qrz_credentials`:
```
username=AK6MJ
password=YOUR_PASSWORD
```

## QTH Reference

| Location | Grid | County | IOTA |
|----------|------|--------|------|
| Folsom, CA | CM98kq | Sacramento | - |
| Freeland, WA | CN88ra | Island | NA-065 |

## Data Sources

- **RX data:** WSJT-X ALL.TXT (local)
- **TX data:** [PSKReporter](https://pskreporter.info) API (last 24 hours only)
- **Solar data:** [HamQSL](https://www.hamqsl.com/solarxml.php) (N0NBH)

## See Also

- `rybtest.md` - Example test procedure for Rybakov vs EFHW comparison
- `comparison_README.md` - Documentation for comparison artifact directories
- `CLAUDE.md` - AI assistant context file
