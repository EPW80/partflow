# Data-quality gate strategy

Phase 4 puts the pipeline on a schedule and makes it fail loudly when data goes bad. This ADR
fixes *what* we check, *where* in the chain we check it, and *how* a failure manifests — so a
corrupted source stops the pipeline at a named gate instead of silently shipping a wrong KPI.

## Principle: gates fail the DAG, never log-and-continue

Every quality check is an Airflow task that raises on violation. A raised exception fails the
task, which fails the DAG run and surfaces in the UI and logs. We never warn-and-proceed — a
gate that doesn't stop bad data is decoration.

## The chain

Each ingest DAG runs: **land → dbt build → DQ gates**, in that order.

```
land_<domain> ... ─► build_marts (dbt build) ─► gate_freshness ─► gate_row_counts ─► gate_null_rates ─► gate_mart_quality
```

Two lines of defence, deliberately redundant:

1. **dbt build** runs the Phase 3 schema/data tests (not_null, unique, relationships,
   value-range). Structural corruption (orphan FKs, duplicate keys, out-of-range KPIs) fails
   here.
2. **DQ gate tasks** run after, querying Postgres directly for the three operational checks
   that dbt tests don't cover well: freshness, volume, and null-rate on landed data. Plus a
   focused expectation suite on the most important mart.

## The three operational gates

Implemented as reusable functions in `pipelines/quality/checks.py`, raising `DataQualityError`:

- **Freshness** — `max(_landed_at)` for each raw table is within a max-age window (default 48h).
  Catches a source that silently stopped delivering.
- **Row count** — each raw table has at least a configured minimum row count. Catches an empty
  or truncated drop.
- **Null rate** — business-critical columns (e.g. `order_date`, `received_date`, `supplier_id`)
  have a null fraction at or below a threshold (default 0). Catches malformed source records.

Thresholds live in a declarative spec (`pipelines/quality/specs.py`) — one row per check — so
adding a gate is data, not code.

## Mart expectation suite

`gate_mart_quality` runs a small assertion suite over `kpi_supplier_scorecard` (the headline
mart): supplier_id non-null and unique, `otd_rate`/`fill_rate` within [0,1], `composite_score`
within [0,100], and row count equal to the supplier dimension. This is a hand-rolled
Great-Expectations-style suite; GE itself is the production swap-in but is intentionally avoided
here to keep the image light and the dependency surface small.

## Corruption demonstration

The done-when gate ("a deliberately corrupted source fails the DAG") is exercised by landing a
malformed batch (e.g. shipments with null `received_date`) and asserting the relevant gate
raises. Covered by `pipelines/tests/test_quality_checks.py` and reproducible against a live DAG.

## Orchestration shape

One end-to-end DAG, `partflow_ingest`, with per-domain landing grouped into TaskGroups
(reference, procurement, inventory). A single DAG keeps the demo legible and the dbt build
shared. The production evolution is per-domain ingest DAGs emitting Airflow Datasets, with a
Dataset-triggered transform DAG — noted here so the simplification is a known decision, not an
oversight.

## dbt inside Airflow

dbt runs in an **isolated virtualenv** baked into the Airflow image (`/opt/dbt-venv`), invoked
by a BashOperator. The venv keeps dbt's dependencies off Airflow's constraint-pinned
environment. dbt writes target/log artifacts to `/tmp` (the mounted project dir is read-only to
the Airflow user) and connects to `postgres:5432` via `PARTFLOW_PG_*` env vars.
