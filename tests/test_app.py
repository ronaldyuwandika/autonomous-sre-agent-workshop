import importlib.util
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app" / "main.py"


def load(monkeypatch, rate):
    monkeypatch.setenv("FAILURE_RATE", str(rate))
    spec = importlib.util.spec_from_file_location("checkout_app", APP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app.test_client()


def test_healthy_revision_never_fails(monkeypatch):
    c = load(monkeypatch, 0)
    assert all(c.post("/checkout", json={"amount": 1}).status_code == 200 for _ in range(50))


def test_bad_revision_fails_and_logs(monkeypatch, caplog):
    c = load(monkeypatch, 1)
    r = c.post("/checkout")
    assert r.status_code == 503
    assert "PaymentGatewayTimeout" in caplog.text
