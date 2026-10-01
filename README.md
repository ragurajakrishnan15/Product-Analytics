# VoiceIQ — AI Voice Product Analytics & Experimentation

**Recruiter-facing interactive portfolio project** focused on product analytics for an AI-powered customer communications platform.

> Synthetic case study inspired by the skills described in the Aircall Data Scientist, Product Analytics role. This project is independent and is not affiliated with Aircall or based on proprietary Aircall data.

## Recruiter first click

> **Note to recruiters & hiring managers:** If viewing this locally or on GitHub, you strictly **do not** need to execute any code or databases. Simply open `site/index.html` in your browser! It has been packaged with static fallback JSON data (in `site/data`) so hiring managers can view the full dashboard functionality offline, instantly! 

The `site/index.html` is the front door of the project and includes:

- Executive KPI view
- Product adoption analysis with plan/segment filters
- AI Voice Agent A/B experimentation readout
- Cohort retention matrix
- Customer health score and account explorer
- AI agent operational metrics
- Technical deep dive with SQL, Python, dbt, and Airflow examples
- Data-quality checklist and repository map

## Role-relevant skills demonstrated

| Capability | Evidence |
|---|---|
| SQL | `sql/` metric, adoption, cohort and experiment queries |
| Python | `analytics/experiment_analysis.py` |
| Product analytics | Adoption, activation, feature usage, customer health |
| Experimentation | Hypothesis, effect size, confidence interval, z-test |
| Visualization | Interactive dashboard in `site/` |
| Data engineering | dbt models + orchestration example |
| AI product analytics | AI Voice Agent usage and quality analysis |
| Stakeholder communication | Decision-ready insights and recommendations |

## Dataset

The generator creates a deterministic synthetic SaaS dataset with:

- 5,000 customers
- 59,000+ call events
- 12 simulated weeks
- plans, segments, industries and regions
- AI adoption and experiment assignment
- retention, churn risk and customer health
- AI-handled call resolution, escalation and quality metrics

Run:

```bash
pip install -r requirements.txt
python3 build_data.py
```

## Run the interactive site locally

Because the dashboard loads JSON with `fetch()`, use a small local server:

```bash
python3 -m http.server 8080 --directory site
```

Then open `http://localhost:8080`.

## Repository map

```text
aircall-product-analytics/
├── site/                         # recruiter-facing interactive dashboard
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── data/
├── data/                         # raw synthetic CSVs
│   ├── customers.csv
│   └── calls.csv
├── sql/                          # analytical SQL
├── analytics/                    # Python statistical analysis
├── dbt/                          # transformation layer
├── airflow/                      # orchestration example
├── tests/                        # data-quality checks
├── build_data.py                 # deterministic dataset generator
├── requirements.txt
└── README.md
```

## Deployment

### GitHub Pages

The `site/` directory is static. Create a GitHub repository and publish the contents of `site/` with GitHub Pages, or place the files in the repository root if using a static-site workflow.

### Netlify / Vercel / Cloudflare Pages

Point the static host at `site/` and use no build command. The app uses only HTML, CSS, JavaScript, and the Chart.js CDN.

## Why this project exists

The portfolio is deliberately built around the recurring product-analytics questions in the target JD: adoption, feature usage, cohorts, experimentation, actionable narratives, data quality, and collaboration with data engineering.

## Important portfolio note

The synthetic dataset is designed to create a clean, reproducible learning environment. In a real interview, be explicit about which data is simulated and which methodology would need production validation.

## Full-stack mode

The portfolio is now available as a single FastAPI application that serves both the interactive site and a live analytics API.

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000` for the recruiter site and `http://localhost:8000/docs` for interactive API documentation.

Available API surfaces include:

- `/api/health`
- `/api/kpis`
- `/api/weekly`
- `/api/features`
- `/api/experiment`
- `/api/cohorts`
- `/api/health-distribution`
- `/api/agent`
- `/api/customers`
- `/api/customers/{customer_id}`
- `/api/export/customers.csv`

The application defaults to SQLite for a one-command demo and supports PostgreSQL via `DATABASE_URL` for deployment.
