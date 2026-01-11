#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyyaml",
# ]
# ///
"""Test configuration loading and saving."""

import sys
import tempfile
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from config import load_config, save_config, DEFAULT_CONFIG


def test_default_config():
    """Test that default config has required fields."""
    print("Testing DEFAULT_CONFIG:\n")

    required_fields = ['callsign', 'grid', 'power', 'device', 'baud']

    for field in required_fields:
        assert field in DEFAULT_CONFIG, f"Missing required field: {field}"
        print(f"  ✓ {field}: {DEFAULT_CONFIG[field]}")

    print("\n✅ Default config has all required fields!\n")


def test_load_nonexistent():
    """Test loading config when file doesn't exist."""
    print("Testing load_config() with nonexistent file:\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "nonexistent.yaml"
        config = load_config(fake_path)

        print(f"  Result: {config}")
        assert config == DEFAULT_CONFIG, "Should return default config"

    print("  ✅ Returns default config\n")


def test_save_and_load():
    """Test saving and loading config."""
    print("Testing save_config() and load_config():\n")

    test_config = {
        'callsign': 'W1AW',
        'grid': 'FN31pr',
        'power': 10,
        'device': '/dev/ttyUSB999',
        'baud': 115200,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"

        # Save
        save_config(test_config, config_path)
        print(f"  Saved to {config_path}")
        assert config_path.exists(), "Config file should exist"

        # Load
        loaded = load_config(config_path)
        print(f"  Loaded: {loaded}")

        # Verify
        for key, value in test_config.items():
            assert loaded[key] == value, f"Mismatch on {key}: {loaded[key]} != {value}"
            print(f"    ✓ {key}: {value}")

    print("\n✅ Save and load works correctly!\n")


def test_config_search_paths():
    """Test that config searches multiple paths."""
    print("Testing config search paths:\n")

    # This just verifies load_config can be called without path
    # and falls back to defaults if nothing found
    config = load_config()

    print(f"  Loaded config (from default paths or defaults): {config}")
    assert 'callsign' in config
    assert 'grid' in config

    print("  ✅ Search path logic works\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing config.py")
    print("=" * 60 + "\n")

    test_default_config()
    test_load_nonexistent()
    test_save_and_load()
    test_config_search_paths()

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
