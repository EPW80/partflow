# pipelines/ — Orchestration & Raw Landing

Ingestion layer for PartFlow. Lands source data into `raw_*` tables in Postgres, idempotently.
Phase 4 wraps these functions in Airflow DAGs with data-quality gates; this layer is the
reusable core those DAGs call.

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
