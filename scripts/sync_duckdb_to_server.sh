#!/bin/bash
# Sync DuckDB from Mac to Hetzner server (atomic replace)
# Cron: */30 * * * * ~/code/midterm-stock-planner/scripts/sync_duckdb_to_server.sh

DB_PATH="$HOME/code/midterm-stock-planner/data/sentimentpulse.db"
SERVER="deploy@178.156.173.199"
REMOTE_DIR="~/stock-planner/data"
REMOTE_PATH="${REMOTE_DIR}/sentimentpulse.db"
REMOTE_TMP="${REMOTE_DIR}/.sentimentpulse.db.tmp"
LOG="$HOME/code/midterm-stock-planner/data/sync.log"
SP_DIR="$HOME/.openclaw/workspace/projects/sentimental_blogs"
WEBHOOK_URL=""

# Load webhook URL from .env
if [ -f "$SP_DIR/.env" ]; then
    WEBHOOK_URL=$(grep -E "^slack_webhook=" "$SP_DIR/.env" | head -1 | cut -d= -f2- | tr -d '"')
fi

send_slack() {
    local level="$1"
    local msg="$2"
    if [ -n "$WEBHOOK_URL" ]; then
        local emoji=":warning:"
        [ "$level" = "error" ] && emoji=":x:"
        [ "$level" = "success" ] && emoji=":white_check_mark:"
        curl -s -X POST "$WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"[sen-pulse] ${emoji} *DuckDB Sync*: ${msg}\"}" \
            > /dev/null 2>&1
    fi
}

log_msg() {
    echo "$(date +%Y-%m-%dT%H:%M:%S) $1" >> "$LOG"
}

log_msg "Syncing sentimentpulse.db to server..."

# Check DB exists
if [ ! -f "$DB_PATH" ]; then
    log_msg "ERROR: $DB_PATH not found"
    send_slack "error" "DB file not found at \`$DB_PATH\`"
    exit 1
fi

# Check DB not empty (minimum 100KB = has actual data)
DB_SIZE=$(stat -f%z "$DB_PATH" 2>/dev/null || stat --format=%s "$DB_PATH" 2>/dev/null)
if [ "${DB_SIZE:-0}" -lt 102400 ]; then
    log_msg "WARNING: DB suspiciously small (${DB_SIZE} bytes) — skipping sync"
    send_slack "warning" "DB file only ${DB_SIZE} bytes — skipping sync to avoid pushing empty DB"
    exit 1
fi

# Check SSH connectivity (5s timeout)
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SERVER" "true" 2>/dev/null; then
    log_msg "ERROR: Cannot reach $SERVER"
    send_slack "error" "Cannot SSH to Hetzner (\`$SERVER\`) — sync failed"
    exit 1
fi

# Sync to temp file first, then atomic rename
# This prevents the API from reading a partially-written file
if rsync -az --checksum "$DB_PATH" "$SERVER:$REMOTE_TMP" 2>> "$LOG"; then
    # Atomic rename on server (mv is atomic on same filesystem)
    ssh "$SERVER" "mv -f $REMOTE_TMP $REMOTE_PATH" 2>> "$LOG"
    DB_HUMAN=$(du -h "$DB_PATH" | cut -f1)
    log_msg "Sync complete ($DB_HUMAN) — atomic replace"
else
    RSYNC_EXIT=$?
    log_msg "ERROR: rsync failed with exit code $RSYNC_EXIT"
    send_slack "error" "rsync to Hetzner failed (exit code $RSYNC_EXIT)"
    # Clean up temp file on failure
    ssh "$SERVER" "rm -f $REMOTE_TMP" 2>/dev/null
    exit 1
fi

# Verify remote file exists and has similar size
REMOTE_SIZE=$(ssh -o ConnectTimeout=5 "$SERVER" "stat --format=%s $REMOTE_PATH 2>/dev/null || echo 0")
SIZE_DIFF=$((DB_SIZE - REMOTE_SIZE))
if [ "${SIZE_DIFF#-}" -gt 1048576 ]; then
    # More than 1MB difference — something's wrong
    log_msg "WARNING: Size mismatch — local=${DB_SIZE} remote=${REMOTE_SIZE}"
    send_slack "warning" "Size mismatch after sync: local=${DB_SIZE} remote=${REMOTE_SIZE}"
fi
