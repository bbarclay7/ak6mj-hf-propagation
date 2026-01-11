#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Antenna comparison tool for FT8 signal analysis.

Antenna Comparison:
    antenna.py define <label> <description>  - Define or update an antenna
    antenna.py list                          - List defined antennas
    antenna.py start [name]                  - Start a comparison session (optional name)
    antenna.py use <label> [band]            - Switch antenna (and optionally band)
    antenna.py pause                         - Pause session (ignore data while tuning/switching)
    antenna.py resume                        - Resume paused session
    antenna.py stop                          - Stop the current session
    antenna.py note <text>                   - Add a note to current session
    antenna.py note <comparison_id> <text>   - Add a note to past comparison
    antenna.py log                           - Show antenna usage log
    antenna.py analyze [grid]                - Compare antenna performance
    antenna.py clear                         - Clear session log

    Analysis includes:
      - RX: Stations you heard (from ALL.TXT)
      - TX: Stations that heard you (from PSKReporter, last 24h only)

Time-of-Day Analysis (same antenna, different times):
    antenna.py tod <HH:MM-HH:MM> <HH:MM-HH:MM> [grid]  - Compare time windows
        Example: antenna.py tod 06:00-09:00 18:00-21:00 CM98kq
        Analyzes ALL.TXT across all days, comparing morning vs evening

Propagation Data:
    antenna.py solar                         - Show current solar/propagation conditions
"""

import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

# Import from shared libraries
from band_utils import BANDS, freq_to_band
from geo_utils import grid_to_latlon, calc_bearing, calc_distance_km, bearing_to_direction
from pskreporter import fetch_spots
from solar import fetch_solar_data


def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp, assuming UTC if no timezone specified."""
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        # Old logs without timezone - assume they were local time (Pacific)
        # For now, just make them naive UTC to avoid comparison issues
        # This is imperfect but handles the transition
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


MY_CALLSIGN = "AK6MJ"

# Use local/ directory for user artifacts
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "local" / "ft8-tools"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ANTENNAS_FILE = DATA_DIR / "antennas.json"
ANTENNA_LOG_FILE = DATA_DIR / "antenna_log.json"
ALL_TXT = Path("/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT")


def load_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text())
    return {} if "log" not in path.name else []


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))


