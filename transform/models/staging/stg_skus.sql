-- SKUs: cast raw TEXT to typed columns. 1:1 with raw_skus.
select
    sku_id,
    description,
    category,
    primary_supplier_id,
    unit_cost::numeric(12, 2) as unit_cost,
    unit_of_measure,
    abc_class
from {{ source('raw', 'raw_skus') }}
