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
    from {{ ref('stg_online_events') }}

),

events as (

    select

        user_id,
        merchant_id,

        case
            when action_code in (0, 1)
                then transaction_date

            when action_code = 2
                then date_received
        end as event_date,

        action_type as event_type,

        'online' as channel,

        coupon_id,
        coupon_id_numeric,

        discount_rate_raw,
        discount_type,
        direct_discount_rate,
        discount_threshold,
        discount_reduction

    from source

)

select *
from events