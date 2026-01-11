#!/bin/bash
# WSPR beacon band rotation script
# Simple UTC-based rotation - keeps it predictable and doesn't need sunrise calculations
# Run from cron every 2 hours to rotate through bands
# Idempotent: Only switches band if not already on the target band

WSPR_DIR="$HOME/work/ak6mj-hf-propagation"
cd "$WSPR_DIR" || exit 1

# Get current UTC hour (WSPR uses UTC)
HOUR=$(date -u +%H)

# Simple rotation based on UTC hour (changes every 2 hours)
# This provides good coverage without needing sunrise calculations
# Pattern optimized for general propagation (not location-specific)

case $((HOUR / 2)) in
    0)  BAND="40m" ;;   # 00-01 UTC = 4-5pm PST (sunset transition)
    1)  BAND="40m" ;;   # 02-03 UTC = 6-7pm PST (evening)
    2)  BAND="40m" ;;   # 04-05 UTC = 8-9pm PST (night)
    3)  BAND="80m" ;;   # 06-07 UTC = 10-11pm PST (late night, 80m opens)
    4)  BAND="80m" ;;   # 08-09 UTC = 12-1am PST (graveyard)
    5)  BAND="80m" ;;   # 10-11 UTC = 2-3am PST (deep night)
    6)  BAND="40m" ;;   # 12-13 UTC = 4-5am PST (pre-dawn)
    7)  BAND="40m" ;;   # 14-15 UTC = 6-7am PST (sunrise)
    8)  BAND="20m" ;;   # 16-17 UTC = 8-9am PST (morning, 20m opens)
    9)  BAND="15m" ;;   # 18-19 UTC = 10-11am PST (15m peak, solar max)
    10) BAND="15m" ;;   # 20-21 UTC = 12-1pm PST (midday, best antenna perf)
    11) BAND="10m" ;;   # 22-23 UTC = 2-3pm PST (afternoon, 10m good at solar max)
    *)  BAND="40m" ;;   # Fallback
esac

# Band frequencies for comparison
declare -A FREQS=(
    ["160m"]=1838100
    ["80m"]=3570100
    ["40m"]=7040100
    ["30m"]=10140200
    ["20m"]=14097100
    ["17m"]=18106100
    ["15m"]=21096100
    ["12m"]=24926100
    ["10m"]=28126100
    ["6m"]=50294500
)

TARGET_FREQ=${FREQS[$BAND]}

# Check current band by monitoring serial output for TX: line
# TX line format: "TX:AK6MJ CM98 23 7040100 DONE"
mkdir -p "$WSPR_DIR/local/logs"
LOG="$WSPR_DIR/local/logs/band-rotation.log"

# Get current frequency from beacon (wait max 5 seconds for a line)
# Use timeout to avoid hanging if beacon is unresponsive
CURRENT_STATUS=$(timeout 5 make monitor 2>/dev/null | head -1)

if [[ "$CURRENT_STATUS" =~ TX:.*[[:space:]]([0-9]+)[[:space:]]DONE ]]; then
    CURRENT_FREQ="${BASH_REMATCH[1]}"

    if [ "$CURRENT_FREQ" = "$TARGET_FREQ" ]; then
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Already on $BAND ($TARGET_FREQ Hz), no change needed" >> "$LOG"
        exit 0
    fi

    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Switching from ${CURRENT_FREQ}Hz to $BAND ($TARGET_FREQ Hz) (UTC hour $HOUR)" >> "$LOG"
else
    # Couldn't determine current band (beacon might be transmitting), switch anyway
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Could not determine current band, switching to $BAND (UTC hour $HOUR)" >> "$LOG"
fi

# Switch band (use make to get OS-aware device detection)
make "$BAND" 2>&1 | head -20 >> "$LOG"
echo "" >> "$LOG"
