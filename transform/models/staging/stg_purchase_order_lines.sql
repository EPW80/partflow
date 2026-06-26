-- Purchase order lines. 1:1 with raw_purchase_order_lines.
select
    po_line_id,
    po_id,
    sku_id,
    ordered_qty::int          as ordered_qty,
    unit_price::numeric(12, 2) as unit_price
from {{ source('raw', 'raw_purchase_order_lines') }}
