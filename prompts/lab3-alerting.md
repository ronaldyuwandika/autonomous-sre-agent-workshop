# Lab 3 · Agent step: alerting as code

Replaces `scripts/03-alerting.sh` (keep the script as the fallback).

> Using the cloud-run-alert-configuration and
> cloud-monitoring-notification-channels-configuration skills, generate Terraform in
> alerting/terraform/ for my current project: a Pub/Sub topic named sre-alerts, a
> Pub/Sub notification channel for it (including the permission the Cloud
> Monitoring notification service agent needs to publish), and one alert policy
> that fires when the Cloud Run service checkout returns 5xx errors. Keep it to
> those resources. Show me terraform plan and wait for my yes before apply.

Then review the plan yourself and run `terraform apply` when it looks right.
Continue with `scripts/04-deploy-agent.sh`.

**Cleanup:** `terraform -chdir=alerting/terraform destroy` before `scripts/99-teardown.sh`.
