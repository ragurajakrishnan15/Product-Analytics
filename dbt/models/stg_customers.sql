{{ config(materialized='view') }}

select
  customer_id,
  plan,
  industry,
  company_size,
  region,
  cast(signup_date as date) as signup_date,
  experiment_group,
  annual_revenue,
  cast(retained_8w as integer) as retained_8w
from {{ source('raw', 'customers') }}
