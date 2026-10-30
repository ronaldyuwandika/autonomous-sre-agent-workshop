import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from sre_agent.tools import plan_scale  # noqa: E402

CUR = {"cpu": "1", "memory": "512Mi", "max_instances": 2, "traffic_follows_latest": True}


def test_scale_out_within_double():
    assert plan_scale(CUR, max_instances=4) == {"changes": {"max_instances": 4}}


def test_scale_out_more_than_double_refused():
    assert "Refused" in plan_scale(CUR, max_instances=5)["error"]


def test_scale_out_past_hard_cap_refused():
    assert "Refused" in plan_scale(dict(CUR, max_instances=8), max_instances=16)["error"]


def test_scale_up_one_cpu_step():
    assert plan_scale(CUR, cpu="2") == {"changes": {"cpu": "2"}}
    assert "one step" in plan_scale(CUR, cpu="4")["error"]


def test_never_scale_down():
    assert "only go up" in plan_scale(dict(CUR, cpu="2"), cpu="1")["error"]
    assert "Refused" in plan_scale(CUR, memory="256Mi")["error"]
    assert "Refused" in plan_scale(CUR, max_instances=1)["error"]


def test_memory_units_and_double_limit():
    assert plan_scale(CUR, memory="1Gi") == {"changes": {"memory": "1024Mi"}}
    assert "Refused" in plan_scale(CUR, memory="2Gi")["error"]
    assert "Refused" in plan_scale(CUR, memory="lots")["error"]


def test_pinned_traffic_refused():
    assert "pinned" in plan_scale(dict(CUR, traffic_follows_latest=False), max_instances=4)["error"]


def test_nothing_to_change_refused():
    assert "nothing to change" in plan_scale(CUR)["error"]
