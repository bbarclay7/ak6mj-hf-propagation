#!/usr/bin/env -S uv run
# -*- mode: python; -*-
# vim: set ft=python:
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
FT8 Tool - Interactive TUI for FT8 log management and antenna analysis.

Run without arguments for interactive menu, or with a command for direct access.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_cmd(args: list[str], capture=False):
    """Run a command and optionally capture output."""
    if capture:
        result = subprocess.run(args, capture_output=True, text=True)
        return result.stdout + result.stderr
    else:
        subprocess.run(args)
        return None


def clear_screen():
    print("\033[2J\033[H", end="")


def pause():
    input("\nPress Enter to continue...")


def print_header(title: str):
    clear_screen()
    print("=" * 60)
    print(f"  FT8 Tool - {title}")
    print("=" * 60)
    print()


def print_menu(options: list[tuple[str, str]]):
    """Print menu options. Each option is (key, description)."""
    for key, desc in options:
        print(f"  [{key}] {desc}")
    print()


def get_input(prompt: str, default: str = "") -> str:
    """Get input with optional default."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


# ============================================================================
# QRZ / Log Management
# ============================================================================

def menu_qrz():
    while True:
        print_header("QRZ & Log Management")
        print("""Use Case: Manage your QRZ profile and split logs by operating location.

When you operate from different QTHs (e.g., home vs portable), your WSJTX log
contains QSOs with different MY_GRIDSQUARE values. QRZ needs separate uploads
for each location, and your profile should match where you're currently operating.
""")
        print_menu([
            ("1", "Check QRZ profile vs current location (IP-based)"),
            ("2", "Split log by gridsquare & copy to WSJT-X folder"),
            ("3", "Switch to Folsom (CM98kq) - open QRZ settings"),
            ("4", "Switch to Freeland (CN88ra) - open QRZ settings"),
            ("b", "Back to main menu"),
        ])

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            print()
            run_cmd(["make", "-C", str(SCRIPT_DIR), "check"])
            pause()
        elif choice == "2":
            print()
            run_cmd(["make", "-C", str(SCRIPT_DIR), "go"])
            pause()
        elif choice == "3":
            print()
            run_cmd(["make", "-C", str(SCRIPT_DIR), "folsom"])
            pause()
        elif choice == "4":
            print()
            run_cmd(["make", "-C", str(SCRIPT_DIR), "freeland"])
            pause()
        elif choice == "b":
            break


# ============================================================================
# Antenna Comparison
# ============================================================================

def menu_antenna():
    while True:
        print_header("Antenna Comparison")
        print("""Use Case: Compare performance of different antennas.

This tool helps you scientifically compare antennas by:
1. Defining your antennas with labels (A, B, etc.)
2. Starting a timed session (captures solar conditions)
3. Switching between antennas during the session
4. Analyzing which antenna hears stations better (by band and direction)

For valid comparison, switch antennas every 10-15 minutes within a session
to minimize propagation variation.
""")
        print_menu([
            ("1", "Show current solar/propagation conditions"),
            ("2", "Define or update an antenna"),
            ("3", "List defined antennas"),
            ("4", "Start a comparison session"),
            ("5", "Mark antenna switch (use antenna)"),
            ("6", "Stop session"),
            ("7", "Analyze session results"),
            ("8", "View session log"),
            ("9", "Clear session log"),
            ("b", "Back to main menu"),
        ])

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "solar"])
            pause()
        elif choice == "2":
            print()
            label = get_input("Antenna label (e.g., A, B, dipole)")
            if label:
                desc = get_input("Description (e.g., 40m EFHW, NW corner, 30ft)")
                if desc:
                    run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "define", label, desc])
            pause()
        elif choice == "3":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "list"])
            pause()
        elif choice == "4":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "start"])
            pause()
        elif choice == "5":
            print()
            # Show available antennas first
            print("Available antennas:")
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "list"])
            print()
            label = get_input("Which antenna are you switching to?")
            if label:
                run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "use", label])
            pause()
        elif choice == "6":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "stop"])
            pause()
        elif choice == "7":
            print()
            grid = get_input("Your gridsquare", "CM98kq")
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "analyze", grid])
            pause()
        elif choice == "8":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "log"])
            pause()
        elif choice == "9":
            print()
            confirm = get_input("Clear session log? (yes/no)", "no")
            if confirm.lower() == "yes":
                run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "clear"])
            pause()
        elif choice == "b":
            break


# ============================================================================
# Time-of-Day Analysis
# ============================================================================

def menu_tod():
    while True:
        print_header("Time-of-Day Analysis")
        print("""Use Case: Compare propagation at different times of day.

