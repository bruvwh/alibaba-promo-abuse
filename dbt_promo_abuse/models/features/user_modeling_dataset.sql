{{ config(
    partition_by={"field": "prediction_date", "data_type": "date", "granularity": "day"},
    cluster_by=["user_id"]
) }}

select
    f.*,
    l.abuse_next_7d,
    case
        when f.prediction_date between date '2016-02-01' and date '2016-04-25'
            then 'train'
        when f.prediction_date between date '2016-05-02' and date '2016-05-16'
            then 'validation'
        when f.prediction_date between date '2016-05-23' and date '2016-06-06'
            then 'test'
    end as dataset_split
from {{ ref('user_behavior_features') }} f
left join {{ ref('user_outcome_labels') }} l using (user_id, prediction_date)
