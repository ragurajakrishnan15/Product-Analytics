-- Adoption of every feature, straight from the usage events.
SELECT
    feature,
    COUNT(DISTINCT customer_id) AS customers,
    COUNT(DISTINCT customer_id) * 1.0 / (SELECT COUNT(*) FROM customers) AS adoption_rate,
    MIN(first_used_week) AS first_seen_week
FROM feature_usage
GROUP BY feature
ORDER BY adoption_rate DESC;
