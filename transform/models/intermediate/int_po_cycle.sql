-- One row per PO with its closure date and cycle time.
-- Closure = the latest receipt across the PO's lines; cycle time only meaningful for
-- POs the source marked 'closed' (fully received).
with orders as (
    select * from {{ ref('stg_purchase_orders') }}
),
receipts as (
    select
        pol.po_id,
        max(sl.received_date) as closure_date
    from {{ ref('stg_shipment_lines') }} sl
    join {{ ref('stg_purchase_order_lines') }} pol on pol.po_line_id = sl.po_line_id
    group by pol.po_id
)
select
    o.po_id,
    o.supplier_id,
    o.order_date,
    o.promised_date,
    o.status,
    r.closure_date,
    case when o.status = 'closed' then (r.closure_date - o.order_date) end as cycle_time_days
from orders o
left join receipts r on r.po_id = o.po_id
