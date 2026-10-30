#!/usr/bin/env bash
# Send N checkout requests (default 200) and print the status-code mix.
set -euo pipefail
source "$(dirname "$0")/env.sh"
N="${1:-200}"
URL=$(gcloud run services describe "$APP_SERVICE" --region "$REGION" --format 'value(status.url)')
echo "==> $N requests to $URL/checkout"
for _ in $(seq "$N"); do
  curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL/checkout" -H 'Content-Type: application/json' -d '{"amount":150000}'
done | sort | uniq -c
