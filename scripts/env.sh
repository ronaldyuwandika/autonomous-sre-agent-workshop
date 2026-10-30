# Shared settings. Sourced by every script; override any value by exporting it first.
export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-asia-southeast2}"            # Jakarta
export GEMINI_LOCATION="${GEMINI_LOCATION:-us-central1}"
export APP_SERVICE="${APP_SERVICE:-checkout}"
export AGENT_SERVICE="${AGENT_SERVICE:-sre-agent}"
export TOPIC="${TOPIC:-sre-alerts}"
export APP_SA="checkout-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export AGENT_SA="sre-agent@${PROJECT_ID}.iam.gserviceaccount.com"
export PUSH_SA="pubsub-pusher@${PROJECT_ID}.iam.gserviceaccount.com"
if [ -z "$PROJECT_ID" ]; then echo "Set a project: gcloud config set project <id>" >&2; exit 1; fi
