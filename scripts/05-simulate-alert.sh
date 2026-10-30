#!/usr/bin/env bash
# Fallback when the real alert is slow: publish a sample incident to the topic.
#   ./scripts/05-simulate-alert.sh             # 5xx errors (Lab 3)
#   ./scripts/05-simulate-alert.sh saturation  # CPU saturation (Lab 4)
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
FILE=alerting/sample-alert.json; [ "${1:-}" = "saturation" ] && FILE=alerting/sample-saturation.json
ID="manual-$(date +%s)"
MSG=$(sed "s/manual-demo-00[12]/$ID/" "$FILE" | tr -d '\n')
gcloud pubsub topics publish "$TOPIC" --message "$MSG"
echo "Published incident $ID. Watch Slack, or: scripts/incidents.sh"
