-- One row per inspection, attributed to the SKU's primary supplier.
-- Basis for defect PPM at supplier and SKU grain.
with inspections as (
    select * from {{ ref('stg_quality_inspections') }}
),
skus as (
    select sku_id, primary_supplier_id from {{ ref('stg_skus') }}
)
select
    i.inspection_id,
    i.shipment_line_id,
    i.sku_id,
    s.primary_supplier_id as supplier_id,
    i.inspection_date,
    i.inspected_qty,
    i.defect_qty,
    i.disposition
from inspections i
join skus s on s.sku_id = i.sku_id
