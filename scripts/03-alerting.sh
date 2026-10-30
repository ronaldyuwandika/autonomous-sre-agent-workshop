#!/usr/bin/env bash
# Lab 3a: Pub/Sub topic + notification channel + alert policy on checkout 5xx.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$(dirname "$0")/.."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')

gcloud pubsub topics describe "$TOPIC" >/dev/null 2>&1 || gcloud pubsub topics create "$TOPIC"

CHANNEL=$(gcloud beta monitoring channels list --filter "displayName=\"$TOPIC\"" --format 'value(name)' | head -1)
if [ -z "$CHANNEL" ]; then
  CHANNEL=$(gcloud beta monitoring channels create --display-name "$TOPIC" --type pubsub \
    --channel-labels "topic=projects/$PROJECT_ID/topics/$TOPIC" --format 'value(name)')
fi
echo "Channel: $CHANNEL"

# Cloud Monitoring's notification agent must be allowed to publish to the topic.
gcloud pubsub topics add-iam-policy-binding "$TOPIC" \
  --member "serviceAccount:service-$PROJECT_NUMBER@gcp-sa-monitoring-notification.iam.gserviceaccount.com" \
  --role roles/pubsub.publisher --quiet >/dev/null

TMP=$(mktemp)
sed "s#__CHANNEL__#$CHANNEL#" alerting/policy.json > "$TMP"
gcloud monitoring policies create --policy-from-file "$TMP"
rm -f "$TMP"
echo "Alert policy created. Metric alerts can take 2-4 minutes to fire."
