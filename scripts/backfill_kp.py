#!/usr/bin/env python3
"""
Backfill historical Kp data from GFZ Potsdam.

GFZ is the official source for Kp index, with data back to 1932.
This script fetches recent data and stores it for correlation with WSPR spots.

Usage:
    python3 backfill_kp.py              # Backfill last 30 days
    python3 backfill_kp.py 2026-01-01   # Backfill from specific date
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

# Output file
DATA_DIR = Path("/var/www/local/wspr-data")
KP_FILE = DATA_DIR / "kp_history.json"

# Fallback for local dev
if not DATA_DIR.exists():
    DATA_DIR = Path.home() / "work/ak6mj-hf-propagation/local/wspr-data"
    KP_FILE = DATA_DIR / "kp_history.json"


def fetch_gfz_kp():
    """Fetch full Kp archive from GFZ Potsdam."""
    url = "https://www-app3.gfz-potsdam.de/kp_index/Kp_ap_since_1932.txt"

    print(f"Fetching from GFZ Potsdam...")
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read().decode()

    records = []
    for line in data.strip().split('\n'):
        if line.startswith('#') or not line.strip():
            continue

        parts = line.split()
        if len(parts) < 9:
            continue

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            hour_start = float(parts[3])
            hour_end = float(parts[4])
            kp = float(parts[7])
            ap = int(parts[8])

            # Skip future/invalid entries (kp = -1)
            if kp < 0:
                continue

            # Create timestamp for the midpoint of the 3-hour period
            hour = int((hour_start + hour_end) / 2)
            try:
                ts = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
            except ValueError:
                continue

            records.append({
                "timestamp": ts.isoformat(),
                "kp": kp,
                "ap": ap,
            })
        except (ValueError, IndexError):
            continue

    return records


def backfill(start_date=None):
    """Backfill Kp data from start_date to now."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_records = fetch_gfz_kp()
    print(f"Fetched {len(all_records)} total Kp records from GFZ")

    # Filter to requested date range
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        records = [r for r in all_records if datetime.fromisoformat(r["timestamp"]) >= start]
    else:
        # Default: last 30 days
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        records = [r for r in all_records if datetime.fromisoformat(r["timestamp"]) >= cutoff]

    print(f"Filtered to {len(records)} records")

    if records:
        print(f"Date range: {records[0]['timestamp']} to {records[-1]['timestamp']}")

    # Save to file
    output = {
        "source": "GFZ Potsdam",
        "url": "https://www-app3.gfz-potsdam.de/kp_index/",
        "fetched": datetime.now(timezone.utc).isoformat(),
        "records": records,
    }

    with open(KP_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to {KP_FILE}")
    return records


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else None
    backfill(start)
