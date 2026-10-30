#!/usr/bin/env bash
# Lab 3b: deploy the agent service (private) and push alerts to it.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')

# --no-cpu-throttling: the agent keeps working after Pub/Sub gets its 204.
# --max-instances 1: incidents live in memory (workshop only).
gcloud run deploy "$AGENT_SERVICE" --source . --region "$REGION" \
  --service-account "$AGENT_SA" --no-allow-unauthenticated \
  --max-instances 1 --no-cpu-throttling --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,REGION=$REGION,GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_LOCATION=$GEMINI_LOCATION,ALLOWED_SERVICES=$APP_SERVICE,DEFAULT_SERVICE=$APP_SERVICE" \
  --quiet

URL=$(gcloud run services describe "$AGENT_SERVICE" --region "$REGION" --format 'value(status.url)')

# Only the push identity may invoke the agent (plus you, as project owner).
gcloud run services add-iam-policy-binding "$AGENT_SERVICE" --region "$REGION" \
  --member "serviceAccount:$PUSH_SA" --role roles/run.invoker --quiet >/dev/null
# Lets Pub/Sub mint OIDC tokens for the push identity (needed on older projects).
gcloud iam service-accounts add-iam-policy-binding "$PUSH_SA" \
  --member "serviceAccount:service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role roles/iam.serviceAccountTokenCreator --quiet >/dev/null

if ! gcloud pubsub subscriptions describe "$TOPIC-push" >/dev/null 2>&1; then
  gcloud pubsub subscriptions create "$TOPIC-push" --topic "$TOPIC" \
    --push-endpoint "$URL/pubsub" --push-auth-service-account "$PUSH_SA" --ack-deadline 60
fi
echo "Agent: $URL  (private; use scripts/incidents.sh)"
