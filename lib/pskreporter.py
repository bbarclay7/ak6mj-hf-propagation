"""PSKReporter API client for retrieving propagation spots."""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


PSKREPORTER_URL = "https://retrieve.pskreporter.info/query"


def fetch_spots(callsign: str, start_time: datetime, end_time: datetime | None = None, mode: str = "FT8") -> list[dict]:
    """Fetch TX spots from PSKReporter for a time window.

    Args:
        callsign: Callsign to query (transmitter)
        start_time: Start of time window (UTC)
        end_time: End of time window (UTC), or None for "now"
        mode: Mode to filter (default: FT8)

    Returns:
        List of dicts with: receiver_call, receiver_grid, freq_mhz, band, snr, timestamp

    Note:
        PSKReporter limits: max 24 hours back, returns max ~100 spots per query
    """
    import time

    now = datetime.now(timezone.utc)

    # Calculate time bounds
    seconds_ago = int((now - start_time).total_seconds())
    if seconds_ago > 86400:
        seconds_ago = 86400  # PSKReporter max is 24 hours

    url = f"{PSKREPORTER_URL}?senderCallsign={callsign}&flowStartSeconds=-{seconds_ago}&mode={mode}&rronly=1"

    # Retry with backoff on rate limiting
    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'ak6mj-hf-tools/1.0')
            with urllib.request.urlopen(req, timeout=30) as response:
                xml_data = response.read().decode('utf-8')

            root = ET.fromstring(xml_data)
            spots = []

            for report in root.findall('./receptionReport'):
                receiver_call = report.get('receiverCallsign', '?')
                receiver_grid = report.get('receiverLocator', '?')
                freq_khz = int(report.get('frequency', 0))
                freq_mhz = freq_khz / 1000.0
                snr_str = report.get('sNR', 'N/A')
                ts_str = report.get('flowStartSeconds', '0')

                try:
                    snr = int(snr_str)
                except ValueError:
                    snr = None

                # Convert Unix timestamp
                ts_unix = int(ts_str)
                timestamp = datetime.fromtimestamp(ts_unix, tz=timezone.utc)

                # Determine band from frequency
                from .band_utils import freq_to_band
                band = freq_to_band(freq_mhz)

                spots.append({
                    'receiver_call': receiver_call,
                    'receiver_grid': receiver_grid,
                    'freq_mhz': freq_mhz,
                    'band': band,
                    'snr': snr,
                    'timestamp': timestamp,
                })

            return spots

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limited
                if attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            raise
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
                continue
            print(f"Error fetching PSKReporter data: {e}")
            return []

    return []
