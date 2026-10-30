#!/usr/bin/env bash
# Delete everything the workshop created. Asks before deleting.
set -euo pipefail
source "$(dirname "$0")/env.sh"
if [ -d "$(dirname "$0")/../alerting/terraform/.terraform" ]; then echo "Note: Lab 3 Terraform found. Run first: terraform -chdir=alerting/terraform destroy"; fi
echo "This deletes in $PROJECT_ID: Cloud Run $APP_SERVICE + $AGENT_SERVICE, Pub/Sub $TOPIC, the alert policy, channel and 3 service accounts."
read -r -p "Type the project id to confirm: " CONFIRM
[ "$CONFIRM" = "$PROJECT_ID" ] || { echo "Aborted."; exit 1; }

gcloud run services delete "$AGENT_SERVICE" --region "$REGION" --quiet || true
gcloud run services delete "$APP_SERVICE" --region "$REGION" --quiet || true
gcloud pubsub subscriptions delete "$TOPIC-push" --quiet || true
for p in $(gcloud monitoring policies list --filter 'displayName="checkout 5xx errors"' --format 'value(name)'); do
  gcloud monitoring policies delete "$p" --quiet || true
done
for c in $(gcloud beta monitoring channels list --filter "displayName=\"$TOPIC\"" --format 'value(name)'); do
  gcloud beta monitoring channels delete "$c" --force --quiet || true
done
gcloud pubsub topics delete "$TOPIC" --quiet || true
for role in roles/logging.viewer roles/run.viewer roles/aiplatform.user; do
  gcloud projects remove-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$AGENT_SA" \
    --role "$role" --condition=None --quiet >/dev/null || true
done
for sa in "$AGENT_SA" "$APP_SA" "$PUSH_SA"; do
  gcloud iam service-accounts delete "$sa" --quiet || true
done
echo "Teardown complete. Container images remain in Artifact Registry (cloud-run-source-deploy)."
