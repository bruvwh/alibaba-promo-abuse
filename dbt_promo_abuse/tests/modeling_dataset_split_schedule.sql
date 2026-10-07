select user_id, prediction_date, dataset_split
from {{ ref('user_modeling_dataset') }}
where prediction_date not in unnest(
        generate_date_array(date '2016-02-01', date '2016-06-06', interval 7 day)
    )
    or dataset_split is null
    or (dataset_split = 'train' and prediction_date not between date '2016-02-01' and date '2016-04-25')
    or (dataset_split = 'validation' and prediction_date not between date '2016-05-02' and date '2016-05-16')
    or (dataset_split = 'test' and prediction_date not between date '2016-05-23' and date '2016-06-06')
