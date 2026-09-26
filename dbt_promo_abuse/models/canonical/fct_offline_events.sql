{{
    config(
        partition_by={
            "field": "event_date",
            "data_type": "date",
            "granularity": "day"
        },
        cluster_by=[
            "user_id",
            "merchant_id"
        ]
    )
}}

with source as (

    select *
    from {{ ref('stg_offline_events') }}

),

coupon_receipts as (

    select

        user_id,
        merchant_id,

        date_received as event_date,

        'coupon_received' as event_type,
        'offline' as channel,

        coupon_id,
        coupon_id_numeric,

        discount_rate_raw,
        discount_type,
        direct_discount_rate,
        discount_threshold,
        discount_reduction,

        distance_bucket,

        false as is_coupon_redemption

    from source

    where date_received is not null

),

purchases as (

    select

        user_id,
        merchant_id,

        transaction_date as event_date,

        'purchase' as event_type,
        'offline' as channel,

        coupon_id,
        coupon_id_numeric,

        discount_rate_raw,
        discount_type,
        direct_discount_rate,
        discount_threshold,
        discount_reduction,

        distance_bucket,

        date_received is not null
            as is_coupon_redemption

    from source

    where transaction_date is not null

),

events as (

    select *
    from coupon_receipts

    union all

    select *
    from purchases

)

select *
from events