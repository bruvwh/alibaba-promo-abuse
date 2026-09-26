with canonical as (

    select
        count(*) as canonical_events

    from {{ ref('fct_offline_events') }}

),

daily as (

    select
        sum(total_events) as daily_events

    from {{ ref('offline_user_daily') }}

)

select
    canonical_events,
    daily_events

from canonical
cross join daily

where canonical_events != daily_events