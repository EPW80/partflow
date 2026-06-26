-- Shipment headers. 1:1 with raw_shipments.
select
    shipment_id,
    po_id,
    carrier,
    ship_date::date     as ship_date,
    received_date::date as received_date
from {{ source('raw', 'raw_shipments') }}
