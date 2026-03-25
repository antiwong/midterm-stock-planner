#!/bin/bash
# Called by systemd OnFailure or cron error trap
# Usage: notify_failure.sh SERVICE_NAME

SERVICE_NAME="${1:-unknown}"
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Load webhook URL
source /home/deploy/stock-planner/.env 2>/dev/null
WEBHOOK="${SLACK_WEBHOOK_URL:-$slack_webhook}"

if [ -z "$WEBHOOK" ]; then
    echo "No SLACK_WEBHOOK_URL set — cannot send failure notification"
    exit 1
fi

# Get last 20 lines of journal for this service
LAST_LOGS=$(journalctl -u "$SERVICE_NAME" -n 20 --no-pager 2>/dev/null \
            | tail -20 | sed 's/"/\\"/g' | sed 's/`/\\`/g')

# If no journal (cron job), check recent log
if [ -z "$LAST_LOGS" ]; then
    LAST_LOGS="(no journal entries — check logs/)"
fi

PAYLOAD=$(cat <<EOF
{
  "attachments": [{
    "color": "#e53935",
    "title": "❌ SYSTEMD/CRON FAILURE: ${SERVICE_NAME}",
    "text": "Service crashed or was killed by the OS.\n\`\`\`${LAST_LOGS}\`\`\`",
    "fields": [
      {"title": "Host", "value": "${HOSTNAME}", "short": true},
      {"title": "Time", "value": "${TIMESTAMP}", "short": true},
      {"title": "Service", "value": "${SERVICE_NAME}", "short": false}
    ],
    "footer": "systemd OnFailure handler"
  }]
}
EOF
)

curl -s -X POST "${WEBHOOK}" \
     -H 'Content-Type: application/json' \
     -d "${PAYLOAD}" > /dev/null

echo "Failure notification sent for ${SERVICE_NAME}"
