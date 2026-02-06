#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "pyserial",
#   "pyyaml",
# ]
# ///
"""wspr-band.py - Configure WSPR beacon band

SPEC
====
Device: WSPR Beacon V1.06 by BG6JJI (serial over USB)
Protocol:
  1. Beacon emits "TX:<call> <grid> <power> <freq> DONE" when idle (between transmissions)
  2. Send "CONFIG:<call>,<grid>,<power>,<freq>\r\n" to reconfigure
  3. Beacon responds with "OK <call> <grid> <power> <freq>"
  4. Beacon then emits new "TX:<call> <grid> <power> <freq> DONE" confirming change

Timing:
  - WSPR TX is ~110 seconds, every even minute
  - May need to wait up to 2 min for TX: idle line

Serial:
  - Baud: 9600 (default)
  - Line ending: \r\n
  - Device: /dev/cu.usbserial-10 (macOS) or /dev/ttyUSB0 (Linux)

WSPR frequencies (Hz):
  160m=1838100, 80m=3570100, 40m=7040100, 30m=10140200, 20m=14097100,
  17m=18106100, 15m=21096100, 12m=24926100, 10m=28126100, 6m=50294500

WSPR powers (dBm -> watts):
  0=1mW, 3=2mW, 7=5mW, 10=10mW, 13=20mW, 17=50mW, 20=100mW, 23=200mW,
  27=500mW, 30=1W, 33=2W, 37=5W, 40=10W, 43=20W, 47=50W, 50=100W,
  53=200W, 57=500W, 60=1kW

Example exchange:
  < TX:AK6MJ CM98 23 7040100 DONE
  > CONFIG:AK6MJ,CM98,23,21096100
  < OK AK6MJ CM98 23 21096100
  < TX:AK6MJ CM98 23 21096100 DONE

Config file: ~/.config/wspr-beacon/config.yaml
  callsign: AK6MJ
  grid: CM98              # Explicit grid (recommended) or "auto" for GPS
  power: 23
  device: /dev/cu.usbserial-10
  baud: 9600

Grid Options:
  CM98: Explicit 4-character Maidenhead grid locator (recommended, default)
  auto: GPS auto-detection (WARNING: Requires GPS antenna! Device will reboot loop without it!)

Usage:
  wspr-band.py <band>                  # use config defaults (explicit grid)
  wspr-band.py 20m -g CM98             # override to explicit grid
  wspr-band.py 20m -g auto             # use GPS auto-grid (requires GPS antenna!)
  wspr-band.py 20m -p 27               # override power to 500mW
  wspr-band.py 40m -d /dev/ttyUSB0     # override device
  wspr-band.py --dump-config           # emit default config to stdout
  wspr-band.py --monitor               # monitor serial output (Ctrl-C to exit)

Dependencies: pyserial, pyyaml
"""

import argparse
import re
import serial
import sys
import yaml
import subprocess
import time
from pathlib import Path

FREQS = {
    "160m": 1838100,
    "80m": 3570100,
    "40m": 7040100,
    "30m": 10140200,
    "20m": 14097100,
    "17m": 18106100,
    "15m": 21096100,
    "12m": 24926100,
    "10m": 28126100,
    "6m": 50294500,
}

POWERS = {
    0: "1 mW", 3: "2 mW", 7: "5 mW", 10: "10 mW", 13: "20 mW",
    17: "50 mW", 20: "100 mW", 23: "200 mW", 27: "500 mW", 30: "1 W",
    33: "2 W", 37: "5 W", 40: "10 W", 43: "20 W", 47: "50 W",
    50: "100 W", 53: "200 W", 57: "500 W", 60: "1 kW",
}

DEFAULTS = {
    "callsign": "AK6MJ",
    "grid": "CM98",  # Explicit grid (safer). Use "auto" for GPS auto-detection ONLY if GPS antenna attached!
    "power": 23,
    "device": "/dev/cu.usbserial-10",
    "baud": 9600,
}

def load_config(path):
    if path.exists():
        config_data = yaml.safe_load(path.read_text())
        if config_data:
            return {**DEFAULTS, **config_data}
    return DEFAULTS

def wait_for(ser, prefix, timeout=120, start_time=None):
    ser.timeout = timeout
    prefixes = (prefix,) if isinstance(prefix, str) else prefix
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            return None
        if start_time:
            elapsed = int(time.time() - start_time)
            print(f"[t+{elapsed:3d}s] < {line}")
        else:
            print(f"[t+???s] < {line}")
        for p in prefixes:
            if line.startswith(p):
                return line

