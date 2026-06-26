-- Quality inspections. 1:1 with raw_quality_inspections.
select
    inspection_id,
    shipment_line_id,
    sku_id,
    inspection_date::date as inspection_date,
    inspected_qty::int    as inspected_qty,
    defect_qty::int       as defect_qty,
    disposition
from {{ source('raw', 'raw_quality_inspections') }}
