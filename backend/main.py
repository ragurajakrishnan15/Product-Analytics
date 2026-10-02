from __future__ import annotations

import io
import json
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, inspect, text

try:
    import statsmodels.api as sm
    from scipy.stats import mannwhitneyu, norm
    from statsmodels.stats.proportion import proportion_confint, proportions_ztest
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("statsmodels and scipy are required; install requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
DB_PATH = ROOT / "voiceiq.db"
RAW_TABLES = ["customers", "calls", "feature_usage"]
SOURCE_FILES = [DATA_DIR / f"{t}.csv" for t in RAW_TABLES] + [ROOT / "sql" / "00_customer_metrics.sql", Path(__file__)]
CUSTOMER_METRICS_SQL = (ROOT / "sql" / "00_customer_metrics.sql").read_text(encoding="utf-8")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if IS_SQLITE else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)

# Single definition of the health bands: (exclusive upper bound, label). Used by the API, the
# static snapshot and the docs, so every surface reports the same distribution.
HEALTH_BANDS = [(35, "Critical"), (50, "At risk"), (65, "Watch"), (80, "Healthy"), (None, "Advocate")]
AT_RISK_BANDS = ("Critical", "At risk")

# Behavioural features used by the churn-risk model (all observable in the event data).
CHURN_FEATURES = {
    "active_week_share": "Share of weeks active",
    "calls_per_active_week": "Calls per active week",
    "feature_count": "Features used",
    "resolution_rate": "Call resolution rate",
    "ai_adopted": "AI Voice Agent adopted",
    "recently_active": "Active in last 2 weeks",
}
COHORT_WEEKS = 8


# ---------------------------------------------------------------- database build

def _sqlite_db_is_current() -> bool:
    db_file = Path(engine.url.database or "")
    if not db_file.exists():
        return False
    if db_file.stat().st_mtime < max(p.stat().st_mtime for p in SOURCE_FILES):
        return False  # raw data or metric logic changed after the DB was built
    return {*RAW_TABLES, "customer_metrics", "model_summary"}.issubset(inspect(engine).get_table_names())


def _auc(y_true: np.ndarray, score: np.ndarray) -> float:
    pos, neg = score[y_true == 1], score[y_true == 0]
    return float(mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg)))