def handle_serial_error(device, error):
    """Handle serial port errors with diagnostics"""
    if "Resource busy" in str(error) or "Permission denied" in str(error):
        print(f"Error: {device} is busy or in use", file=sys.stderr)
        try:
            result = subprocess.run(['lsof', device],
                                  capture_output=True,
                                  text=True,
                                  timeout=2)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print("\nPort is currently opened by:", file=sys.stderr)
                    print('\n'.join(lines[1:]), file=sys.stderr)
                    print("\nClose the application using the port and try again.", file=sys.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        sys.exit(1)
    else:
        sys.exit(f"Failed to open {device}: {error}")

def monitor_serial(device, baud):
    """Monitor serial output from the beacon"""
    print(f"Monitoring {device} at {baud} baud")
    print("Press Ctrl-C to exit")
    print("-" * 60)

    try:
        ser = serial.Serial(device, baud, timeout=1)
    except serial.SerialException as e:
        handle_serial_error(device, e)

    try:
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(line)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()

def main():
    p = argparse.ArgumentParser(description="Configure WSPR beacon band")
    p.add_argument("band", nargs="?", choices=FREQS.keys(), help="Band to set")
    p.add_argument("-c", "--call", help="Callsign")
    p.add_argument("-g", "--grid", help="Grid square")
    p.add_argument("-p", "--power", type=int, help="Power in dBm (default: 23)")
    p.add_argument("-d", "--device", help="Serial device")
    p.add_argument("-b", "--baud", type=int, help="Baud rate")
    p.add_argument("--config", type=Path, default=Path.home() / ".config/wspr-beacon/config.yaml")
    p.add_argument("--dump-config", action="store_true", help="Emit default config to stdout")
    p.add_argument("--monitor", action="store_true", help="Monitor serial output")
    args = p.parse_args()

    if args.dump_config:
        print(yaml.dump(DEFAULTS, default_flow_style=False))
        sys.exit(0)

    cfg = load_config(args.config)
    device = args.device or cfg["device"]
    baud = args.baud or cfg["baud"]

    if args.monitor:
        monitor_serial(device, baud)
        sys.exit(0)

    if not args.band:
        p.error("band is required unless --dump-config or --monitor")

    call = args.call or cfg["callsign"]
    grid = args.grid or cfg["grid"]
    power = args.power if args.power is not None else cfg["power"]

    # Handle compound callsign suffix (e.g., AK6MJ-2)
    # WSPR Type 1 only supports standard callsigns (max 6 chars).
    # Strip the suffix and offset the grid so the beacon is
    # distinguishable from the primary on WSPRnet.
    suffix_match = re.match(r'^(.+)-(\d+)$', call)
    if suffix_match:
        call_base = suffix_match.group(1)
        call_suffix = int(suffix_match.group(2))
        if len(call_base) > 6:
            sys.exit(f"Base callsign '{call_base}' exceeds beacon 6-character limit")
        print(f"Compound callsign '{call}':")
        print(f"  WSPR beacon only supports standard callsigns (max 6 chars)")
        call = call_base
        print(f"  Beacon callsign: {call}")
        # Offset grid to distinguish from primary beacon
        if not args.grid:
            if len(grid) == 4 and grid[3].isdigit():
                orig_grid = grid
                lat_digit = int(grid[3])
                new_digit = max(lat_digit - (call_suffix - 1), 0)
                grid = grid[:3] + str(new_digit)
                if grid != orig_grid:
                    print(f"  Grid: {orig_grid} -> {grid} (offset to distinguish on WSPRnet)")

    if power not in POWERS:
        sys.exit(f"Invalid power {power} dBm. Valid: {list(POWERS.keys())}")

    # Convert "auto" to 4 spaces for GPS auto-grid
    if grid.lower() == "auto":
        grid_display = "auto (GPS)"
        grid_config = "    "  # 4 spaces
    else:
        grid_display = grid
        grid_config = grid

    freq = FREQS[args.band]
    config_str = f"CONFIG:{call},{grid_config},{power},{freq}"

    print(f"Callsign: {call}, Grid: {grid_display}")
    print(f"Power: {power} dBm ({POWERS[power]})")
    print(f"Band: {args.band} ({freq} Hz)")
    print(f"Opening {device} at {baud} baud")

    start_time = time.time()

    try:
        ser = serial.Serial(device, baud)
    except serial.SerialException as e:
        handle_serial_error(device, e)

    try:
        print("Waiting for TX idle...")
        print("Note: WSPR transmits every ~2 minutes. Complete process may take 3-4 minutes.")
        print("      Don't panic - grab coffee and watch the timestamps!")
        if not wait_for(ser, "TX:", start_time=start_time):
            sys.exit("Timeout waiting for TX line")

        elapsed = int(time.time() - start_time)
        print(f"[t+{elapsed:3d}s] > {config_str}")
        ser.write(f"{config_str}\r\n".encode())

        response = wait_for(ser, ("OK", "ERR"), start_time=start_time)
        if not response:
            sys.exit("No response received from beacon")
        elif response.startswith("ERR"):
            sys.exit("Beacon rejected configuration (invalid format or parameters)")

        tx_line = wait_for(ser, "TX:", start_time=start_time)
        if not tx_line:
            sys.exit("No TX confirmation")

        # Verify frequency in TX line
        if str(freq) in tx_line:
            elapsed = int(time.time() - start_time)
            print(f"[t+{elapsed:3d}s] Success: Beacon now on {args.band} ({freq} Hz) at {POWERS[power]}")
        else:
            print(f"Warning: TX line shows different frequency: {tx_line}", file=sys.stderr)
            sys.exit(1)
    finally:
        ser.close()

if __name__ == "__main__":
    main()
