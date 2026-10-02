-- Explainable customer health score components.
SELECT
    customer_id,
    plan,
    company_size,
    ai_adopted,
    active_weeks,
    feature_count,
    calls_12w,
    resolution_rate,
    retained_8w,
    health_score,
    churn_risk,
    annual_revenue
FROM customer_metrics  -- built by sql/00_customer_metrics.sql
ORDER BY churn_risk DESC, annual_revenue DESC;
