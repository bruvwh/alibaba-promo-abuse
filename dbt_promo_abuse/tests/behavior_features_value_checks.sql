select *
from {{ ref('user_behavior_features') }}
where offline_events_7d is null
   or offline_events_30d is null
   or offline_events_7d < 0
   or offline_events_7d > offline_events_30d
   or offline_coupon_receipts_7d is null
   or offline_coupon_receipts_30d is null
   or offline_coupon_receipts_7d < 0
   or offline_coupon_receipts_7d > offline_coupon_receipts_30d
   or offline_purchases_7d is null
   or offline_purchases_30d is null
   or offline_purchases_7d < 0
   or offline_purchases_7d > offline_purchases_30d
   or offline_redemptions_7d is null
   or offline_redemptions_30d is null
   or offline_redemptions_7d < 0
   or offline_redemptions_7d > offline_redemptions_30d
   or offline_active_days_7d not between 0 and 7
   or offline_active_days_30d not between 0 and 30
   or offline_active_days_7d > offline_active_days_30d
   or online_events_7d is null
   or online_events_30d is null
   or online_events_7d < 0
   or online_events_7d > online_events_30d
   or online_coupon_receipts_7d is null
   or online_coupon_receipts_30d is null
   or online_coupon_receipts_7d < 0
   or online_coupon_receipts_7d > online_coupon_receipts_30d
   or online_purchases_7d is null
   or online_purchases_30d is null
   or online_purchases_7d < 0
   or online_purchases_7d > online_purchases_30d
   or online_clicks_7d is null
   or online_clicks_30d is null
   or online_clicks_7d < 0
   or online_clicks_7d > online_clicks_30d
   or online_active_days_7d not between 0 and 7
   or online_active_days_30d not between 0 and 30
   or online_active_days_7d > online_active_days_30d
   or days_since_last_offline_purchase not between 1 and 30
   or (offline_purchases_30d = 0 and days_since_last_offline_purchase is not null)
   or (offline_purchases_30d > 0 and days_since_last_offline_purchase is null)
   or days_since_last_offline_redemption not between 1 and 30
   or (offline_redemptions_30d = 0 and days_since_last_offline_redemption is not null)
   or (offline_redemptions_30d > 0 and days_since_last_offline_redemption is null)
   or days_since_last_online_click not between 1 and 30
   or (online_clicks_30d = 0 and days_since_last_online_click is not null)
   or (online_clicks_30d > 0 and days_since_last_online_click is null)
   or (offline_coupon_receipts_30d = 0 and offline_redemption_rate_30d is not null)
   or (offline_coupon_receipts_30d > 0 and offline_redemption_rate_30d is null)
   or offline_redemptions_30d > offline_purchases_30d
