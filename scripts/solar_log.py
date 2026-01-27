#!/usr/bin/env python3
"""
Log solar/propagation conditions for correlation with WSPR data.

Run via cron every 15-30 minutes to build up historical data.
Data stored in /var/www/local/wspr-data/solar_log.jsonl (JSON lines format)

Sources:
- NOAA: Kp index, solar flux
- hamqsl.com: Current conditions summary
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

# Output file - JSON lines format for easy appending
DATA_DIR = Path("/var/www/local/wspr-data")
SOLAR_LOG = DATA_DIR / "solar_log.jsonl"

# Fallback for local dev
if not DATA_DIR.exists():
    DATA_DIR = Path.home() / "work/ak6mj-hf-propagation/local/wspr-data"
    SOLAR_LOG = DATA_DIR / "solar_log.jsonl"


def fetch_noaa_kp():
    """Fetch current Kp from NOAA."""
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.load(resp)
        # data[0] is header, data[-1] is most recent
        if len(data) > 1:
            latest = data[-1]
            return {
                "time": latest[0],
                "kp": float(latest[1]),
                "a_running": int(latest[2]) if latest[2] else None,
            }
    except Exception as e:
        print(f"NOAA Kp fetch error: {e}", file=sys.stderr)
    return None


def fetch_hamqsl():
    """Fetch current conditions from hamqsl.com."""
    url = "https://www.hamqsl.com/solarxml.php"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            root = ET.fromstring(resp.read())

        solar = root.find('.//solardata')
        if solar is not None:
            return {
                "sfi": int(solar.findtext('solarflux', '0')),
                "a_index": int(solar.findtext('aindex', '0')),
                "k_index": int(solar.findtext('kindex', '0')),
                "sunspots": int(solar.findtext('sunspots', '0')),
                "xray": solar.findtext('xray', ''),
                "geomagfield": solar.findtext('geomagfield', ''),
                "signalnoise": solar.findtext('signalnoise', ''),
            }
    except Exception as e:
        print(f"hamqsl fetch error: {e}", file=sys.stderr)
    return None


def log_conditions():
    """Fetch and log current solar conditions."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    noaa = fetch_noaa_kp()
    hamqsl = fetch_hamqsl()

    record = {
        "timestamp": now.isoformat(),
        "noaa_kp": noaa,
        "hamqsl": hamqsl,
    }

    # Append to JSON lines file
    with open(SOLAR_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Logged: Kp={noaa['kp'] if noaa else '?'}, SFI={hamqsl['sfi'] if hamqsl else '?'}")
    return record


if __name__ == "__main__":
    log_conditions()
