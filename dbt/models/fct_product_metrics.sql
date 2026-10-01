{{ config(materialized='table') }}

select
  plan,
  company_size,
  count(*) as customers,
  avg(ai_adopted) as ai_adoption_rate,
  avg(calls_12w) as avg_calls_12w,
  avg(resolution_rate) as resolution_rate,
  avg(health_score) as avg_health,
  avg(retained_8w) as retention_8w
from {{ ref('stg_customers') }}
group by 1,2
