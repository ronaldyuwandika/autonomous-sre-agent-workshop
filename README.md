# Can Your Cloud Fix Itself? — Autonomous SRE Agent with Google Cloud & Agent Skills

Hands-on workshop for **DevFest Cloud Surabaya 2026** (21 Nov 2026, 90 min).
You build an SRE agent with Google ADK + Gemini that diagnoses Cloud Run incidents
(a bad release, or CPU/memory exhaustion), reports its analysis to **Slack and email**,
and fixes them by **rollback, scale-up or scale-out**: either after a human presses
**Approve in Slack**, or on its own when you **instruct it to** (`AUTONOMY=auto`).
You pair with **Antigravity CLI loaded with Google's Agent Skills** for one step in every lab.

```
checkout (Cloud Run) ─5xx / CPU / mem─▶ Cloud Monitoring alert ──▶ Pub/Sub ──push──▶ sre-agent (Cloud Run)
        ▲                                                                       │ read-only tools:
        │                                                                       │ logs, request stats, revisions
        │                                                                       │ logs, request stats, revisions,
        │                                                                       │ CPU/memory/instances (Monitoring)
        │                                                                       ▼ proposes rollback OR scale
        │                                                               policy (AUTONOMY)
        │                                                      auto ┌──────────┴──────────┐ approve
        │                                                           ▼                     ▼
        └────── rollback_traffic / scale_service ◀── runs now   Slack [Approve][Reject] ── human
                                                                + email report for every outcome
```

| Mode | Set with | What happens |
| --- | --- | --- |
| Approve (default) | `AUTONOMY=approve` | Analysis + **Approve / Reject** buttons in Slack, copy by email; nothing changes until an approver clicks |
| Self-healing | `AUTONOMY=auto` + `AUTO_ACTIONS=scale` | Scale-up/out runs at once, then the analysis and the result go to Slack + email; rollbacks still wait for a click |

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
| 3 · Close the loop, approve in Slack | Alerting as Terraform: topic, channel, 5xx policy | `cloud-run-alert-configuration`, `cloud-monitoring-notification-channels-configuration` |
| 4 · Self-healing on exhaustion | Saturation alert as Terraform; review the autonomy guardrails | `cloud-run-alert-configuration` |
| Bonus | SLO alert wizard | `google-cloud-slo-alert-configuration` |

## Repo layout

| Path | What it is |
| --- | --- |
| `app/` | Checkout API (Flask). `FAILURE_RATE=0.5` makes a revision fail half the requests |
| `agent/sre_agent/` | ADK agents and tools. `root_agent` for `adk web`, `alert_agent` for the service |
| `service/main.py` | Alert service: Pub/Sub push → agent → policy → auto-remediate or Slack approval |
| `service/notify.py` | Slack (webhook + buttons) and email (SMTP) reports |
| `agent/sre_agent/policy.py` | `AUTONOMY` / `AUTO_ACTIONS`: what may run without a click |
| `prompts/` | The agent-step prompt for each lab |
| `AGENTS.md` | Ground rules for the coding agent (read-only by default, keep names, keep guardrails) |
| `alerting/` | 5xx and saturation policy JSON for the script fallbacks; generated Terraform lands in `alerting/terraform/` |
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

## Lab 3 — Close the loop, approve in Slack (17 min)

One-time Slack app (5 min, can be pre-work): create an app at api.slack.com/apps,
turn on **Incoming Webhooks** (add one to your channel) and **Interactivity**, and
note the **Signing Secret**. Email is optional (any SMTP server; Gmail needs an app password).

```bash
./scripts/06-notify-secrets.sh                 # webhook URL, signing secret, SMTP password → Secret Manager
export SLACK_APPROVERS=U0123ABCD               # your Slack member ID (comma list)
export SMTP_HOST=smtp.gmail.com SMTP_USER=you@example.com EMAIL_TO=oncall@example.com   # optional
```

