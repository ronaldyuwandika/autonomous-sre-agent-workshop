# Can Your Cloud Fix Itself? — Autonomous SRE Agent with Google Cloud & Agent Skills

Hands-on workshop for **DevFest Cloud Surabaya 2026** (21 Nov 2026, 90 min).
You build an SRE agent with Google ADK + Gemini that finds a bad Cloud Run
revision and rolls it back **after a human approves**, and you pair with
**Antigravity CLI loaded with Google's Agent Skills** for one step in every lab.

```
checkout (Cloud Run) ──5xx──▶ Cloud Monitoring alert ──▶ Pub/Sub ──push──▶ sre-agent (Cloud Run)
        ▲                                                                       │ read-only tools:
        │                                                                       │ logs, request stats, revisions
        └──────── rollback_traffic ◀── POST /incidents/{id}/approve ◀── human ◀─┘ proposes a rollback
```

## Two agents, two jobs

| Agent | What it is | Where |
| --- | --- | --- |
| **SRE agent** | The thing you build: ADK + Gemini, runs in production | `agent/`, `service/` |
| **Coding agent** | Your pair: Antigravity CLI + Google Agent Skills, runs on your laptop | `prompts/`, `AGENTS.md` |

Each lab is hybrid: the scripts and reference code get you there reliably, and one
**agent step** (a prompt in `prompts/`) shows a skill doing real work.

| Lab | Agent step | Skills |
| --- | --- | --- |
| 0 · Deploy the patient | Check the project is ready, read-only | `gcloud` |
| 1 · An agent that can see | Generate and run the log queries the tools use | `cloud-logging-query-generation` |
| 2 · Act with permission | Review the guardrails and least-privilege IAM | `google-agents-cli-adk-code`, `google-cloud-recipe-auth` |
| 3 · Close the loop | Alerting as Terraform: topic, channel, 5xx policy | `cloud-run-alert-configuration`, `cloud-monitoring-notification-channels-configuration` |
| Bonus | SLO alert wizard | `google-cloud-slo-alert-configuration` |

## Repo layout

| Path | What it is |
| --- | --- |
| `app/` | Checkout API (Flask). `FAILURE_RATE=0.5` makes a revision fail half the requests |
| `agent/sre_agent/` | ADK agents and tools. `root_agent` for `adk web`, `alert_agent` for the service |
| `service/main.py` | Lab 3 service: Pub/Sub push → agent → approval endpoints |
| `prompts/` | The agent-step prompt for each lab |
| `AGENTS.md` | Ground rules for the coding agent (read-only by default, keep names, keep guardrails) |
| `alerting/` | Alert policy JSON for the script fallback; generated Terraform lands in `alerting/terraform/` |
| `scripts/` | One script per lab step, plus skills setup and teardown |
| `tests/` | Offline tests (no GCP needed): `pip install -r requirements-dev.txt && pytest` |

## Before the workshop

- A GCP project with billing (or event credits); `gcloud` logged in and
  `gcloud config set project <your-project-id>`
- [Antigravity CLI](https://antigravity.google/) and Node.js (for `npx`) on your laptop
- Install the skills once:

```bash
./scripts/00-skills.sh
```

It installs the `google-cloud-developer` plugin
(`agy plugin install https://github.com/google/skills/plugins/cloud/google-cloud-developer`),
then runs `npx skills add google/skills` and `npx skills add google/agents-cli`,
telling you which skills to tick.

## Lab 0 — Deploy the patient (10 min)

```bash
./scripts/00-setup.sh        # APIs, service accounts, healthy checkout v1
./scripts/02-load.sh 20      # all 200s
```

**Agent step:** start `agy` in this folder and paste `prompts/lab0-check.md`.

## Lab 1 — An agent that can see (20 min)

```bash
./scripts/01-break.sh        # ships v2 at 50% failures and sends load
```

**Agent step:** `prompts/lab1-logs.md`: the logging skill writes and runs the
queries; compare them with `get_recent_errors` / `get_request_stats`.

Then run the SRE agent:

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example sre_agent/.env   # set GOOGLE_CLOUD_PROJECT
adk web                          # Web Preview / localhost:8000
```

Ask: **"Why is checkout failing?"** It should name the newest revision and cite
`PaymentGatewayTimeout` log lines.

## Lab 2 — Act with permission (15 min)

**Agent step:** `prompts/lab2-review.md`: the coding agent confirms the human gate
and checks IAM against `scripts/00-setup.sh`.

Then ask the SRE agent: **"Fix it."** `rollback_traffic` is registered with
`require_confirmation=True`, so `adk web` waits for your approval. Verify with
`./scripts/02-load.sh 20`, then re-break for Lab 3: `./scripts/01-break.sh`.

## Lab 3 — Close the loop (20 min)

**Agent step:** `prompts/lab3-alerting.md`: the Cloud Run alerting and
notification-channel skills generate Terraform for the topic, channel and 5xx
policy. Review `terraform plan`, then apply. Short on time? `./scripts/03-alerting.sh`
does the same with gcloud.

```bash
./scripts/04-deploy-agent.sh   # private agent service + push subscription
./scripts/02-load.sh 300       # keep the errors coming
./scripts/incidents.sh         # wait for "awaiting_approval" (alert takes 2-4 min)
./scripts/incidents.sh approve <incident_id>
```

Alert slow? `./scripts/05-simulate-alert.sh` publishes a sample incident instead.

## Guardrails built in

| Guardrail | Where |
| --- | --- |
| Least privilege | `sre-agent` SA: logging/run viewer + Vertex AI user; `run.developer` on `checkout` only |
| Blast radius | `ALLOWED_SERVICES` allow-list checked in every tool (`tools.py`) |
| Validated action | Rollback only to a revision that belongs to the service |
| Human approval | Lab 2: ADK tool confirmation. Lab 3: the agent has no write tool; code runs the rollback after `/approve` |
| Coding agent | `AGENTS.md`: read-only by default, show the command or plan, wait for yes |
| Prompt injection | Logs and alert text marked untrusted in the instruction; tools validate inputs |
| Private endpoint | Agent service deployed with `--no-allow-unauthenticated`; Pub/Sub pushes with OIDC |
| Audit | `APPROVED`/`REJECTED`/`ROLLBACK` log lines with approver, service and revision |

Notes: in Lab 1–2 `adk web` runs with *your* credentials, not the agent's service account.
Incidents in Lab 3 are stored in memory (one instance) — fine for a workshop, not production.
Set `SRE_MODEL` to switch Gemini models (default `gemini-2.5-flash`).

## Cleanup

```bash
terraform -chdir=alerting/terraform destroy   # if you used the Lab 3 agent step
./scripts/99-teardown.sh
```

## Skills used

- [google/skills](https://github.com/google/skills): Agent Skills for Google Cloud
- [google/agents-cli](https://github.com/google/agents-cli): ADK skills and CLI
