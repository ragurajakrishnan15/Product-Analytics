{{ config(materialized='table') }}

-- Account-level health view for customer success (churn_risk is scored by the API's model).
select
  customer_id,
  plan,
  company_size,
  annual_revenue,
  ai_adopted,
  active_weeks,
  observable_weeks,
  feature_count,
  calls_12w,
  resolution_rate,
  recently_active,
  health_score,
  case
    when health_score < 35 then 'Critical'
    when health_score < 50 then 'At risk'
    when health_score < 65 then 'Watch'
    when health_score < 80 then 'Healthy'
    else 'Advocate'
  end as health_band,
  retained_8w
from {{ ref('fct_customer_metrics') }}
