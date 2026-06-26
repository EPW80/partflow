-- Supplier scorecard: every supplier KPI on one row plus a 0-100 composite score.
-- Formulas and weights are defined in docs/adr/0002-dimensional-mart-design.md
-- and models/marts/README.md. This is the single source for these numbers.
with supplier as (
    select * from {{ ref('dim_supplier') }}
),
delivery as (
    select
        supplier_id,
        count(*)                                              as shipment_count,
        avg(case when is_on_time then 1.0 else 0.0 end)       as otd_rate,
        avg(lead_time_days)::numeric                          as avg_lead_time_days
    from {{ ref('fct_shipments') }}
    group by supplier_id
),
fulfillment as (
    select
        supplier_id,
        sum(received_qty)::numeric / nullif(sum(ordered_qty), 0) as fill_rate
    from {{ ref('fct_purchase_order_lines') }}
    group by supplier_id
),
cycle as (
    select
        supplier_id,
        avg(cycle_time_days)::numeric as avg_po_cycle_time_days
    from {{ ref('int_po_cycle') }}
    where cycle_time_days is not null
    group by supplier_id
),
quality as (
    select
        supplier_id,
        sum(defect_qty)::numeric / nullif(sum(inspected_qty), 0) * 1000000 as defect_ppm
    from {{ ref('fct_quality_inspections') }}
    group by supplier_id
),
combined as (
    select
        s.supplier_id,
        s.supplier_name,
        s.tier,
        s.country,
        s.promised_lead_time_days,
        d.shipment_count,
        d.otd_rate,
        d.avg_lead_time_days,
        f.fill_rate,
        c.avg_po_cycle_time_days,
        q.defect_ppm
    from supplier s
    left join delivery d    on d.supplier_id = s.supplier_id
    left join fulfillment f on f.supplier_id = s.supplier_id
    left join cycle c       on c.supplier_id = s.supplier_id
    left join quality q     on q.supplier_id = s.supplier_id
)
select
    supplier_id,
    supplier_name,
    tier,
    country,
    promised_lead_time_days,
    shipment_count,
    round(otd_rate, 4)                  as otd_rate,
    round(avg_lead_time_days, 1)        as avg_lead_time_days,
    round(fill_rate, 4)                 as fill_rate,
    round(avg_po_cycle_time_days, 1)    as avg_po_cycle_time_days,
    round(defect_ppm, 1)                as defect_ppm,
    -- Composite 0-100 score; higher is better. Weights per ADR-0002.
    round(100 * (
          0.35 * coalesce(otd_rate, 0)
        + 0.25 * coalesce(fill_rate, 0)
        + 0.20 * (1 - least(1, coalesce(defect_ppm, 0) / 25000))
        + 0.20 * (1 - least(1, coalesce(avg_lead_time_days, 0)
                              / nullif(promised_lead_time_days, 0)))
    ), 1) as composite_score
from combined
