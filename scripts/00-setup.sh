#!/usr/bin/env bash
# Lab 0: enable APIs, create service accounts, deploy a healthy checkout (v1).
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."

echo "==> Enabling APIs in $PROJECT_ID"
gcloud services enable run.googleapis.com aiplatform.googleapis.com pubsub.googleapis.com \
  monitoring.googleapis.com logging.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com iam.googleapis.com

echo "==> Service accounts"
for sa in checkout-runtime sre-agent pubsub-pusher; do
  gcloud iam service-accounts describe "$sa@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1 \
    || gcloud iam service-accounts create "$sa" --display-name "$sa"
done

echo "==> Read-only project roles for the agent (least privilege)"
for role in roles/logging.viewer roles/monitoring.viewer roles/run.viewer roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$AGENT_SA" \
    --role "$role" --condition=None --quiet >/dev/null
done

echo "==> Deploying healthy $APP_SERVICE (v1)"
gcloud run deploy "$APP_SERVICE" --source ./app --region "$REGION" \
  --service-account "$APP_SA" --allow-unauthenticated --max-instances 3 \
  --set-env-vars FAILURE_RATE=0,APP_VERSION=v1 --quiet

echo "==> Agent may change traffic on $APP_SERVICE only"
gcloud run services add-iam-policy-binding "$APP_SERVICE" --region "$REGION" \
  --member "serviceAccount:$AGENT_SA" --role roles/run.developer --quiet >/dev/null
# Updating a Cloud Run service requires actAs on its runtime service account.
gcloud iam service-accounts add-iam-policy-binding "$APP_SA" \
  --member "serviceAccount:$AGENT_SA" --role roles/iam.serviceAccountUser --quiet >/dev/null

URL=$(gcloud run services describe "$APP_SERVICE" --region "$REGION" --format 'value(status.url)')
echo "Done. Try: curl $URL/checkout"
