-- One row per shipment with delivery performance vs the PO promise.
-- Basis for OTD rate and average lead time.
with shipments as (
    select * from {{ ref('stg_shipments') }}
),
orders as (
    select * from {{ ref('stg_purchase_orders') }}
)
select
    s.shipment_id,
    s.po_id,
    o.supplier_id,
    s.carrier,
    o.order_date,
    o.promised_date,
    s.ship_date,
    s.received_date,
    (s.received_date - o.order_date)     as lead_time_days,
    (s.received_date <= o.promised_date) as is_on_time
from shipments s
join orders o on o.po_id = s.po_id
