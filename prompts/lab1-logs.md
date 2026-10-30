# Lab 1 · Agent step: let a skill write the log queries

After `scripts/01-break.sh`, before you start `adk web`.

> Using the cloud-logging-query-generation skill, write two Cloud Logging queries
> for the Cloud Run service checkout over the last 15 minutes: (1) ERROR log lines,
> (2) request logs with HTTP status 500 or above. Run each with gcloud logging read
> (limit 5) and show which revision the errors come from. Then compare the filters
> with get_recent_errors and get_request_stats in agent/sre_agent/tools.py and say
> whether they match. Don't edit files.

**Expect:** the errors come from the newest revision, and the skill's filters match
the ones the SRE agent's tools already use: the agent's tools are just these queries
wrapped as Python functions.
