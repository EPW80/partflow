# pipelines/ — Orchestration & Raw Landing

Ingestion + orchestration layer for PartFlow. Lands source data into `raw_*` tables
idempotently, then an Airflow DAG chains landing → `dbt build` → data-quality gates that fail
loudly on bad data.

## Orchestration

`dags/partflow_ingest.py` runs the end-to-end chain on a daily schedule:

```
apply_raw_schema
  └─► land_reference / land_procurement / land_inventory   (per-domain TaskGroups)
        └─► build_marts (dbt build)
              └─► gate_freshness ─► gate_row_counts ─► gate_null_rates ─► gate_mart_quality
```

Each gate is a task that raises `DataQualityError` on violation, failing the DAG — never
log-and-continue (see [ADR-0003](../docs/adr/0003-data-quality-gate-strategy.md)). dbt runs in
an isolated venv baked into the Airflow image (`infra/airflow/Dockerfile`).

### Data-quality gates (`quality/`)

- `checks.py` — primitives: `check_freshness`, `check_row_count`, `check_null_rate`
- `specs.py` — declarative thresholds (adding a gate is data, not code)
- `mart_expectations.py` — GE-style assertion suite over `kpi_supplier_scorecard`

### Run the DAG locally

```bash
docker compose -f infra/docker-compose.yml up -d --build       # builds the dbt-enabled image
docker compose -f infra/docker-compose.yml exec airflow-scheduler \
    airflow dags test partflow_ingest                          # full chain end-to-end
```
Or trigger it from the Airflow UI at http://localhost:8080 (`airflow` / `airflow`).

## Three source patterns

| Pattern | Source | Tables |
| ------- | ------ | ------ |
| CSV drop | `data/output/*.csv` (batch, full refresh) | All 9 `raw_*` tables |
| REST endpoint | Fake supplier catalog API | `raw_suppliers`, `raw_skus` |
| Webhook | Real-time material-flow events | `raw_material_flow_events` |

All three land via UPSERT on the source's natural PK — re-running yields identical row counts.

## Run (standalone, without Airflow)

```bash
# 1. Generate source data (if not done)
cd ../data && .venv/bin/python generate.py --out output

# 2. Install deps and land
cd ../pipelines
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python land.py --data ../data/output
```

Requires the stack to be up: `docker compose -f infra/docker-compose.yml up -d`

## Test before commit

```bash
.venv/bin/python -m pytest    # runs against live Postgres on localhost:5433
```

Tests are skipped automatically if Postgres is not reachable.

## Layout

- `ingestion/db.py` — connection helper (no top-level connections; safe for Airflow DAG parse)
- `ingestion/schema.py` — `CREATE TABLE IF NOT EXISTS raw_*` DDL + `apply_schema(conn)`
- `ingestion/loaders.py` — `land_csv_table`, `land_rest_records`, `land_webhook_event`
- `ingestion/sources.py` — fake REST catalog + webhook stream simulators
- `land.py` — standalone runner demonstrating all three patterns
- `dags/` — Airflow DAGs (Phase 4)
- `quality/` — DQ gate functions (Phase 4)
