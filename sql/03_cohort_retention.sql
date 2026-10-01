-- Cohort retention skeleton for PostgreSQL.
WITH first_activity AS (
  SELECT customer_id, MIN(week)::date AS first_week
  FROM calls
  GROUP BY customer_id
), activity AS (
  SELECT DISTINCT customer_id, DATE_TRUNC('week', week::date)::date AS active_week
  FROM calls
)
SELECT
  f.first_week AS cohort_week,
  EXTRACT(WEEK FROM a.active_week - f.first_week) AS weeks_since_signup,
  COUNT(DISTINCT a.customer_id) AS active_customers
FROM first_activity f
JOIN activity a USING (customer_id)
GROUP BY 1, 2
ORDER BY 1, 2;
