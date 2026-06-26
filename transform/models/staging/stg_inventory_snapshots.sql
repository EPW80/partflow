-- Daily inventory snapshots. 1:1 with raw_inventory_snapshots.
select
    snapshot_date::date     as snapshot_date,
    sku_id,
    on_hand_qty::int        as on_hand_qty,
    daily_demand_qty::int   as daily_demand_qty,
    in_stockout::boolean    as in_stockout
from {{ source('raw', 'raw_inventory_snapshots') }}
