select *

from {{ ref('user_scoring_population') }}

where eligibility_event_count_30d < 5
   or eligibility_coupon_receipts_30d < 1