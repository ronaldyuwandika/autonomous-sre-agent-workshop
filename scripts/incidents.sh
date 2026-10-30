#!/usr/bin/env bash
# List incidents, or approve/reject one (you must be in APPROVER_EMAILS; Slack buttons do the same).
#   scripts/incidents.sh                    # list
#   scripts/incidents.sh approve <id>       # executes the proposed rollback
#   scripts/incidents.sh reject  <id> "why"
set -euo pipefail
source "$(dirname "$0")/env.sh"
URL=$(gcloud run services describe "$AGENT_SERVICE" --region "$REGION" --format 'value(status.url)')
TOKEN=$(gcloud auth print-identity-token)
case "${1:-list}" in
  list) curl -sf -H "Authorization: Bearer $TOKEN" "$URL/incidents" | python3 -m json.tool ;;
  approve|reject)
    [ -n "${2:-}" ] || { echo "usage: $0 $1 <incident_id>" >&2; exit 1; }
    BODY=$(python3 -c 'import json,sys; print(json.dumps({"note": sys.argv[1]}))' "${3:-}")
    curl -sf -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      -d "$BODY" "$URL/incidents/$2/$1" | python3 -m json.tool ;;
  *) echo "usage: $0 [list|approve <id>|reject <id> [note]]" >&2; exit 1 ;;
esac
