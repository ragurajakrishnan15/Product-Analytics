-- Weekly product health by plan.
SELECT
    DATE_TRUNC('week', week) AS week,
    c.plan,
    COUNT(*) AS calls,
    COUNT(DISTINCT c.customer_id) AS active_customers,
    AVG(CASE WHEN c.ai_handled = 1 THEN 1.0 ELSE 0.0 END) AS ai_call_share,
    AVG(c.resolved::float) AS resolution_rate,
    AVG(c.quality_score) AS avg_quality
FROM calls c
JOIN customers u USING (customer_id)
GROUP BY 1, 2
ORDER BY 1, 2;
