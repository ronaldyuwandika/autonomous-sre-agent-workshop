#!/usr/bin/env bash
# Store Slack and SMTP secrets in Secret Manager (values are read silently, never echoed or logged).
# Skip any prompt with Enter to leave that secret unset. Re-run 04-deploy-agent.sh afterwards.
set -euo pipefail
source "$(dirname "$0")/env.sh"
gcloud services enable secretmanager.googleapis.com >/dev/null

store() {  # name, prompt
  local value; read -rsp "$2: " value; echo
  [ -z "$value" ] && { echo "  skipped $1"; return; }
  if gcloud secrets describe "$1" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$1" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$1" --replication-policy automatic --data-file=- >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "$1" --member "serviceAccount:$AGENT_SA" \
    --role roles/secretmanager.secretAccessor --quiet >/dev/null
  echo "  stored $1"
}
store slack-webhook-url    "Slack incoming webhook URL"
store slack-signing-secret "Slack app signing secret"
store smtp-password        "SMTP password (e.g. a Gmail app password)"
echo "Also export SLACK_APPROVERS (Slack user IDs) and SMTP_HOST/SMTP_USER/EMAIL_TO before deploying."
