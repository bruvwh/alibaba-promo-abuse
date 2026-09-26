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
    from {{ ref('fct_offline_events') }}

),

daily as (

    select

        user_id,
        event_date as activity_date,

        count(*) as total_events,

        countif(
            event_type = 'coupon_received'
        ) as coupon_receipts,

        countif(
            event_type = 'purchase'
        ) as purchases,

        countif(
            event_type = 'purchase'
            and is_coupon_redemption
        ) as coupon_redemptions,

        countif(
            event_type = 'purchase'
            and not is_coupon_redemption
        ) as ordinary_purchases,

        count(
            distinct merchant_id
        ) as unique_merchants,

        count(
            distinct case
                when event_type = 'coupon_received'
                then coupon_id
            end
        ) as unique_coupons_received,

        count(
            distinct case
                when event_type = 'purchase'
                    and is_coupon_redemption
                then coupon_id
            end
        ) as unique_coupons_redeemed,

        avg(
            case
                when event_type = 'purchase'
                then distance_bucket
            end
        ) as avg_purchase_distance

    from events

    group by
        user_id,
        event_date

)

select *
from daily