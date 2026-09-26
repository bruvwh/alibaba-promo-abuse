with expected as (

    select

        countif(
            date_received is not null
        )
        +
        countif(
            transaction_date is not null
        ) as expected_event_count

    from {{ ref('stg_offline_events') }}

),

actual as (

    select
        count(*) as actual_event_count

    from {{ ref('fct_offline_events') }}

)

select
    expected_event_count,
    actual_event_count

from expected
cross join actual

where expected_event_count
    != actual_event_count