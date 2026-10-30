# Lab 2 · Agent step: review the guardrails

Before you ask the SRE agent to fix anything.

> Using the google-agents-cli-adk-code and google-cloud-recipe-auth skills, review
> agent/sre_agent/agent.py and agent/sre_agent/tools.py. (1) Confirm that
> rollback_traffic and scale_service can only run after a human confirms them, and point to the lines.
> (2) List the smallest set of IAM roles the sre-agent service account needs for
> these tools, and compare it with what scripts/00-setup.sh grants. Report only;
> don't change files.

**Expect:** `require_confirmation=True` on both write tools (`rollback_traffic`, `scale_service`), plus viewer roles
project-wide and `run.developer` on `checkout` only.
