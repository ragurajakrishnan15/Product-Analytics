-- Primary experiment metric: customer-level AI adoption.
SELECT
    experiment_group,
    COUNT(*) AS customers,
    SUM(ai_adopted) AS adopters,
    AVG(ai_adopted::float) AS adoption_rate,
    AVG(retained_8w::float) AS retention_8w,
    AVG(health_score) AS avg_health
FROM customers
GROUP BY experiment_group;

-- Segment readout for treatment heterogeneity.
SELECT
    company_size,
    experiment_group,
    COUNT(*) AS customers,
    AVG(ai_adopted::float) AS adoption_rate,
    AVG(retained_8w::float) AS retention_8w
FROM customers
GROUP BY company_size, experiment_group
ORDER BY company_size, experiment_group;
