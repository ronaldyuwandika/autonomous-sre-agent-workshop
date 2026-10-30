import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agent"), str(ROOT / "service")]

SECRET = "test-signing-secret"
ROLLBACK = {"action": "rollback", "service": "checkout", "revision": "checkout-00001-abc", "reason": "v2 5xx"}
SCALE = {"action": "scale", "service": "checkout", "max_instances": 4, "reason": "instances at max"}


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("SLACK_APPROVERS", "U_ALICE")
    monkeypatch.setenv("APPROVER_EMAILS", "ronald@example.com")
    monkeypatch.delenv("AUTONOMY", raising=False)
    import main
    import notify
    from fastapi.testclient import TestClient

    main.INCIDENTS.clear()
    state = {"proposal": ROLLBACK, "executed": [], "sent": [], "updates": []}

    async def fake_run_agent(inc):  # stands in for the Gemini call only; policy + notify run for real
        return "analysis", dict(state["proposal"])

    monkeypatch.setattr(main, "run_agent", fake_run_agent)
    monkeypatch.setattr(main, "rollback_traffic", lambda s, r: state["executed"].append(("rollback", s, r)) or {"status": "done"})
    monkeypatch.setattr(main, "scale_service", lambda s, c, m, n: state["executed"].append(("scale", s, n)) or {"status": "done"})
    monkeypatch.setattr(notify, "report", lambda inc: state["sent"].append(inc["status"]) or {"slack": True, "email": True})
    monkeypatch.setattr(notify, "slack_update", lambda url, inc: state["updates"].append(inc["status"]))
    monkeypatch.setattr(notify, "email", lambda inc: True)
    monkeypatch.setattr(main, "require_pubsub", lambda request: None)
    monkeypatch.setattr(main, "require_approver", lambda request: "ronald@example.com")
    c = TestClient(main.app)
    c.state, c.main = state, main
    return c


def push(incident_id="i-1", state="open"):
    inc = {"incident_id": incident_id, "state": state, "policy_name": "checkout 5xx",
           "resource": {"labels": {"service_name": "checkout"}}, "summary": "5xx high"}
    return {"message": {"data": base64.b64encode(json.dumps({"incident": inc}).encode()).decode()}}


def slack_post(c, user="U_ALICE", action="approve", incident="i-1", secret=SECRET, ts=None):
    payload = {"user": {"id": user}, "response_url": "https://hooks.slack.com/actions/T/1/x",
               "actions": [{"action_id": action, "value": incident}]}
    body = urlencode({"payload": json.dumps(payload)}).encode()
    ts = str(int(time.time()) if ts is None else ts)
    sig = "v0=" + hmac.new(secret.encode(), b"v0:" + ts.encode() + b":" + body, hashlib.sha256).hexdigest()
    return c.post("/slack/actions", content=body, headers={
        "x-slack-request-timestamp": ts, "x-slack-signature": sig,
        "content-type": "application/x-www-form-urlencoded"})


# ----------------------------------------------------------------- approve mode

def test_default_policy_waits_for_approval_and_reports(svc):
    assert svc.post("/pubsub", json=push()).status_code == 204
    assert svc.get("/incidents").json()[0]["status"] == "awaiting_approval"
    assert svc.state["executed"] == [] and svc.state["sent"] == ["awaiting_approval"]


def test_slack_button_approves_and_executes(svc):
    svc.post("/pubsub", json=push())
    r = slack_post(svc)
    assert r.status_code == 200
    assert svc.state["executed"] == [("rollback", "checkout", "checkout-00001-abc")]
    inc = svc.get("/incidents").json()[0]
    assert inc["status"] == "rolled_back" and inc["approved_by"] == "slack:U_ALICE"
    assert svc.state["updates"] == ["rolled_back"]


def test_slack_reject(svc):
    svc.post("/pubsub", json=push())
    slack_post(svc, action="reject")
    assert svc.state["executed"] == []
    assert svc.get("/incidents").json()[0]["status"] == "rejected"


def test_slack_bad_signature_rejected(svc):
    svc.post("/pubsub", json=push())
    assert slack_post(svc, secret="wrong").status_code == 401
    assert svc.state["executed"] == []


def test_slack_replay_rejected(svc):
    svc.post("/pubsub", json=push())
    assert slack_post(svc, ts=int(time.time()) - 600).status_code == 401


def test_slack_non_approver_cannot_approve(svc):
    svc.post("/pubsub", json=push())
    r = slack_post(svc, user="U_MALLORY")
    assert r.status_code == 200 and "not on the approver list" in r.json()["text"]
    assert svc.state["executed"] == []
    assert svc.get("/incidents").json()[0]["status"] == "awaiting_approval"


def test_second_click_does_nothing(svc):
    svc.post("/pubsub", json=push())
    slack_post(svc)
    slack_post(svc)
    assert len(svc.state["executed"]) == 1


def test_cli_approve_still_works(svc):
    svc.post("/pubsub", json=push())
    r = svc.post("/incidents/i-1/approve", json={"note": "lgtm"})
    assert r.json()["status"] == "rolled_back"
    assert svc.post("/incidents/i-1/approve", json={}).status_code == 409