**Agent step:** `prompts/lab3-alerting.md`: the alerting skills generate Terraform for
the topic, channel and 5xx policy; review the plan, then apply. Fallback: `./scripts/03-alerting.sh`.

```bash
AUTONOMY=approve ./scripts/04-deploy-agent.sh  # prints the Slack Interactivity Request URL: paste it into the app
./scripts/02-load.sh 300                       # checkout is still broken from Lab 2
```

In 2–4 minutes Slack shows the agent's analysis with **Approve / Reject**; email gets
the same report. Click **Approve**: the message updates with the result. Not an approver?
The click is refused. No Slack? `./scripts/incidents.sh approve <incident_id>`.
Alert slow? `./scripts/05-simulate-alert.sh`.

## Lab 4 — Self-healing on resource exhaustion (17 min)

**Agent steps:** `prompts/lab4-policy-review.md` (what may the agent do alone?), then
`prompts/lab4-saturation.md` (CPU/memory saturation alert as Terraform).
Fallback: `./scripts/08-saturation-alert.sh`.

```bash
AUTONOMY=auto ./scripts/04-deploy-agent.sh     # instruct it: scaling may run without a click
./scripts/07-exhaust.sh                        # healthy but hungry v3: 1 vCPU, 2 instances, concurrency 4, flooded
```

The agent reads CPU, memory, instance and latency metrics, decides between scale **out**
(instances at max) and scale **up** (per-instance CPU/memory), applies one guarded step,
and posts the analysis + what it changed to Slack and email. Check it:

```bash
gcloud run services describe checkout --region asia-southeast2 --format 'yaml(spec.template)'
# look for the new cpu/memory limits or autoscaling.knative.dev/maxScale
```

**Same incident, approval-based:** `AUTONOMY=approve ./scripts/04-deploy-agent.sh`, then
`./scripts/07-exhaust.sh` again. This time the scaling proposal waits behind Slack buttons.

## Guardrails built in

| Guardrail | Where |
| --- | --- |
| Least privilege | `sre-agent` SA: logging/run viewer + Vertex AI user; `run.developer` on `checkout` only |
| Blast radius | `ALLOWED_SERVICES` allow-list checked in every tool (`tools.py`) |
| Validated action | Rollback only to a revision that belongs to the service |
| Human approval | Lab 2: ADK tool confirmation. Labs 3–4: the agent has no write tool; code runs the action after an approver clicks, or when the policy allows it |
| Autonomy is opt-in | `AUTONOMY` defaults to `approve`; `auto` only covers `AUTO_ACTIONS` (default `scale`); unknown values fall back to `approve` |
| Scale guardrails | `plan_scale`: up/out only, one CPU step, at most double memory/instances, caps `MAX_CPU` / `MAX_MEMORY_MI` / `MAX_INSTANCES_CAP`, refused if traffic is pinned |
| Slack buttons | Signature (`SLACK_SIGNING_SECRET`) checked, 5-minute replay window, clicker must be in `SLACK_APPROVERS`, first click wins |
| Every outcome reported | Slack + email for auto actions, approvals, rejections and failures |
| Secrets | Webhook, signing secret and SMTP password in Secret Manager; never logged |
| Coding agent | `AGENTS.md`: read-only by default, show the command or plan, wait for yes |
| Prompt injection | Logs and alert text marked untrusted in the instruction; tools validate inputs |
| Caller checks | Service is public for Slack, so each endpoint checks its caller: Pub/Sub OIDC token (fixed audience), approver Google ID token, or Slack signature |
| Audit | `AUTO`/`APPROVED`/`REJECTED`/`ROLLBACK`/`SCALE` log lines with who, what and before/after |

Notes: in Lab 1–2 `adk web` runs with *your* credentials, not the agent's service account.
If your organization blocks public Cloud Run services (`allUsers`), Slack buttons can't
reach the agent: approve with `scripts/incidents.sh` instead.
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
