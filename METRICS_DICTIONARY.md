# Metrics dictionary

All customer-level metrics are derived from raw events in `sql/00_customer_metrics.sql`.

| Metric | Definition | Grain | Why it matters |
|---|---|---|---|
| AI adoption | Account has turned on the AI Voice Agent (a `feature_usage` event) | customer | Primary experiment metric and activation KPI |
| Cumulative AI adoption | Accounts adopted by week *w* / all accounts | week | Adoption trend |
| Feature adoption | Accounts that have used a feature / all accounts | feature | Which capabilities become habitual |
| AI call share | AI-handled calls / all calls | week | Depth of AI usage |
| Resolution rate | Resolved calls / calls | call, customer | Product effectiveness |
| Escalation rate | Escalated calls / calls (only unresolved calls can escalate) | call | Quality / safety signal |
| Active weeks | Distinct weeks with at least one call | customer | Engagement depth |
| Weeks observable | Weeks from first activity to the end of the window | customer | Fair denominator for new accounts |
| 8-week retention | Subscription still active 8 weeks after first activity (billing outcome) | customer | Durability; churn-model label; experiment guardrail |
| Cohort retention | Share of a weekly signup cohort with >= 1 call in week N after signup | cohort x week | Early drop-off vs durable usage |
| Health score | 100 x (0.35 active weeks / weeks observable + 0.20 min(calls per active week / 3, 1) + 0.15 features used / 6 + 0.15 resolution rate + 0.10 AI adopted + 0.05 active in last 2 weeks) | customer | Explainable account prioritisation |
| Health band | Critical < 35, At risk 35–49, Watch 50–64, Healthy 65–79, Advocate >= 80 | customer | Triage tiers |
| Churn risk | Logistic-regression probability of churning within 8 weeks, from standardised behavioural features | customer | Risk triage; reported with holdout AUC |
| Relative lift | (Treatment rate - Control rate) / Control rate | experiment | Effect size |
| Difference CI | Treatment - control +/- 1.96 x Wald standard error | experiment, segment | Uncertainty of the effect |
| Minimum detectable effect | (z<sub>0.975</sub> + z<sub>0.8</sub>) x sqrt(p(1-p)(1/n<sub>c</sub> + 1/n<sub>t</sub>)) | experiment, segment | Whether a null result is informative |
| p-value | Probability of a result at least this extreme under H0 (two-sided z-test) | experiment | Statistical evidence, not business value |
