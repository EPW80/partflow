-- Conformed supplier dimension: descriptive attributes + catalog size.
with suppliers as (
    select * from {{ ref('stg_suppliers') }}
),
sku_counts as (
    select primary_supplier_id as supplier_id, count(*) as sku_count
    from {{ ref('stg_skus') }}
    group by primary_supplier_id
)
select
    s.supplier_id,
    s.supplier_name,
    s.country,
    s.tier,
    s.category,
    s.promised_lead_time_days,
    s.onboarded_date,
    coalesce(c.sku_count, 0) as sku_count
from suppliers s
left join sku_counts c on c.supplier_id = s.supplier_id
