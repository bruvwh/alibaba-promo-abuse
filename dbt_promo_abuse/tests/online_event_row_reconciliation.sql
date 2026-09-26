with source_count as (

    select
        count(*) as expected_event_count

    from {{ ref('stg_online_events') }}

),

canonical_count as (

    select
        count(*) as actual_event_count

    from {{ ref('fct_online_events') }}

)

select
    expected_event_count,
    actual_event_count

from source_count
cross join canonical_count

where expected_event_count
    != actual_event_count