# Dimensional mart design and KPI grain

Phase 3 turns the nine `raw_*` landing tables into the business entities and the full KPI set
from [CONTEXT.md](../../CONTEXT.md). This ADR fixes the mart layer's shape — what tables exist,
at what grain, and the exact formula behind each KPI — so the web app and BI tools (and any
future model) read one agreed contract instead of re-deriving numbers. KPI logic lives here and
nowhere else.

## Layering

Standard dbt three-layer flow, materialized per the `transform/CLAUDE.md` rules:

- **staging** (`stg_<source>__<entity>`, views) — 1:1 with each `raw_*` table: rename, cast
  TEXT→typed, no business logic. The only layer allowed to reference `raw_*`.
- **intermediate** (`int_<concept>`, ephemeral) — the joins and per-row derivations that more
  than one mart needs (line fulfilment, shipment delivery, PO closure, daily inventory).
- **marts** (tables) — dimensions, atomic facts, and KPI roll-ups below.

## Marts

**Conformed dimensions**
- `dim_supplier` — one row per supplier (descriptive attributes only).
- `dim_sku` — one row per SKU, incl. `unit_cost` and `abc_class`.

**Atomic facts** (one row per source event — the drill-down grain for BI/web)
- `fct_purchase_order_lines` — one row per PO line: ordered vs received qty, line fill rate,
  lead time, on-time flag. The grain procurement KPIs roll up from.
- `fct_shipments` — one row per shipment: lead time days, on-time flag.
- `fct_quality_inspections` — one row per inspection: inspected/defect qty.
- `fct_inventory_daily` — one row per SKU-day: on-hand, demand, days-of-supply, stockout flag.

**KPI roll-ups** (the queryable KPI columns the done-when gate requires)
- `kpi_supplier_scorecard` — one row per supplier: every supplier KPI + composite score.
- `kpi_supplier_monthly` — one row per supplier-month: OTD, lead time, fill rate, defect PPM as
  a time series (the surface Grafana trends read).
- `kpi_sku_inventory` — one row per SKU: inventory turns, days-of-supply, stockout frequency.

## KPI definitions (single source of truth)

All "on-time" comparisons use the **PO promised date**; a shipment is on-time if
`received_date <= promised_date`. Each formula below is implemented exactly once.

| KPI | Grain | Formula |
| --- | ----- | ------- |
| On-time-delivery rate | supplier, supplier-month | `count(on_time shipments) / count(shipments)` |
| Lead time | shipment → avg per supplier | `received_date - order_date` (days) |
| Fill rate | PO line → agg per supplier | `sum(received_qty) / sum(ordered_qty)` |
| Defect PPM | supplier, supplier-month | `sum(defect_qty) / sum(inspected_qty) * 1e6` |
| PO cycle time | closed PO → avg per supplier | `closure_date - order_date` (days); closure = max received_date when fully received |
| Inventory turns | SKU | `sum(daily_demand) over window / avg(on_hand) * (365 / window_days)` |
| Days of supply | SKU | `latest on_hand / avg(daily_demand)` |
| Stockout frequency | SKU | `count(stockout SKU-days) / count(SKU-days)` |
| Supplier scorecard | supplier | weighted composite, below |

### Composite supplier score

A 0–100 score, higher is better, combining four normalized components:

```
score = 100 * (0.35 * otd_rate
             + 0.25 * fill_rate
             + 0.20 * (1 - defect_ppm / 25000 capped to [0,1])
             + 0.20 * lead_time_score)
lead_time_score = 1 - (avg_lead_time / promised_lead_time capped to [0,1])
```

Weights favour reliability (OTD + fill = 60%) over cost-of-quality and speed. Weights live in
this ADR and in `kpi_supplier_scorecard`; changing them is an ADR change, not an ad-hoc edit.

## Consequences

- Every CONTEXT.md KPI is a column on exactly one mart; nothing recomputes them downstream.
- Atomic facts give BI/web drill-down without re-querying raw or staging.
- `inventory_turns` and `days_of_supply` use the full generated window as their averaging period;
  if a rolling window is wanted later, that's a documented change to `fct_inventory_daily`.
- Marts build into a `marts` schema; staging into `staging`. The read-only web/BI role is granted
  SELECT on `marts` only (wired in Phase 7).
