{{
    config(
        partition_by={
            "field": "activity_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=["user_id"]
    )
}}

with events as (

    select *
    from {{ ref('fct_online_events') }}

),

daily as (

    select

        user_id,
        event_date as activity_date,

        count(*) as total_events,

        countif(
            event_type = 'click'
        ) as clicks,

        countif(
            event_type = 'purchase'
        ) as purchases,

        countif(
            event_type = 'coupon_received'
        ) as coupon_receipts,

        count(
            distinct merchant_id
        ) as unique_merchants,

        count(
            distinct case
                when event_type = 'coupon_received'
                then coupon_id
            end
        ) as unique_coupons_received

    from events

    group by
        user_id,
        event_date

)

select *
from daily