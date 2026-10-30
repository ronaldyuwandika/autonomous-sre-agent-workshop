#!/usr/bin/env bash
# Fallback when the real alert is slow: publish a sample incident to the topic.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
ID="manual-$(date +%s)"
MSG=$(sed "s/manual-demo-001/$ID/" alerting/sample-alert.json | tr -d '\n')
gcloud pubsub topics publish "$TOPIC" --message "$MSG"
echo "Published incident $ID. Check: scripts/incidents.sh"
