"""API tests. Run with `pytest tests/`. Uses a throwaway SQLite database so the repo DB is untouched."""
import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = f"sqlite:///{Path(tempfile.mkdtemp()) / 'test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import HEALTH_BANDS, app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs the lifespan, which builds the database
        yield c


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["customers"] == 5000
    assert body["calls"] > 0


def test_kpis_are_consistent(client):
    kpis = client.get("/api/kpis").json()
    assert kpis["calls"] == client.get("/api/health").json()["calls"]
    assert 0 < kpis["ai_adoption_rate"] < 1
    assert 0 < kpis["retention_8w"] < 1


def test_agent_counts_only_ai_calls(client):
    agent = client.get("/api/agent").json()
    total = client.get("/api/health").json()["calls"]
    assert agent["ai_calls"] + agent["human_baseline"]["calls"] == total
    assert 0 < agent["ai_calls"] < total


def test_weekly_adoption_is_cumulative(client):
    rates = [w["ai_adoption_rate"] for w in client.get("/api/weekly").json()]
    assert len(rates) == 12
    assert rates == sorted(rates)
    assert rates[-1] == pytest.approx(client.get("/api/kpis").json()["ai_adoption_rate"])


def test_features_are_measured(client):
    rows = client.get("/api/features").json()
    assert len(rows) == 6
    assert all(0 < r["adoption_rate"] < 1 for r in rows)


def test_experiment_readout(client):
    e = client.get("/api/experiment").json()
    assert e["difference_ci"]["low"] <= e["absolute_lift"] <= e["difference_ci"]["high"]
    assert 0.45 < e["sample_ratio"] < 0.55
    for s in e["segments"]:
        ci = s["diff_ci"]
        expected = "positive" if ci["low"] > 0 else "negative" if ci["high"] < 0 else "inconclusive"
        assert s["result"] == expected
    assert e["retention_guardrail"]["result"] in {"positive", "negative", "inconclusive"}


def test_cohorts_are_a_valid_triangle(client):
    cohorts = client.get("/api/cohorts").json()
    assert cohorts
    for row in cohorts:
        assert row["W0"] == 1.0  # signup week is the first activity by definition
        values = [row[f"W{k}"] for k in range(8)]
        observed = [v for v in values if v is not None]
        assert all(0 <= v <= 1 for v in observed)
        assert values[:len(observed)] == observed  # blanks only at the end


def test_health_bands_cover_all_customers(client):
    bands = client.get("/api/health-distribution").json()
    assert [b["band"] for b in bands] == [label for _, label in HEALTH_BANDS]
    assert sum(b["customers"] for b in bands) == 5000


def test_churn_model(client):
    m = client.get("/api/churn-model").json()
    assert 0.5 < m["holdout_auc"] <= 1
    assert len(m["drivers"]) == 6


def test_customers_filter_and_detail(client):
    rows = client.get("/api/customers", params={"plan": "Enterprise", "limit": 20}).json()
    assert 0 < len(rows) <= 20 and all(r["plan"] == "Enterprise" for r in rows)
    risks = [r["churn_risk"] for r in rows]
    assert risks == sorted(risks, reverse=True)
    detail = client.get(f"/api/customers/{rows[0]['customer_id']}").json()
    assert detail["customer"]["customer_id"] == rows[0]["customer_id"]
    assert len(detail["calls"]) == detail["customer"]["calls_12w"]
    assert client.get("/api/customers/NOPE").status_code == 404


def test_insights_and_dashboard(client):
    dash = client.get("/api/dashboard").json()
    assert {"kpis", "weekly", "features", "experiment", "cohorts", "health_distribution", "churn_model",
            "agent_metrics", "insights"} <= dash.keys()
    assert len(dash["insights"]) == 4


def test_export_and_site(client):
    csv = client.get("/api/export/customers.csv")
    assert csv.status_code == 200 and csv.text.startswith("customer_id,")
    assert client.get("/").status_code == 200
