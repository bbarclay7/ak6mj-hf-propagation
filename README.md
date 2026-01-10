# AK6MJ HF Propagation Tools

Personal HF propagation monitoring and beacon control tools for AK6MJ (CM98).

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
# Make scripts executable (first time only)
chmod +x wspr_band.py test_wspr_band.py

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
grid: auto              # Use GPS auto-detection, or explicit grid like "CM98"
power: 23
device: /dev/cu.usbserial-10
baud: 9600
```

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

## Planned

- **WSPR/FT8 Propagation Dashboard** - Real-time propagation monitoring with PSKReporter integration, DXCC/grid tracking, and Pushover alerts. See `wspr_dashboard_spec.md` for details.

## License

Personal project - use at your own risk.

## Author

Brandon (AK6MJ) - CM98
