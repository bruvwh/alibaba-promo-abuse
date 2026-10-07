select user_id, prediction_date, count(*) as row_count
from {{ ref('user_modeling_dataset') }}
group by user_id, prediction_date
having count(*) != 1
