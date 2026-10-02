-- Weekly product health by plan (PostgreSQL).
SELECT
    DATE_TRUNC('week', ca.week::date)::date AS week,
    cu.plan,
    COUNT(*) AS calls,
    COUNT(DISTINCT ca.customer_id) AS active_customers,
    AVG(CASE WHEN ca.ai_handled = 1 THEN 1.0 ELSE 0.0 END) AS ai_call_share,
    AVG(ca.resolved::float) AS resolution_rate,
    AVG(ca.quality_score) AS avg_quality
FROM calls ca
JOIN customers cu USING (customer_id)
GROUP BY 1, 2
ORDER BY 1, 2;
