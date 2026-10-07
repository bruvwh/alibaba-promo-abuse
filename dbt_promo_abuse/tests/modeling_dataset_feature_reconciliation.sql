select coalesce(f.user_id, m.user_id) as user_id,
       coalesce(f.prediction_date, m.prediction_date) as prediction_date
from {{ ref('user_behavior_features') }} f
full outer join {{ ref('user_modeling_dataset') }} m using (user_id, prediction_date)
where f.user_id is null or m.user_id is null
