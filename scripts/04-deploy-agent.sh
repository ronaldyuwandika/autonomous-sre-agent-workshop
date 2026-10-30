#!/usr/bin/env bash
# Labs 3-4: deploy the agent service and push alerts to it.
#   AUTONOMY=approve ./scripts/04-deploy-agent.sh   # every change waits for Slack/CLI approval (default)
#   AUTONOMY=auto    ./scripts/04-deploy-agent.sh   # AUTO_ACTIONS (default: scale) run alone, then report
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')

# Secrets from scripts/06-notify-secrets.sh, if you created them.
SECRETS=""
for pair in SLACK_WEBHOOK_URL=slack-webhook-url SLACK_SIGNING_SECRET=slack-signing-secret SMTP_PASSWORD=smtp-password; do
  if gcloud secrets describe "${pair#*=}" >/dev/null 2>&1; then SECRETS="${SECRETS:+$SECRETS,}$pair:latest"; fi
done

# '@' separates env vars so comma lists (approvers, recipients) survive.
ENVS="^@^GOOGLE_CLOUD_PROJECT=$PROJECT_ID@REGION=$REGION@GOOGLE_GENAI_USE_VERTEXAI=TRUE@GOOGLE_CLOUD_LOCATION=$GEMINI_LOCATION"
ENVS="$ENVS@ALLOWED_SERVICES=$APP_SERVICE@DEFAULT_SERVICE=$APP_SERVICE@AUTONOMY=$AUTONOMY@AUTO_ACTIONS=$AUTO_ACTIONS"
ENVS="$ENVS@MAX_CPU=$MAX_CPU@MAX_MEMORY_MI=$MAX_MEMORY_MI@MAX_INSTANCES_CAP=$MAX_INSTANCES_CAP"
ENVS="$ENVS@PUSH_AUDIENCE=$PUSH_AUDIENCE@PUSH_SA=$PUSH_SA@APPROVER_EMAILS=$APPROVER_EMAILS@SLACK_APPROVERS=$SLACK_APPROVERS"
ENVS="$ENVS@SMTP_HOST=$SMTP_HOST@SMTP_PORT=$SMTP_PORT@SMTP_USER=$SMTP_USER@EMAIL_FROM=$EMAIL_FROM@EMAIL_TO=$EMAIL_TO"

# Public so Slack can call /slack/actions. Every endpoint checks its caller in code:
# Pub/Sub OIDC token, approver ID token, or Slack signature (service/main.py).
# --no-cpu-throttling: the agent keeps working after Pub/Sub gets its 204.
# --max-instances 1: incidents live in memory (workshop only).
gcloud run deploy "$AGENT_SERVICE" --source . --region "$REGION" \
  --service-account "$AGENT_SA" --allow-unauthenticated \
  --max-instances 1 --no-cpu-throttling --timeout 300 \
  --set-env-vars "$ENVS" ${SECRETS:+--set-secrets "$SECRETS"} --quiet

URL=$(gcloud run services describe "$AGENT_SERVICE" --region "$REGION" --format 'value(status.url)')

# Lets Pub/Sub mint OIDC tokens for the push identity (needed on older projects).
gcloud iam service-accounts add-iam-policy-binding "$PUSH_SA" \
  --member "serviceAccount:service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role roles/iam.serviceAccountTokenCreator --quiet >/dev/null

if gcloud pubsub subscriptions describe "$TOPIC-push" >/dev/null 2>&1; then
  gcloud pubsub subscriptions update "$TOPIC-push" --push-endpoint "$URL/pubsub" \
    --push-auth-service-account "$PUSH_SA" --push-auth-token-audience "$PUSH_AUDIENCE"
else
  gcloud pubsub subscriptions create "$TOPIC-push" --topic "$TOPIC" --push-endpoint "$URL/pubsub" \
    --push-auth-service-account "$PUSH_SA" --push-auth-token-audience "$PUSH_AUDIENCE" --ack-deadline 60
fi
echo "Agent: $URL   autonomy=$AUTONOMY auto_actions=$AUTO_ACTIONS"
echo "Slack app → Interactivity → Request URL: $URL/slack/actions"
