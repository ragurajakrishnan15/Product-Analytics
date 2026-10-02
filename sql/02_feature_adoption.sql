-- Feature adoption by plan and company size (customer_metrics is built by sql/00_customer_metrics.sql).
SELECT
    plan,
    company_size,
    COUNT(*) AS customers,
    AVG(ai_adopted::float) AS ai_adoption_rate,
    AVG(feature_count::float) AS avg_features,
    AVG(active_weeks::float) AS avg_active_weeks
FROM customer_metrics  -- built by sql/00_customer_metrics.sql
GROUP BY 1, 2
ORDER BY ai_adoption_rate DESC;
