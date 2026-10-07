{{ config(
    partition_by={"field": "prediction_date", "data_type": "date", "granularity": "day"},
    cluster_by=["user_id"]
) }}

-- Controlled episode ground truth, kept separate from behavioral predictors.
-- An episode's end date is inclusive, matching the EDA label definition.
select
    p.user_id,
    p.prediction_date,
    max(case when a.user_id is not null then 1 else 0 end) as abuse_next_7d
from {{ ref('user_scoring_population') }} p
left join {{ ref('stg_abuse_cases') }} a
    on p.user_id = a.user_id
    and a.abuse_start_date < date_add(p.prediction_date, interval 7 day)
    and a.abuse_end_date >= p.prediction_date
group by p.user_id, p.prediction_date
