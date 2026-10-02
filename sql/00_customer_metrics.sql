-- Customer-level metric layer, derived only from raw events (calls, feature_usage) and account data.
-- Portable SQL (SQLite + PostgreSQL). The backend runs this file verbatim to build `customer_metrics`;
-- dbt/models/fct_customer_health.sql is the same logic expressed as a dbt model.
--
-- Health score (0-100), explainable by construction:
--   35% engagement   active weeks / weeks observable since first activity
--   20% intensity    calls per active week, capped at 3
--   15% breadth      features used / 6
--   15% quality      call resolution rate
--   10% AI adoption  has turned on the AI Voice Agent
--    5% recency      active in either of the last two weeks
WITH weeks AS (
  SELECT DISTINCT week FROM calls
), last_two_weeks AS (
  SELECT MIN(week) AS since FROM (SELECT week FROM weeks ORDER BY week DESC LIMIT 2) t
), call_stats AS (
  SELECT customer_id,
         COUNT(*) AS calls_12w,
         SUM(ai_handled) AS ai_calls_12w,
         COUNT(DISTINCT week) AS active_weeks,
         MIN(week) AS first_active_week,
         MAX(week) AS last_active_week,
         AVG(resolved * 1.0) AS resolution_rate,
         AVG(escalated * 1.0) AS escalation_rate,
         AVG(duration_sec * 1.0) AS avg_handle_time_sec,
         AVG(quality_score) AS avg_quality_score
  FROM calls
  GROUP BY customer_id
), observable AS (
  SELECT cs.customer_id, COUNT(*) AS observable_weeks
  FROM call_stats cs
  JOIN weeks w ON w.week >= cs.first_active_week
  GROUP BY cs.customer_id
), features AS (
  SELECT customer_id,
         COUNT(*) AS feature_count,
         MAX(CASE WHEN feature = 'AI Voice Agent' THEN 1 ELSE 0 END) AS ai_adopted,
         MIN(CASE WHEN feature = 'AI Voice Agent' THEN first_used_week END) AS ai_adopted_week
  FROM feature_usage
  GROUP BY customer_id
), base AS (
  SELECT c.customer_id, c.plan, c.industry, c.company_size, c.region, c.signup_date,
         c.experiment_group, c.annual_revenue, c.retained_8w,
         cs.calls_12w, cs.ai_calls_12w, cs.active_weeks, o.observable_weeks,
         cs.first_active_week, cs.last_active_week,
         cs.resolution_rate, cs.escalation_rate, cs.avg_handle_time_sec, cs.avg_quality_score,
         COALESCE(f.feature_count, 0) AS feature_count,
         COALESCE(f.ai_adopted, 0) AS ai_adopted,
         f.ai_adopted_week,
         cs.active_weeks * 1.0 / o.observable_weeks AS active_week_share,
         cs.calls_12w * 1.0 / cs.active_weeks AS calls_per_active_week,
         CASE WHEN cs.last_active_week >= (SELECT since FROM last_two_weeks) THEN 1 ELSE 0 END AS recently_active
  FROM customers c
  JOIN call_stats cs ON cs.customer_id = c.customer_id
  JOIN observable o ON o.customer_id = c.customer_id
  LEFT JOIN features f ON f.customer_id = c.customer_id
)
SELECT base.*,
       ROUND(100 * (
           0.35 * active_week_share
         + 0.20 * CASE WHEN calls_per_active_week >= 3 THEN 1.0 ELSE calls_per_active_week / 3 END
         + 0.15 * feature_count / 6.0
         + 0.15 * resolution_rate
         + 0.10 * ai_adopted
         + 0.05 * recently_active
       )) AS health_score
FROM base
