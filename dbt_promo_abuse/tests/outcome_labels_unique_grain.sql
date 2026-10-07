select user_id, prediction_date, count(*) as row_count
from {{ ref('user_outcome_labels') }}
group by user_id, prediction_date
having count(*) != 1
