with source as (

    select *
    from {{ source('promo_abuse_raw', 'abuse_cases') }}

),

renamed as (

    select
        cast(episode_id as string) as episode_id,
        cast(user_id as int64) as user_id,
        lower(trim(channel)) as channel,
        abuse_start_date,
        abuse_end_date,
        confirmed_date

    from source

)

select *
from renamed