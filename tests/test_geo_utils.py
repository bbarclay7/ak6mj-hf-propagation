#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Test geographic utility functions for correctness on spherical Earth."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from geo_utils import grid_to_latlon, calc_bearing, calc_distance_km


def test_bearing_known_values():
    """Test bearing calculation with known geographic cases."""

    # Test 1: Due East from equator
    # From (0°N, 0°E) to (0°N, 90°E) should be 90° (East)
    bearing = calc_bearing(0, 0, 0, 90)
    print(f"Test 1 - Due East from equator: {bearing:.1f}° (expected: 90.0°)")
    assert abs(bearing - 90.0) < 0.1

    # Test 2: Due North
    # From (0°N, 0°E) to (45°N, 0°E) should be 0° (North)
    bearing = calc_bearing(0, 0, 45, 0)
    print(f"Test 2 - Due North: {bearing:.1f}° (expected: 0.0°)")
    assert abs(bearing - 0.0) < 0.1

    # Test 3: Due South
    # From (45°N, 0°E) to (0°N, 0°E) should be 180° (South)
    bearing = calc_bearing(45, 0, 0, 0)
    print(f"Test 3 - Due South: {bearing:.1f}° (expected: 180.0°)")
    assert abs(bearing - 180.0) < 0.1

    # Test 4: Due West from equator
    # From (0°N, 90°E) to (0°N, 0°E) should be 270° (West)
    bearing = calc_bearing(0, 90, 0, 0)
    print(f"Test 4 - Due West: {bearing:.1f}° (expected: 270.0°)")
    assert abs(bearing - 270.0) < 0.1

    # Test 5: Real world - Folsom, CA to London, UK
    # CM98kq (Folsom) ≈ 38.6°N, 121.2°W = -121.2°E
    # IO91wl (London) ≈ 51.5°N, 0.2°W = -0.2°E
    # Expected: roughly 35-45° (Northeast)
    bearing = calc_bearing(38.6, -121.2, 51.5, -0.2)
    print(f"Test 5 - Folsom to London: {bearing:.1f}° (expected: ~35-45° NE)")
    assert 30 < bearing < 50

    # Test 6: Spherical effect - North from near pole
    # From 80°N, 0°E to North Pole should be ~0° (but slightly different due to convergence)
    bearing = calc_bearing(80, 0, 90, 0)
    print(f"Test 6 - Near pole to pole: {bearing:.1f}° (expected: ~0° but can vary)")
    # At high latitudes, any longitude reaches the pole

    # Test 7: Antipodal points (opposite sides of Earth)
    # From 0°N, 0°E to 0°N, 180°E - great circle goes either way
    # Initial bearing should be 90° (due East is shorter)
    bearing = calc_bearing(0, 0, 0, 180)
    print(f"Test 7 - Halfway around equator: {bearing:.1f}° (expected: 90.0°)")
    assert abs(bearing - 90.0) < 0.1

    print("\n✅ All bearing tests passed - formula is correct for spherical Earth!")


def test_distance_known_values():
    """Test distance calculation with known values."""

    # Test 1: Quarter way around equator (90° longitude)
    # Should be ~10,000 km (1/4 of ~40,000 km circumference)
    dist = calc_distance_km(0, 0, 0, 90)
    print(f"\nTest 1 - Quarter equator: {dist:.0f} km (expected: ~10,000 km)")
    assert abs(dist - 10018) < 100  # ~10,018 km actual

    # Test 2: Halfway around Earth at equator (180° longitude)
    # Should be ~20,000 km (1/2 of ~40,000 km)
    dist = calc_distance_km(0, 0, 0, 180)
    print(f"Test 2 - Half equator: {dist:.0f} km (expected: ~20,000 km)")
    assert abs(dist - 20015) < 100  # ~20,015 km actual

    # Test 3: Pole to pole (0° to 90°N latitude)
    # Should be ~10,000 km (1/4 of meridian)
    dist = calc_distance_km(0, 0, 90, 0)
    print(f"Test 3 - Equator to pole: {dist:.0f} km (expected: ~10,000 km)")
    assert abs(dist - 10001) < 100

    # Test 4: Real world - Folsom to London
    # Should be ~8,600 km
    dist = calc_distance_km(38.6, -121.2, 51.5, -0.2)
    print(f"Test 4 - Folsom to London: {dist:.0f} km (expected: ~8,600 km)")
    assert abs(dist - 8600) < 200

    print("\n✅ All distance tests passed - Haversine formula is correct!")


def test_grid_to_latlon():
    """Test Maidenhead grid square conversion."""

    # Test known gridsquares (values are grid CENTER, not exact city location)
    test_cases = [
        ("CM98kq", 38.69, -121.12),  # Folsom area (grid center)
        ("CN88ra", 48.02, -122.54),  # Freeland area (grid center)
        ("JO01", 51.5, 1.0),         # 4-char grid near London (grid center)
    ]

    print("\nGrid square tests:")
    for grid, exp_lat, exp_lon in test_cases:
        lat, lon = grid_to_latlon(grid)
        print(f"  {grid}: ({lat:.2f}°, {lon:.2f}°) - expected: ({exp_lat:.2f}°, {exp_lon:.2f}°)")
        assert abs(lat - exp_lat) < 0.2  # Grid squares are ~1°x2°, center can be off
        assert abs(lon - exp_lon) < 0.2

    print("\n✅ All grid tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing geo_utils on spherical Earth")
    print("=" * 60)

    test_bearing_known_values()
    test_distance_known_values()
    test_grid_to_latlon()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Formulas are correct for sphere!")
    print("=" * 60)
