-- Conformed SKU dimension: attributes + primary supplier name for convenience.
with skus as (
    select * from {{ ref('stg_skus') }}
),
suppliers as (
    select supplier_id, supplier_name from {{ ref('stg_suppliers') }}
)
select
    k.sku_id,
    k.description,
    k.category,
    k.primary_supplier_id,
    s.supplier_name as primary_supplier_name,
    k.unit_cost,
    k.unit_of_measure,
    k.abc_class
from skus k
left join suppliers s on s.supplier_id = k.primary_supplier_id
