-- One row per PO line, enriched with what was actually received against it.
-- Basis for fill rate and the atomic PO-line fact. A line may be fulfilled by one or
-- more shipment lines; we aggregate received/shipped qty and take the earliest receipt.
with lines as (
    select * from {{ ref('stg_purchase_order_lines') }}
),
orders as (
    select * from {{ ref('stg_purchase_orders') }}
),
shipped as (
    select
        po_line_id,
        sum(shipped_qty)   as shipped_qty,
        sum(received_qty)  as received_qty,
        min(received_date) as received_date
    from {{ ref('stg_shipment_lines') }}
    group by po_line_id
)
select
    l.po_line_id,
    l.po_id,
    o.supplier_id,
    l.sku_id,
    o.order_date,
    o.promised_date,
    l.ordered_qty,
    l.unit_price,
    coalesce(s.shipped_qty, 0)  as shipped_qty,
    coalesce(s.received_qty, 0) as received_qty,
    s.received_date,
    least(1.0, coalesce(s.received_qty, 0)::numeric / nullif(l.ordered_qty, 0)) as line_fill_rate,
    (s.received_date - o.order_date)        as lead_time_days,
    (s.received_date <= o.promised_date)    as is_on_time
from lines l
join orders o on o.po_id = l.po_id
left join shipped s on s.po_line_id = l.po_line_id
