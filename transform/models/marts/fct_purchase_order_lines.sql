-- Atomic procurement fact: one row per PO line with fulfilment and timing.
-- Drill-down grain for fill rate, lead time, and on-time performance.
select
    po_line_id,
    po_id,
    supplier_id,
    sku_id,
    order_date,
    promised_date,
    received_date,
    ordered_qty,
    shipped_qty,
    received_qty,
    unit_price,
    round(ordered_qty * unit_price, 2) as line_value,
    line_fill_rate,
    lead_time_days,
    is_on_time
from {{ ref('int_po_line_fulfillment') }}
