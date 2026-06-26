-- Supplier KPI time series: one row per supplier-month. The surface Grafana trends read.
-- OTD and lead time are bucketed by shipment received month; fill rate by line receipt
-- month; defect PPM by inspection month. Months with any activity appear.
with shipments_m as (
    select
        supplier_id,
        date_trunc('month', received_date)::date         as month,
        count(*)                                          as shipment_count,
        avg(case when is_on_time then 1.0 else 0.0 end)   as otd_rate,
        avg(lead_time_days)::numeric                      as avg_lead_time_days
    from {{ ref('fct_shipments') }}
    group by 1, 2
),
fill_m as (
    select
        supplier_id,
        date_trunc('month', received_date)::date as month,
        sum(received_qty)::numeric / nullif(sum(ordered_qty), 0) as fill_rate
    from {{ ref('fct_purchase_order_lines') }}
    where received_date is not null
    group by 1, 2
),
defect_m as (
    select
        supplier_id,
        date_trunc('month', inspection_date)::date as month,
        sum(defect_qty)::numeric / nullif(sum(inspected_qty), 0) * 1000000 as defect_ppm
    from {{ ref('fct_quality_inspections') }}
    group by 1, 2
),
grain as (
    select supplier_id, month from shipments_m
    union
    select supplier_id, month from fill_m
    union
    select supplier_id, month from defect_m
)
select
    g.supplier_id || '|' || g.month::text as supplier_month_key,
    g.supplier_id,
    g.month,
    s.shipment_count,
    round(s.otd_rate, 4)            as otd_rate,
    round(s.avg_lead_time_days, 1)  as avg_lead_time_days,
    round(f.fill_rate, 4)           as fill_rate,
    round(d.defect_ppm, 1)          as defect_ppm
from grain g
left join shipments_m s on s.supplier_id = g.supplier_id and s.month = g.month
left join fill_m f      on f.supplier_id = g.supplier_id and f.month = g.month
left join defect_m d    on d.supplier_id = g.supplier_id and d.month = g.month
