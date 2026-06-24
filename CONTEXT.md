# PartFlow — Domain Context

Shared language for the supply-chain operations domain. Use these terms verbatim in code,
model names, test names, issue titles, and KPI columns. All data is **synthetic**.

> This glossary is seeded, not exhaustive. `/grill-with-docs` extends it as terms get
> resolved; `/grill-with-docs` and ADRs under `docs/adr/` record the *why* behind decisions.

## Core entities

- **Supplier** — an external vendor that fulfills purchase orders. Identified by `supplier_id`.
- **Part / SKU** — a stock-keeping unit; the thing bought, stored, and inspected. `sku_id`.
  "Part" and "SKU" are interchangeable; prefer **SKU** in code.
- **Purchase Order (PO)** — an order placed with a supplier for one or more SKUs. `po_id`.
  Has an order date, promised date, and line items.
- **Shipment** — a physical delivery fulfilling all or part of a PO. `shipment_id`.
  Has a ship date and a received date.
- **Inventory Position** — on-hand quantity of a SKU at a point in time. Snapshotted daily.
- **Quality Inspection** — an inspection of received goods recording pass/fail and defects.
- **Material-Flow Event** — an atomic movement event (received, putaway, picked, shipped)
  forming the event stream over which throughput is measured.

## KPIs (defined ONLY in `transform/` marts — never recomputed elsewhere)

- **On-Time-Delivery (OTD) Rate** — share of shipments received on or before the PO promised
  date. Per supplier and overall.
- **Lead Time** — elapsed time from PO order date to shipment received date (days).
- **Fill Rate** — share of ordered quantity actually delivered (line-level → aggregated).
- **Inventory Turns** — cost of goods sold over the period ÷ average inventory; how many times
  inventory cycles.
- **Days of Supply** — current on-hand quantity ÷ average daily demand; runway in days.
- **Defect PPM** — defective units per million inspected (parts-per-million quality measure).
- **PO Cycle Time** — elapsed time from PO creation to PO closure (fully received).
- **Stockout Frequency** — count/rate of SKU-days where on-hand quantity hit zero against demand.
- **Supplier Scorecard** — composite supplier rating rolling up OTD, lead-time variance, fill
  rate, and defect PPM.

## Pipeline vocabulary

- **Raw landing** — loading source data as-received into `raw_*` tables; no shaping. Lives in
  `pipelines/`. Must be **idempotent** (re-run yields identical row counts).
- **Staging** (`stg_<source>__<entity>`) — 1:1 renames + casts, materialized as views.
- **Intermediate** (`int_<concept>`) — joins and business logic, ephemeral.
- **Mart** (`<entity>` or `kpi_<metric>`) — business entities and KPIs, materialized as tables.
  The only contract `web/` and BI tools read.
- **Data-Quality (DQ) gate** — an explicit Airflow task that *fails the DAG loudly* on bad data
  (freshness, row-count, null-rate). Never log-and-continue.
- **Source simulator** — synthetic generator standing in for a real source (CSV drop, fake REST
  endpoint, webhook). There are no real supplier APIs.
