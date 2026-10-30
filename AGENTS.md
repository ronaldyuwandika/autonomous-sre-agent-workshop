# Context for coding agents (Antigravity CLI and others)

This repo is a 90-minute workshop: an SRE agent built with Google ADK + Gemini that
diagnoses Cloud Run incidents and rolls back or scales, after a Slack approval or, for
allowed actions, on its own (AUTONOMY=auto).

## Layout

- `app/` — the checkout API (Flask) that gets broken on purpose.
- `agent/sre_agent/` — ADK agents, tools and the remediation policy (`tools.py`, `agent.py`, `policy.py`).
- `service/` — alert service (Pub/Sub push → agent → policy → auto-remediate or Slack approval; `notify.py` sends Slack/email).
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
- Don't weaken the agent's guardrails: allow-list, revision check, scale-up-only caps in
  `plan_scale`, human confirmation, the policy defaults in `policy.py`, or the caller
  checks in `service/main.py` (Pub/Sub token, approver token, Slack signature).
- Never print or commit Slack webhook URLs, signing secrets or SMTP passwords; they live
  in Secret Manager (`scripts/06-notify-secrets.sh`).
- Put generated Terraform under `alerting/terraform/`.
