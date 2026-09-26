select *
from {{ ref('stg_abuse_cases') }}

where abuse_end_date < abuse_start_date
   or confirmed_date < abuse_end_date