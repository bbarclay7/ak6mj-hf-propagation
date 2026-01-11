"""Unified configuration loader for AK6MJ HF tools."""

import yaml
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "callsign": "AK6MJ",
    "grid": "CM98",  # Default grid (Folsom, CA)
    "power": 23,     # WSPR power in dBm (200mW)
    "device": "/dev/ttyUSB0",  # Serial device (Linux default)
    "baud": 9600,
}


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file with defaults.

    Searches for config in:
    1. Provided path
    2. local/config/config.yaml (user config, gitignored)
    3. ~/.config/ak6mj-hf/config.yaml (XDG standard)
    4. Falls back to defaults

    Args:
        config_path: Optional path to config file

    Returns:
        Dict with configuration values
    """
    config = DEFAULT_CONFIG.copy()

    # Try paths in order
    search_paths = []

    if config_path:
        search_paths.append(config_path)

    # Local config (gitignored, stays with repo)
    repo_root = Path(__file__).parent.parent
    search_paths.append(repo_root / "local" / "config" / "config.yaml")

    # XDG config
    xdg_config = Path.home() / ".config" / "ak6mj-hf" / "config.yaml"
    search_paths.append(xdg_config)

    # Legacy WSPR beacon config
    wspr_config = Path.home() / ".config" / "wspr-beacon" / "config.yaml"
    search_paths.append(wspr_config)

    # Load first found config
    for path in search_paths:
        if path and path.exists():
            try:
                with open(path) as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        config.update(user_config)
                return config
            except Exception as e:
                print(f"Warning: Could not load config from {path}: {e}")

    return config


def save_config(config: dict[str, Any], config_path: Path | None = None) -> None:
    """Save configuration to YAML file.

    Args:
        config: Configuration dict to save
        config_path: Optional path to save to (defaults to local/config/config.yaml)
    """
    if config_path is None:
        repo_root = Path(__file__).parent.parent
        config_path = repo_root / "local" / "config" / "config.yaml"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
