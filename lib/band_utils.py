"""Band and frequency utilities for amateur radio."""

# Band edges for categorization (MHz)
BANDS = {
    "160m": (1.8, 2.0),
    "80m": (3.5, 4.0),
    "60m": (5.3, 5.4),
    "40m": (7.0, 7.3),
    "30m": (10.1, 10.15),
    "20m": (14.0, 14.35),
    "17m": (18.068, 18.168),
    "15m": (21.0, 21.45),
    "12m": (24.89, 24.99),
    "10m": (28.0, 29.7),
    "6m": (50.0, 54.0),
    "2m": (144.0, 148.0),
}

# WSPR frequencies (Hz) - from wspr_band.py
WSPR_FREQS = {
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


def freq_to_band(freq_mhz: float) -> str:
    """Convert frequency to band name.

    Args:
        freq_mhz: Frequency in MHz

    Returns:
        Band name (e.g., "20m") or frequency string if not in a known band
    """
    for band, (low, high) in BANDS.items():
        if low <= freq_mhz <= high:
            return band
    return f"{freq_mhz:.3f}MHz"


def band_to_wspr_freq(band: str) -> int | None:
    """Get WSPR frequency for a band.

    Args:
        band: Band name (e.g., "20m")

    Returns:
        WSPR frequency in Hz, or None if band not supported
    """
    return WSPR_FREQS.get(band)


def is_warc_band(band: str) -> bool:
    """Check if band is a WARC band (no contests allowed).

    Args:
        band: Band name (e.g., "30m")

    Returns:
        True if WARC band (30m, 17m, 12m, 60m)
    """
    return band in ("30m", "17m", "12m", "60m")
