#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Test solar data functions."""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from solar import interpret_conditions


def test_interpret_conditions():
    """Test solar data interpretation logic."""
    print("Testing interpret_conditions():\n")

    # Test 1: Fair conditions (SFI=80, A=25)
    # Logic: sfi >= 70 OR a_index <= 25 → Fair
    fair_data_1 = {
        'solarflux': '80',
        'aindex': '25',
        'kindex': '5',
    }

    result = interpret_conditions(fair_data_1)
    print("Test 1 - Fair conditions (SFI=80, A=25, K=5):")
    print(f"  HF: {result['hf_conditions']}")
    print(f"  VHF: {result['vhf_conditions']}")
    print(f"  Noise: {result['noise']}")
    assert result['hf_conditions'] == 'Fair'  # sfi >= 70 OR a <= 25
    assert result['vhf_conditions'] == 'Good'  # k >= 5 (aurora)
    assert result['noise'] == 'S7-S9'  # a_index 15-25
    print("  ✅ Passed\n")

    # Test 2: Good conditions (SFI=120, A=12)
    # Logic: sfi >= 100 AND a_index <= 15 → Good
    good_data = {
        'solarflux': '120',
        'aindex': '12',
        'kindex': '3',
    }

    result = interpret_conditions(good_data)
    print("Test 2 - Good conditions (SFI=120, A=12, K=3):")
    print(f"  HF: {result['hf_conditions']}")
    print(f"  Noise: {result['noise']}")
    assert result['hf_conditions'] == 'Good'  # sfi >= 100 and a <= 15
    assert result['noise'] == 'S4-S6'  # a_index 8-15
    print("  ✅ Passed\n")

    # Test 3: Excellent conditions (SFI=180, A=5)
    # Logic: sfi >= 150 AND a_index <= 7 → Excellent
    excellent_data = {
        'solarflux': '180',
        'aindex': '5',
        'kindex': '1',
    }

    result = interpret_conditions(excellent_data)
    print("Test 3 - Excellent conditions (SFI=180, A=5, K=1):")
    print(f"  HF: {result['hf_conditions']}")
    print(f"  Noise: {result['noise']}")
    assert result['hf_conditions'] == 'Excellent'  # sfi >= 150 and a <= 7
    assert result['noise'] == 'S0-S3'  # a_index <= 7
    print("  ✅ Passed\n")

    # Test 4: Poor conditions (low SFI, high A)
    # Logic: NOT (sfi >= 70 OR a_index <= 25) → Poor
    poor_data = {
        'solarflux': '60',
        'aindex': '30',
        'kindex': '7',
    }

    result = interpret_conditions(poor_data)
    print("Test 4 - Poor conditions (SFI=60, A=30, K=7):")
    print(f"  HF: {result['hf_conditions']}")
    print(f"  Noise: {result['noise']}")
    assert result['hf_conditions'] == 'Poor'  # sfi < 70 AND a > 25
    assert result['noise'] == 'S9+'  # a_index > 25
    print("  ✅ Passed\n")

    # Test 5: VHF aurora conditions (high K)
    aurora_data = {
        'solarflux': '100',
        'aindex': '20',
        'kindex': '6',
    }

    result = interpret_conditions(aurora_data)
    print("Test 5 - VHF aurora conditions (K=6):")
    print(f"  VHF: {result['vhf_conditions']}")
    print(f"  Summary: {result['summary']}")
    assert result['vhf_conditions'] == 'Good'  # k >= 5 (aurora likely)
    assert '(Aurora likely)' in result['summary']
    print("  ✅ Passed\n")

    # Test 6: Solar max indicator (very high SFI)
    solar_max_data = {
        'solarflux': '200',
        'aindex': '6',
        'kindex': '2',
    }

    result = interpret_conditions(solar_max_data)
    print("Test 6 - Solar maximum (SFI=200):")
    print(f"  HF: {result['hf_conditions']}")
    print(f"  Summary: {result['summary']}")
    assert result['hf_conditions'] == 'Excellent'
    assert '(Solar max conditions)' in result['summary']
    print("  ✅ Passed\n")

    print("✅ All interpret_conditions tests passed!\n")


def test_edge_cases():
    """Test edge cases and missing data."""
    print("Testing edge cases:\n")

    # Test with minimal data
    minimal_data = {
        'solarflux': '100',
        'kindex': '2',
    }

    result = interpret_conditions(minimal_data)
    print("Test 1 - Minimal data:")
    print(f"  HF: {result['hf_conditions']}")
    assert 'hf_conditions' in result
    assert 'summary' in result
    print("  ✅ Passed\n")

    # Test with string numbers
    string_data = {
        'solarflux': 'not_a_number',
        'kindex': 'also_not_a_number',
    }

    result = interpret_conditions(string_data)
    print("Test 2 - Invalid string values:")
    print(f"  Result: {result}")
    assert 'hf_conditions' in result  # Should have defaults
    print("  ✅ Passed (graceful handling)\n")

    print("✅ All edge case tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing solar.py")
    print("=" * 60 + "\n")

    test_interpret_conditions()
    test_edge_cases()

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nNote: fetch_solar_data() requires network access.")
    print("Test it manually with: python -c 'from solar import fetch_solar_data; print(fetch_solar_data())'")
