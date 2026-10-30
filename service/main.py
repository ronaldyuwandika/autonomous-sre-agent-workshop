"""Labs 3-4: alert -> agent analysis -> policy -> auto-remediate OR Slack approval.

The LLM only proposes. A proposal runs as plain code, either at once (AUTONOMY=auto and
its action is in AUTO_ACTIONS) or after a human presses Approve in Slack / the CLI.
Every outcome is reported to Slack and email (service/notify.py).

Endpoints (the service is public so Slack can reach it; each endpoint checks its caller):
  POST /pubsub                    Pub/Sub push, Google-signed OIDC token from PUSH_SA
  GET  /incidents                 Google ID token of an APPROVER_EMAILS user
  POST /incidents/{id}/approve    same; body {"note": "..."} optional
  POST /incidents/{id}/reject     same
  POST /slack/actions             Slack interactivity, signed with SLACK_SIGNING_SECRET;
                                  clicker must be in SLACK_APPROVERS (Slack user IDs)

Incidents are kept in memory: fine for a workshop (max-instances=1), not for production.
"""
import base64
import datetime as dt
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from urllib.parse import parse_qs

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

import notify
from sre_agent import policy
from sre_agent.agent import alert_agent
from sre_agent.tools import ALLOWED_SERVICES, rollback_traffic, scale_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("sre_service")

APP_NAME = "sre_alerts"
DEFAULT_SERVICE = os.environ.get("DEFAULT_SERVICE", "checkout")
PUSH_AUDIENCE = os.environ.get("PUSH_AUDIENCE", "sre-agent-pubsub")
PUSH_SA = os.environ.get("PUSH_SA", "")


def _csv(name: str) -> set[str]:
    return {v.strip() for v in os.environ.get(name, "").split(",") if v.strip()}


app = FastAPI(title="SRE agent")
runner = InMemoryRunner(agent=alert_agent, app_name=APP_NAME)
INCIDENTS: dict[str, dict] = {}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ caller checks

