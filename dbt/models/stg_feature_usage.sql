{{ config(materialized='view') }}

select customer_id, feature, first_used_week
from {{ source('raw', 'feature_usage') }}
