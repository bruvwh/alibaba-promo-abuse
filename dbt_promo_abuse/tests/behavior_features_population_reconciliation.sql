select coalesce(p.user_id, f.user_id) as user_id,
       coalesce(p.prediction_date, f.prediction_date) as prediction_date
from {{ ref('user_scoring_population') }} p
full outer join {{ ref('user_behavior_features') }} f using (user_id, prediction_date)
where p.user_id is null or f.user_id is null
   or f.offline_events_30d + f.online_events_30d != p.eligibility_event_count_30d
   or f.offline_coupon_receipts_30d + f.online_coupon_receipts_30d
      != p.eligibility_coupon_receipts_30d
