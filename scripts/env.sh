# Shared settings. Sourced by every script; override any value by exporting it first.
export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-asia-southeast2}"            # Jakarta
export GEMINI_LOCATION="${GEMINI_LOCATION:-global}"   # Vertex AI endpoint for Gemini; Cloud Run stays in REGION
export APP_SERVICE="${APP_SERVICE:-checkout}"
export AGENT_SERVICE="${AGENT_SERVICE:-sre-agent}"
export TOPIC="${TOPIC:-sre-alerts}"
export APP_SA="checkout-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export AGENT_SA="sre-agent@${PROJECT_ID}.iam.gserviceaccount.com"
export PUSH_SA="pubsub-pusher@${PROJECT_ID}.iam.gserviceaccount.com"
if [ -z "$PROJECT_ID" ]; then echo "Set a project: gcloud config set project <id>" >&2; exit 1; fi

# Remediation policy (Lab 4). approve = every change waits for a human; auto = AUTO_ACTIONS run alone.
export AUTONOMY="${AUTONOMY:-approve}"
export AUTO_ACTIONS="${AUTO_ACTIONS:-scale}"
# Hard caps the scale tool never exceeds.
export MAX_CPU="${MAX_CPU:-4}" MAX_MEMORY_MI="${MAX_MEMORY_MI:-4096}" MAX_INSTANCES_CAP="${MAX_INSTANCES_CAP:-10}"
# Who may approve: Google accounts (CLI) and Slack user IDs (buttons). Comma lists.
export APPROVER_EMAILS="${APPROVER_EMAILS:-$(gcloud config get-value account 2>/dev/null)}"
export SLACK_APPROVERS="${SLACK_APPROVERS:-}"
# Email (optional). The SMTP password lives in Secret Manager, never here.
export SMTP_HOST="${SMTP_HOST:-}" SMTP_PORT="${SMTP_PORT:-587}" SMTP_USER="${SMTP_USER:-}"
export EMAIL_FROM="${EMAIL_FROM:-$SMTP_USER}" EMAIL_TO="${EMAIL_TO:-}"
export PUSH_AUDIENCE="${PUSH_AUDIENCE:-sre-agent-pubsub}"
