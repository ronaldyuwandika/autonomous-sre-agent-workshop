#!/usr/bin/env bash
# Lab 4 fallback: CPU / memory saturation alert on checkout to the same Pub/Sub channel.
# (The agent step generates this with the cloud-run-alert-configuration skill instead.)
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
CHANNEL=$(gcloud beta monitoring channels list --filter "displayName=\"$TOPIC\"" --format 'value(name)' | head -1)
[ -n "$CHANNEL" ] || { echo "No '$TOPIC' channel yet: run 03-alerting.sh (or the Lab 3 agent step) first." >&2; exit 1; }
TMP=$(mktemp)
sed "s#__CHANNEL__#$CHANNEL#" alerting/saturation-policy.json > "$TMP"
gcloud monitoring policies create --policy-from-file "$TMP"
rm -f "$TMP"
