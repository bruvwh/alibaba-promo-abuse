select user_id, prediction_date, count(*) as row_count
from {{ ref('user_behavior_features') }}
group by user_id, prediction_date
having count(*) != 1
