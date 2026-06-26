# transform/ — dbt Project

Turns `raw_*` landing tables into business entities and the full KPI set. This is the contract
the web app and BI tools read. KPI definitions live **only** here — see
[models/marts/README.md](models/marts/README.md).

## Layers

```
models/
  staging/        stg_<source>__<entity>  — 1:1 renames + casts (views)
  intermediate/   int_<concept>           — joins / per-row logic (ephemeral)
  marts/          dim_*, fct_*, kpi_*      — entities + KPIs (tables)
```

Schemas: staging views land in `staging`, marts in `marts` (see `macros/generate_schema_name.sql`).
Only `staging/` may reference `raw_*`.

## Run

Requires the stack up and Phase 2 landing done (`raw_*` populated):

```bash
python3 -m venv .venv && .venv/bin/pip install dbt-postgres==1.9.0
.venv/bin/dbt debug --profiles-dir .
.venv/bin/dbt build  --profiles-dir .      # models + all tests
```

Connection defaults to `localhost:5433` (host-mapped Postgres); override with
`PARTFLOW_PG_HOST/PORT/USER/PASSWORD/DBNAME/SCHEMA` env vars (Airflow uses `postgres:5432`).

## Test before commit

`dbt build` (models + tests). Must pass clean — every mart has `not_null`/`unique` on its key,
`relationships` on its FKs, plus a singular KPI value-range test.
