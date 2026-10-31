#!/usr/bin/env bash
# Preflight for any machine (macOS, Linux, WSL, Cloud Shell): checks tools and versions, changes nothing.
#   ./scripts/check-env.sh
set -uo pipefail
fail=0
ok()   { printf '  ok    %s\n' "$1"; }
bad()  { printf '  FIX   %s\n' "$1"; fail=1; }
warn() { printf '  note  %s\n' "$1"; }

echo "==> Required"
command -v gcloud >/dev/null && ok "gcloud $(gcloud version 2>/dev/null | head -1 | awk '{print $NF}')" || bad "gcloud missing: https://cloud.google.com/sdk/docs/install"
if command -v python3 >/dev/null && python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  ok "python $(python3 -V 2>&1 | awk '{print $2}')"
else bad "Python 3.11+ needed for google-adk 2.13 (found: $(python3 -V 2>&1 || echo none))"; fi
python3 -c 'import venv' 2>/dev/null && ok "python venv module" || bad "python venv missing (Ubuntu/WSL: sudo apt install -y python3-venv)"
command -v curl >/dev/null && ok "curl" || bad "curl missing"
PROJECT=$(gcloud config get-value project 2>/dev/null)
[ -n "$PROJECT" ] && ok "project $PROJECT" || bad "no project: gcloud config set project <id>"
gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q . && ok "gcloud login" || bad "not logged in: gcloud auth login"
gcloud auth application-default print-access-token >/dev/null 2>&1 && ok "application default credentials (adk web)" || bad "no ADC for adk web: gcloud auth application-default login"
for s in scripts/*.sh; do [ -x "$s" ] || { bad "$s not executable: chmod +x scripts/*.sh"; break; }; done
grep -l $'\r' scripts/*.sh >/dev/null 2>&1 && bad "Windows line endings in scripts: clone inside WSL, or run: sed -i 's/\r$//' scripts/*.sh"

echo "==> For the agent steps (Antigravity CLI + Agent Skills)"
command -v agy >/dev/null && ok "Antigravity CLI (agy)" || warn "agy not found: install it, or use each lab's fallback script"
if command -v node >/dev/null && node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=20)?0:1)'; then
  ok "node $(node -v)"
else warn "Node 22.20+ needed for 'npx skills' (found: $(node -v 2>/dev/null || echo none)); nvm install --lts"; fi
if command -v npx >/dev/null && [ "$(npx --version 2>/dev/null)" != "$(npm --version 2>/dev/null)" ]; then
  warn "stale npx on PATH ($(command -v npx)): npm uninstall -g npx"; fi
command -v terraform >/dev/null && ok "terraform $(terraform version 2>/dev/null | head -1 | awk '{print $2}')" || warn "terraform not found: Lab 3/4 agent steps need it (fallback scripts don't)"

[ "$fail" = 0 ] && echo "Ready." || { echo "Fix the FIX lines above, then run this again."; exit 1; }
