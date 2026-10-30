# 5 Whys and three points of view

Use this at the Lab 3 and Lab 4 checkpoints. It explains *why* each incident happened
and *who sees what* while the agent works. The agent code does not change.

## How to read a 5 Whys

Start at the symptom and ask "why?" until you reach something a team can change.

- **Whys 1–4: the agent.** Each answer comes from a read-only tool, so it has evidence (a number or a log line).
- **Why 5: humans.** The root cause is a process or a decision. The agent's fix only makes the incident stop. The team fixes the process.

Numbers below are example values from the labs; yours will differ.

## Incident A — bad release (Labs 1–3)

| # | Why? | Answer | Evidence (tool) |
| --- | --- | --- | --- |
| 1 | Why is checkout failing? | About half of `/checkout` requests return 5xx | `get_request_stats` |
| 2 | Why 5xx? | The newest revision throws `PaymentGatewayTimeout`; the previous revision is healthy | `get_recent_errors`, `list_revisions` |
| 3 | Why does the new revision fail? | It shipped with a bad change (`FAILURE_RATE=0.5` in this lab) | Revision env/config, release diff |
| 4 | Why did it get all the traffic? | `gcloud run deploy` sends 100% of traffic to the latest revision; no canary | `list_revisions` (traffic %) |
| 5 | Why wasn't it stopped before users saw it? | No progressive rollout with an error-rate gate | **Team** (post-incident review) |

- **Fix now (agent, after a Slack click):** route 100% traffic back to the healthy revision (`rollback_traffic`).
- **Fix for good (team):** canary releases (`--no-traffic` + gradual `update-traffic`) gated on the 5xx alert.

## Incident B — resource exhaustion (Lab 4)

| # | Why? | Answer | Evidence (tool) |
| --- | --- | --- | --- |
| 1 | Why is checkout slow and returning 429? | Requests can't get an instance; p95 latency is in seconds | Saturation alert, `get_resource_usage` |
| 2 | Why no instance? | Both instances are busy: 2 of max 2, concurrency 4 each | `get_resource_usage` (peak instances) |
| 3 | Why are they busy? | CPU p99 ≈ 0.97: each request burns ~300 ms of CPU | `get_resource_usage` (CPU p99) |
| 4 | Why can't it grow? | Limits are tight: `max-instances 2`, 1 vCPU | `get_resource_usage` (current config) |
| 5 | Why were the limits that tight? | Sized without a load test or a capacity review | **Team** (capacity planning) |

- **Fix now (agent, alone in `AUTONOMY=auto`):** scale out one step, `max_instances` 2 → 4 (`scale_service`, capped by `plan_scale`).
- **Fix for good (team):** load-test before release, right-size CPU/memory/max instances, add a saturation SLO.

> The agent's fix buys time. It never closes the incident's root cause. That's why every outcome is reported to Slack and email: a human owns why #5.

## Three points of view, one incident

The same Incident A, as each person (or agent) experiences it.

| | On-call engineer | SRE agent | Approver (Slack) |
| --- | --- | --- | --- |
| **Sees** | A Slack message with the analysis and a proposed fix, not a bare alert | The alert, then logs, request stats, revisions, CPU/memory (read-only) | The same message with **Approve / Reject** and a confirm dialog |
| **Does** | Reads the evidence in ~30 s, agrees or pushes back | Answers whys 1–4, proposes **one** capped fix, posts it | Clicks; the message updates with the result |
| **Can't** | Get silently overridden: nothing changes until a click (or the policy allows it) | Write anything itself, or touch services outside `ALLOWED_SERVICES` | Be bypassed: non-approvers, forged or replayed clicks are refused |
| **Owns** | Why #5 and the post-incident review | Evidence and a safe proposal | The decision, recorded in the audit log (`APPROVED by slack:U…`) |

The on-call engineer and the approver are often the same person. They're split here because
`SLACK_APPROVERS` decides who can click, not who gets paged.

### Minute by minute (example timing)

| Time | SRE agent | On-call engineer | Approver |
| --- | --- | --- | --- |
| T+0 | Alert arrives via Pub/Sub | Asleep | — |
| T+1 | Calls `get_request_stats`, `get_recent_errors`, `list_revisions` | Asleep | — |
| T+2 | Proposes rollback; policy says *approve*; posts to Slack + email | Phone buzzes; reads the analysis | Sees the buttons |
| T+3 | Waits (no write tool) | Agrees with the evidence | Clicks **Approve**, confirms |
| T+4 | Service runs `rollback_traffic`; message updates; audit line | Checks `02-load.sh 20`: all 200 | Done |
| Later | — | Writes the review for why #5 | — |

In `AUTONOMY=auto` (Incident B) the agent's column runs straight through: it scales at T+2 and
everyone else gets the report afterwards.
