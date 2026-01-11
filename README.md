# AK6MJ HF Propagation Tools

Personal HF propagation monitoring and beacon control tools for AK6MJ (CM98).

## Project Structure

```
wspr/
├── wspr_band.py          # WSPR beacon controller
├── lib/                  # Shared libraries
│   ├── band_utils.py     # Band/frequency utilities
│   ├── config.py         # Configuration management
│   ├── geo_utils.py      # Geographic calculations
│   ├── pskreporter.py    # PSKReporter API client
│   └── solar.py          # Solar data fetching
├── tools/                # FT8 and antenna analysis tools
│   ├── antenna.py        # Antenna comparison tool
│   ├── antenna_web.py    # Web interface for antenna tests
│   ├── ft8tool.py        # FT8 analysis utilities
│   └── ...
├── tests/                # Test suite
├── docs/                 # Documentation
├── scripts/              # Automation scripts
└── local/                # User artifacts (gitignored)
```

## Tools

### wspr_band.py - WSPR Beacon Band Controller

Control WSPR Beacon V1.06 by BG6JJI via serial interface.

**Features:**
- Switch between HF bands (160m-10m)
- Configure callsign, grid, and power
- Monitor serial output
- Automatic dependency management with uv
- Timestamped protocol logging
- Frequency verification

**Quick Start:**
```bash
# Show available commands
make

# Switch bands
make 20m
make 40m POWER=27

# Monitor beacon
make monitor

# Run tests
make test
```

### FT8 Tools (tools/ directory)

See `tools/README.md` for detailed documentation on:
- **antenna.py** - Compare antenna performance using FT8/WSPR data
- **antenna_web.py** - Web interface for antenna experiments
- **ft8tool.py** - FT8 analysis and statistics
- **wsjtx_control.py** - WSJT-X automation

All tools use PEP 723 metadata and run with `uv run`.

**Direct Usage:**
```bash
./wspr_band.py 20m                     # Switch to 20m
./wspr_band.py 40m -p 27               # 40m at 500mW
./wspr_band.py --monitor               # Monitor serial output
./wspr_band.py --dump-config           # Show default config
```

**Configuration:**
Create `~/.config/wspr-beacon/config.yaml`:
```yaml
callsign: AK6MJ
grid: CM98              # Explicit grid recommended. Use "auto" for GPS ONLY if antenna attached!
power: 23
device: /dev/cu.usbserial-10
baud: 9600
```

**⚠️ GPS Auto-Grid Warning:**
- Using `grid: auto` enables GPS-based grid calculation
- **CRITICAL**: Requires GPS antenna to be attached and working
- Without GPS, device will enter reboot loop trying to get GPS lock
- Config persists in EEPROM - device may need factory reset to recover
- **Recommended**: Use explicit grid square (e.g., "CM98") unless you have GPS antenna connected
- **If stuck in reboot loop**: See `docs/RECOVERY.md` for recovery instructions (in attic/)

## Hardware

**WSPR Beacon V1.06 by BG6JJI**
- GPS-synced WSPR transmitter
- USB serial interface (CH340)
- Supports 160m-10m bands
- Purchase: [Banggood](https://uk.banggood.com/custlink/KG38...) or [AliExpress](https://s.click.aliexpress.com/e/_c37...)

Inspired by [Tech Minds: "A CHEAP Way To Test Your HF Antennas Performance With WSPR!"](https://www.youtube.com/watch?v=9ELzV6UiAiU)

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for dependency management
- WSPR Beacon V1.06 hardware (see above)

Dependencies are automatically installed via uv inline script metadata.

**Platform Support:**
- Tested on macOS
- Linux untested (serial device path may differ: `/dev/ttyUSB0` instead of `/dev/cu.usbserial-10`)
- Windows untested

## Documentation

- `docs/INTEGRATION_PLAN.md` - Phase 1-4 modernization and integration plan
- `docs/PHASE1_COMPLETE.md` - Phase 1 completion summary
- `docs/CRON_SETUP.md` - Automated band rotation setup
- `docs/wspr_dashboard_spec.md` - Future dashboard specifications
- `docs/ARTIFACT_STRATEGY.md` - Local artifact management strategy

## Development

**Running Tests:**
```bash
# Run all tests
uv run tests/test_geo_utils.py
uv run tests/test_band_utils.py
uv run tests/test_solar.py
uv run tests/test_config.py
uv run tests/test_wspr_band.py
```

**Automated Band Rotation:**
See `docs/CRON_SETUP.md` for setting up automatic band changes based on time of day and propagation conditions.

## Planned Features

- **Unified Web Dashboard** - Combining WSPR beacon control with FT8/antenna analysis
- **Band Scheduler** - Visual timeline with automatic band switching
- **PSKReporter Integration** - Real-time propagation monitoring with DXCC/grid tracking

## License

Personal project - use at your own risk.

## Author

Brandon (AK6MJ) - CM98