This analyzes your ALL.TXT across multiple days to find patterns like:
- Which bands work better in the morning vs evening?
- Do certain directions favor certain times?

Unlike antenna comparison (which uses a single session), this aggregates
data across all your logged activity to find time-based patterns.

Examples:
- Compare sunrise (06:00-09:00) vs sunset (18:00-21:00)
- Compare morning (08:00-12:00) vs afternoon (14:00-18:00)
- Compare late night (22:00-02:00) vs early morning (05:00-08:00)
""")
        print_menu([
            ("1", "Show current solar conditions"),
            ("2", "Run time-of-day comparison"),
            ("b", "Back to main menu"),
        ])

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "solar"])
            pause()
        elif choice == "2":
            print()
            print("Enter time ranges in HH:MM-HH:MM format")
            print("Example: 06:00-09:00 for 6am to 9am")
            print()
            range1 = get_input("First time range (e.g., 06:00-09:00)")
            range2 = get_input("Second time range (e.g., 18:00-21:00)")
            if range1 and range2:
                grid = get_input("Your gridsquare", "CM98kq")
                print()
                run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "tod", range1, range2, grid])
            pause()
        elif choice == "b":
            break


# ============================================================================
# Main Menu
# ============================================================================

# ============================================================================
# WSJT-X Control
# ============================================================================

def menu_wsjtx():
    while True:
        print_header("WSJT-X Remote Control")
        print("""Use Case: Control WSJT-X on Windows from WSL2 via UDP.

Requirements:
- WSJT-X: File -> Settings -> Reporting
- Check "Accept UDP requests"
- Set UDP Server to 0.0.0.0 (to accept from WSL2)
- UDP Server port: 2237

For band switching, create WSJT-X configurations named by band
(e.g., '20m', '40m', '15m') with appropriate frequencies set.
""")
        print_menu([
            ("1", "Show connection status"),
            ("2", "Test connection (clear Band Activity)"),
            ("3", "Switch band/configuration"),
            ("4", "Set grid locator"),
            ("b", "Back to main menu"),
        ])

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "wsjtx_control.py"), "status"])
            pause()
        elif choice == "2":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "wsjtx_control.py"), "test"])
            pause()
        elif choice == "3":
            print()
            print("Enter configuration name (e.g., '20m', '40m', or custom name)")
            config = get_input("Configuration name")
            if config:
                run_cmd(["python3", str(SCRIPT_DIR / "wsjtx_control.py"), "switch", config])
            pause()
        elif choice == "4":
            print()
            grid = get_input("Grid locator (e.g., CM98kq)")
            if grid:
                run_cmd(["python3", str(SCRIPT_DIR / "wsjtx_control.py"), "grid", grid])
            pause()
        elif choice == "b":
            break


def main_menu():
    while True:
        print_header("Main Menu")
        print("""Welcome! This tool helps you:
- Manage QRZ profile and logs when operating from multiple locations
- Compare antenna performance scientifically
- Analyze propagation patterns by time of day
- Control WSJT-X remotely from WSL2
""")
        print_menu([
            ("1", "QRZ & Log Management - profile sync, log splitting"),
            ("2", "Antenna Comparison - A/B test your antennas"),
            ("3", "Time-of-Day Analysis - find propagation patterns"),
            ("4", "Solar Conditions - current HF propagation"),
            ("5", "WSJT-X Control - band switching, grid sync"),
            ("q", "Quit"),
        ])

        choice = input("Choice: ").strip().lower()

        if choice == "1":
            menu_qrz()
        elif choice == "2":
            menu_antenna()
        elif choice == "3":
            menu_tod()
        elif choice == "4":
            print()
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py"), "solar"])
            pause()
        elif choice == "5":
            menu_wsjtx()
        elif choice == "q":
            clear_screen()
            print("73!")
            break


def main():
    if len(sys.argv) > 1:
        # Direct command passthrough
        cmd = sys.argv[1].lower()
        if cmd in ("check", "go", "folsom", "freeland"):
            run_cmd(["make", "-C", str(SCRIPT_DIR), cmd])
        else:
            run_cmd(["python3", str(SCRIPT_DIR / "antenna.py")] + sys.argv[1:])
    else:
        try:
            main_menu()
        except KeyboardInterrupt:
            print("\n73!")


if __name__ == "__main__":
    main()
