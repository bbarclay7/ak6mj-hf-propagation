#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
# ]
# ///
"""
Sync FT8 data from hamtop1 to www server.

This script runs on hamtop1 (Windows/WSL2) and pushes ALL.TXT to the www server
via HTTP POST. Designed to run on a schedule (every 5-30 minutes).

Usage:
    python sync_to_www.py                          # Push ALL.TXT to www
    python sync_to_www.py --dry-run                # Test without uploading
    python sync_to_www.py --check                  # Check connection only

Schedule with Windows Task Scheduler:
    wsl python3 /path/to/sync_to_www.py
"""

import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime, timezone

# Configuration
WWW_URL = "https://www.shoeph.one/hf/api/upload/alltxt"
USERNAME = "ak6mj"
PASSWORD = "HF73DX2026!"
ALL_TXT_PATH = Path("/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT")


def check_connection():
    """Test connection to www server."""
    try:
        r = requests.get("https://www.shoeph.one/hf/health", timeout=10, verify=False)
        r.raise_for_status()
        data = r.json()
        print(f"✓ Connection OK: {data['service']} v{data['version']}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def sync_alltxt(dry_run=False):
    """Upload ALL.TXT to www server."""
    # Check if file exists
    if not ALL_TXT_PATH.exists():
        print(f"✗ File not found: {ALL_TXT_PATH}")
        return False

    # Get file info
    size = ALL_TXT_PATH.stat().st_size
    mtime = datetime.fromtimestamp(ALL_TXT_PATH.stat().st_mtime, tz=timezone.utc)

    print(f"File: {ALL_TXT_PATH}")
    print(f"Size: {size:,} bytes")
    print(f"Modified: {mtime.isoformat()}")

    if dry_run:
        print("✓ Dry run - would upload to:", WWW_URL)
        return True

    # Read and upload
    try:
        with open(ALL_TXT_PATH, "rb") as f:
            files = {"file": ("ALL.TXT", f, "text/plain")}
            data = {
                "source": "hamtop1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            print(f"Uploading to {WWW_URL}...")
            r = requests.post(
                WWW_URL,
                files=files,
                data=data,
                auth=(USERNAME, PASSWORD),
                timeout=30,
                verify=False,  # Self-signed cert
            )
            r.raise_for_status()

            result = r.json()
            print(f"✓ Upload successful: {result}")
            return True

    except Exception as e:
        print(f"✗ Upload failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sync FT8 data to www server")
    parser.add_argument("--dry-run", action="store_true", help="Test without uploading")
    parser.add_argument("--check", action="store_true", help="Check connection only")
    args = parser.parse_args()

    print("=" * 60)
    print(f"FT8 Data Sync - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    if args.check:
        success = check_connection()
    else:
        success = sync_alltxt(dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
