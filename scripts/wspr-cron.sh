#!/bin/bash
# WSPR beacon band rotation script
# Simple UTC-based rotation - keeps it predictable and doesn't need sunrise calculations
# Run from cron every 2 hours to rotate through bands

WSPR_DIR="$HOME/work/ak6mj-hf-propagation"
cd "$WSPR_DIR" || exit 1

# Get current UTC hour (WSPR uses UTC)
HOUR=$(date -u +%H)

# Simple rotation based on UTC hour (changes every 2 hours)
# This provides good coverage without needing sunrise calculations
# Pattern optimized for general propagation (not location-specific)

case $((HOUR / 2)) in
    0)  BAND="80m" ;;   # 00-01 UTC
    1)  BAND="40m" ;;   # 02-03 UTC
    2)  BAND="40m" ;;   # 04-05 UTC
    3)  BAND="30m" ;;   # 06-07 UTC
    4)  BAND="20m" ;;   # 08-09 UTC
    5)  BAND="20m" ;;   # 10-11 UTC
    6)  BAND="17m" ;;   # 12-13 UTC
    7)  BAND="15m" ;;   # 14-15 UTC
    8)  BAND="20m" ;;   # 16-17 UTC
    9)  BAND="20m" ;;   # 18-19 UTC
    10) BAND="30m" ;;   # 20-21 UTC
    11) BAND="40m" ;;   # 22-23 UTC
    *)  BAND="40m" ;;   # Fallback
esac

# Log band change
mkdir -p "$WSPR_DIR/local/logs"
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Switching to $BAND (UTC hour $HOUR)" >> "$WSPR_DIR/local/logs/band-rotation.log"

# Switch band (use make to get OS-aware device detection)
cd "$WSPR_DIR" && make "$BAND" 2>&1 | head -20 >> "$WSPR_DIR/local/logs/band-rotation.log"
echo "" >> "$WSPR_DIR/local/logs/band-rotation.log"
