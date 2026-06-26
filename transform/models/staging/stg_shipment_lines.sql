-- Shipment lines. 1:1 with raw_shipment_lines.
select
    shipment_line_id,
    shipment_id,
    po_line_id,
    sku_id,
    shipped_qty::int    as shipped_qty,
    received_qty::int   as received_qty,
    received_date::date as received_date
from {{ source('raw', 'raw_shipment_lines') }}
