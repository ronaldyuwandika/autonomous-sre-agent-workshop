import base64
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agent"), str(ROOT / "service")]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    import main
    from fastapi.testclient import TestClient

    main.INCIDENTS.clear()

    async def fake_investigate(incident_id):
        main.INCIDENTS[incident_id].update(
            status="awaiting_approval", findings="v2 fails 50%",
            proposal={"service": "checkout", "revision": "checkout-00001-abc", "reason": "v2 5xx"})

    monkeypatch.setattr(main, "investigate", fake_investigate)
    calls = []
    monkeypatch.setattr(main, "rollback_traffic", lambda s, r: calls.append((s, r)) or {"status": "done"})
    c = TestClient(main.app)
    c.calls = calls
    return c


def push(incident):
    data = base64.b64encode(json.dumps({"incident": incident}).encode()).decode()
    return {"message": {"data": data, "messageId": "1"}, "subscription": "s"}


ALERT = {"incident_id": "i-1", "state": "open", "policy_name": "checkout 5xx",
         "resource": {"labels": {"service_name": "checkout"}}, "summary": "5xx high"}


def test_alert_creates_incident_and_approval_rolls_back(client):
    assert client.post("/pubsub", json=push(ALERT)).status_code == 204
    inc = client.get("/incidents").json()[0]
    assert inc["status"] == "awaiting_approval"
    r = client.post("/incidents/i-1/approve", json={"approver": "ronald@example.com"})
    assert r.json()["status"] == "rolled_back"
    assert client.calls == [("checkout", "checkout-00001-abc")]


def test_cannot_approve_twice(client):
    client.post("/pubsub", json=push(ALERT))
    client.post("/incidents/i-1/approve", json={"approver": "a@b.c"})
    assert client.post("/incidents/i-1/approve", json={"approver": "a@b.c"}).status_code == 409


def test_duplicate_and_closed_alerts_ignored(client):
    client.post("/pubsub", json=push(ALERT))
    client.post("/pubsub", json=push(ALERT))
    client.post("/pubsub", json=push({**ALERT, "incident_id": "i-2", "state": "closed"}))
    assert len(client.get("/incidents").json()) == 1


def test_malformed_message_is_acked(client):
    assert client.post("/pubsub", json={"message": {"data": "!!"}}).status_code == 204


def test_tools_refuse_services_outside_allow_list(monkeypatch):
    from sre_agent import tools
    monkeypatch.setattr(tools, "PROJECT", "demo-project")
    assert "Refused" in tools.rollback_traffic("payments", "payments-0001")["error"]
    assert "Refused" in tools.get_recent_errors("payments")["error"]
