#!/usr/bin/env bash
# Ship a bad release (v2) that fails ~50% of checkouts, then send traffic to it.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
gcloud run deploy "$APP_SERVICE" --source ./app --region "$REGION" \
  --service-account "$APP_SA" --allow-unauthenticated --max-instances 3 \
  --set-env-vars FAILURE_RATE=0.5,APP_VERSION=v2 --quiet
"$(dirname "$0")/02-load.sh" "${1:-200}"