def parse_all_txt_line(line: str) -> dict | None:
    """Parse a single line from ALL.TXT, return dict or None."""
    # Format: YYMMDD_HHMMSS  freq Rx/Tx MODE snr dt audio_freq message
    match = re.match(
        r'(\d{6}_\d{6})\s+(\d+\.\d+)\s+(Rx|Tx)\s+(\w+)\s+(-?\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(.+)',
        line.strip()
    )
    if not match:
        return None

    ts_str, freq, direction, mode, snr, dt, audio_freq, message = match.groups()

    if direction != "Rx" or mode != "FT8":
        return None

    # Parse timestamp (ALL.TXT is always UTC)
    try:
        ts = datetime.strptime(ts_str, "%y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    # Extract callsign and grid from message
    # Messages can be: "CQ CALL GRID", "CALL1 CALL2 GRID", "CALL1 CALL2 RPT", etc.
    parts = message.split()
    callsign = None
    grid = None

    # Look for a grid (4 or 6 char maidenhead)
    for part in parts:
        if re.match(r'^[A-R]{2}[0-9]{2}([A-X]{2})?$', part, re.I):
            grid = part.upper()

    # Find the transmitting callsign (usually first non-CQ, non-grid token that looks like a call)
    for part in parts:
        if part.upper() in ("CQ", "DE", "QRZ", "POTA", "SOTA"):
            continue
        if re.match(r'^[A-R]{2}[0-9]{2}', part, re.I):  # Skip grids
            continue
        if re.match(r'^[+-]?\d+$', part):  # Skip signal reports
            continue
        if re.match(r'^R[+-]?\d+$', part, re.I):  # Skip R+/- reports
            continue
        if part.upper() in ("RRR", "RR73", "73"):
            continue
        # Looks like a callsign
        if re.match(r'^[A-Z0-9]{1,3}[0-9][A-Z0-9]{0,4}(/[A-Z0-9]+)?$', part, re.I):
            callsign = part.upper()
            break

    if not callsign:
        return None

    return {
        "timestamp": ts,
        "freq_mhz": float(freq),
        "band": freq_to_band(float(freq)),
        "snr": int(snr),
        "callsign": callsign,
        "grid": grid,
        "message": message,
    }


# ============================================================
# API Functions (for web app and programmatic access)
# ============================================================

def get_antennas() -> dict:
    """Get all defined antennas."""
    return load_json(ANTENNAS_FILE)


def get_session_status() -> dict:
    """Get current session status for web UI.

    Returns dict with:
        active: bool - whether session is running
        paused: bool - whether session is paused
        start_time: str|None - ISO timestamp of session start
        current_antenna: str|None - label of current antenna
        current_antenna_since: str|None - when current antenna was selected
        events: list - full event log
        elapsed_seconds: int - seconds since session start
        antenna_elapsed_seconds: int - seconds on current antenna
    """
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    status = {
        "active": False,
        "paused": False,
        "start_time": None,
        "name": None,
        "notes": [],
        "current_antenna": None,
        "current_antenna_since": None,
        "current_antenna_description": None,
        "events": log,
        "elapsed_seconds": 0,
        "antenna_elapsed_seconds": 0,
        "solar": None,
    }

    for entry in log:
        event = entry.get("event")
        if event == "start":
            status["active"] = True
            status["paused"] = False
            status["start_time"] = entry.get("timestamp")
            status["solar"] = entry.get("solar")
            status["name"] = entry.get("name")
            status["current_antenna"] = None
        elif event == "note":
            status["notes"].append(entry.get("text", ""))
        elif event == "stop":
            status["active"] = False
            status["current_antenna"] = None
        elif event == "pause":
            status["paused"] = True
        elif event == "resume":
            status["paused"] = False
        elif event == "use":
            status["current_antenna"] = entry.get("antenna")
            status["current_antenna_since"] = entry.get("timestamp")
            status["current_antenna_description"] = entry.get("description")

    # Calculate elapsed times
    now = datetime.now(timezone.utc)
    if status["start_time"]:
        start = parse_timestamp(status["start_time"])
        status["elapsed_seconds"] = int((now - start).total_seconds())

    if status["current_antenna_since"]:
        ant_start = parse_timestamp(status["current_antenna_since"])
        status["antenna_elapsed_seconds"] = int((now - ant_start).total_seconds())

    return status


def get_session_intervals() -> list[dict]:
    """Build list of antenna intervals from session log.

    Returns list of dicts with:
        antenna: str
        start: datetime
        end: datetime
        band: str|None (if recorded)
    """
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        return []

    intervals = []
    session_start = None
    current_antenna = None
    current_start = None
    current_band = None

    for entry in log:
        event = entry.get("event")
        ts = parse_timestamp(entry["timestamp"]) if "timestamp" in entry else None

        if event == "start":
            session_start = ts
            current_antenna = None
        elif event == "stop":
            if current_antenna and current_start:
                intervals.append({
                    "antenna": current_antenna,
                    "start": current_start,
                    "end": ts,
                    "band": current_band,
                })
            current_antenna = None
            session_start = None
        elif event == "pause":
            if current_antenna and current_start:
                intervals.append({
                    "antenna": current_antenna,
                    "start": current_start,
                    "end": ts,
                    "band": current_band,
                })
            current_antenna = None
        elif event == "resume":
            pass  # Next 'use' will set the antenna
        elif event == "use":
            if current_antenna and current_start:
                intervals.append({
                    "antenna": current_antenna,
                    "start": current_start,
                    "end": ts,
                    "band": current_band,
                })
            current_antenna = entry.get("antenna")
            current_start = ts
            current_band = entry.get("band")

    # If session still active, add current interval to now
    if current_antenna and current_start and session_start:
        intervals.append({
            "antenna": current_antenna,
            "start": current_start,
            "end": datetime.now(timezone.utc),
            "band": current_band,
        })

    return intervals


def get_live_preview(grid: str = "CM98kq") -> dict:
    """Get live preview of data collected so far (fast, no PSKReporter).

    Returns dict with:
        intervals: list of intervals with station counts
        last_decodes: list of recent decodes
        total_stations: int
    """
    intervals = get_session_intervals()
    if not intervals:
        return {"intervals": [], "last_decodes": [], "total_stations": 0}

    # Parse ALL.TXT for the session timeframe
    session_start = min(i["start"] for i in intervals)

    # Read and parse ALL.TXT
    antenna_data = defaultdict(lambda: defaultdict(set))  # ant -> band -> set of calls
    last_decodes = []

    if ALL_TXT.exists():
        with open(ALL_TXT, 'r', errors='replace') as f:
            for line in f:
                parsed = parse_all_txt_line(line)
                if not parsed:
                    continue

                ts = parsed["timestamp"]
                if ts < session_start:
                    continue

                # Find which interval this belongs to
                for interval in intervals:
                    if interval["start"] <= ts < interval["end"]:
                        ant = interval["antenna"]
                        band = parsed["band"]
                        if parsed["callsign"]:
                            antenna_data[ant][band].add(parsed["callsign"])

                        # Track recent decodes
                        last_decodes.append({
                            "timestamp": ts.isoformat(),
                            "callsign": parsed["callsign"],
                            "snr": parsed["snr"],
                            "band": band,
                            "antenna": ant,
                        })
                        break

    # Keep only last 10 decodes
    last_decodes = last_decodes[-10:]
    last_decodes.reverse()  # Most recent first

    # Build summary
    interval_summary = []
    total_stations = 0
    for interval in intervals:
        ant = interval["antenna"]
        bands_data = {}
        for band, calls in antenna_data[ant].items():
            bands_data[band] = len(calls)
            total_stations += len(calls)

        interval_summary.append({
            "antenna": ant,
            "start": interval["start"].isoformat(),
            "end": interval["end"].isoformat(),
            "band": interval.get("band"),
            "stations_by_band": bands_data,
        })

    return {
        "intervals": interval_summary,
        "last_decodes": last_decodes,
        "total_stations": total_stations,
    }


def list_comparisons() -> list[dict]:
    """List all past comparison directories."""
    comparisons = []
    for d in sorted(DATA_DIR.glob("comparison_*"), reverse=True):
        if d.is_dir():
            session_file = d / "session.json"
            report_file = d / "report.txt"
            info = {
                "id": d.name,
                "path": str(d),
                "has_report": report_file.exists(),
            }
            if session_file.exists():
                session = json.loads(session_file.read_text())
                info["start_time"] = session.get("session_start")
                info["end_time"] = session.get("session_end")
                info["grid"] = session.get("grid")
                info["antennas"] = list(set(i.get("antenna") for i in session.get("intervals", [])))
            comparisons.append(info)
    return comparisons


def get_comparison(comparison_id: str) -> dict | None:
    """Get details of a specific comparison."""
    comp_dir = DATA_DIR / comparison_id
    if not comp_dir.is_dir():
        return None

    result = {"id": comparison_id, "path": str(comp_dir)}

    session_file = comp_dir / "session.json"
    if session_file.exists():
        result["session"] = json.loads(session_file.read_text())

    report_file = comp_dir / "report.txt"
    if report_file.exists():
        result["report"] = report_file.read_text()

    map_file = comp_dir / "map_data.json"
    if map_file.exists():
        result["map_data"] = json.loads(map_file.read_text())

    return result


# ============================================================
# CLI Command Functions
# ============================================================

def cmd_define(label: str, description: str):
    """Define or update an antenna."""
    antennas = load_json(ANTENNAS_FILE)
    is_update = label in antennas
    antennas[label] = {
        "description": description,
        "created": antennas.get(label, {}).get("created", datetime.now(timezone.utc).isoformat()),
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    save_json(ANTENNAS_FILE, antennas)
    action = "Updated" if is_update else "Defined"
    print(f"{action} antenna '{label}': {description}")


def cmd_list():
    """List defined antennas."""
    antennas = load_json(ANTENNAS_FILE)
    if not antennas:
        print("No antennas defined. Use: antenna.py define <label> <description>")
        return

    print("Defined antennas:")
    for label, info in antennas.items():
        print(f"  {label}: {info['description']}")


def cmd_start(name: str = None):
    """Start a new comparison session with optional name."""
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    # Check if session already active
    for entry in log:
        if entry.get("event") == "start":
            has_stop = any(e.get("event") == "stop" and e["timestamp"] > entry["timestamp"] for e in log)
            if not has_stop:
                print(f"Session already active since {entry['timestamp']}")
                print("Use 'antenna.py stop' to end it first, or 'antenna.py clear' to reset")
                sys.exit(1)

    # Capture solar conditions at start
    solar = fetch_solar_data()
    solar_summary = None
    if solar:
        solar_summary = {
            "sfi": solar.get("solarflux"),
            "k": solar.get("kindex"),
            "a": solar.get("aindex"),
            "geomagfield": solar.get("geomagfield"),
        }

    entry = {
        "event": "start",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "solar": solar_summary,
    }
    if name:
        entry["name"] = name
    log.append(entry)
    save_json(ANTENNA_LOG_FILE, log)
    print(f"[{entry['timestamp']}] Session started")
    if name:
        print(f"  Name: {name}")
    if solar_summary:
        print(f"  Solar: SFI={solar_summary['sfi']}, K={solar_summary['k']}, A={solar_summary['a']}, {solar_summary['geomagfield']}")
    print("Now use 'antenna.py use <label>' to mark antenna switches")


def cmd_stop():
    """Stop the current comparison session."""
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    # Check if session is active
    session_active = False
    for entry in log:
        if entry.get("event") == "start":
            session_active = True
        elif entry.get("event") == "stop":
            session_active = False

    if not session_active:
        print("No active session to stop")
        sys.exit(1)

    entry = {
        "event": "stop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    save_json(ANTENNA_LOG_FILE, log)
    print(f"[{entry['timestamp']}] Session stopped")
    print("Use 'antenna.py analyze' to see results")


def cmd_clear():
    """Clear the session log."""
    save_json(ANTENNA_LOG_FILE, [])
    print("Session log cleared")


def cmd_note(text: str, comparison_id: str = None):
    """Add a note to the current session or a past comparison.

    If comparison_id is provided, adds note to that comparison's session.json.
    Otherwise adds to the current session log.
    """
    if comparison_id:
        # Add note to past comparison
        comp_dir = DATA_DIR / comparison_id
        session_file = comp_dir / "session.json"

        if not session_file.exists():
            print(f"Comparison '{comparison_id}' not found")
            sys.exit(1)

        session = json.loads(session_file.read_text())
        if "notes" not in session:
            session["notes"] = []
        session["notes"].append({
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        session_file.write_text(json.dumps(session, indent=2))
        print(f"Note added to {comparison_id}")
    else:
        # Add note to current session
        log = load_json(ANTENNA_LOG_FILE)
        if not isinstance(log, list):
            log = []

        entry = {
            "event": "note",
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        log.append(entry)
        save_json(ANTENNA_LOG_FILE, log)
        print(f"[{entry['timestamp']}] Note added: {text}")


def switch_band(band: str) -> bool:
    """Switch WSJT-X to a band configuration. Returns True on success."""
    try:
        # Import here to avoid circular dependency
        from wsjtx_control import WSJTXController
        ctrl = WSJTXController()
        print(f"Switching WSJT-X to {band}...")
        ctrl.switch_configuration(band)
        ctrl.close()
        print(f"Band switched to {band}")
        return True
    except Exception as e:
        print(f"Warning: Could not switch band: {e}")
        return False


def cmd_use(label: str, band: str = None):
    """Mark that we're now using a specific antenna, optionally switch band."""
    antennas = load_json(ANTENNAS_FILE)
    if label not in antennas:
        print(f"Unknown antenna '{label}'. Defined antennas: {', '.join(antennas.keys())}")
        sys.exit(1)

    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    # Check if session is active and not paused
    session_active = False
    session_paused = False
    for entry in log:
        if entry.get("event") == "start":
            session_active = True
            session_paused = False
        elif entry.get("event") == "stop":
            session_active = False
        elif entry.get("event") == "pause":
            session_paused = True
        elif entry.get("event") == "resume":
            session_paused = False

    if not session_active:
        print("No active session. Use 'antenna.py start' first")
        sys.exit(1)

    # Switch band first if specified
    if band:
        switch_band(band)

    entry = {
        "event": "use",
        "antenna": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": antennas[label]["description"],
    }
    if band:
        entry["band"] = band
    log.append(entry)
    save_json(ANTENNA_LOG_FILE, log)

    if session_paused:
        print(f"[{entry['timestamp']}] Antenna set to '{label}' (session paused)")
        print("Use 'antenna.py resume' to start recording data")
    else:
        print(f"[{entry['timestamp']}] Now using antenna '{label}': {antennas[label]['description']}")


def cmd_pause():
    """Pause the current session (data received while paused is ignored)."""
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    # Check session state
    session_active = False
    session_paused = False
    for entry in log:
        if entry.get("event") == "start":
            session_active = True
            session_paused = False
        elif entry.get("event") == "stop":
            session_active = False
        elif entry.get("event") == "pause":
            session_paused = True
        elif entry.get("event") == "resume":
            session_paused = False

    if not session_active:
        print("No active session to pause")
        sys.exit(1)

    if session_paused:
        print("Session already paused")
        sys.exit(1)

    entry = {
        "event": "pause",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    save_json(ANTENNA_LOG_FILE, log)
    print(f"[{entry['timestamp']}] Session paused - data will be ignored until resume")
    print("Use 'antenna.py resume' when ready to continue")


def cmd_resume():
    """Resume a paused session."""
    log = load_json(ANTENNA_LOG_FILE)
    if not isinstance(log, list):
        log = []

    # Check session state
    session_active = False
    session_paused = False
    for entry in log:
        if entry.get("event") == "start":
            session_active = True
            session_paused = False
        elif entry.get("event") == "stop":
            session_active = False
        elif entry.get("event") == "pause":
            session_paused = True
        elif entry.get("event") == "resume":
            session_paused = False

    if not session_active:
        print("No active session to resume")
        sys.exit(1)

    if not session_paused:
        print("Session is not paused")
        sys.exit(1)

    entry = {
        "event": "resume",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.append(entry)
    save_json(ANTENNA_LOG_FILE, log)
    print(f"[{entry['timestamp']}] Session resumed")
    print("Use 'antenna.py use <label>' to mark which antenna you're using")


def cmd_log():
    """Show antenna usage log."""
    log = load_json(ANTENNA_LOG_FILE)
    if not log:
        print("No antenna usage logged. Use: antenna.py use <label>")
        return

    print("Antenna usage log:")
    for entry in log:
        print(f"  {entry['timestamp']}: {entry['antenna']} - {entry['description']}")


def cmd_analyze(my_grid: str = "CM98kq"):
    """Analyze antenna performance from ALL.TXT."""
    log = load_json(ANTENNA_LOG_FILE)
    if not log:
        print("No session data. Use 'antenna.py start' to begin a session.")
        return

    # Find session boundaries and build intervals
    intervals = []
    session_start = None
    session_end = None
    current_antenna = None
    current_start = None
    current_desc = None
    current_band = None
    paused = False

    for entry in log:
        event = entry.get("event", "use")  # backward compat

        if event == "start":
            session_start = parse_timestamp(entry["timestamp"])
            current_antenna = None
            current_band = None
            paused = False
        elif event == "stop":
            # Close out current antenna interval
            if current_antenna and current_start and not paused:
                intervals.append({
                    "antenna": current_antenna,
                    "description": current_desc,
                    "band": current_band,
                    "start": current_start,
                    "end": parse_timestamp(entry["timestamp"]),
                })
            session_end = parse_timestamp(entry["timestamp"])
            current_antenna = None
        elif event == "pause":
            # Close out current antenna interval at pause time
            if current_antenna and current_start:
                intervals.append({
                    "antenna": current_antenna,
                    "description": current_desc,
                    "band": current_band,
                    "start": current_start,
                    "end": parse_timestamp(entry["timestamp"]),
                })
            paused = True
            current_antenna = None
            current_start = None
        elif event == "resume":
            paused = False
            # Antenna must be set again after resume
        elif event == "use":
            if session_start is None:
                # Legacy log without explicit start
                session_start = parse_timestamp(entry["timestamp"])

            # Close previous antenna interval (if not paused)
            if current_antenna and current_start:
                intervals.append({
                    "antenna": current_antenna,
                    "description": current_desc,
                    "band": current_band,
                    "start": current_start,
                    "end": parse_timestamp(entry["timestamp"]),
                })

            current_antenna = entry.get("antenna")
            current_start = parse_timestamp(entry["timestamp"])
            current_desc = entry.get("description", "")
            current_band = entry.get("band")

    # Handle still-active session
    if current_antenna and current_start and session_end is None and not paused:
        intervals.append({
            "antenna": current_antenna,
            "description": current_desc,
            "band": current_band,
            "start": current_start,
            "end": datetime.now(timezone.utc),
        })

    if len(intervals) < 2:
        print("Need at least 2 antenna intervals to compare.")
        print("Use: antenna.py start, then antenna.py use <A>, then antenna.py use <B>")
        return

    # Show session info
    print(f"Session: {session_start} to {session_end or 'now'}")

    # Show solar conditions if captured
    for entry in log:
        if entry.get("event") == "start" and entry.get("solar"):
            s = entry["solar"]
            print(f"Solar conditions: SFI={s.get('sfi')}, K={s.get('k')}, A={s.get('a')}, {s.get('geomagfield')}")
            break

    print(f"Intervals: {len(intervals)}")
    for iv in intervals:
        print(f"  {iv['antenna']}: {iv['start'].strftime('%H:%M:%S')} - {iv['end'].strftime('%H:%M:%S')} ({iv['description']})")
    print()

    print(f"Analyzing {len(intervals)} antenna intervals...")
    print()

    # Parse ALL.TXT
    if not ALL_TXT.exists():
        print(f"ALL.TXT not found at {ALL_TXT}")
        return

    # Get my location for bearing calculation
    my_loc = grid_to_latlon(my_grid)
    if not my_loc:
        print(f"Invalid grid: {my_grid}")
        return

    my_lat, my_lon = my_loc
    print(f"My grid: {my_grid} ({my_lat:.2f}, {my_lon:.2f})")
    print()

    # Create artifact directory
    artifact_dir = DATA_DIR / f"comparison_{session_start.strftime('%Y%m%d_%H%M%S')}"
    artifact_dir.mkdir(exist_ok=True)

    # Copy README template if it exists
    readme_template = DATA_DIR / "comparison_README.md"
    if readme_template.exists():
        (artifact_dir / "README.md").write_text(readme_template.read_text())

    # Save session metadata
    solar_data = None
    for entry in log:
        if entry.get("event") == "start" and entry.get("solar"):
            solar_data = entry["solar"]
            break

    session_meta = {
        "session_start": session_start.isoformat(),
        "session_end": (session_end or datetime.now(timezone.utc)).isoformat(),
        "my_grid": my_grid,
        "my_lat": my_lat,
        "my_lon": my_lon,
        "solar": solar_data,
        "intervals": [
            {
                "antenna": iv["antenna"],
                "description": iv["description"],
                "band": iv.get("band"),
                "start": iv["start"].isoformat(),
                "end": iv["end"].isoformat(),
            }
            for iv in intervals
        ],
    }
    save_json(artifact_dir / "session.json", session_meta)

    # Collect data per antenna
    # Structure: antenna -> band -> callsign -> list of SNRs
    antenna_data: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    # Also track bearings
    callsign_grids: dict[str, str] = {}

    # Store raw RX lines per antenna/band for artifact export
    rx_raw_lines: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    with open(ALL_TXT, 'r', errors='replace') as f:
        for line in f:
            parsed = parse_all_txt_line(line)
            if not parsed:
                continue

            ts = parsed["timestamp"]

            # Find which antenna interval this belongs to
            antenna = None
            for interval in intervals:
                if interval["start"] <= ts < interval["end"]:
                    antenna = interval["antenna"]
                    break

            if not antenna:
                continue

            band = parsed["band"]
            call = parsed["callsign"]
            snr = parsed["snr"]

            antenna_data[antenna][band][call].append(snr)
            rx_raw_lines[antenna][band].append(line.rstrip())

            if parsed["grid"] and call not in callsign_grids:
                callsign_grids[call] = parsed["grid"]

    # Save RX artifacts per band/antenna
    all_bands_for_artifacts = set()
    for ant_data in antenna_data.values():
        all_bands_for_artifacts.update(ant_data.keys())

    for band in all_bands_for_artifacts:
        band_dir = artifact_dir / band
        band_dir.mkdir(exist_ok=True)
        for antenna in rx_raw_lines:
            if rx_raw_lines[antenna][band]:
                rx_file = band_dir / f"{antenna}_all.txt"
                rx_file.write_text("\n".join(rx_raw_lines[antenna][band]) + "\n")

    # Find common callsigns between antennas for comparison
    all_antennas = list(antenna_data.keys())
    if len(all_antennas) < 2:
        print("Not enough data from different antennas to compare.")
        return

    # Collect report lines for artifact
    report_lines = []

    def report(line: str = ""):
        print(line)
        report_lines.append(line)

    # Track scores for summary: {antenna: {band: {'rx_delta': float, 'tx_reach': int, 'tx_delta': float}}}
    summary_scores = defaultdict(lambda: defaultdict(dict))

    report("=" * 60)
    report("COMPARISON BY BAND (Priority 1)")
    report("=" * 60)

    all_bands = set()
    for ant_data in antenna_data.values():
        all_bands.update(ant_data.keys())

    for band in sorted(all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
        report(f"\n{band}:")

        # Find calls heard by multiple antennas on this band
        calls_by_antenna = {}
        for ant in all_antennas:
            calls_by_antenna[ant] = set(antenna_data[ant][band].keys())

        # Common calls across all antennas
        common_calls = set.intersection(*calls_by_antenna.values()) if calls_by_antenna else set()

        if not common_calls:
            report("  No common callsigns to compare")
            continue

        # Calculate average SNR per antenna for common calls
        report(f"  Common stations: {len(common_calls)}")

        ant_avg = {}
        for ant in all_antennas:
            snrs = []
            for call in common_calls:
                snrs.extend(antenna_data[ant][band][call])
            if snrs:
                ant_avg[ant] = sum(snrs) / len(snrs)

        # Display comparison
        baseline_ant = all_antennas[0]
        baseline = ant_avg.get(baseline_ant, 0)

        for ant in all_antennas:
            avg = ant_avg.get(ant, 0)
            delta = avg - baseline
            delta_str = f"{delta:+.1f} dB" if ant != baseline_ant else "(baseline)"
            report(f"    {ant}: avg SNR {avg:.1f} dB {delta_str}")
            # Record for summary
            summary_scores[ant][band]['rx_delta'] = delta
            summary_scores[ant][band]['rx_common'] = len(common_calls)

        # Calculate distance stats per antenna (all stations, not just common)
        ant_distances = {}
        for ant in all_antennas:
            distances = []
            for call in antenna_data[ant][band]:
                if call in callsign_grids:
                    loc = grid_to_latlon(callsign_grids[call])
                    if loc:
                        dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                        distances.append(dist)
            if distances:
                ant_distances[ant] = {
                    'avg': sum(distances) / len(distances),
                    'max': max(distances),
                    'count': len(distances),
                }

        if ant_distances:
            report("  Distance (all stations with grids):")
            baseline_dist = ant_distances.get(baseline_ant, {}).get('avg', 0)
            for ant in all_antennas:
                if ant in ant_distances:
                    d = ant_distances[ant]
                    delta_km = d['avg'] - baseline_dist
                    delta_str = f"{delta_km:+.0f} km" if ant != baseline_ant else "(baseline)"
                    report(f"    {ant}: avg {d['avg']:.0f} km, max {d['max']:.0f} km ({d['count']} stns) {delta_str}")
                    summary_scores[ant][band]['rx_avg_dist'] = d['avg']
                    summary_scores[ant][band]['rx_max_dist'] = d['max']

    report()
    report("=" * 60)
    report("COMPARISON BY BEARING + BAND (Priority 2)")
    report("=" * 60)

    # Group by bearing sectors (45-degree sectors: N, NE, E, SE, S, SW, W, NW)
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def bearing_to_sector(bearing: float) -> str:
        idx = round(bearing / 45) % 8
        return sectors[idx]

    for band in sorted(all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
        # Find calls with known grids
        calls_with_bearing = {}
        for ant in all_antennas:
            for call in antenna_data[ant][band]:
                if call in callsign_grids and call not in calls_with_bearing:
                    loc = grid_to_latlon(callsign_grids[call])
                    if loc:
                        bearing = calc_bearing(my_lat, my_lon, loc[0], loc[1])
                        calls_with_bearing[call] = (bearing, bearing_to_sector(bearing))

        if not calls_with_bearing:
            continue

        report(f"\n{band}:")

        # Analyze by sector - show ALL stations per antenna, not just common
        for sector in sectors:
            sector_calls = [c for c, (b, s) in calls_with_bearing.items() if s == sector]

            if not sector_calls:
                continue

            # Gather stats per antenna for this sector (SNR and distance)
            ant_stats = {}
            for ant in all_antennas:
                snrs = []
                distances = []
                count = 0
                for call in sector_calls:
                    if call in antenna_data[ant][band]:
                        snrs.extend(antenna_data[ant][band][call])
                        count += 1
                        # Calculate distance for this station
                        if call in callsign_grids:
                            loc = grid_to_latlon(callsign_grids[call])
                            if loc:
                                dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                                distances.append(dist)
                if snrs:
                    ant_stats[ant] = {
                        'avg': sum(snrs) / len(snrs),
                        'count': count,
                        'avg_dist': sum(distances) / len(distances) if distances else 0,
                        'max_dist': max(distances) if distances else 0,
                    }

            if not ant_stats:
                continue

            # Find who heard more stations in this direction
            counts = [(ant, s['count']) for ant, s in ant_stats.items()]
            max_count = max(c for _, c in counts)

            report(f"  {sector}:")
            baseline_ant = all_antennas[0]
            baseline_avg = ant_stats.get(baseline_ant, {}).get('avg', 0)

            for ant in all_antennas:
                if ant in ant_stats:
                    s = ant_stats[ant]
                    delta = s['avg'] - baseline_avg
                    delta_str = f"{delta:+.1f} dB" if ant != baseline_ant else "(baseline)"
                    winner_mark = " *" if s['count'] == max_count and len([c for _, c in counts if c == max_count]) == 1 else ""
                    dist_str = f", avg {s['avg_dist']:.0f} km, max {s['max_dist']:.0f} km" if s['max_dist'] > 0 else ""
                    report(f"      {ant}: {s['count']} stns, avg {s['avg']:.1f} dB{dist_str} {delta_str}{winner_mark}")
                else:
                    report(f"      {ant}: 0 stns")

    # TX Analysis from PSKReporter
    report()
    report("=" * 60)
    report("TX ANALYSIS (PSKReporter - who heard you)")
    report("=" * 60)

    # Initialize TX data structures (will be populated if PSKReporter data is available)
    tx_antenna_data: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    tx_callsign_grids: dict[str, str] = {}

    # Check if we have cached PSKReporter data or if session is within 24-hour window
    psk_cache_file = artifact_dir / "pskreporter_cache.json"
    now = datetime.now(timezone.utc)
    session_too_old = session_start and (now - session_start).total_seconds() > 86400

    if session_too_old and not psk_cache_file.exists():
        report("\nSession older than 24 hours - PSKReporter data unavailable")
    else:
        # Collect TX spots per antenna interval
        tx_raw_spots: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        total_spots = 0

        # Fetch ALL spots in one query, then assign to intervals
        # Check for cached PSKReporter data first
        if psk_cache_file.exists():
            print("Loading cached PSKReporter data...")
            cached = json.loads(psk_cache_file.read_text())
            all_spots = []
            for spot in cached:
                spot['timestamp'] = parse_timestamp(spot['timestamp'])
                all_spots.append(spot)
        elif not session_too_old:
            print(f"\nFetching PSKReporter spots for {MY_CALLSIGN}...")  # Progress only, not in report
            all_spots = fetch_pskreporter_spots(MY_CALLSIGN, session_start)
            # Cache the results if we got any
            if all_spots:
                cache_data = [
                    {**spot, 'timestamp': spot['timestamp'].isoformat()}
                    for spot in all_spots
                ]
                save_json(psk_cache_file, cache_data)
                print(f"Cached {len(all_spots)} PSKReporter spots")
        else:
            all_spots = []  # Shouldn't get here, but safe default

        for spot in all_spots:
            # Skip bad data (PSKReporter sometimes returns freq_mhz=0)
            if spot['freq_mhz'] <= 0:
                continue

            # Find which antenna interval this spot belongs to
            spot_ts = spot['timestamp']
            ant = None
            for interval in intervals:
                if interval["start"] <= spot_ts < interval["end"]:
                    ant = interval["antenna"]
                    break

            if not ant:
                continue  # Spot outside our test intervals

            band = spot['band']
            # Store raw spot for artifact (include all spots, even without SNR)
            tx_raw_spots[ant][band].append({
                "receiver_call": spot['receiver_call'],
                "receiver_grid": spot['receiver_grid'],
                "freq_mhz": spot['freq_mhz'],
                "snr": spot['snr'],
                "timestamp": spot['timestamp'].isoformat(),
            })
            if spot['snr'] is not None:
                call = spot['receiver_call']
                tx_antenna_data[ant][band][call].append(spot['snr'])
                if spot['receiver_grid']:
                    tx_callsign_grids[call] = spot['receiver_grid']
                total_spots += 1

        # Save TX artifacts per band/antenna
        for antenna in tx_raw_spots:
            for band in tx_raw_spots[antenna]:
                if tx_raw_spots[antenna][band]:
                    band_dir = artifact_dir / band
                    band_dir.mkdir(exist_ok=True)
                    tx_file = band_dir / f"{antenna}_pskreporter.json"
                    save_json(tx_file, tx_raw_spots[antenna][band])

        if total_spots == 0:
            report("\nNo TX spots found in PSKReporter for this session")
            report("(You may not have transmitted, or spots haven't been uploaded yet)")
        else:
            report(f"\nFound {total_spots} TX spots")
            report()

            # Use same antenna order as RX analysis for consistent baseline
            tx_all_antennas = [a for a in all_antennas if a in tx_antenna_data]
            tx_all_bands = set()
            for ant_data in tx_antenna_data.values():
                tx_all_bands.update(ant_data.keys())

            report("-" * 40)
            report("TX BY BAND")
            report("-" * 40)

            for band in sorted(tx_all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
                calls_by_antenna = {ant: set(tx_antenna_data[ant][band].keys()) for ant in tx_all_antennas}
                common_calls = set.intersection(*calls_by_antenna.values()) if all(calls_by_antenna.values()) else set()

                # Gather stats for each antenna
                ant_stats = {}
                for ant in tx_all_antennas:
                    if tx_antenna_data[ant][band]:
                        all_snrs = []
                        for call in tx_antenna_data[ant][band]:
                            all_snrs.extend(tx_antenna_data[ant][band][call])
                        if all_snrs:
                            ant_stats[ant] = {
                                'avg': sum(all_snrs) / len(all_snrs),
                                'max': max(all_snrs),
                                'min': min(all_snrs),
                                'count': len(tx_antenna_data[ant][band]),  # unique stations
                                'spots': len(all_snrs),  # total spots
                            }

                if not ant_stats:
                    continue

                if common_calls:
                    report(f"\n{band}: ({len(common_calls)} common stations)")
                    # Calculate common-station averages for comparison
                    common_avg = {}
                    for ant in tx_all_antennas:
                        snrs = []
                        for call in common_calls:
                            snrs.extend(tx_antenna_data[ant][band][call])
                        if snrs:
                            common_avg[ant] = sum(snrs) / len(snrs)

                    baseline_ant = tx_all_antennas[0]
                    baseline = common_avg.get(baseline_ant, 0)

                    for ant in tx_all_antennas:
                        if ant in ant_stats:
                            s = ant_stats[ant]
                            avg = common_avg.get(ant, 0)
                            delta = avg - baseline
                            delta_str = f"{delta:+.1f} dB" if ant != baseline_ant else "(baseline)"
                            report(f"    {ant}: avg {avg:.1f} dB {delta_str} | reach: {s['count']} stns, range [{s['min']:+d} to {s['max']:+d}]")
                            # Record for summary
                            summary_scores[ant][band]['tx_delta'] = delta
                            summary_scores[ant][band]['tx_reach'] = s['count']
                else:
                    report(f"\n{band}:")
                    # No common stations - compare reach and signal strength distribution
                    baseline_ant = tx_all_antennas[0]
                    baseline_count = ant_stats.get(baseline_ant, {}).get('count', 0)

                    for ant in tx_all_antennas:
                        if ant in ant_stats:
                            s = ant_stats[ant]
                            reach_delta = s['count'] - baseline_count
                            reach_str = f"{reach_delta:+d}" if ant != baseline_ant else "(baseline)"
                            report(f"    {ant}: reach {s['count']} stns {reach_str} | avg {s['avg']:.1f} dB, range [{s['min']:+d} to {s['max']:+d}]")
                            # Record for summary (use reach delta as proxy when no common stations)
                            summary_scores[ant][band]['tx_reach'] = s['count']
                            summary_scores[ant][band]['tx_reach_delta'] = reach_delta

                # TX distance stats per antenna
                tx_ant_distances = {}
                for ant in tx_all_antennas:
                    distances = []
                    for call in tx_antenna_data[ant][band]:
                        if call in tx_callsign_grids:
                            loc = grid_to_latlon(tx_callsign_grids[call])
                            if loc:
                                dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                                distances.append(dist)
                    if distances:
                        tx_ant_distances[ant] = {
                            'avg': sum(distances) / len(distances),
                            'max': max(distances),
                            'count': len(distances),
                        }

                if tx_ant_distances:
                    report("  Distance (all receivers with grids):")
                    baseline_dist = tx_ant_distances.get(tx_all_antennas[0], {}).get('avg', 0)
                    for ant in tx_all_antennas:
                        if ant in tx_ant_distances:
                            d = tx_ant_distances[ant]
                            delta_km = d['avg'] - baseline_dist
                            delta_str = f"{delta_km:+.0f} km" if ant != tx_all_antennas[0] else "(baseline)"
                            report(f"    {ant}: avg {d['avg']:.0f} km, max {d['max']:.0f} km ({d['count']} stns) {delta_str}")
                            summary_scores[ant][band]['tx_avg_dist'] = d['avg']
                            summary_scores[ant][band]['tx_max_dist'] = d['max']

            # TX by bearing
            report()
            report("-" * 40)
            report("TX BY BEARING + BAND")
            report("-" * 40)

            for band in sorted(tx_all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
                calls_with_bearing = {}
                for ant in tx_all_antennas:
                    for call in tx_antenna_data[ant][band]:
                        if call in tx_callsign_grids and call not in calls_with_bearing:
                            loc = grid_to_latlon(tx_callsign_grids[call])
                            if loc:
                                bearing = calc_bearing(my_lat, my_lon, loc[0], loc[1])
                                calls_with_bearing[call] = (bearing, bearing_to_sector(bearing))

                if not calls_with_bearing:
                    continue

                band_has_data = False
                for sector in sectors:
                    sector_calls = [c for c, (b, s) in calls_with_bearing.items() if s == sector]

                    if not sector_calls:
                        continue

                    # Gather stats per antenna for this sector (SNR and distance)
                    ant_stats = {}
                    for ant in tx_all_antennas:
                        snrs = []
                        distances = []
                        count = 0
                        for call in sector_calls:
                            if call in tx_antenna_data[ant][band]:
                                snrs.extend(tx_antenna_data[ant][band][call])
                                count += 1
                                if call in tx_callsign_grids:
                                    loc = grid_to_latlon(tx_callsign_grids[call])
                                    if loc:
                                        dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                                        distances.append(dist)
                        if snrs:
                            ant_stats[ant] = {
                                'avg': sum(snrs) / len(snrs),
                                'count': count,
                                'avg_dist': sum(distances) / len(distances) if distances else 0,
                                'max_dist': max(distances) if distances else 0,
                            }

                    if not ant_stats:
                        continue

                    if not band_has_data:
                        report(f"\n{band}:")
                        band_has_data = True

                    # Find who reached more stations in this direction
                    counts = [(ant, s['count']) for ant, s in ant_stats.items()]
                    max_count = max(c for _, c in counts)

                    report(f"  {sector}:")
                    baseline_ant = tx_all_antennas[0]
                    baseline_avg = ant_stats.get(baseline_ant, {}).get('avg', 0)

                    for ant in tx_all_antennas:
                        if ant in ant_stats:
                            s = ant_stats[ant]
                            delta = s['avg'] - baseline_avg
                            delta_str = f"{delta:+.1f} dB" if ant != baseline_ant else "(baseline)"
                            winner_mark = " *" if s['count'] == max_count and len([c for _, c in counts if c == max_count]) == 1 else ""
                            dist_str = f", avg {s['avg_dist']:.0f} km, max {s['max_dist']:.0f} km" if s['max_dist'] > 0 else ""
                            report(f"      {ant}: {s['count']} stns, avg {s['avg']:.1f} dB{dist_str} {delta_str}{winner_mark}")
                        else:
                            report(f"      {ant}: 0 stns")

    # Generate summary/recommendation
    report()
    report("=" * 60)
    report("SUMMARY")
    report("=" * 60)

    # Collect all bands that have data
    summary_bands = set()
    for ant in summary_scores:
        summary_bands.update(summary_scores[ant].keys())

    if summary_bands:
        baseline_ant = all_antennas[0]
        other_ants = [a for a in all_antennas if a != baseline_ant]

        report(f"\nBaseline antenna: {baseline_ant}")
        report()

        for band in sorted(summary_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
            report(f"{band}:")
            band_verdicts = []

            for ant in other_ants:
                scores = summary_scores[ant].get(band, {})
                baseline_scores = summary_scores[baseline_ant].get(band, {})

                rx_delta = scores.get('rx_delta', 0)
                rx_common = scores.get('rx_common', 0)
                tx_delta = scores.get('tx_delta')  # May be None if no common stations
                tx_reach = scores.get('tx_reach', 0)
                tx_reach_delta = scores.get('tx_reach_delta', 0)
                baseline_tx_reach = baseline_scores.get('tx_reach', 0)

                # Build verdict
                parts = []

                # RX verdict
                if rx_common > 0:
                    if rx_delta > 1:
                        parts.append(f"RX: {ant} +{rx_delta:.1f}dB better")
                    elif rx_delta < -1:
                        parts.append(f"RX: {baseline_ant} {-rx_delta:.1f}dB better")
                    else:
                        parts.append("RX: similar")

                # TX verdict
                if tx_delta is not None:
                    if tx_delta > 1:
                        parts.append(f"TX: {ant} +{tx_delta:.1f}dB better")
                    elif tx_delta < -1:
                        parts.append(f"TX: {baseline_ant} {-tx_delta:.1f}dB better")
                    else:
                        parts.append("TX: similar")
                elif tx_reach > 0 or baseline_tx_reach > 0:
                    # No common stations, use reach (proportional threshold: 20% difference)
                    max_reach = max(tx_reach, baseline_tx_reach, 1)
                    pct_diff = abs(tx_reach_delta) / max_reach
                    if tx_reach_delta > 0 and pct_diff > 0.2:
                        parts.append(f"TX reach: {ant} +{tx_reach_delta} stns ({tx_reach} vs {baseline_tx_reach})")
                    elif tx_reach_delta < 0 and pct_diff > 0.2:
                        parts.append(f"TX reach: {baseline_ant} +{-tx_reach_delta} stns ({baseline_tx_reach} vs {tx_reach})")
                    else:
                        parts.append(f"TX reach: similar ({tx_reach} vs {baseline_tx_reach})")

                if parts:
                    report(f"  {ant} vs {baseline_ant}: {' | '.join(parts)}")
                else:
                    report(f"  {ant} vs {baseline_ant}: insufficient data")

        # Overall recommendation
        report()
        report("-" * 40)
        report("RECOMMENDATION:")

        # Count wins per antenna across all bands
        wins = defaultdict(lambda: {'rx': 0, 'tx': 0})
        for band in summary_bands:
            for ant in other_ants:
                scores = summary_scores[ant].get(band, {})
                baseline_scores = summary_scores[baseline_ant].get(band, {})

                rx_delta = scores.get('rx_delta', 0)
                if rx_delta > 1:
                    wins[ant]['rx'] += 1
                elif rx_delta < -1:
                    wins[baseline_ant]['rx'] += 1

                tx_delta = scores.get('tx_delta')
                if tx_delta is not None:
                    if tx_delta > 1:
                        wins[ant]['tx'] += 1
                    elif tx_delta < -1:
                        wins[baseline_ant]['tx'] += 1
                else:
                    # Use reach (proportional threshold: 20% difference)
                    tx_reach = scores.get('tx_reach', 0)
                    baseline_tx_reach = baseline_scores.get('tx_reach', 0)
                    tx_reach_delta = scores.get('tx_reach_delta', 0)
                    max_reach = max(tx_reach, baseline_tx_reach, 1)
                    pct_diff = abs(tx_reach_delta) / max_reach
                    if tx_reach_delta > 0 and pct_diff > 0.2:
                        wins[ant]['tx'] += 1
                    elif tx_reach_delta < 0 and pct_diff > 0.2:
                        wins[baseline_ant]['tx'] += 1

        for ant in all_antennas:
            w = wins[ant]
            report(f"  {ant}: {w['rx']} RX wins, {w['tx']} TX wins")

        # Simple recommendation
        total_wins = {ant: wins[ant]['rx'] + wins[ant]['tx'] for ant in all_antennas}
        best_ant = max(total_wins, key=total_wins.get)
        if total_wins[best_ant] > 0:
            report()
            report(f"  --> {best_ant} appears to be the better overall performer")
        else:
            report()
            report("  --> Results too close to call; consider more testing")

    # Save report to artifact directory
    report_file = artifact_dir / "report.txt"
    report_file.write_text("\n".join(report_lines) + "\n")

    # Generate map data for azimuthal visualization
    map_data = {
        "qth": {"grid": my_grid, "lat": my_lat, "lon": my_lon},
        "antennas": all_antennas,
        "rx_stations": [],
        "tx_stations": [],
    }

    # Collect RX station data
    for ant in all_antennas:
        for band in antenna_data[ant]:
            for call, snrs in antenna_data[ant][band].items():
                if call in callsign_grids:
                    loc = grid_to_latlon(callsign_grids[call])
                    if loc:
                        bearing = calc_bearing(my_lat, my_lon, loc[0], loc[1])
                        dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                        avg_snr = sum(snrs) / len(snrs)
                        map_data["rx_stations"].append({
                            "call": call,
                            "grid": callsign_grids[call],
                            "antenna": ant,
                            "band": band,
                            "bearing": round(bearing, 1),
                            "distance_km": round(dist),
                            "snr": round(avg_snr, 1),
                        })

    # Collect TX station data if available
    if tx_antenna_data:
        for ant in tx_antenna_data:
            for band in tx_antenna_data[ant]:
                for call, snrs in tx_antenna_data[ant][band].items():
                    if call in tx_callsign_grids:
                        loc = grid_to_latlon(tx_callsign_grids[call])
                        if loc:
                            bearing = calc_bearing(my_lat, my_lon, loc[0], loc[1])
                            dist = calc_distance_km(my_lat, my_lon, loc[0], loc[1])
                            avg_snr = sum(snrs) / len(snrs)
                            map_data["tx_stations"].append({
                                "call": call,
                                "grid": tx_callsign_grids[call],
                                "antenna": ant,
                                "band": band,
                                "bearing": round(bearing, 1),
                                "distance_km": round(dist),
                                "snr": round(avg_snr, 1),
                            })

    map_file = artifact_dir / "map_data.json"
    map_file.write_text(json.dumps(map_data, indent=2))

    # Print artifact location
    print()
    print("=" * 60)
    print(f"Raw data saved to: {artifact_dir}")
    print("=" * 60)


def fetch_pskreporter_spots(callsign: str, start_time: datetime, end_time: datetime | None = None) -> list[dict]:
    """Fetch TX spots from PSKReporter for a time window.

    Returns list of dicts with: receiver_call, receiver_grid, freq_mhz, band, snr, timestamp
    If end_time is None, fetches all spots from start_time to now.
    """
    # Use library function
    spots = fetch_spots(callsign, start_time, end_time, mode="FT8")

    # Filter by end_time if specified (library doesn't support this yet)
    if end_time:
        spots = [s for s in spots if s['timestamp'] <= end_time]

    return spots


def cmd_solar():
    """Display current solar/propagation conditions."""
    data = fetch_solar_data()
    if not data:
        print("Could not fetch solar data")
        return

    print("Current Solar/Propagation Conditions")
    print(f"  Updated: {data.get('updated', 'N/A')}")
    print(f"  Source:  {data.get('source', 'N/A')}")
    print()

    print("Solar Activity:")
    print(f"  Solar Flux Index (SFI): {data.get('solarflux', 'N/A')}")
    print(f"  Sunspot Number:         {data.get('sunspots', 'N/A')}")
    print(f"  X-Ray:                  {data.get('xray', 'N/A')}")
    print()

    print("Geomagnetic:")
    print(f"  A-Index:    {data.get('aindex', 'N/A')}")
    print(f"  K-Index:    {data.get('kindex', 'N/A')}")
    print(f"  Geo Field:  {data.get('geomagfield', 'N/A')}")
    print()

    print("Space Weather:")
    print(f"  Solar Wind:     {data.get('solarwind', 'N/A')} km/s")
    print(f"  Proton Flux:    {data.get('protonflux', 'N/A')}")
    print(f"  Electron Flux:  {data.get('electonflux', 'N/A')}")
    print()

    # Interpret conditions
    sfi = int(data.get('solarflux', 0) or 0)
    k = int(data.get('kindex', 0) or 0)

    print("Assessment:")
    if sfi >= 150 and k <= 2:
        print("  HF: Excellent conditions for DX")
    elif sfi >= 100 and k <= 3:
        print("  HF: Good conditions")
    elif sfi >= 70 and k <= 4:
        print("  HF: Fair conditions")
    else:
        print("  HF: Poor/disturbed conditions")

    if k >= 5:
        print("  Warning: Geomagnetic storm in progress")


def parse_time_range(s: str) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Parse 'HH:MM-HH:MM' into ((start_h, start_m), (end_h, end_m))."""
    match = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', s)
    if not match:
        return None
    sh, sm, eh, em = map(int, match.groups())
    if not (0 <= sh < 24 and 0 <= sm < 60 and 0 <= eh < 24 and 0 <= em < 60):
        return None
    return ((sh, sm), (eh, em))


def time_in_range(ts: datetime, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Check if timestamp's time-of-day falls within range (handles overnight spans)."""
    t = ts.hour * 60 + ts.minute
    s = start[0] * 60 + start[1]
    e = end[0] * 60 + end[1]

    if s <= e:
        return s <= t < e
    else:  # overnight range like 22:00-06:00
        return t >= s or t < e


def cmd_tod(ranges: list[str], my_grid: str = "CM98kq"):
    """Analyze by time-of-day windows."""
    parsed_ranges = []
    for r in ranges:
        parsed = parse_time_range(r)
        if not parsed:
            print(f"Invalid time range: {r}")
            print("Format: HH:MM-HH:MM (e.g., 06:00-09:00)")
            sys.exit(1)
        parsed_ranges.append((r, parsed[0], parsed[1]))

    if len(parsed_ranges) < 2:
        print("Need at least 2 time ranges to compare")
        sys.exit(1)

    # Get my location for bearing calculation
    my_loc = grid_to_latlon(my_grid)
    if not my_loc:
        print(f"Invalid grid: {my_grid}")
        return
    my_lat, my_lon = my_loc

    print(f"Time-of-Day Analysis")
    print(f"My grid: {my_grid}")
    print(f"Comparing time windows:")
    for label, start, end in parsed_ranges:
        print(f"  {label}")
    print()

    if not ALL_TXT.exists():
        print(f"ALL.TXT not found at {ALL_TXT}")
        return

    # Collect data per time window
    # Structure: window_label -> band -> callsign -> list of SNRs
    window_data: dict[str, dict[str, dict[str, list[int]]]] = {
        r[0]: defaultdict(lambda: defaultdict(list)) for r in parsed_ranges
    }
    callsign_grids: dict[str, str] = {}
    days_seen: set[str] = set()

    with open(ALL_TXT, 'r', errors='replace') as f:
        for line in f:
            parsed = parse_all_txt_line(line)
            if not parsed:
                continue

            ts = parsed["timestamp"]
            days_seen.add(ts.strftime("%Y-%m-%d"))

            # Find which time window this belongs to
            window_label = None
            for label, start, end in parsed_ranges:
                if time_in_range(ts, start, end):
                    window_label = label
                    break

            if not window_label:
                continue

            band = parsed["band"]
            call = parsed["callsign"]
            snr = parsed["snr"]

            window_data[window_label][band][call].append(snr)

            if parsed["grid"] and call not in callsign_grids:
                callsign_grids[call] = parsed["grid"]

    print(f"Analyzed {len(days_seen)} days of data")
    print()

    all_windows = [r[0] for r in parsed_ranges]
    all_bands = set()
    for wd in window_data.values():
        all_bands.update(wd.keys())

    print("=" * 60)
    print("COMPARISON BY BAND")
    print("=" * 60)

    for band in sorted(all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
        # Find calls heard in all time windows on this band
        calls_by_window = {w: set(window_data[w][band].keys()) for w in all_windows}
        common_calls = set.intersection(*calls_by_window.values()) if all(calls_by_window.values()) else set()

        if not common_calls:
            continue

        print(f"\n{band} ({len(common_calls)} common stations):")

        window_avg = {}
        for w in all_windows:
            snrs = []
            for call in common_calls:
                snrs.extend(window_data[w][band][call])
            if snrs:
                window_avg[w] = sum(snrs) / len(snrs)

        baseline_window = all_windows[0]
        baseline = window_avg.get(baseline_window, 0)

        for w in all_windows:
            avg = window_avg.get(w, 0)
            delta = avg - baseline
            delta_str = f"{delta:+.1f} dB" if w != baseline_window else "(baseline)"
            print(f"    {w}: avg SNR {avg:.1f} dB {delta_str}")

    print()
    print("=" * 60)
    print("COMPARISON BY BEARING + BAND")
    print("=" * 60)

    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def bearing_to_sector(bearing: float) -> str:
        idx = round(bearing / 45) % 8
        return sectors[idx]

    for band in sorted(all_bands, key=lambda b: BANDS.get(b, (999, 999))[0]):
        calls_with_bearing = {}
        for w in all_windows:
            for call in window_data[w][band]:
                if call in callsign_grids and call not in calls_with_bearing:
                    loc = grid_to_latlon(callsign_grids[call])
                    if loc:
                        bearing = calc_bearing(my_lat, my_lon, loc[0], loc[1])
                        calls_with_bearing[call] = (bearing, bearing_to_sector(bearing))

        if not calls_with_bearing:
            continue

        band_has_data = False
        band_output = []

        for sector in sectors:
            sector_calls = [c for c, (b, s) in calls_with_bearing.items() if s == sector]
            common_sector_calls = [c for c in sector_calls if all(c in window_data[w][band] for w in all_windows)]

            if not common_sector_calls:
                continue

            if not band_has_data:
                band_output.append(f"\n{band}:")
                band_has_data = True

            band_output.append(f"  {sector} ({len(common_sector_calls)} common stations):")

            window_avg = {}
            for w in all_windows:
                snrs = []
                for call in common_sector_calls:
                    snrs.extend(window_data[w][band][call])
                if snrs:
                    window_avg[w] = sum(snrs) / len(snrs)

            baseline_window = all_windows[0]
            baseline = window_avg.get(baseline_window, 0)

            for w in all_windows:
                avg = window_avg.get(w, 0)
                delta = avg - baseline
                delta_str = f"{delta:+.1f} dB" if w != baseline_window else "(baseline)"
                band_output.append(f"      {w}: avg {avg:.1f} dB {delta_str}")

        if band_has_data:
            print("\n".join(band_output))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "define" and len(sys.argv) >= 4:
        cmd_define(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "list":
        cmd_list()
    elif cmd == "start":
        name = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        cmd_start(name)
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "clear":
        cmd_clear()
    elif cmd == "use" and len(sys.argv) >= 3:
        label = sys.argv[2]
        band = sys.argv[3] if len(sys.argv) >= 4 else None
        cmd_use(label, band)
    elif cmd == "log":
        cmd_log()
    elif cmd == "analyze":
        grid = sys.argv[2] if len(sys.argv) >= 3 else "CM98kq"
        cmd_analyze(grid)
    elif cmd == "tod" and len(sys.argv) >= 4:
        # Find time ranges and optional grid
        ranges = []
        grid = "CM98kq"
        for arg in sys.argv[2:]:
            if parse_time_range(arg):
                ranges.append(arg)
            else:
                grid = arg
        cmd_tod(ranges, grid)
    elif cmd == "solar":
        cmd_solar()
    elif cmd == "pause":
        cmd_pause()
    elif cmd == "resume":
        cmd_resume()
    elif cmd == "note" and len(sys.argv) >= 3:
        # Check if first arg looks like a comparison_id
        if sys.argv[2].startswith("comparison_") and len(sys.argv) >= 4:
            cmd_note(" ".join(sys.argv[3:]), sys.argv[2])
        else:
            cmd_note(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
