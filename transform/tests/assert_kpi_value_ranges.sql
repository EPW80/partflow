-- KPI sanity: rates must be valid proportions and scores within 0-100.
-- Returns offending rows; dbt fails the test if any are returned.
select 'scorecard.otd_rate' as check_name, supplier_id::text as id, otd_rate as value
from {{ ref('kpi_supplier_scorecard') }}
where otd_rate is not null and (otd_rate < 0 or otd_rate > 1)

union all
select 'scorecard.fill_rate', supplier_id::text, fill_rate
from {{ ref('kpi_supplier_scorecard') }}
where fill_rate is not null and (fill_rate < 0 or fill_rate > 1)

union all
select 'scorecard.composite_score', supplier_id::text, composite_score
from {{ ref('kpi_supplier_scorecard') }}
where composite_score is not null and (composite_score < 0 or composite_score > 100)

union all
select 'sku_inventory.stockout_frequency', sku_id, stockout_frequency
from {{ ref('kpi_sku_inventory') }}
where stockout_frequency < 0 or stockout_frequency > 1

union all
select 'po_lines.line_fill_rate', po_line_id, line_fill_rate
from {{ ref('fct_purchase_order_lines') }}
where line_fill_rate is not null and (line_fill_rate < 0 or line_fill_rate > 1)
