# Context for coding agents (Antigravity CLI and others)

This repo is a 90-minute workshop: an SRE agent built with Google ADK + Gemini
that diagnoses a broken Cloud Run service and rolls it back after a human approves.

## Layout

- `app/` — the checkout API (Flask) that gets broken on purpose.
- `agent/sre_agent/` — ADK agents and tools (`tools.py`, `agent.py`).
- `service/` — Lab 3 alert service (Pub/Sub push → agent → approval endpoints).
- `scripts/` — one script per lab step; `scripts/env.sh` holds shared names.
- `prompts/` — the prompts participants give you, one file per lab.

## Rules for you

- Prefer the installed Google Agent Skills (`gcloud`, `cloud-run-*`,
  `cloud-logging-query-generation`, `cloud-monitoring-*`, `google-agents-cli-*`)
  over guessing commands or APIs.
- Read-only by default. Before any command that creates, changes or deletes a
  Google Cloud resource, show the exact command or Terraform plan and wait for
  the user to say yes.
- Never print, log or commit credentials or API keys.
- Resource names must match `scripts/env.sh` (service `checkout`, topic
  `sre-alerts`, service accounts `checkout-runtime`, `sre-agent`, `pubsub-pusher`)
  so the lab scripts keep working.
- Don't weaken the agent's guardrails in `agent/sre_agent/tools.py`
  (allow-list, revision check, human confirmation).
- Put generated Terraform under `alerting/terraform/`.
