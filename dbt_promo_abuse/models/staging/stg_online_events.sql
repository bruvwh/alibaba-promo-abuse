with source as (

    select *
    from {{ source('promo_abuse_raw', 'online_events') }}

),

renamed as (

    select
        cast(User_id as int64) as user_id,
        cast(Merchant_id as int64) as merchant_id,
        cast(Action as int64) as action_code,

        case
            when Action = 0 then 'click'
            when Action = 1 then 'purchase'
            when Action = 2 then 'coupon_received'
            else 'unknown'
        end as action_type,

        nullif(trim(Coupon_id), '') as coupon_id,

        safe_cast(
            regexp_replace(
                nullif(trim(Coupon_id), ''),
                r'\.0$',
                ''
            )
            as int64
        ) as coupon_id_numeric,

        nullif(
            trim(Discount_rate),
            ''
        ) as discount_rate_raw,

        case
            when Discount_rate is null
                or trim(Discount_rate) = ''
                then null

            when lower(trim(Discount_rate)) = 'fixed'
                then 'fixed'

            when strpos(trim(Discount_rate), ':') > 0
                then 'threshold_reduction'

            when safe_cast(
                trim(Discount_rate)
                as float64
            ) is not null
                then 'direct_discount'

            else 'unknown'
        end as discount_type,

        case
            when strpos(trim(Discount_rate), ':') = 0
            then safe_cast(
                Discount_rate
                as float64
            )
        end as direct_discount_rate,

        case
            when strpos(trim(Discount_rate), ':') > 0
            then safe_cast(
                split(Discount_rate, ':')[safe_offset(0)]
                as float64
            )
        end as discount_threshold,

        case
            when strpos(trim(Discount_rate), ':') > 0
            then safe_cast(
                split(Discount_rate, ':')[safe_offset(1)]
                as float64
            )
        end as discount_reduction,

        safe.parse_date(
            '%Y%m%d',
            regexp_replace(
                nullif(trim(Date_received), ''),
                r'\.0$',
                ''
            )
        ) as date_received,

        safe.parse_date(
            '%Y%m%d',
            regexp_replace(
                nullif(trim(Date), ''),
                r'\.0$',
                ''
            )
        ) as transaction_date

    from source

)

select *
from renamed