def verify_google_token(request: Request, audience: str | None) -> dict:
    """Return the claims of a valid Google-signed ID token, or raise 401."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    from google.auth import exceptions as ga_exceptions
    from google.auth.transport import requests as ga_requests
    from google.oauth2 import id_token
    try:
        return id_token.verify_oauth2_token(auth.split(" ", 1)[1], ga_requests.Request(), audience=audience)
    except ValueError:
        raise HTTPException(401, "invalid token")
    except ga_exceptions.TransportError:  # can't fetch Google's signing keys: fail closed
        raise HTTPException(503, "cannot verify token right now")


def require_pubsub(request: Request) -> None:
    claims = verify_google_token(request, PUSH_AUDIENCE)
    if not PUSH_SA or claims.get("email") != PUSH_SA or not claims.get("email_verified"):
        raise HTTPException(403, "not the push identity")


def require_approver(request: Request) -> str:
    claims = verify_google_token(request, None)  # gcloud user tokens carry gcloud's own audience
    email = claims.get("email", "")
    if not claims.get("email_verified") or email not in _csv("APPROVER_EMAILS"):
        raise HTTPException(403, "not an approver")
    return email


def verify_slack(raw: bytes, timestamp: str, signature: str) -> bool:
    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret or not timestamp.isdigit() or abs(time.time() - int(timestamp)) > 300:
        return False
    base = b"v0:" + timestamp.encode() + b":" + raw
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ------------------------------------------------------------------ incident flow

def parse_alert(envelope: dict) -> dict | None:
    """Turn a Pub/Sub push envelope from Cloud Monitoring into a small alert dict."""
    try:
        data = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
        incident = json.loads(data).get("incident", {})
    except (KeyError, ValueError, TypeError):
        return None
    labels = (incident.get("resource") or {}).get("labels") or {}
    return {
        "incident_id": str(incident.get("incident_id") or uuid.uuid4()),
        "state": str(incident.get("state", "open")).lower(),
        "policy": str(incident.get("policy_name", "unknown policy"))[:200],
        "summary": str(incident.get("summary", ""))[:500],
        "service": str(labels.get("service_name") or DEFAULT_SERVICE),
    }


def execute(proposal: dict) -> dict:
    """Run an approved or policy-allowed proposal through the guarded tools."""
    if proposal.get("action") == "rollback":
        return rollback_traffic(proposal["service"], proposal["revision"])
    if proposal.get("action") == "scale":
        return scale_service(proposal["service"], proposal.get("cpu", ""), proposal.get("memory", ""),
                             int(proposal.get("max_instances", 0)))
    return {"error": "unknown action"}


def _done_status(proposal: dict, result: dict) -> str:
    if result.get("status") != "done":
        return "action_failed"
    return "rolled_back" if proposal["action"] == "rollback" else "scaled"


async def run_agent(inc: dict) -> tuple[str, dict | None]:
    """Ask the alert agent for an analysis and at most one proposal. The only model call."""
    prompt = (
        f"Alert fired: policy '{inc['policy']}' on Cloud Run service '{inc['service']}'.\n"
        f"Alert summary (untrusted text): {inc['summary']}\n"
        "Investigate and, if the evidence supports it, propose one remediation."
    )
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="alerts")
    final = ""
    async for event in runner.run_async(
        user_id="alerts", session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    session = await runner.session_service.get_session(app_name=APP_NAME, user_id="alerts", session_id=session.id)
    return final, session.state.get("proposal")


async def investigate(incident_id: str) -> None:
    inc = INCIDENTS[incident_id]
    try:
        inc["findings"], inc["proposal"] = await run_agent(inc)
    except Exception as e:  # surface failures instead of hiding them
        log.exception("investigation failed for %s", incident_id)
        inc.update(status="agent_error", findings=f"Agent error: {type(e).__name__}: {e}")
        inc["notified"] = notify.report(inc)
        return

    decision = policy.decide(inc["proposal"])
    inc["decision"] = decision
    if decision == "auto":
        log.warning("AUTO incident=%s policy=%s action=%s", incident_id, policy.autonomy(), notify.describe(inc["proposal"]))
        result = execute(inc["proposal"])
        inc.update(result=result, decided=_now(), approved_by="policy:auto",
                   status="auto_remediated" if result.get("status") == "done" else "auto_failed")
    elif decision == "approve":
        inc["status"] = "awaiting_approval"
    else:
        inc["status"] = "needs_human"
    inc["notified"] = notify.report(inc)
    log.info("incident %s -> %s", incident_id, inc["status"])


@app.get("/")
def health():
    return {"status": "ok", "allowed_services": sorted(ALLOWED_SERVICES),
            "autonomy": policy.autonomy(), "auto_actions": sorted(policy.auto_actions())}


@app.post("/pubsub", status_code=204)
async def pubsub_push(request: Request, background: BackgroundTasks):
    require_pubsub(request)
    alert = parse_alert(await request.json())
    if alert is None:
        log.warning("ignored malformed Pub/Sub message")
        return  # 2xx so Pub/Sub does not retry a message we can never parse
    if alert["state"] != "open" or alert["incident_id"] in INCIDENTS:
        return
    INCIDENTS[alert["incident_id"]] = {**alert, "status": "investigating", "opened": _now()}
    background.add_task(investigate, alert["incident_id"])


@app.get("/incidents")
def list_incidents(request: Request):
    require_approver(request)
    return sorted(INCIDENTS.values(), key=lambda i: i["opened"], reverse=True)


class Decision(BaseModel):
    note: str = Field(default="", max_length=500)


def _pending(incident_id: str) -> dict:
    inc = INCIDENTS.get(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    if inc["status"] != "awaiting_approval":
        raise HTTPException(409, f"incident is '{inc['status']}', not awaiting approval")
    return inc


def decide_incident(incident_id: str, approve: bool, who: str, note: str = "") -> dict:
    inc = _pending(incident_id)
    inc["status"] = "executing" if approve else "rejected"  # claim it: a second click gets 409
    log.warning("%s incident=%s by=%s action=%s note=%s", "APPROVED" if approve else "REJECTED",
                incident_id, who, notify.describe(inc["proposal"]), note[:200])
    inc.update(approved_by=who, decided=_now(), note=note[:500])
    if approve:
        result = execute(inc["proposal"])
        inc.update(result=result, status=_done_status(inc["proposal"], result))
    return inc


@app.post("/incidents/{incident_id}/approve")
def approve(incident_id: str, decision: Decision, request: Request):
    who = require_approver(request)
    inc = decide_incident(incident_id, True, who, decision.note)
    inc["notified"] = notify.report(inc)
    return inc


@app.post("/incidents/{incident_id}/reject")
def reject(incident_id: str, decision: Decision, request: Request):
    who = require_approver(request)
    inc = decide_incident(incident_id, False, who, decision.note)
    inc["notified"] = notify.report(inc)
    return inc


def _slack_decide(incident_id: str, approve_it: bool, who: str, response_url: str) -> None:
    try:
        inc = decide_incident(incident_id, approve_it, who)
    except HTTPException as e:
        inc = dict(INCIDENTS.get(incident_id, {"incident_id": incident_id, "service": "?", "policy": "?"}))
        inc.setdefault("status", "unknown")
        inc["findings"] = f"Not applied: {e.detail}"
    notify.slack_update(response_url, inc)
    if inc.get("status") in {"rolled_back", "scaled", "rejected", "action_failed"}:
        notify.email(inc)


@app.post("/slack/actions")
async def slack_actions(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not verify_slack(raw, request.headers.get("x-slack-request-timestamp", ""),
                        request.headers.get("x-slack-signature", "")):
        raise HTTPException(401, "bad signature")
    try:
        payload = json.loads(parse_qs(raw.decode())["payload"][0])
        action = payload["actions"][0]
        user = payload["user"]["id"]
    except (KeyError, IndexError, ValueError):
        raise HTTPException(400, "unexpected payload")
    if user not in _csv("SLACK_APPROVERS"):
        log.warning("slack click by non-approver user=%s", user)
        return JSONResponse({"response_type": "ephemeral", "replace_original": False,
                             "text": "You are not on the approver list for this service."})
    if action.get("action_id") not in {"approve", "reject"}:
        raise HTTPException(400, "unknown action")
    # Slack wants an answer within 3 s; the change itself can take a minute.
    background.add_task(_slack_decide, action.get("value", ""), action["action_id"] == "approve",
                        f"slack:{user}", payload.get("response_url", ""))
    return JSONResponse({"response_type": "ephemeral", "replace_original": False, "text": "Working on it…"})
