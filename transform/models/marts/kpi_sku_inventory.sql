-- SKU inventory KPIs: one row per SKU with turns, days-of-supply, and stockout frequency.
with daily as (
    select * from {{ ref('fct_inventory_daily') }}
),
agg as (
    select
        sku_id,
        count(*)                                          as snapshot_days,
        avg(on_hand_qty)::numeric                          as avg_on_hand,
        sum(daily_demand_qty)                              as total_demand,
        avg(case when in_stockout then 1.0 else 0.0 end)  as stockout_frequency
    from daily
    group by sku_id
),
latest as (
    select distinct on (sku_id)
        sku_id,
        on_hand_qty    as current_on_hand,
        days_of_supply as current_days_of_supply
    from daily
    order by sku_id, snapshot_date desc
),
sku as (
    select sku_id, abc_class, unit_cost from {{ ref('dim_sku') }}
)
select
    a.sku_id,
    k.abc_class,
    a.snapshot_days,
    round(a.avg_on_hand, 1)                  as avg_on_hand,
    a.total_demand,
    l.current_on_hand,
    round(l.current_days_of_supply, 1)       as days_of_supply,
    round(a.stockout_frequency, 4)           as stockout_frequency,
    -- Annualized inventory turns = (demand rate * 365) / average on-hand.
    round(
        (a.total_demand::numeric / nullif(a.snapshot_days, 0) * 365)
        / nullif(a.avg_on_hand, 0),
    2) as inventory_turns
from agg a
join latest l on l.sku_id = a.sku_id
left join sku k on k.sku_id = a.sku_id
