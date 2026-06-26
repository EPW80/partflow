-- Atomic inventory fact: one row per SKU-day with days-of-supply.
select
    sku_id || '|' || snapshot_date::text as inventory_day_key,
    snapshot_date,
    sku_id,
    on_hand_qty,
    daily_demand_qty,
    in_stockout,
    round(avg_daily_demand, 2)            as avg_daily_demand,
    round(days_of_supply, 1)             as days_of_supply
from {{ ref('int_inventory_daily') }}
