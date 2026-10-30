# Lab 4 · Agent step: a saturation alert as code

Replaces `scripts/08-saturation-alert.sh` (keep the script as the fallback).

> Using the cloud-run-alert-configuration skill, add Terraform to alerting/terraform/
> for one more alert policy on the Cloud Run service checkout: fire when container CPU
> utilization p99 is above 80% or memory utilization p99 is above 85% for one minute.
> Send it to the existing sre-alerts Pub/Sub notification channel. Keep everything else
> unchanged. Show me terraform plan and wait for my yes before apply.

**Expect:** a plan that adds one alert policy and changes nothing else.