def fit_churn_model(metrics: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Logistic regression of 8-week churn on standardised behaviour; returns (risk per customer, summary)."""
    y = (1 - metrics["retained_8w"]).to_numpy()
    raw = metrics[list(CHURN_FEATURES)].astype(float)
    X = sm.add_constant((raw - raw.mean()) / raw.std())
    train = np.random.default_rng(7).random(len(metrics)) < 0.7
    model = sm.Logit(y[train], X[train]).fit(disp=False)
    risk = model.predict(X)
    summary = {
        "outcome": "churned within 8 weeks (1 - retained_8w)",
        "method": "Logistic regression on standardised features; 70/30 train/holdout split",
        "n_train": int(train.sum()),
        "n_holdout": int((~train).sum()),
        "holdout_auc": _auc(y[~train], risk[~train]),
        "base_churn_rate": float(y.mean()),
        "caveat": ("Features and outcome share the same 12-week window, which inflates the AUC. In production, "
                   "score accounts at a cutoff date and predict churn after it."),
        "drivers": sorted(
            [{"feature": label, "odds_ratio_per_sd": float(math.exp(model.params[col])), "p_value": float(model.pvalues[col])}
             for col, label in CHURN_FEATURES.items()],
            key=lambda d: abs(math.log(d["odds_ratio_per_sd"])), reverse=True,
        ),
    }
    return risk, summary


def init_db() -> None:
    """Load the raw tables, derive the customer metric layer and fit the churn model."""
    if IS_SQLITE and _sqlite_db_is_current():
        return
    for table in RAW_TABLES:
        pd.read_csv(DATA_DIR / f"{table}.csv").to_sql(table, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calls_customer ON calls(customer_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_calls_week ON calls(week)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_features_customer ON feature_usage(customer_id)"))

    with engine.connect() as conn:
        metrics = pd.read_sql(text(CUSTOMER_METRICS_SQL), conn)
    risk, summary = fit_churn_model(metrics)
    metrics["churn_risk"] = np.round(risk, 4)
    metrics.to_sql("customer_metrics", engine, if_exists="replace", index=False)
    pd.DataFrame([{"key": "churn_model", "value": json.dumps(summary)}]).to_sql(
        "model_summary", engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_metrics_customer ON customer_metrics(customer_id)"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="VoiceIQ Product Analytics API",
    version="2.0.0",
    description="Backend API for an AI Voice product analytics portfolio case study.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def scalar(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


def records(sql: str, params: dict | None = None) -> list[dict]:
    with engine.connect() as conn:
        return [dict(row._mapping) for row in conn.execute(text(sql), params or {}).fetchall()]


def frame(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def _to_json_safe(value):
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    return value


def _safe_records(rows: list[dict]) -> list[dict]:
    return [{k: _to_json_safe(v) for k, v in row.items()} for row in rows]


def _health_band_sql() -> str:
    whens = " ".join(f"WHEN health_score < {upper} THEN '{label}'" for upper, label in HEALTH_BANDS if upper)
    return f"CASE {whens} ELSE '{HEALTH_BANDS[-1][1]}' END"


def two_proportion_test(x_control: int, n_control: int, x_treat: int, n_treat: int) -> dict:
    """Difference in proportions (treatment - control) with a Wald 95% CI and a two-sided z-test."""
    p_c, p_t = x_control / n_control, x_treat / n_treat
    se = math.sqrt(p_c * (1 - p_c) / n_control + p_t * (1 - p_t) / n_treat)
    z, p = proportions_ztest([x_treat, x_control], [n_treat, n_control])
    return {"diff": p_t - p_c, "ci_low": p_t - p_c - 1.96 * se, "ci_high": p_t - p_c + 1.96 * se,
            "z": float(z), "p_value": float(p)}


def minimum_detectable_effect(p: float, n_control: int, n_treat: int, alpha: float = 0.05, power: float = 0.8) -> float:
    return (norm.ppf(1 - alpha / 2) + norm.ppf(power)) * math.sqrt(p * (1 - p) * (1 / n_control + 1 / n_treat))


def classify(test: dict) -> str:
    if test["ci_low"] > 0:
        return "positive"
    if test["ci_high"] < 0:
        return "negative"
    return "inconclusive"


# ---------------------------------------------------------------- metric payloads

def kpis_payload() -> dict:
    row = records(
        """
        SELECT COUNT(*) AS customers,
               SUM(calls_12w) AS calls,
               AVG(ai_adopted * 1.0) AS ai_adoption_rate,
               AVG(retained_8w * 1.0) AS retention_8w,
               AVG(health_score) AS avg_health,
               SUM(annual_revenue) AS annual_revenue
        FROM customer_metrics
        """
    )[0]
    return _safe_records([row])[0]


def weekly_payload() -> list[dict]:
    rows = records(
        """
        SELECT week,
               COUNT(DISTINCT customer_id) AS active_customers,
               COUNT(*) AS calls,
               AVG(CASE WHEN ai_handled=1 THEN 1.0 ELSE 0 END) AS ai_handling_share
        FROM calls
        GROUP BY week
        ORDER BY week
        """
    )
    # Cumulative adoption: share of all customers who had turned on the AI Voice Agent by week w.
    total = int(scalar("SELECT COUNT(*) FROM customers"))
    adoptions = {r["first_used_week"]: int(r["n"]) for r in records(
        "SELECT first_used_week, COUNT(*) AS n FROM feature_usage WHERE feature='AI Voice Agent' GROUP BY first_used_week")}
    cumulative = 0
    for r in rows:
        cumulative += adoptions.get(r["week"], 0)
        r["ai_adoption_rate"] = cumulative / total
    return _safe_records(rows)


def features_payload() -> list[dict]:
    rows = records(
        """
        SELECT feature, COUNT(DISTINCT customer_id) * 1.0 / (SELECT COUNT(*) FROM customers) AS adoption_rate
        FROM feature_usage
        GROUP BY feature
        ORDER BY adoption_rate DESC
        """
    )
    return _safe_records(rows)


def experiment_payload() -> dict:
    groups = {r["experiment_group"]: r for r in records(
        """
        SELECT experiment_group,
               COUNT(*) AS n,
               SUM(ai_adopted) AS adopters,
               SUM(retained_8w) AS retained
        FROM customer_metrics
        GROUP BY experiment_group
        """
    )}
    c, t = groups["Control"], groups["Treatment"]
    n_c, n_t = int(c["n"]), int(t["n"])
    adoption = two_proportion_test(int(c["adopters"]), n_c, int(t["adopters"]), n_t)
    retention = two_proportion_test(int(c["retained"]), n_c, int(t["retained"]), n_t)
    control_rate, treatment_rate = int(c["adopters"]) / n_c, int(t["adopters"]) / n_t
    ci_ctrl = proportion_confint(int(c["adopters"]), n_c, alpha=0.05, method="wilson")
    ci_treat = proportion_confint(int(t["adopters"]), n_t, alpha=0.05, method="wilson")

    segments = []
    for s in records(
        """
        SELECT company_size AS segment,
               SUM(CASE WHEN experiment_group='Control' THEN ai_adopted ELSE 0 END) AS control_adopters,
               SUM(CASE WHEN experiment_group='Control' THEN 1 ELSE 0 END) AS control_n,
               SUM(CASE WHEN experiment_group='Treatment' THEN ai_adopted ELSE 0 END) AS treatment_adopters,
               SUM(CASE WHEN experiment_group='Treatment' THEN 1 ELSE 0 END) AS treatment_n
        FROM customer_metrics
        GROUP BY company_size
        ORDER BY CASE company_size WHEN 'SMB' THEN 1 WHEN 'Mid-Market' THEN 2 ELSE 3 END
        """
    ):
        xc, nc, xt, nt = (int(s[k]) for k in ("control_adopters", "control_n", "treatment_adopters", "treatment_n"))
        test = two_proportion_test(xc, nc, xt, nt)
        segments.append({
            "segment": s["segment"], "control_n": nc, "treatment_n": nt, "n": nc + nt,
            "control_adoption": xc / nc, "treatment_adoption": xt / nt,
            "relative_lift": test["diff"] / (xc / nc) if xc else 0.0,
            "diff_ci": {"low": test["ci_low"], "high": test["ci_high"]},
            "p_value": test["p_value"],
            "result": classify(test),
            "mde": float(minimum_detectable_effect(xc / nc, nc, nt)),
        })

    return {
        "control": {"n": n_c, "adopters": int(c["adopters"]), "rate": control_rate, "retention_8w": int(c["retained"]) / n_c},
        "treatment": {"n": n_t, "adopters": int(t["adopters"]), "rate": treatment_rate, "retention_8w": int(t["retained"]) / n_t},
        "absolute_lift": adoption["diff"],
        "relative_lift": adoption["diff"] / control_rate if control_rate else 0.0,
        "p_value": adoption["p_value"],
        "z_stat": adoption["z"],
        "difference_ci": {"low": adoption["ci_low"], "high": adoption["ci_high"]},
        "control_ci": {"low": float(ci_ctrl[0]), "high": float(ci_ctrl[1])},
        "treatment_ci": {"low": float(ci_treat[0]), "high": float(ci_treat[1])},
        "mde": float(minimum_detectable_effect(control_rate, n_c, n_t)),
        "sample_ratio": n_t / (n_c + n_t),
        "retention_guardrail": {"diff": retention["diff"], "ci_low": retention["ci_low"], "ci_high": retention["ci_high"],
                                "p_value": retention["p_value"], "result": classify(retention)},
        "segments": segments,
    }


def cohorts_payload() -> list[dict]:
    """Weekly signup cohorts (accounts that signed up inside the event window) x weeks since signup."""
    customers = frame("SELECT customer_id, signup_date FROM customers")
    calls = frame("SELECT DISTINCT customer_id, week FROM calls")
    weeks = pd.to_datetime(sorted(calls["week"].unique()))
    customers["signup_week"] = pd.to_datetime(customers["signup_date"]).dt.to_period("W-SUN").dt.start_time
    cohort_customers = customers[customers["signup_week"] >= weeks[0]]
    activity = calls.merge(cohort_customers, on="customer_id")
    activity["age"] = (pd.to_datetime(activity["week"]) - activity["signup_week"]).dt.days // 7
    out = []
    for cohort, members in cohort_customers.groupby("signup_week"):
        size = len(members)
        observable = int((weeks[-1] - cohort).days // 7) + 1
        active = activity[activity["signup_week"] == cohort].groupby("age")["customer_id"].nunique()
        row = {"cohort": cohort.strftime("%Y-%m-%d"), "customers": size}
        for k in range(COHORT_WEEKS):
            row[f"W{k}"] = round(float(active.get(k, 0)) / size, 4) if k < observable else None
        out.append(row)
    return out


def health_distribution_payload() -> list[dict]:
    rows = records(
        f"""
        SELECT {_health_band_sql()} AS band,
               COUNT(*) AS customers,
               SUM(annual_revenue) AS annual_revenue,
               AVG(retained_8w * 1.0) AS retention_8w
        FROM customer_metrics
        GROUP BY band
        """
    )
    present = {r["band"]: r for r in rows}
    return [
        {"band": label,
         "customers": int(present.get(label, {}).get("customers") or 0),
         "annual_revenue": int(present.get(label, {}).get("annual_revenue") or 0),
         "retention_8w": _to_json_safe(present.get(label, {}).get("retention_8w"))}
        for _, label in HEALTH_BANDS
    ]


def churn_model_payload() -> dict:
    return json.loads(scalar("SELECT value FROM model_summary WHERE key = 'churn_model'"))


def agent_payload() -> dict:
    rows = records(
        """
        SELECT ai_handled,
               COUNT(*) AS calls,
               AVG(resolved * 1.0) AS resolution_rate,
               AVG(escalated * 1.0) AS escalation_rate,
               AVG(quality_score) AS avg_quality_score,
               AVG(duration_sec * 1.0) AS avg_handle_time_sec,
               AVG(first_response_min) AS avg_first_response_min
        FROM calls
        GROUP BY ai_handled
        """
    )
    by_kind = {int(r.pop("ai_handled")): r for r in rows}
    ai = by_kind.get(1, {})
    human = by_kind.get(0, {})
    return _safe_records([{
        "ai_calls": int(ai.get("calls") or 0),
        "resolution_rate": ai.get("resolution_rate"),
        "escalation_rate": ai.get("escalation_rate"),
        "avg_quality_score": ai.get("avg_quality_score"),
        "avg_handle_time_sec": ai.get("avg_handle_time_sec"),
        "avg_first_response_min": ai.get("avg_first_response_min"),
    }])[0] | {"human_baseline": _safe_records([human])[0] if human else {}}


def _pp(x: float) -> str:
    return f"{x * 100:+.1f}"


def insights_payload(kpis: dict, experiment: dict, agent: dict, health: list[dict], churn: dict) -> list[str]:
    """Decision-ready insights generated from the computed metrics (never hardcoded numbers)."""
    insights = []

    plan_rows = records("SELECT plan, AVG(ai_adopted * 1.0) AS rate FROM customer_metrics GROUP BY plan ORDER BY rate")
    lowest = plan_rows[0]
    not_adopted = kpis["customers"] - round(kpis["ai_adoption_rate"] * kpis["customers"])
    insights.append(
        f"AI Voice Agent adoption is {kpis['ai_adoption_rate']:.1%} of accounts; {not_adopted:,} customers "
        f"({1 - kpis['ai_adoption_rate']:.0%}) have not adopted. {lowest['plan']} is the weakest plan at "
        f"{lowest['rate']:.1%}. RECOMMENDATION: target in-app onboarding at non-adopters, starting with {lowest['plan']}."
    )

    e = experiment
    ci, g = e["difference_ci"], e["retention_guardrail"]
    guardrail = (f"8-week retention moved {_pp(g['diff'])} pp (95% CI {_pp(g['ci_low'])} to {_pp(g['ci_high'])}), "
                 + ("not a significant change" if g["result"] == "inconclusive" else f"a significant {g['result']} change"))
    if e["p_value"] < 0.05 and e["absolute_lift"] > 0:
        unclear = [s for s in e["segments"] if s["result"] != "positive"]
        harmed = [s for s in e["segments"] if s["result"] == "negative"]
        text_ = (f"Treatment lifted AI adoption from {e['control']['rate']:.1%} to {e['treatment']['rate']:.1%} "
                 f"({e['relative_lift']:+.1%} relative, p={e['p_value']:.2g}, 95% CI {_pp(ci['low'])} to {_pp(ci['high'])} pp). "
                 f"{guardrail}.")
        if harmed:
            text_ += f" Adoption fell significantly in {', '.join(s['segment'] for s in harmed)}."
        if unclear:
            details = "; ".join(f"{s['segment']} (n={s['n']:,}, CI {_pp(s['diff_ci']['low'])} to {_pp(s['diff_ci']['high'])} pp)"
                                for s in unclear if s["result"] == "inconclusive")
            if details:
                text_ += f" Segment reads are exploratory; the effect is inconclusive in {details}."
        text_ += (" RECOMMENDATION: ramp exposure in stages, keep retention as a guardrail, and size a follow-up test "
                  "for under-powered segments before a full rollout.")
        insights.append(text_)
    else:
        insights.append(
            f"The experiment shows no significant adoption difference ({e['control']['rate']:.1%} vs "
            f"{e['treatment']['rate']:.1%}, p={e['p_value']:.2g}; minimum detectable effect {e['mde'] * 100:.1f} pp). "
            f"RECOMMENDATION: do not ship on this evidence."
        )

    human = agent["human_baseline"]
    if human:
        insights.append(
            f"AI-handled calls resolve at {agent['resolution_rate']:.1%} vs {human['resolution_rate']:.1%} for "
            f"human-handled calls, with quality {agent['avg_quality_score']:.2f}/5 vs {human['avg_quality_score']:.2f}/5 "
            f"(observational; AI calls are not randomly assigned). RECOMMENDATION: segment escalations by call type "
            f"before expanding AI coverage."
        )

    top = churn["drivers"][0]
    risk = [b for b in health if b["band"] in AT_RISK_BANDS]
    risk_n = sum(b["customers"] for b in risk)
    risk_arr = sum(b["annual_revenue"] for b in risk)
    insights.append(
        f"The churn model (holdout AUC {churn['holdout_auc']:.2f}) ranks '{top['feature']}' as the strongest signal "
        f"(odds ratio {top['odds_ratio_per_sd']:.2f} per SD). {risk_n:,} accounts ({risk_n / kpis['customers']:.0%}) sit in "
        f"the {' / '.join(AT_RISK_BANDS)} health bands, carrying ${risk_arr:,.0f} in ARR. RECOMMENDATION: route them to "
        f"customer success, prioritised by churn risk x ARR."
    )
    return insights


def dashboard_payload() -> dict:
    kpis = kpis_payload()
    experiment = experiment_payload()
    agent = agent_payload()
    health = health_distribution_payload()
    churn = churn_model_payload()
    return {
        "kpis": kpis,
        "weekly": weekly_payload(),
        "features": features_payload(),
        "experiment": experiment,
        "cohorts": cohorts_payload(),
        "health_distribution": health,
        "churn_model": churn,
        "agent_metrics": agent,
        "insights": insights_payload(kpis, experiment, agent, health, churn),
    }


def customers_payload(plan: Optional[str] = None, size: Optional[str] = None, q: Optional[str] = None,
                      limit: int = 100) -> list[dict]:
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
        FROM customer_metrics
        {where}
        ORDER BY churn_risk DESC, health_score ASC
        LIMIT :limit
        """,
        params,
    )
    return _safe_records(rows)


