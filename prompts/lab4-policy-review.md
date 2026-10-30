# Lab 4 · Agent step: check the autonomy guardrails before you turn them on

> Read agent/sre_agent/policy.py and plan_scale in agent/sre_agent/tools.py. In five
> bullets, tell me exactly what the SRE agent may do alone when AUTONOMY=auto and
> AUTO_ACTIONS=scale, and what still needs a human. Report only; don't change files.

**Expect:** only scaling runs alone; one step up/out at a time; never down; capped by
MAX_CPU / MAX_MEMORY_MI / MAX_INSTANCES_CAP; refused when traffic is pinned; rollbacks
still wait for a Slack Approve.
