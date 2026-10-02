-- Weekly signup cohorts x weeks since signup (PostgreSQL). Matches the dashboard cohort table:
-- only accounts that signed up inside the event window, share with >= 1 call in week N after signup.
WITH window_start AS (
  SELECT MIN(week::date) AS first_week FROM calls
), cohort_members AS (
  SELECT customer_id, DATE_TRUNC('week', signup_date::date)::date AS signup_week
  FROM customers, window_start
  WHERE DATE_TRUNC('week', signup_date::date)::date >= window_start.first_week
), cohort_size AS (
  SELECT signup_week, COUNT(*) AS customers FROM cohort_members GROUP BY signup_week
), activity AS (
  SELECT DISTINCT m.signup_week, c.customer_id, (c.week::date - m.signup_week) / 7 AS weeks_since_signup
  FROM calls c
  JOIN cohort_members m USING (customer_id)
)
SELECT
  a.signup_week,
  s.customers AS cohort_size,
  a.weeks_since_signup,
  COUNT(*) AS active_customers,
  ROUND(COUNT(*)::numeric / s.customers, 4) AS retention_rate
FROM activity a
JOIN cohort_size s USING (signup_week)
WHERE a.weeks_since_signup < 8
GROUP BY 1, 2, 3
ORDER BY 1, 3;
