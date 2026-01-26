#!/bin/bash
# WSPR beacon band rotation script - Stochastic version
# 20-minute slots with time-appropriate band pools
# Run from cron every 20 minutes: */20 * * * *
# Rotates through bands frequently to catch band openings
# Idempotent: Only switches band if not already on the target band

# Set PATH for cron environment (uv is typically in ~/.local/bin)
export PATH="$HOME/.local/bin:$PATH"

WSPR_DIR="$HOME/work/ak6mj-hf-propagation"
cd "$WSPR_DIR" || exit 1

# Get current UTC time
# Strip leading zeros to avoid octal interpretation
HOUR=$(date -u +%H | sed 's/^0//')
MINUTE=$(date -u +%M | sed 's/^0*//')
DAY_OF_YEAR=$(date -u +%j | sed 's/^0*//')

# Handle empty minute (00 becomes empty after sed)
[ -z "$MINUTE" ] && MINUTE=0

# Calculate 20-minute slot within hour (0, 1, or 2)
SLOT_IN_HOUR=$((MINUTE / 20))

# Define band pools for different times of day
# Night:      40m, 80m, 30m (lower bands propagate at night)
# Transition: 20m, 40m, 30m (sunrise/sunset, mixed conditions)
# Day:        10m, 15m, 20m, 17m (higher bands for daytime skip)

NIGHT_BANDS=("40m" "80m" "30m")
TRANSITION_BANDS=("20m" "40m" "30m")
DAY_BANDS=("10m" "15m" "20m" "17m")

# Select pool based on UTC hour
# UTC 04-12 = PST 8pm-4am (night)
# UTC 12-16 = PST 4-8am (sunrise transition)
# UTC 16-24 = PST 8am-4pm (day)
# UTC 00-04 = PST 4-8pm (sunset transition)

if [ "$HOUR" -ge 4 ] && [ "$HOUR" -lt 12 ]; then
    POOL=("${NIGHT_BANDS[@]}")
    POOL_NAME="night"
elif [ "$HOUR" -ge 12 ] && [ "$HOUR" -lt 16 ]; then
    POOL=("${TRANSITION_BANDS[@]}")
    POOL_NAME="sunrise"
elif [ "$HOUR" -ge 16 ] && [ "$HOUR" -lt 24 ]; then
    POOL=("${DAY_BANDS[@]}")
    POOL_NAME="day"
else
    # 00-04 UTC
    POOL=("${TRANSITION_BANDS[@]}")
    POOL_NAME="sunset"
fi

# Rotate through pool, using day-of-year to shuffle the starting point
# This ensures variety across days while cycling through all bands in pool
POOL_SIZE=${#POOL[@]}
INDEX=$(( (DAY_OF_YEAR + HOUR * 3 + SLOT_IN_HOUR) % POOL_SIZE ))
BAND=${POOL[$INDEX]}

# Sanity check: ensure BAND is set
if [ -z "$BAND" ]; then
    mkdir -p "$WSPR_DIR/local/logs"
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - ERROR: BAND variable is empty (HOUR=$HOUR)" >> "$WSPR_DIR/local/logs/band-rotation.log"
    exit 1
fi

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

# Function to write and push beacon status
write_beacon_status() {
    STATUS_FILE="$WSPR_DIR/local/wspr-data/beacon_status.json"
    mkdir -p "$(dirname "$STATUS_FILE")"
    cat > "$STATUS_FILE" << EOJSON
{
  "band": "$BAND",
  "frequency_hz": $TARGET_FREQ,
  "pool": "$POOL_NAME",
  "slot": $SLOT_IN_HOUR,
  "last_updated": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "status": "active"
}
EOJSON
    # Push status to www server (disarray -> www, not the reverse for security)
    scp -q "$STATUS_FILE" hftools@www:/var/www/local/wspr-data/beacon_status.json 2>/dev/null || true
}

if [[ "$CURRENT_STATUS" =~ TX:.*[[:space:]]([0-9]+)[[:space:]]DONE ]]; then
    CURRENT_FREQ="${BASH_REMATCH[1]}"

    if [ "$CURRENT_FREQ" = "$TARGET_FREQ" ]; then
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Already on $BAND, no change (pool=$POOL_NAME, slot=$SLOT_IN_HOUR)" >> "$LOG"
        write_beacon_status
        exit 0
    fi

    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Switching to $BAND (pool=$POOL_NAME, slot=$SLOT_IN_HOUR, from ${CURRENT_FREQ}Hz)" >> "$LOG"
else
    # Couldn't determine current band (beacon might be transmitting), switch anyway
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') - Switching to $BAND (pool=$POOL_NAME, slot=$SLOT_IN_HOUR, status unknown)" >> "$LOG"
fi

# Switch band (use make to get OS-aware device detection)
make "$BAND" 2>&1 | head -20 >> "$LOG"
echo "" >> "$LOG"

# Write and push beacon status after band switch
write_beacon_status
