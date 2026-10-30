#!/usr/bin/env bash
# Pre-workshop: give Antigravity CLI the Google Agent Skills used in the labs.
# Sources: github.com/google/skills and github.com/google/agents-cli
set -euo pipefail
source "$(dirname "$0")/env.sh"

command -v agy >/dev/null || { echo "Antigravity CLI (agy) not found: install it from https://antigravity.google/ first." >&2; exit 1; }
command -v npx >/dev/null || { echo "npx not found: install Node.js first." >&2; exit 1; }

echo "==> Google Cloud Developer plugin (gcloud, IAM, onboarding, Developer Knowledge MCP)"
agy plugin install https://github.com/google/skills/plugins/cloud/google-cloud-developer
gcloud services enable developerknowledge.googleapis.com --project "$PROJECT_ID"

echo "==> Google Cloud skills. When prompted, choose Antigravity CLI as the target agent"
echo "# tick cloud-run-*, cloud-monitoring-*, cloud-logging-query-generation (google-cloud-slo-alert-configuration for the bonus)"
npx skills add google/skills

echo "==> ADK skills from agents-cli. Same target agent; tick google-agents-cli-adk-code"
npx skills add google/agents-cli

echo "Done. Start Antigravity CLI in this folder: agy"
