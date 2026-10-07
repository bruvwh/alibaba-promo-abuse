select coalesce(p.user_id, l.user_id) as user_id,
       coalesce(p.prediction_date, l.prediction_date) as prediction_date
from {{ ref('user_scoring_population') }} p
full outer join {{ ref('user_outcome_labels') }} l using (user_id, prediction_date)
where p.user_id is null or l.user_id is null
