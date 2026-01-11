#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Test band and frequency utility functions."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from band_utils import BANDS, WSPR_FREQS, freq_to_band, band_to_wspr_freq, is_warc_band


def test_freq_to_band():
    """Test frequency to band conversion."""
    print("Testing freq_to_band():")

    test_cases = [
        (1.84, "160m"),
        (3.573, "80m"),
        (7.074, "40m"),
        (10.136, "30m"),
        (14.074, "20m"),
        (18.1, "17m"),
        (21.074, "15m"),
        (24.915, "12m"),
        (28.074, "10m"),
        (50.313, "6m"),
        (144.174, "2m"),
        (99.999, "99.999MHz"),  # Out of band
    ]

    for freq, expected in test_cases:
        result = freq_to_band(freq)
        print(f"  {freq} MHz → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✅ All freq_to_band tests passed!\n")


def test_band_to_wspr_freq():
    """Test band to WSPR frequency conversion."""
    print("Testing band_to_wspr_freq():")

    test_cases = [
        ("160m", 1838100),
        ("80m", 3570100),
        ("40m", 7040100),
        ("30m", 10140200),
        ("20m", 14097100),
        ("17m", 18106100),
        ("15m", 21096100),
        ("12m", 24926100),
        ("10m", 28126100),
        ("6m", 50294500),
        ("2m", None),  # Not in WSPR_FREQS
        ("invalid", None),
    ]

    for band, expected in test_cases:
        result = band_to_wspr_freq(band)
        print(f"  {band} → {result} Hz (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✅ All band_to_wspr_freq tests passed!\n")


def test_is_warc_band():
    """Test WARC band detection."""
    print("Testing is_warc_band():")

    test_cases = [
        ("160m", False),
        ("80m", False),
        ("60m", True),
        ("40m", False),
        ("30m", True),
        ("20m", False),
        ("17m", True),
        ("15m", False),
        ("12m", True),
        ("10m", False),
        ("6m", False),
        ("2m", False),
    ]

    for band, expected in test_cases:
        result = is_warc_band(band)
        status = "WARC" if result else "non-WARC"
        print(f"  {band}: {status} (expected: {'WARC' if expected else 'non-WARC'})")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✅ All is_warc_band tests passed!\n")


def test_band_definitions():
    """Test that BANDS and WSPR_FREQS are consistent."""
    print("Testing BANDS and WSPR_FREQS consistency:")

    # All WSPR bands should be in BANDS
    for band in WSPR_FREQS.keys():
        assert band in BANDS, f"WSPR band {band} not in BANDS"
        print(f"  ✓ {band} exists in BANDS")

    # WSPR frequencies should fall within band edges
    for band, freq_hz in WSPR_FREQS.items():
        freq_mhz = freq_hz / 1_000_000
        low, high = BANDS[band]
        assert low <= freq_mhz <= high, f"WSPR freq {freq_mhz} MHz not in {band} ({low}-{high})"
        print(f"  ✓ {band}: {freq_mhz:.4f} MHz is within {low}-{high} MHz")

    print("✅ All consistency tests passed!\n")


def test_band_coverage():
    """Test that we have expected ham bands."""
    print("Testing band coverage:")

    expected_bands = ["160m", "80m", "60m", "40m", "30m", "20m",
                     "17m", "15m", "12m", "10m", "6m", "2m"]

    for band in expected_bands:
        assert band in BANDS, f"Missing expected band: {band}"
        print(f"  ✓ {band} defined")

    print(f"✅ All {len(expected_bands)} expected bands present!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing band_utils.py")
    print("=" * 60 + "\n")

    test_freq_to_band()
    test_band_to_wspr_freq()
    test_is_warc_band()
    test_band_definitions()
    test_band_coverage()

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
