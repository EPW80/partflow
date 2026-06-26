-- Atomic delivery fact: one row per shipment with lead time and on-time flag.
select
    shipment_id,
    po_id,
    supplier_id,
    carrier,
    order_date,
    promised_date,
    ship_date,
    received_date,
    lead_time_days,
    is_on_time
from {{ ref('int_shipment_delivery') }}
