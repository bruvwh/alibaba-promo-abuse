{{
    config(
        partition_by={
            "field": "prediction_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=["user_id"]
    )
}}

with prediction_dates as (

    select
        prediction_date

    from unnest(
        generate_date_array(
            date '2016-02-01',
            date '2016-06-06',
            interval 7 day
        )
    ) as prediction_date

),

offline_daily as (

    select
        user_id,
        activity_date,
        total_events,
        coupon_receipts

    from {{ ref('offline_user_daily') }}

),

online_daily as (

    select
        user_id,
        activity_date,
        total_events,
        coupon_receipts

    from {{ ref('online_user_daily') }}

),

combined_daily as (

    select
        user_id,
        activity_date,
        sum(total_events) as total_events,
        sum(coupon_receipts) as coupon_receipts

    from (

        select *
        from offline_daily

        union all

        select *
        from online_daily

    )

    group by
        user_id,
        activity_date

),

historical_activity as (

    select

        d.user_id,
        p.prediction_date,

        date_sub(
            p.prediction_date,
            interval 30 day
        ) as history_start_date,

        date_sub(
            p.prediction_date,
            interval 1 day
        ) as history_end_date,

        sum(
            d.total_events
        ) as eligibility_event_count_30d,

        sum(
            d.coupon_receipts
        ) as eligibility_coupon_receipts_30d

    from prediction_dates p

    join combined_daily d

        on d.activity_date >= date_sub(
            p.prediction_date,
            interval 30 day
        )

        and d.activity_date < p.prediction_date

    group by
        d.user_id,
        p.prediction_date

),

eligible as (

    select *

    from historical_activity

    where eligibility_event_count_30d >= 5
      and eligibility_coupon_receipts_30d >= 1

)

select *
from eligible