-- Material-flow events. 1:1 with raw_material_flow_events.
select
    event_id,
    event_type,
    sku_id,
    qty::int          as qty,
    event_ts::date    as event_ts,
    reference_type,
    reference_id
from {{ source('raw', 'raw_material_flow_events') }}
