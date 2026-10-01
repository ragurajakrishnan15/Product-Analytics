-- Feature adoption by plan and company size.
SELECT
    plan,
    company_size,
    COUNT(*) AS customers,
    AVG(ai_adopted::float) AS ai_adoption_rate,
    AVG(feature_count::float) AS avg_features,
    AVG(active_weeks::float) AS avg_active_weeks
FROM customers
GROUP BY 1, 2
ORDER BY ai_adoption_rate DESC;
