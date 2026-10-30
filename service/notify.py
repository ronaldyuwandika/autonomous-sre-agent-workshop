"""Incident reports to Slack and email. Best effort: a failed send is logged, never fatal.

Env (secrets come from Secret Manager via `gcloud run deploy --set-secrets`):
  SLACK_WEBHOOK_URL   incoming webhook of your Slack app (secret)
  SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD (secret), EMAIL_FROM, EMAIL_TO (comma list)
Anything unset = that channel is skipped.
"""
import json
import logging
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

log = logging.getLogger("sre_service.notify")

ICON = {"auto_remediated": "Auto-remediated", "auto_failed": "Auto-remediation FAILED",
        "awaiting_approval": "Approval needed", "needs_human": "Needs a human",
        "rolled_back": "Approved and executed", "scaled": "Approved and executed",
        "rejected": "Rejected", "action_failed": "Approved, but the action FAILED",
        "agent_error": "Agent error"}


def describe(p: dict | None) -> str:
    """One line for a proposal: what would change."""
    if not p:
        return "No change proposed."
    if p.get("action") == "rollback":
        return f"Rollback {p['service']}: route 100% traffic to {p['revision']}"
    if p.get("action") == "scale":
        parts = [f"{k}={p[k]}" for k in ("cpu", "memory", "max_instances") if k in p]
        return f"Scale {p['service']}: " + ", ".join(parts)
    return "Unknown action."


def _text(inc: dict) -> str:
    lines = [f"[{ICON.get(inc['status'], inc['status'])}] {inc['service']} · {inc['policy']}",
             "", (inc.get("findings") or "").strip()[:2500], "",
             "Action: " + describe(inc.get("proposal"))]
    if inc.get("result"):
        lines.append("Result: " + json.dumps(inc["result"])[:500])
    if inc["status"] == "awaiting_approval":
        lines.append(f"Approve in Slack, or: ./scripts/incidents.sh approve {inc['incident_id']}")
    lines.append(f"Incident: {inc['incident_id']}")
    return "\n".join(lines)


def _slack_escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slack_blocks(inc: dict) -> list:
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": _slack_escape(_text(inc))[:2900]}}]
    if inc["status"] == "awaiting_approval":
        blocks.append({"type": "actions", "block_id": "decision", "elements": [
            {"type": "button", "action_id": "approve", "style": "primary", "value": inc["incident_id"],
             "text": {"type": "plain_text", "text": "Approve"},
             "confirm": {"title": {"type": "plain_text", "text": "Run this change?"},
                         "text": {"type": "plain_text", "text": describe(inc.get("proposal"))[:300]},
                         "confirm": {"type": "plain_text", "text": "Approve"},
                         "deny": {"type": "plain_text", "text": "Cancel"}}},
            {"type": "button", "action_id": "reject", "style": "danger", "value": inc["incident_id"],
             "text": {"type": "plain_text", "text": "Reject"}},
        ]})
    return blocks


def _post_json(url: str, payload: dict) -> None:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:  # nosec: URL comes from our own secret/Slack
        r.read()


def slack(inc: dict) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        _post_json(url, {"text": _text(inc)[:300], "blocks": slack_blocks(inc)})
        return True
    except Exception as e:
        log.warning("slack send failed: %s", type(e).__name__)  # never log the webhook URL
        return False


def slack_update(response_url: str, inc: dict) -> None:
    """Replace the original Slack message (buttons gone) with the outcome."""
    if not response_url.startswith("https://hooks.slack.com/"):
        log.warning("ignored unexpected response_url host")
        return
    try:
        _post_json(response_url, {"replace_original": True, "text": _text(inc)[:300], "blocks": slack_blocks(inc)})
    except Exception as e:
        log.warning("slack update failed: %s", type(e).__name__)


def email(inc: dict) -> bool:
    host, to = os.environ.get("SMTP_HOST", ""), os.environ.get("EMAIL_TO", "")
    if not host or not to:
        return False
    msg = EmailMessage()
    msg["Subject"] = f"[SRE agent] {ICON.get(inc['status'], inc['status'])}: {inc['service']}"
    msg["From"] = os.environ.get("EMAIL_FROM", os.environ.get("SMTP_USER", "sre-agent@localhost"))
    msg["To"] = to
    msg.set_content(_text(inc))
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            if os.environ.get("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return True
    except Exception as e:
        log.warning("email send failed: %s", type(e).__name__)
        return False


def report(inc: dict) -> dict:
    return {"slack": slack(inc), "email": email(inc)}