# ----------------------------------------------------------------- auto mode

def test_auto_mode_scales_without_waiting(svc, monkeypatch):
    monkeypatch.setenv("AUTONOMY", "auto")
    svc.state["proposal"] = SCALE
    svc.post("/pubsub", json=push())
    assert svc.state["executed"] == [("scale", "checkout", 4)]
    assert svc.get("/incidents").json()[0]["status"] == "auto_remediated"
    assert svc.state["sent"] == ["auto_remediated"]


def test_auto_mode_still_asks_for_actions_not_listed(svc, monkeypatch):
    monkeypatch.setenv("AUTONOMY", "auto")  # AUTO_ACTIONS defaults to "scale" only
    svc.post("/pubsub", json=push())       # proposal is a rollback
    assert svc.state["executed"] == []
    assert svc.get("/incidents").json()[0]["status"] == "awaiting_approval"


# ----------------------------------------------------------------- plumbing

def test_duplicate_and_closed_alerts_ignored(svc):
    svc.post("/pubsub", json=push())
    svc.post("/pubsub", json=push())
    svc.post("/pubsub", json=push("i-2", "closed"))
    assert len(svc.get("/incidents").json()) == 1


def test_malformed_message_is_acked(svc):
    assert svc.post("/pubsub", json={"message": {"data": "!!"}}).status_code == 204


def test_endpoints_need_tokens_when_auth_is_real(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    import importlib
    import main
    from fastapi.testclient import TestClient
    real = importlib.reload(main)  # fresh module: real auth functions, nothing patched
    from google.oauth2 import id_token

    def reject(token, request, audience=None):  # offline stand-in for Google's signature check
        raise ValueError("bad token")
    monkeypatch.setattr(id_token, "verify_oauth2_token", reject)
    c = TestClient(real.app)
    assert c.post("/pubsub", json=push()).status_code == 401
    assert c.get("/incidents").status_code == 401
    assert c.get("/incidents", headers={"authorization": "Bearer not-a-jwt"}).status_code == 401
    assert c.post("/slack/actions", content=b"payload=%7B%7D").status_code == 401


def test_valid_token_but_wrong_identity_is_forbidden(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("APPROVER_EMAILS", "ronald@example.com")
    import importlib
    import main
    from fastapi.testclient import TestClient
    real = importlib.reload(main)
    from google.oauth2 import id_token
    monkeypatch.setattr(id_token, "verify_oauth2_token",
                        lambda t, r, audience=None: {"email": "mallory@example.com", "email_verified": True})
    c = TestClient(real.app)
    h = {"authorization": "Bearer x"}
    assert c.get("/incidents", headers=h).status_code == 403
    assert c.post("/pubsub", json=push(), headers=h).status_code == 403


def test_policy_decide(monkeypatch):
    from sre_agent import policy
    monkeypatch.delenv("AUTONOMY", raising=False)
    assert policy.decide(SCALE) == "approve"
    monkeypatch.setenv("AUTONOMY", "auto")
    assert policy.decide(SCALE) == "auto"
    assert policy.decide(ROLLBACK) == "approve"
    monkeypatch.setenv("AUTO_ACTIONS", "scale,rollback")
    assert policy.decide(ROLLBACK) == "auto"
    monkeypatch.setenv("AUTONOMY", "yolo")  # unknown -> safe default
    assert policy.decide(SCALE) == "approve"
    assert policy.decide(None) == "none"


def test_notify_text_and_buttons():
    import notify
    inc = {"incident_id": "i-9", "status": "awaiting_approval", "service": "checkout", "policy": "p",
           "findings": "<b>cpu 0.97</b>", "proposal": SCALE}
    blocks = notify.slack_blocks(inc)
    assert "&lt;b&gt;" in blocks[0]["text"]["text"]
    assert [e["action_id"] for e in blocks[1]["elements"]] == ["approve", "reject"]
    assert "max_instances=4" in notify.describe(SCALE)
    done = dict(inc, status="auto_remediated")
    assert len(notify.slack_blocks(done)) == 1  # no buttons once acted on


def test_notify_skips_unconfigured_channels(monkeypatch):
    import importlib
    import notify
    notify = importlib.reload(notify)
    for k in ("SLACK_WEBHOOK_URL", "SMTP_HOST", "EMAIL_TO"):
        monkeypatch.delenv(k, raising=False)
    inc = {"incident_id": "i", "status": "scaled", "service": "checkout", "policy": "p", "proposal": SCALE}
    assert notify.report(inc) == {"slack": False, "email": False}


def test_tools_refuse_services_outside_allow_list(monkeypatch):
    from sre_agent import tools
    monkeypatch.setattr(tools, "PROJECT", "demo-project")
    assert "Refused" in tools.rollback_traffic("payments", "payments-0001")["error"]
    assert "Refused" in tools.get_recent_errors("payments")["error"]
    assert "Refused" in tools.scale_service("payments", max_instances=4)["error"]
