#!/usr/bin/env bash
# Sync FT8 data from hamtop1 to www server
#
# This script runs on www and pulls ALL.TXT from hamtop1 via rsync over SSH.
# Designed to run via cron every 15-30 minutes.
#
# Setup on www:
#   1. Ensure SSH access to hamtop1 is configured (see HAMTOP1_SSH_SETUP.md)
#   2. Test manually: rsync -avz hamtop1:/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT /tmp/
#   3. Install in crontab: */15 * * * * /var/www/hf-tools/scripts/sync_from_hamtop1.sh
#
# Logs to syslog with tag "ft8-sync"

set -euo pipefail

# Configuration
HAMTOP1_HOST="hamtop1"  # From ~/.ssh/config
HAMTOP1_PATH="/mnt/c/Users/admin/AppData/Local/WSJT-X/ALL.TXT"
LOCAL_DIR="/var/www/local/ft8-tools"
LOG_TAG="ft8-sync"

# Ensure local directory exists
mkdir -p "$LOCAL_DIR"

# Log function
log() {
    echo "$@" | logger -t "$LOG_TAG"
    echo "[$(date -Iseconds)] $@"
}

# Check if hamtop1 is reachable
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$HAMTOP1_HOST" true 2>/dev/null; then
    log "ERROR: Cannot connect to $HAMTOP1_HOST"
    exit 1
fi

# Sync ALL.TXT
log "Starting sync from $HAMTOP1_HOST..."

if rsync -avz --timeout=60 \
    "$HAMTOP1_HOST:$HAMTOP1_PATH" \
    "$LOCAL_DIR/" 2>&1 | logger -t "$LOG_TAG"; then

    # Get file info
    if [ -f "$LOCAL_DIR/ALL.TXT" ]; then
        SIZE=$(stat -f%z "$LOCAL_DIR/ALL.TXT" 2>/dev/null || stat -c%s "$LOCAL_DIR/ALL.TXT" 2>/dev/null)
        LINES=$(wc -l < "$LOCAL_DIR/ALL.TXT")
        log "SUCCESS: Synced ALL.TXT ($SIZE bytes, $LINES lines)"
    else
        log "WARNING: Sync completed but file not found"
    fi
else
    log "ERROR: rsync failed"
    exit 1
fi

# Optional: Also sync any analysis/comparison results back to hamtop1
# Uncomment to enable bidirectional sync
# rsync -avz --timeout=60 \
#     "$LOCAL_DIR/comparisons/" \
#     "$HAMTOP1_HOST:/mnt/c/Users/admin/wspr-results/" 2>&1 | logger -t "$LOG_TAG"

log "Sync completed successfully"
