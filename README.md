# Can Your Cloud Fix Itself? — Autonomous SRE Agent workshop

Hands-on workshop for **DevFest Cloud Surabaya 2026** (21 Nov 2026, 90 min).
You deploy a Cloud Run app, break it, and build an agent with Google ADK + Gemini that
finds the bad revision and rolls it back **after a human approves**.

```
checkout (Cloud Run) ──5xx──▶ Cloud Monitoring alert ──▶ Pub/Sub ──push──▶ sre-agent (Cloud Run)
        ▲                                                                       │ read-only tools:
        │                                                                       │ logs, request stats, revisions
        └──────── rollback_traffic ◀── POST /incidents/{id}/approve ◀── human ◀─┘ proposes a rollback
```

## Repo layout

| Path | What it is |
| --- | --- |
| `app/` | Checkout API (Flask). `FAILURE_RATE=0.5` makes a revision fail half the requests |
| `agent/sre_agent/` | ADK agents and tools. `root_agent` for `adk web`, `alert_agent` for the service |
| `service/main.py` | Lab 3 service: Pub/Sub push → agent → approval endpoints |
| `alerting/` | Alert policy and a sample alert for the manual fallback |
| `scripts/` | One script per lab step, plus teardown |
| `tests/` | Offline tests (no GCP needed): `pip install -r requirements-dev.txt && pytest` |

## Before the workshop

- A GCP project with billing (or event credits), opened in **Cloud Shell**
- `gcloud config set project <your-project-id>`

## Lab 0 — Deploy the patient (10 min)

```bash
./scripts/00-setup.sh        # APIs, service accounts, healthy checkout v1
./scripts/02-load.sh 20      # all 200s
```

## Lab 1 — An agent that can see (20 min)

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example sre_agent/.env   # set GOOGLE_CLOUD_PROJECT
gcloud auth application-default login   # skip in Cloud Shell if ADC already works
adk web                          # Cloud Shell: Web Preview on port 8000
```

In another terminal: `./scripts/01-break.sh` (ships v2 at 50% failures and sends load).
Ask the agent: **"Why is checkout failing?"** It should name the v2 revision and cite
`PaymentGatewayTimeout` log lines.

> To keep Lab 1 strictly read-only, comment out the `FunctionTool(rollback_traffic, …)` line in `agent.py`.

## Lab 2 — Act with permission (15 min)

Ask: **"Fix it."** The agent calls `rollback_traffic`, which is registered with
`require_confirmation=True`, so `adk web` asks you to approve before anything changes.
Approve, then run `./scripts/02-load.sh 20` — all 200s again.

Re-break for Lab 3: `./scripts/01-break.sh`.

## Lab 3 — Close the loop (15 min)

```bash
./scripts/03-alerting.sh       # topic, Pub/Sub channel, alert policy (5xx > 5/min)
./scripts/04-deploy-agent.sh   # private agent service + push subscription
./scripts/02-load.sh 300       # keep the errors coming
./scripts/incidents.sh         # wait for status "awaiting_approval" (alert takes 2-4 min)
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
| Prompt injection | Logs and alert text marked untrusted in the instruction; tools validate inputs |
| Private endpoint | Agent service deployed with `--no-allow-unauthenticated`; Pub/Sub pushes with OIDC |
| Audit | `APPROVED`/`REJECTED`/`ROLLBACK` log lines with approver, service and revision |

Notes: in Lab 1–2 `adk web` runs with *your* credentials, not the agent's service account.
Incidents in Lab 3 are stored in memory (one instance) — fine for a workshop, not production.
Set `SRE_MODEL` to switch Gemini models (default `gemini-2.5-flash`).

## Cleanup

```bash
./scripts/99-teardown.sh
```
