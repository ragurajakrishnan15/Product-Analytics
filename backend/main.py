from __future__ import annotations

import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

try:
    from statsmodels.stats.proportion import proportions_ztest, proportion_confint
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("statsmodels is required; install requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
DB_PATH = ROOT / "voiceiq.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)

app = FastAPI(
    title="VoiceIQ Product Analytics API",
    version="1.0.0",
    description="Backend API for an AI Voice product analytics portfolio case study.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sqlite_conn():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Seed a local SQLite database from the reproducible CSV artifacts."""
    if DATABASE_URL.startswith("sqlite") and DB_PATH.exists():
        with _sqlite_conn() as conn:
            tables = {
                row[0] for row in conn.execute("select name from sqlite_master where type='table'").fetchall()
            }
            if {"customers", "calls"}.issubset(tables):
                return

    customers = pd.read_csv(DATA_DIR / "customers.csv")
    calls = pd.read_csv(DATA_DIR / "calls.csv")
    customers.to_sql("customers", engine, if_exists="replace", index=False)
    calls.to_sql("calls", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        if DATABASE_URL.startswith("sqlite"):
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calls_customer ON calls(customer_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calls_week ON calls(week)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_plan ON customers(plan)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_customers_group ON customers(experiment_group)"))


@app.on_event("startup")
def startup() -> None:
    init_db()


def scalar(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


def records(sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(text(sql), params or {}).fetchall()]


def _to_json_safe(value):
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _safe_records(rows: list[dict]) -> list[dict]:
    return [{k: _to_json_safe(v) for k, v in row.items()} for row in rows]


def experiment_payload() -> dict:
    rows = records(
        """
        SELECT experiment_group,
               COUNT(*) AS n,
               SUM(ai_adopted) AS adopters,
               AVG(ai_adopted) AS rate
        FROM customers
        GROUP BY experiment_group
        ORDER BY experiment_group
        """
    )
    by_group = {r["experiment_group"].lower(): r for r in rows}
    control = by_group["control"]
    treatment = by_group["treatment"]
    counts = [int(control["adopters"]), int(treatment["adopters"])]
    nobs = [int(control["n"]), int(treatment["n"])]
    z_stat, p_value = proportions_ztest(counts, nobs)
    control_rate = float(control["rate"])
    treatment_rate = float(treatment["rate"])
    absolute_lift = treatment_rate - control_rate
    relative_lift = absolute_lift / control_rate if control_rate else 0.0
    ci_treat = proportion_confint(counts[1], nobs[1], alpha=0.05, method="wilson")
    ci_ctrl = proportion_confint(counts[0], nobs[0], alpha=0.05, method="wilson")

    seg = records(
        """
        SELECT company_size AS segment,
               AVG(CASE WHEN experiment_group='Control' THEN ai_adopted END) AS control_adoption,
               AVG(CASE WHEN experiment_group='Treatment' THEN ai_adopted END) AS treatment_adoption,
               COUNT(*) AS n
        FROM customers
        GROUP BY company_size
        ORDER BY CASE company_size WHEN 'SMB' THEN 1 WHEN 'Mid-Market' THEN 2 ELSE 3 END
        """
    )
    return {
        "control": {"n": nobs[0], "adopters": counts[0], "rate": control_rate},
        "treatment": {"n": nobs[1], "adopters": counts[1], "rate": treatment_rate},
        "absolute_lift": absolute_lift,
        "relative_lift": relative_lift,
        "p_value": float(p_value),
        "z_stat": float(z_stat),
        "difference_ci": {"low": float(absolute_lift - 1.96 * math.sqrt(max(1e-12, control_rate*(1-control_rate)/nobs[0] + treatment_rate*(1-treatment_rate)/nobs[1]))),
                           "high": float(absolute_lift + 1.96 * math.sqrt(max(1e-12, control_rate*(1-control_rate)/nobs[0] + treatment_rate*(1-treatment_rate)/nobs[1])))},
        "control_ci": {"low": float(ci_ctrl[0]), "high": float(ci_ctrl[1])},
        "treatment_ci": {"low": float(ci_treat[0]), "high": float(ci_treat[1])},
        "segments": _safe_records(seg),
    }


@app.get("/api/health")
def api_health() -> dict:
    return {
        "status": "ok",
        "service": "voiceiq-api",
        "database": "sqlite" if DATABASE_URL.startswith("sqlite") else "postgresql",
        "customers": int(scalar("SELECT COUNT(*) FROM customers")),
        "calls": int(scalar("SELECT COUNT(*) FROM calls")),
    }


@app.get("/api/kpis")
def kpis() -> dict:
    row = records(
        """
        SELECT COUNT(*) AS customers,
               SUM(calls_12w) AS calls,
               AVG(ai_adopted) AS ai_adoption_rate,
               AVG(retained_8w) AS retention_8w,
               AVG(health_score) AS avg_health,
               SUM(annual_revenue) AS annual_revenue
        FROM customers
        """
    )[0]
    return _safe_records([row])[0]


@app.get("/api/weekly")
def weekly() -> list[dict]:
    rows = records(
        """
        SELECT week,
               COUNT(DISTINCT customer_id) AS active_customers,
               AVG(CASE WHEN ai_handled=1 THEN 1.0 ELSE 0 END) AS ai_handling_share
        FROM calls
        GROUP BY week
        ORDER BY week
        """
    )
    adopted = scalar("SELECT AVG(ai_adopted) FROM customers")
    for r in rows:
        r["ai_adoption_rate"] = float(adopted)
    return _safe_records(rows)


@app.get("/api/features")
def features() -> list[dict]:
    # Keep a small metric layer derived from the customer table; feature counts are synthetic but reproducible.
    rows = [
        {"feature": "AI Voice Agent", "adoption_rate": float(scalar("SELECT AVG(ai_adopted) FROM customers"))},
        {"feature": "WhatsApp", "adoption_rate": 0.51},
        {"feature": "Analytics", "adoption_rate": 0.43},
        {"feature": "Call Routing", "adoption_rate": 0.36},
        {"feature": "AI Assist", "adoption_rate": 0.27},
        {"feature": "Integrations", "adoption_rate": 0.22},
    ]
    return rows


@app.get("/api/experiment")
def experiment() -> dict:
    return experiment_payload()


@app.get("/api/cohorts")
def cohorts() -> list[dict]:
    # cohort-retention view from the source artifact; exposed through the backend API for the live site.
    csv = pd.read_csv(SITE_DIR / "data" / "cohorts.csv")
    return json.loads(csv.to_json(orient="records"))


@app.get("/api/health-distribution")
def health_distribution() -> list[dict]:
    rows = records(
        """
        SELECT CASE
                 WHEN health_score < 30 THEN 'Critical'
                 WHEN health_score < 45 THEN 'At risk'
                 WHEN health_score < 60 THEN 'Watch'
                 WHEN health_score < 75 THEN 'Healthy'
                 ELSE 'Advocate'
               END AS band,
               COUNT(*) AS customers
        FROM customers
        GROUP BY band
        ORDER BY CASE band WHEN 'Critical' THEN 1 WHEN 'At risk' THEN 2 WHEN 'Watch' THEN 3 WHEN 'Healthy' THEN 4 ELSE 5 END
        """
    )
    return rows


@app.get("/api/agent")
def agent() -> dict:
    row = records(
        """
        SELECT COUNT(*) AS ai_calls,
               AVG(CASE WHEN ai_handled=1 THEN resolved END) AS resolution_rate,
               AVG(CASE WHEN ai_handled=1 THEN escalated END) AS escalation_rate,
               AVG(CASE WHEN ai_handled=1 THEN quality_score END) AS avg_quality_score,
               AVG(CASE WHEN ai_handled=1 THEN duration_sec END) AS avg_handle_time_sec
        FROM calls
        """
    )[0]
    return row


@app.get("/api/customers")
def customers(
    plan: Optional[str] = Query(default=None),
    size: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=5000),
) -> list[dict]:
    clauses = []
    params: dict = {"limit": limit}
    if plan and plan != "All":
        clauses.append("plan = :plan")
        params["plan"] = plan
    if size and size != "All":
        clauses.append("company_size = :size")
        params["size"] = size
    if q:
        clauses.append("(customer_id LIKE :q OR plan LIKE :q OR company_size LIKE :q OR industry LIKE :q OR region LIKE :q)")
        params["q"] = f"%{q}%"
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = records(
        f"""
        SELECT customer_id, plan, company_size, industry, region,
               ai_adopted, calls_12w, health_score, churn_risk, annual_revenue,
               active_weeks, feature_count, retained_8w
        FROM customers
        {where}
        ORDER BY churn_risk DESC, health_score ASC
        LIMIT :limit
        """,
        params,
    )
    return _safe_records(rows)


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str) -> dict:
    rows = records(
        "SELECT * FROM customers WHERE customer_id = :customer_id LIMIT 1",
        {"customer_id": customer_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Customer not found")
    calls = records(
        """
        SELECT week, call_type, ai_handled, duration_sec, resolved, escalated, quality_score
        FROM calls WHERE customer_id = :customer_id ORDER BY week
        """,
        {"customer_id": customer_id},
    )
    return {"customer": _safe_records(rows)[0], "calls": _safe_records(calls)}


@app.get("/api/export/customers.csv")
def export_customers() -> FileResponse:
    export_path = ROOT / "data" / "customers.csv"
    return FileResponse(export_path, media_type="text/csv", filename="voiceiq_customers.csv")


# Static frontend — the same FastAPI process serves the recruiter-facing website and the live API.
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
