# Marts — KPI Definitions

This is the **single source of truth** for every PartFlow KPI. If a number appears in the web
app or a dashboard, it is a column defined here — nothing downstream recomputes it. Design
rationale and weights live in [docs/adr/0002-dimensional-mart-design.md](../../../docs/adr/0002-dimensional-mart-design.md).

All "on-time" logic compares a shipment's `received_date` to the PO `promised_date`.

## Tables

| Mart | Grain | Purpose |
| ---- | ----- | ------- |
| `dim_supplier` | supplier | Conformed supplier dimension |
| `dim_sku` | SKU | Conformed SKU dimension |
| `fct_purchase_order_lines` | PO line | Atomic procurement fact (fill, lead time, on-time) |
| `fct_shipments` | shipment | Atomic delivery fact (lead time, on-time) |
| `fct_quality_inspections` | inspection | Atomic quality fact (defect PPM per inspection) |
| `fct_inventory_daily` | SKU-day | Atomic inventory fact (on-hand, days-of-supply) |
| `kpi_supplier_scorecard` | supplier | All supplier KPIs + composite score |
| `kpi_supplier_monthly` | supplier-month | Supplier KPI time series (for Grafana) |
| `kpi_sku_inventory` | SKU | Inventory turns, days-of-supply, stockout frequency |

## KPI formulas

### On-Time-Delivery (OTD) Rate — `kpi_supplier_scorecard.otd_rate`, `kpi_supplier_monthly.otd_rate`
Share of a supplier's shipments received on or before the PO promised date.
```
count(shipments where received_date <= promised_date) / count(shipments)
```
Range 0–1. Monthly version buckets by shipment received month.

### Lead Time — `kpi_supplier_scorecard.avg_lead_time_days`
Days from PO order to receipt, averaged per supplier.
```
avg(received_date - order_date)   -- per shipment in fct_shipments
```

### Fill Rate — `kpi_supplier_scorecard.fill_rate`
Quantity delivered vs ordered, aggregated across the supplier's PO lines.
```
sum(received_qty) / sum(ordered_qty)
```
Per-line version: `fct_purchase_order_lines.line_fill_rate` (capped at 1).

### Defect PPM — `kpi_supplier_scorecard.defect_ppm`, `kpi_supplier_monthly.defect_ppm`
Defective units per million inspected.
```
sum(defect_qty) / sum(inspected_qty) * 1,000,000
```
Per-inspection version: `fct_quality_inspections.defect_ppm`.

### PO Cycle Time — `kpi_supplier_scorecard.avg_po_cycle_time_days`
Days from PO creation to closure (fully received), for closed POs only.
```
avg(closure_date - order_date)    -- closure = max receipt date across the PO's lines
```

### Inventory Turns — `kpi_sku_inventory.inventory_turns`
Annualized demand throughput relative to average stock held.
```
(sum(daily_demand) / snapshot_days * 365) / avg(on_hand_qty)
```

### Days of Supply — `kpi_sku_inventory.days_of_supply`
Runway at current stock given average demand (from the latest snapshot).
```
current_on_hand / avg(daily_demand)
```

### Stockout Frequency — `kpi_sku_inventory.stockout_frequency`
Share of a SKU's days spent at zero on-hand.
```
count(SKU-days in stockout) / count(SKU-days)
```
Range 0–1.

### Supplier Scorecard — `kpi_supplier_scorecard.composite_score`
0–100 composite, higher is better. Weights favour reliability (OTD + fill = 60%).
```
100 * ( 0.35 * otd_rate
      + 0.25 * fill_rate
      + 0.20 * (1 - min(1, defect_ppm / 25000))
      + 0.20 * (1 - min(1, avg_lead_time_days / promised_lead_time_days)) )
```

## Tests

Every mart has `not_null` + `unique` on its key and `relationships` on its foreign keys
(see `_marts.yml`). A singular test (`tests/assert_kpi_value_ranges.sql`) asserts all rates
stay within [0,1] and scores within [0,100]. Run with `dbt build`.
