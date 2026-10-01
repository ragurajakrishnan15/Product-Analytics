# Metrics dictionary

| Metric | Definition | Grain | Why it matters |
|---|---|---|---|
| AI adoption rate | Customers with `ai_adopted=1` / eligible customers | customer | Primary activation KPI |
| AI call share | AI-handled calls / all calls | customer / week | Depth of AI usage |
| Resolution rate | Resolved calls / total calls | call | Product effectiveness |
| Escalation rate | Escalated AI calls / AI calls | call | Quality / safety signal |
| Active weeks | Distinct active weeks in analysis window | customer | Engagement depth |
| 8-week retention | Customers retained at week 8 / cohort | cohort | Durability |
| Health score | Weighted combination of retention, usage, quality, adoption | customer | Account prioritization |
| Churn risk | 1 - modeled retention tendency, bounded 0–1 | customer | Risk triage |
| Relative lift | (Treatment rate - Control rate) / Control rate | experiment | Effect size |
| p-value | Probability of observing a result at least this extreme under H0 | experiment | Statistical evidence, not business value |
