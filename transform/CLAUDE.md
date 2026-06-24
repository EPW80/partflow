# transform/ — dbt: staging → marts → KPIs

Owns all data shaping and every KPI definition. This is the contract the rest of the system reads.

## Rules
- IMPORTANT: Every mart model needs dbt tests (`not_null` + `unique` on its key, `relationships` on FKs). Untested marts have shipped wrong KPIs silently — a mart without tests is incomplete.
- IMPORTANT: KPI logic lives here and nowhere else. If the web app or a dashboard needs a number, expose it as a mart column.
- Do layer strictly: `staging/` (1:1 renames + casts, materialized as views), `intermediate/` (joins/logic, ephemeral), `marts/` (business entities + KPIs, tables).
- Do name: `stg_<source>__<entity>`, `int_<concept>`, and `<entity>` or `kpi_<metric>` for marts.
- Don't reference `raw_*` tables outside `staging/`. Don't `select *` in marts.
- Document every KPI formula in `models/marts/README.md` — the single source for definitions.

## KPIs to model
supplier on-time-delivery rate, lead time, fill rate, inventory turns, days-of-supply, defect PPM, PO cycle time, stockout frequency, supplier scorecard.

## Test before commit
`dbt build` (models + tests). Must pass clean.
