select
    user_id,
    prediction_date,
    count(*) as row_count

from {{ ref('user_scoring_population') }}

group by
    user_id,
    prediction_date

having count(*) > 1