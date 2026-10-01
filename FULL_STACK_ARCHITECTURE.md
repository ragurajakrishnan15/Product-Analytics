# VoiceIQ Full-Stack Architecture

The recruiter site is backed by a real API and SQL database in the full-stack version.

```text
Browser / Recruiter
        |
        v
FastAPI application
  |       |        |
  |       |        +--> /api/experiment (statsmodels)
  |       +-----------> /api/customers (SQL filters)
  +-------------------> /api/kpis, /api/cohorts, /api/agent
        |
        v
SQLite by default / PostgreSQL via DATABASE_URL
        |
        v
customers + calls tables
        |
        +--> SQL metric layer
        +--> dbt models
        +--> Python experiment analysis
        +--> Airflow orchestration example
```

For a production deployment, set `DATABASE_URL` to PostgreSQL, run the ingestion/transform jobs, and deploy the FastAPI service behind HTTPS.
