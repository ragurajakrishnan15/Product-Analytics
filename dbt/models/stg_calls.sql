{{ config(materialized='view') }}

select
  call_id,
  customer_id,
  week,
  call_type,
  cast(ai_handled as integer) as ai_handled,
  duration_sec,
  cast(resolved as integer) as resolved,
  cast(escalated as integer) as escalated,
  quality_score,
  first_response_min
from {{ source('raw', 'calls') }}
