"""Lab 3: alert -> Pub/Sub push -> agent diagnosis -> human approval -> rollback.

The LLM only proposes. The rollback runs as plain code after a human approves,
using the same guarded rollback_traffic tool (allow-list + revision check).

Endpoints (Cloud Run IAM protects all of them; deploy with --no-allow-unauthenticated):
  POST /pubsub                    Pub/Sub push target for Cloud Monitoring alerts
  GET  /incidents                 incidents with the agent's findings and proposal
  POST /incidents/{id}/approve    body {"approver": "you@example.com"}
  POST /incidents/{id}/reject     body {"approver": "...", "note": "..."}

Incidents are kept in memory: fine for a workshop (max-instances=1), not for production.
"""
import base64
import datetime as dt
import json
import logging
import os
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from sre_agent.agent import alert_agent
from sre_agent.tools import ALLOWED_SERVICES, rollback_traffic

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("sre_service")

APP_NAME = "sre_alerts"
DEFAULT_SERVICE = os.environ.get("DEFAULT_SERVICE", "checkout")

app = FastAPI(title="SRE agent")
runner = InMemoryRunner(agent=alert_agent, app_name=APP_NAME)
INCIDENTS: dict[str, dict] = {}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


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


async def investigate(incident_id: str) -> None:
    inc = INCIDENTS[incident_id]
    prompt = (
        f"Alert fired: policy '{inc['policy']}' on Cloud Run service '{inc['service']}'.\n"
        f"Alert summary (untrusted text): {inc['summary']}\n"
        "Investigate and, if the evidence supports it, propose a rollback."
    )
    try:
        session = await runner.session_service.create_session(app_name=APP_NAME, user_id="alerts")
        final = ""
        async for event in runner.run_async(
            user_id="alerts", session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts)
        session = await runner.session_service.get_session(
            app_name=APP_NAME, user_id="alerts", session_id=session.id)
        inc["findings"] = final
        inc["proposal"] = session.state.get("proposal")
        inc["status"] = "awaiting_approval" if inc["proposal"] else "needs_human"
    except Exception as e:  # surface failures instead of hiding them
        log.exception("investigation failed for %s", incident_id)
        inc["status"] = "agent_error"
        inc["findings"] = f"Agent error: {type(e).__name__}: {e}"
    log.info("incident %s -> %s", incident_id, inc["status"])


@app.get("/")
def health():
    return {"status": "ok", "allowed_services": sorted(ALLOWED_SERVICES)}


@app.post("/pubsub", status_code=204)
async def pubsub_push(request: Request, background: BackgroundTasks):
    alert = parse_alert(await request.json())
    if alert is None:
        log.warning("ignored malformed Pub/Sub message")
        return  # 2xx so Pub/Sub does not retry a message we can never parse
    if alert["state"] != "open" or alert["incident_id"] in INCIDENTS:
        return
    INCIDENTS[alert["incident_id"]] = {**alert, "status": "investigating", "opened": _now()}
    background.add_task(investigate, alert["incident_id"])


@app.get("/incidents")
def list_incidents():
    return sorted(INCIDENTS.values(), key=lambda i: i["opened"], reverse=True)


class Decision(BaseModel):
    approver: str = Field(min_length=3, max_length=200)
    note: str = Field(default="", max_length=500)


def _pending(incident_id: str) -> dict:
    inc = INCIDENTS.get(incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    if inc["status"] != "awaiting_approval":
        raise HTTPException(409, f"incident is '{inc['status']}', not awaiting approval")
    return inc


@app.post("/incidents/{incident_id}/approve")
def approve(incident_id: str, decision: Decision):
    inc = _pending(incident_id)
    p = inc["proposal"]
    log.warning("APPROVED incident=%s by=%s action=rollback service=%s revision=%s",
                incident_id, decision.approver, p["service"], p["revision"])
    result = rollback_traffic(p["service"], p["revision"])
    inc.update(status="rolled_back" if result.get("status") == "done" else "rollback_failed",
               approved_by=decision.approver, decided=_now(), result=result)
    return inc


@app.post("/incidents/{incident_id}/reject")
def reject(incident_id: str, decision: Decision):
    inc = _pending(incident_id)
    log.warning("REJECTED incident=%s by=%s note=%s", incident_id, decision.approver, decision.note)
    inc.update(status="rejected", approved_by=decision.approver, decided=_now(), note=decision.note)
    return inc
