{{ config(materialized='table') }}

select
  plan,
  company_size,
  count(*) as customers,
  avg(ai_adopted * 1.0) as ai_adoption_rate,
  avg(calls_12w * 1.0) as avg_calls_12w,
  avg(feature_count * 1.0) as avg_features,
  avg(resolution_rate) as resolution_rate,
  avg(health_score) as avg_health,
  avg(retained_8w * 1.0) as retention_8w
from {{ ref('fct_customer_metrics') }}
group by 1, 2
