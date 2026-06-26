# PartFlow — Supply Chain Operations Data Platform

> **All data in this project is synthetic.** No real supplier, vendor, or PII data is used
> anywhere. Source files are machine-generated and carry a `# SYNTHETIC DATA` header.

PartFlow is an end-to-end data platform for supply-chain operations: it generates realistic
synthetic ops data, lands it through an orchestrated ETL pipeline, models it into KPI marts,
and surfaces those KPIs to dashboards and a self-service web app. It's a full-lifecycle demo of
data-engineering ownership — **ingest → transform → model → surface → monitor → iterate**.

## Why this exists

Supply-chain teams need trustworthy answers to operational questions — *which suppliers are
slipping? where will we stock out? which parts fail inspection?* — without analysts hand-rolling
a different number in every spreadsheet. PartFlow demonstrates the engineering that makes those
answers reliable: a single warehouse of record, KPI logic defined exactly once, tested
transformations, and monitored pipelines that fail loudly on bad data.

## Architecture

```
 data/                pipelines/              transform/ (dbt)            web/ + BI
┌───────────┐  CSV   ┌──────────────┐  raw_* ┌────────────────────┐ marts ┌──────────────┐
│ synthetic │ ─────► │ idempotent   │ ─────► │ staging → int →    │ ────► │ Next.js app  │
│ generator │  REST  │ landing      │        │ marts (KPIs)       │       │ Grafana      │
│ (Faker)   │ webhook│ (UPSERT)     │        │ tested, documented │       │ Metabase     │
└───────────┘        └──────────────┘        └────────────────────┘       └──────────────┘
                            ▲                          ▲
                      ┌─────┴──────────────────────────┴─────┐
                      │ Airflow: land → dbt build → DQ gates  │   (orchestration, Phase 4)
                      └───────────────────────────────────────┘

                 Postgres is the single source of truth for every layer.
```

**Layer boundaries are strict:** `pipelines/` lands raw data as-received, `transform/` owns all
shaping and every KPI definition, and `web/` + BI tools only ever read marts. Presentation code
never computes a business metric — if a number isn't in a mart, the fix is a new mart column.

## Current state

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 0 | Infra scaffolding — one-command Docker stack (Postgres, Airflow, Grafana, Metabase) | ✅ Done |
| 1 | Data model + synthetic generator (9 referentially-intact source tables) | ✅ Done |
| 2 | Ingestion — idempotent `raw_*` landing (CSV drop, REST, webhook) | ✅ Done |
| 3 | dbt transforms + KPI marts (staging → intermediate → marts, fully tested) | ✅ Done |
| 4 | Airflow orchestration + data-quality gates | ⬜ Planned |
| 5 | ML — supplier lead-time forecast / inventory anomaly detection | ⬜ Planned |
| 6 | BI dashboards (Grafana ops monitoring + Metabase self-service) | ⬜ Planned |
| 7 | Next.js self-service app (read-only, typed, plain-language KPIs) | ⬜ Planned |
| 8 | CI/CD, monitoring, and the full lifecycle narrative | ⬜ Planned |

See [BUILD_PLAN.md](BUILD_PLAN.md) for the phased plan and gates.

## KPIs

Every KPI is defined exactly once, as a column in a dbt mart
([formulas here](transform/models/marts/README.md)):

- **Supplier scorecard** — composite 0–100 reliability score per supplier
- **On-time-delivery rate**, **lead time**, **fill rate** — supplier delivery performance
- **Defect PPM** — quality, from inspections
- **PO cycle time** — order-to-closure duration
- **Inventory turns**, **days of supply**, **stockout frequency** — inventory health

Supplier KPIs are also exposed as a monthly time series for trend monitoring.

## Tech stack

| Concern | Tool |
| ------- | ---- |
| Warehouse | PostgreSQL 16 |
| Synthetic data | Python, Faker, NumPy |
| Ingestion | Python (psycopg2), idempotent UPSERT |
| Transformation | dbt (dbt-postgres) |
| Orchestration | Apache Airflow (LocalExecutor) |
| BI | Grafana, Metabase |
| App | Next.js (App Router), TypeScript |
| Local infra | Docker Compose |

## Quickstart

Requires Docker, Python 3.12+, and Node 22+.

```bash
# 1. Bring up the stack (Postgres, Airflow, Grafana, Metabase)
docker compose -f infra/docker-compose.yml up -d

# 2. Generate synthetic source data
cd data && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python generate.py --out output        # 6 months, ~140k rows
cd ..

# 3. Land it into raw_* tables (idempotent)
cd pipelines && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python land.py --data ../data/output
cd ..

# 4. Build the KPI marts
cd transform && python3 -m venv .venv && .venv/bin/pip install dbt-postgres==1.9.0
.venv/bin/dbt build --profiles-dir .
```

Then explore the marts in Metabase (http://localhost:3000) or query directly:

```sql
SELECT * FROM marts.kpi_supplier_scorecard ORDER BY composite_score DESC;
```

| Service | URL | Default login |
| ------- | --- | ------------- |
| Metabase | http://localhost:3000 | set on first load |
| Airflow | http://localhost:8080 | `airflow` / `airflow` |
| Grafana | http://localhost:3001 | `admin` / `admin` |
| Postgres | `localhost:5433` | `partflow` / `partflow` |

## Repository layout

```
data/         synthetic generator + source simulators (Phase 1)
pipelines/    Airflow DAGs + idempotent raw landing (Phase 2, 4)
transform/    dbt project: staging → intermediate → marts (Phase 3)
web/          Next.js self-service app (Phase 7)
infra/        docker-compose stack + provisioning
docs/adr/     architecture decision records
BUILD_PLAN.md phased delivery plan
```

## Testing

Each layer is tested before commit:

```bash
cd data       && .venv/bin/python -m pytest    # generator: 35 tests
cd pipelines  && .venv/bin/python -m pytest    # ingestion: 13 integration tests
cd transform  && .venv/bin/dbt build --profiles-dir .   # 66 models + data tests
```

## Status

Phases 0–3 are complete: the stack boots with one command, generates a coherent multi-month
dataset, lands it idempotently, and builds a clean, fully-tested set of KPI marts. Orchestration,
ML, dashboards, and the web app are next.
