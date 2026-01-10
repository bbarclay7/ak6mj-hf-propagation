#!/usr/bin/env python3
"""
Check current QRZ.com profile settings for a callsign via the XML API.
Requires QRZ XML subscription. Store credentials in ~/.qrz_credentials:
    username=YOURCALL
    password=YOURPASSWORD
"""

import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import urllib.request
import urllib.parse

CREDENTIALS_FILE = Path.home() / ".qrz_credentials"

# IP geolocation to QTH mapping (region -> expected grid)
REGION_TO_QTH = {
    "California": "CM98",
    "Washington": "CN88",
}

# Expected settings for each QTH
QTH_SETTINGS = {
    "CN88": {
        "grid": "CN88ra",
        "county": "Island",
        "iota": "NA-065",
        "description": "Freeland, WA",
    },
    "CM98": {
        "grid": "CM98kq",
        "county": "Sacramento",
        "iota": "",
        "description": "Folsom, CA",
    },
}


def get_ip_location() -> dict:
    """Get current location based on IP address."""
    try:
        req = urllib.request.Request("https://ipinfo.io/json")
        req.add_header('User-Agent', 'qth-checker/1.0')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception:
        return {}


def load_credentials() -> tuple[str, str]:
    if not CREDENTIALS_FILE.exists():
        print(f"Error: Create {CREDENTIALS_FILE} with:")
        print("  username=YOURCALL")
        print("  password=YOURPASSWORD")
        sys.exit(1)

    creds = {}
    for line in CREDENTIALS_FILE.read_text().strip().split('\n'):
        if '=' in line:
            key, val = line.split('=', 1)
            creds[key.strip()] = val.strip()

    return creds.get('username', ''), creds.get('password', '')


def get_session_key(username: str, password: str) -> str:
    url = "https://xmldata.qrz.com/xml/current/"
    params = urllib.parse.urlencode({
        'username': username,
        'password': password,
    })

    req = urllib.request.Request(f"{url}?{params}")
    req.add_header('User-Agent', f'{username}-qth-checker/1.0')

    with urllib.request.urlopen(req) as response:
        xml = response.read().decode('utf-8')

    root = ET.fromstring(xml)
    ns = {'qrz': 'http://xmldata.qrz.com'}

    # Try with namespace first, then without
    key = root.find('.//{http://xmldata.qrz.com}Key')
    if key is None:
        key = root.find('.//Key')
    if key is not None and key.text:
        return key.text

    # Check for error
    error = root.find('.//{http://xmldata.qrz.com}Error')
    if error is None:
        error = root.find('.//Error')
    if error is not None:
        print(f"QRZ API Error: {error.text}")
        sys.exit(1)

    print("Failed to get session key")
    print(xml)
    sys.exit(1)


def lookup_callsign(session_key: str, callsign: str) -> dict:
    url = "https://xmldata.qrz.com/xml/current/"
    params = urllib.parse.urlencode({
        's': session_key,
        'callsign': callsign,
    })

    req = urllib.request.Request(f"{url}?{params}")
    req.add_header('User-Agent', f'{callsign}-qth-checker/1.0')

    with urllib.request.urlopen(req) as response:
        xml = response.read().decode('utf-8')

    root = ET.fromstring(xml)

    result = {}
    # Try to find Callsign element (with or without namespace)
    callsign_elem = root.find('.//{http://xmldata.qrz.com}Callsign')
    if callsign_elem is None:
        callsign_elem = root.find('.//Callsign')

    if callsign_elem is not None:
        for child in callsign_elem:
            # Strip namespace from tag
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            result[tag.lower()] = child.text or ""

    return result


def main():
    username, password = load_credentials()
    callsign = username.upper()

    # Get IP-based location
    ip_info = get_ip_location()
    ip_region = ip_info.get('region', '')
    ip_city = ip_info.get('city', '')
    expected_qth = REGION_TO_QTH.get(ip_region)

    print(f"IP Location: {ip_city}, {ip_region}")
    if expected_qth:
        expected_settings = QTH_SETTINGS[expected_qth]
        print(f"Expected QTH: {expected_qth} ({expected_settings['description']})")
    print()

    print(f"Checking QRZ settings for {callsign}...")
    print()

    session_key = get_session_key(username, password)
    data = lookup_callsign(session_key, callsign)

    if not data:
        print("No data returned from QRZ")
        sys.exit(1)

    # Display current settings
    current_grid = data.get('grid', '').upper()
    current_county = data.get('county', '')
    current_iota = data.get('iota', '')

    print("Current QRZ Profile Settings:")
    print(f"  Grid:   {current_grid}")
    print(f"  County: {current_county}")
    print(f"  IOTA:   {current_iota or '(none)'}")
    print()

    # Check against known QTHs
    matched_qth = None
    for qth, expected in QTH_SETTINGS.items():
        if current_grid.startswith(expected['grid'][:4]):
            matched_qth = qth
            break

    if matched_qth:
        expected = QTH_SETTINGS[matched_qth]
        print(f"QRZ Profile QTH: {matched_qth} ({expected['description']})")

        # Check if QRZ matches IP location
        if expected_qth and matched_qth != expected_qth:
            exp = QTH_SETTINGS[expected_qth]
            print()
            print(f"*** MISMATCH: You appear to be in {expected_qth} ({exp['description']}) but QRZ shows {matched_qth} ***")
            print(f"Run 'make {exp['description'].split(',')[0].lower()}' to update")
            sys.exit(1)

        # Check details
        issues = []
        if expected['iota'] and current_iota != expected['iota']:
            issues.append(f"  IOTA should be {expected['iota']}, got {current_iota or '(none)'}")
        elif not expected['iota'] and current_iota:
            issues.append(f"  IOTA should be blank, got {current_iota}")
        if expected['county'] and expected['county'].lower() not in current_county.lower():
            issues.append(f"  County should contain '{expected['county']}', got '{current_county}'")

        if issues:
            print("Issues found:")
            for issue in issues:
                print(issue)
            sys.exit(1)
        else:
            print("All settings look correct!")
    else:
        print(f"Grid {current_grid} doesn't match any known QTH:")
        for qth, expected in QTH_SETTINGS.items():
            print(f"  {qth}: {expected['description']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