# ---------------------------------------------------------------- routes

@app.get("/api/health")
def api_health() -> dict:
    return {
        "status": "ok",
        "service": "voiceiq-api",
        "database": "sqlite" if IS_SQLITE else "postgresql",
        "customers": int(scalar("SELECT COUNT(*) FROM customers")),
        "calls": int(scalar("SELECT COUNT(*) FROM calls")),
    }


@app.get("/api/dashboard")
def dashboard() -> dict:
    return dashboard_payload()


@app.get("/api/kpis")
def kpis() -> dict:
    return kpis_payload()


@app.get("/api/weekly")
def weekly() -> list[dict]:
    return weekly_payload()


@app.get("/api/features")
def features() -> list[dict]:
    return features_payload()


@app.get("/api/experiment")
def experiment() -> dict:
    return experiment_payload()


@app.get("/api/cohorts")
def cohorts() -> list[dict]:
    return cohorts_payload()


@app.get("/api/health-distribution")
def health_distribution() -> list[dict]:
    return health_distribution_payload()


@app.get("/api/churn-model")
def churn_model() -> dict:
    return churn_model_payload()


@app.get("/api/agent")
def agent() -> dict:
    return agent_payload()


@app.get("/api/insights")
def insights() -> list[str]:
    return dashboard_payload()["insights"]


@app.get("/api/customers")
def customers(
    plan: Optional[str] = Query(default=None),
    size: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=5000),
) -> list[dict]:
    return customers_payload(plan, size, q, limit)


@app.get("/api/customers/{customer_id}")
def customer_detail(customer_id: str) -> dict:
    rows = records(
        "SELECT * FROM customer_metrics WHERE customer_id = :customer_id LIMIT 1",
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
    features = records(
        "SELECT feature, first_used_week FROM feature_usage WHERE customer_id = :customer_id ORDER BY first_used_week",
        {"customer_id": customer_id},
    )
    return {"customer": _safe_records(rows)[0], "calls": _safe_records(calls), "features": features}


@app.get("/api/export/customers.csv")
def export_customers() -> StreamingResponse:
    buffer = io.StringIO()
    frame("SELECT * FROM customer_metrics ORDER BY customer_id").to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=voiceiq_customer_metrics.csv"})


# Static frontend — the same FastAPI process serves the recruiter-facing website and the live API.
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
