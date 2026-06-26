-- One row per SKU-day with days-of-supply derived against each SKU's average demand.
-- Basis for the inventory fact and the SKU inventory KPIs.
with snapshots as (
    select * from {{ ref('stg_inventory_snapshots') }}
),
sku_demand as (
    select
        sku_id,
        avg(daily_demand_qty)::numeric as avg_daily_demand
    from snapshots
    group by sku_id
)
select
    s.snapshot_date,
    s.sku_id,
    s.on_hand_qty,
    s.daily_demand_qty,
    s.in_stockout,
    d.avg_daily_demand,
    case
        when d.avg_daily_demand > 0 then s.on_hand_qty / d.avg_daily_demand
    end as days_of_supply
from snapshots s
join sku_demand d on d.sku_id = s.sku_id
