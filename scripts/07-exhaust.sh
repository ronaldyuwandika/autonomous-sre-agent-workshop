#!/usr/bin/env bash
# Lab 4: ship a healthy but hungry revision with tight limits, then flood it.
# Each checkout burns ~300 ms of CPU; 1 vCPU, 2 instances, concurrency 4 saturate fast.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
gcloud run deploy "$APP_SERVICE" --source ./app --region "$REGION" \
  --service-account "$APP_SA" --allow-unauthenticated \
  --cpu 1 --memory 512Mi --max-instances 2 --concurrency 4 \
  --set-env-vars FAILURE_RATE=0,APP_VERSION=v3,BURN_MS=300 --quiet
# The scale tool only acts when traffic follows the latest revision (Labs 2-3 pinned it).
gcloud run services update-traffic "$APP_SERVICE" --region "$REGION" --to-latest --quiet

N="${1:-1500}"; P="${2:-40}"
URL=$(gcloud run services describe "$APP_SERVICE" --region "$REGION" --format 'value(status.url)')
echo "==> $N requests, $P in parallel, to $URL/checkout"
seq "$N" | xargs -P "$P" -I{} curl -s -o /dev/null -w '%{http_code}\n' -X POST "$URL/checkout" | sort | uniq -c
