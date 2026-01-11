"""Solar and propagation data fetching from HamQSL."""

import urllib.request
import xml.etree.ElementTree as ET


SOLAR_XML_URL = "https://www.hamqsl.com/solarxml.php"


def fetch_solar_data() -> dict | None:
    """Fetch current solar/propagation data from HamQSL.

    Returns:
        Dict with solar data fields or None on error:
            - updated: Update timestamp
            - source: Data source
            - solarflux: Solar Flux Index (SFI)
            - sunspots: Sunspot number
            - xray: X-Ray level
            - aindex: A-Index
            - kindex: K-Index
            - geomagfield: Geomagnetic field status
            - solarwind: Solar wind speed (km/s)
            - protonflux: Proton flux
            - electonflux: Electron flux (note: typo in XML)
            - and more...
    """
    try:
        req = urllib.request.Request(SOLAR_XML_URL)
        req.add_header('User-Agent', 'ak6mj-hf-tools/1.0')
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read().decode('utf-8')

        root = ET.fromstring(xml_data)
        solar = root.find('.//solardata')
        if solar is None:
            return None

        data = {}
        for child in solar:
            data[child.tag] = child.text

        return data
    except Exception as e:
        print(f"Error fetching solar data: {e}")
        return None


def interpret_conditions(solar_data: dict) -> dict:
    """Interpret solar data into propagation conditions.

    Args:
        solar_data: Dict from fetch_solar_data()

    Returns:
        Dict with:
            - hf_conditions: "Poor", "Fair", "Good", or "Excellent"
            - vhf_conditions: "Poor", "Fair", "Good", or "Excellent"
            - noise: "S0-S3", "S4-S6", "S7-S9", "S9+"
            - summary: Human-readable summary string
    """
    try:
        sfi = int(solar_data.get('solarflux', '0'))
        a_index = int(solar_data.get('aindex', '0'))
        k_index = int(solar_data.get('kindex', '0'))
    except ValueError:
        return {
            'hf_conditions': 'Unknown',
            'vhf_conditions': 'Unknown',
            'noise': 'Unknown',
            'summary': 'Unable to parse solar data'
        }

    # HF propagation interpretation
    if sfi >= 150 and a_index <= 7:
        hf_cond = "Excellent"
    elif sfi >= 100 and a_index <= 15:
        hf_cond = "Good"
    elif sfi >= 70 or a_index <= 25:
        hf_cond = "Fair"
    else:
        hf_cond = "Poor"

    # VHF conditions (aurora/Es)
    if k_index >= 5:
        vhf_cond = "Good"  # Aurora likely
    elif k_index <= 2 and sfi >= 100:
        vhf_cond = "Fair"  # Sporadic-E possible
    else:
        vhf_cond = "Poor"

    # Noise level estimation
    if a_index <= 7:
        noise = "S0-S3"
    elif a_index <= 15:
        noise = "S4-S6"
    elif a_index <= 25:
        noise = "S7-S9"
    else:
        noise = "S9+"

    # Build summary
    summary_parts = []
    summary_parts.append(f"HF: {hf_cond}")
    summary_parts.append(f"VHF: {vhf_cond}")
    summary_parts.append(f"Noise: {noise}")

    if k_index >= 5:
        summary_parts.append("(Aurora likely)")
    if sfi >= 150:
        summary_parts.append("(Solar max conditions)")

    return {
        'hf_conditions': hf_cond,
        'vhf_conditions': vhf_cond,
        'noise': noise,
        'summary': ', '.join(summary_parts)
    }
