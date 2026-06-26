-- Atomic quality fact: one row per inspection with per-inspection defect PPM.
select
    inspection_id,
    shipment_line_id,
    sku_id,
    supplier_id,
    inspection_date,
    inspected_qty,
    defect_qty,
    disposition,
    case
        when inspected_qty > 0
        then round(defect_qty::numeric / inspected_qty * 1000000, 1)
    end as defect_ppm
from {{ ref('int_inspection_quality') }}
