{{ config(materialized='table') }}

select
  customer_id,
  plan,
  company_size,
  ai_adopted,
  calls_12w,
  active_weeks,
  feature_count,
  retained_8w,
  churn_risk,
  health_score,
  annual_revenue
from {{ ref('stg_customers') }}
