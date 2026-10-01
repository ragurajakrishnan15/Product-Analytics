{{ config(materialized='view') }}

select
  customer_id,
  plan,
  industry,
  company_size,
  region,
  experiment_group,
  cast(ai_adopted as integer) as ai_adopted,
  calls_12w,
  ai_calls_12w,
  resolution_rate,
  escalation_rate,
  feature_count,
  active_weeks,
  retained_8w,
  churn_risk,
  health_score,
  annual_revenue
from {{ source('raw', 'customers') }}
