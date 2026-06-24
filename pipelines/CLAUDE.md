# pipelines/ — Orchestration & Raw Landing

Airflow DAGs that run source simulators, land raw data, trigger dbt, and gate on data quality.

## Rules
- IMPORTANT: No DB calls, network calls, or heavy imports at DAG-parse top level. Airflow re-parses every file on a schedule — top-level side effects cause silent scheduler stalls and import errors that never reach task logs. All work goes inside task functions.
- IMPORTANT: Tasks must be idempotent. Re-running for the same logical date produces the same result — truncate-and-load or upsert on a natural key, never blind append.
- Don't put transformation logic here. Land raw as-received into `raw_*` tables; `transform/` (dbt) owns all shaping.
- Do name DAGs `<domain>_ingest` and tasks `<verb>_<object>` (e.g. `load_purchase_orders`).
- Do make data-quality gates explicit tasks that *fail the DAG loudly*, never log-and-continue.

## Layout
- `dags/`        one DAG per source domain
- `ingestion/`   reusable landing functions (CSV drop, fake REST, webhook)
- `quality/`     freshness + row-count + null-rate checks

## Test before commit
`pytest pipelines/`, plus `airflow dags test <dag_id> <date>` for any changed DAG.
