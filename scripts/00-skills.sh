#!/usr/bin/env bash
# Pre-workshop: give Antigravity CLI the Google Agent Skills used in the labs.
# Sources: github.com/google/skills and github.com/google/agents-cli
set -euo pipefail
source "$(dirname "$0")/env.sh"

command -v agy >/dev/null || { echo "Antigravity CLI (agy) not found: install it from https://antigravity.google/ first." >&2; exit 1; }
command -v npx >/dev/null || { echo "npx not found: install Node.js 22.20+ first." >&2; exit 1; }

# The skills CLI needs Node >= 22.20 and a modern npx (npm 7+). An old npx (npm 6, or the
# standalone "npx" package) fails with "cb.apply is not a function" / "Install for [...] failed".
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=20)?0:1)' || {
  echo "Node $(node -v) is too old: the skills CLI needs Node 22.20 or newer." >&2
  echo "Fix: install the current Node LTS (nvm install --lts, or brew upgrade node), then re-run this script." >&2; exit 1; }
# A modern npx ships with npm and reports npm's version; anything else is a stale npx earlier on PATH.
NPM_V=$(npm --version 2>/dev/null || echo 0); NPX_V=$(npx --version 2>/dev/null || echo 0)
if [ "${NPM_V%%.*}" -lt 7 ] || [ "$NPX_V" != "$NPM_V" ]; then
  echo "Outdated npx: npx $NPX_V ($(command -v npx)), npm $NPM_V ($(command -v npm)), node $(node -v)." >&2
  echo "Fix: npm uninstall -g npx; npm install -g npm@latest; then 'which -a npx' should point next to node." >&2; exit 1
fi

echo "==> Google Cloud Developer plugin (gcloud, IAM, onboarding, Developer Knowledge MCP)"
agy plugin install https://github.com/google/skills/plugins/cloud/google-cloud-developer
gcloud services enable developerknowledge.googleapis.com --project "$PROJECT_ID"

echo "==> Google Cloud skills. When prompted, choose Antigravity CLI as the target agent"
echo "# tick cloud-run-*, cloud-monitoring-*, cloud-logging-query-generation (google-cloud-slo-alert-configuration for the bonus)"
npx skills add google/skills

echo "==> ADK skills from agents-cli. Same target agent; tick google-agents-cli-adk-code"
npx skills add google/agents-cli

echo "Done. Start Antigravity CLI in this folder: agy"
