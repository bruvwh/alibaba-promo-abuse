{{ config(
    partition_by={"field": "prediction_date", "data_type": "date", "granularity": "day"},
    cluster_by=["user_id"]
) }}

-- Behavioral predictors only. No episode labels or generation metadata.
with population as (
    select user_id, prediction_date
    from {{ ref('user_scoring_population') }}
),

offline as (
    select
        p.user_id,
        p.prediction_date,
        coalesce(sum(d.total_events), 0) as offline_events_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.total_events, 0)), 0) as offline_events_7d,
        coalesce(sum(d.coupon_receipts), 0) as offline_coupon_receipts_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.coupon_receipts, 0)), 0) as offline_coupon_receipts_7d,
        coalesce(sum(d.purchases), 0) as offline_purchases_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.purchases, 0)), 0) as offline_purchases_7d,
        coalesce(sum(d.coupon_redemptions), 0) as offline_redemptions_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.coupon_redemptions, 0)), 0) as offline_redemptions_7d,
        countif(d.total_events > 0) as offline_active_days_30d,
        countif(d.total_events > 0 and d.activity_date >= date_sub(p.prediction_date, interval 7 day)) as offline_active_days_7d,
        date_diff(p.prediction_date, max(if(d.purchases > 0, d.activity_date, null)), day) as days_since_last_offline_purchase,
        date_diff(p.prediction_date, max(if(d.coupon_redemptions > 0, d.activity_date, null)), day) as days_since_last_offline_redemption
    from population p
    left join {{ ref('offline_user_daily') }} d
        on p.user_id = d.user_id
        and d.activity_date >= date_sub(p.prediction_date, interval 30 day)
        and d.activity_date < p.prediction_date
        and d.activity_date between date '2016-01-02' and date '2016-06-05'
    group by p.user_id, p.prediction_date
),

online as (
    select
        p.user_id,
        p.prediction_date,
        coalesce(sum(d.total_events), 0) as online_events_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.total_events, 0)), 0) as online_events_7d,
        coalesce(sum(d.coupon_receipts), 0) as online_coupon_receipts_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.coupon_receipts, 0)), 0) as online_coupon_receipts_7d,
        coalesce(sum(d.purchases), 0) as online_purchases_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.purchases, 0)), 0) as online_purchases_7d,
        coalesce(sum(d.clicks), 0) as online_clicks_30d,
        coalesce(sum(if(d.activity_date >= date_sub(p.prediction_date, interval 7 day), d.clicks, 0)), 0) as online_clicks_7d,
        countif(d.total_events > 0) as online_active_days_30d,
        countif(d.total_events > 0 and d.activity_date >= date_sub(p.prediction_date, interval 7 day)) as online_active_days_7d,
        date_diff(p.prediction_date, max(if(d.clicks > 0, d.activity_date, null)), day) as days_since_last_online_click
    from population p
    left join {{ ref('online_user_daily') }} d
        on p.user_id = d.user_id
        and d.activity_date >= date_sub(p.prediction_date, interval 30 day)
        and d.activity_date < p.prediction_date
        and d.activity_date between date '2016-01-02' and date '2016-06-05'
    group by p.user_id, p.prediction_date
),

counts as (
    select
        p.user_id,
        p.prediction_date,
        offline.offline_events_30d,
        offline.offline_events_7d,
        offline.offline_coupon_receipts_30d,
        offline.offline_coupon_receipts_7d,
        offline.offline_purchases_30d,
        offline.offline_purchases_7d,
        offline.offline_redemptions_30d,
        offline.offline_redemptions_7d,
        offline.offline_active_days_30d,
        offline.offline_active_days_7d,
        offline.days_since_last_offline_purchase,
        offline.days_since_last_offline_redemption,
        online.online_events_30d,
        online.online_events_7d,
        online.online_coupon_receipts_30d,
        online.online_coupon_receipts_7d,
        online.online_purchases_30d,
        online.online_purchases_7d,
        online.online_clicks_30d,
        online.online_clicks_7d,
        online.online_active_days_30d,
        online.online_active_days_7d,
        online.days_since_last_online_click
    from population p
    left join offline using (user_id, prediction_date)
    left join online using (user_id, prediction_date)
),

features as (
    select
        *,
        offline_coupon_receipts_7d / 7.0 - (offline_coupon_receipts_30d - offline_coupon_receipts_7d) / 23.0 as offline_coupon_receipts_acceleration,
        offline_purchases_7d / 7.0 - (offline_purchases_30d - offline_purchases_7d) / 23.0 as offline_purchases_acceleration,
        offline_redemptions_7d / 7.0 - (offline_redemptions_30d - offline_redemptions_7d) / 23.0 as offline_redemptions_acceleration,
        online_coupon_receipts_7d / 7.0 - (online_coupon_receipts_30d - online_coupon_receipts_7d) / 23.0 as online_coupon_receipts_acceleration,
        online_purchases_7d / 7.0 - (online_purchases_30d - online_purchases_7d) / 23.0 as online_purchases_acceleration,
        online_clicks_7d / 7.0 - (online_clicks_30d - online_clicks_7d) / 23.0 as online_clicks_acceleration,
        safe_divide(offline_redemptions_30d, offline_coupon_receipts_30d) as offline_redemption_rate_30d,
        cast(offline_redemptions_30d > 0 as int64) as has_offline_redemption,
        cast(offline_purchases_30d > 0 as int64) as has_offline_purchase,
        cast(online_clicks_30d > 0 as int64) as has_online_click,
        cast(online_clicks_30d > 0 and offline_redemptions_30d > 0 as int64) as has_click_and_redemption
    from counts
)

select
    *,
    cast(online_clicks_acceleration > 0 and offline_redemptions_acceleration > 0 as int64)
        as both_click_redemption_accelerating
from features
