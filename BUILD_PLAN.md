# PartFlow — Build Plan

A phased plan for building the platform end-to-end. Each phase has a goal, a routed model,
deliverables, and a done-when gate. Build phases in order; don't start a phase until the
previous one's gate is green.

## Model routing

| Model      | Use for                                                                                                                                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Opus**   | Architecturally novel or foundational decisions: the data model, the KPI/mart dimensional design, the data-quality strategy, the ML approach, the README lifecycle narrative. Anything where a wrong call propagates everywhere. |
| **Sonnet** | Constrained implementation against a settled design: DAGs, dbt models, components, dashboards, CI config. The bulk of the build.                                                                                                 |
| **Haiku**  | Mechanical, low-judgment work: boilerplate models, repetitive panels, fixture data, YAML wiring, renames.                                                                                                                        |

Rule of thumb: Opus decides the shape, Sonnet builds it, Haiku fills it in.

## Phase overview

| #   | Phase                               | Lead model             |
| --- | ----------------------------------- | ---------------------- |
| 0   | Infra scaffolding                   | Sonnet → Haiku         |
| 1   | Data model + synthetic generator    | Opus → Haiku           |
| 2   | Ingestion / raw landing             | Sonnet → Haiku         |
| 3   | dbt transforms + KPI marts          | Opus → Sonnet → Haiku  |
| 4   | Airflow orchestration + DQ gates    | Opus (DQ) → Sonnet     |
| 5   | ML: lead-time forecast / anomaly    | Opus → Sonnet          |
| 6   | BI dashboards (Grafana + Metabase)  | Sonnet → Haiku         |
| 7   | Next.js self-service app            | Sonnet → Haiku         |
| 8   | CI/CD, monitoring, README narrative | Sonnet + Opus (README) |

---

## Phase 0 — Infra scaffolding

**Model:** Sonnet (compose architecture) → Haiku (boilerplate)
**Goal:** One-command local stack.
**Deliverables:** `infra/docker-compose.yml` running Postgres, Airflow, Grafana, Metabase; `.env.example`; repo skeleton matching the Map in root `CLAUDE.md`; `.gitignore` including `.claude/local.md` and `.env`.
**Done when:** `docker compose up` brings all services healthy and each UI loads.

## Phase 1 — Data model + synthetic generator

**Model:** Opus (schema design) → Haiku (generator code)
**Goal:** A realistic, synthetic supply chain dataset and the schema it lands into.
**Deliverables:** ER design for suppliers, parts/SKUs, purchase orders, shipments, inventory positions, quality inspections, material-flow events; Python generator (Faker + realistic distributions: lead-time variance, seasonal demand, defect rates) writing `# SYNTHETIC DATA`-headed source files.
**Done when:** Generator produces a coherent multi-month dataset with referential integrity across domains.

## Phase 2 — Ingestion / raw landing

**Model:** Sonnet (landing design) → Haiku (connectors)
**Goal:** Get raw data into Postgres `raw_*` tables from varied "sources."
**Deliverables:** Idempotent landing functions for a CSV drop, a fake supplier REST endpoint, and a webhook; `raw_*` tables. No shaping — land as-received.
**Done when:** A full load is idempotent (re-run yields identical row counts) and every source domain is present in `raw_*`.

## Phase 3 — dbt transforms + KPI marts

**Model:** Opus (mart/KPI dimensional design) → Sonnet (model impl) → Haiku (boilerplate + tests)
**Goal:** Turn raw into business entities and the full KPI set.
**Deliverables:** `staging/` (views), `intermediate/` (ephemeral), `marts/` (tables) including all KPIs from `transform/CLAUDE.md`; dbt tests on every mart; `models/marts/README.md` documenting each formula.
**Done when:** `dbt build` passes clean and every listed KPI is a queryable mart column.

## Phase 4 — Airflow orchestration + data-quality gates

**Model:** Opus (DQ strategy) → Sonnet (DAGs)
**Goal:** Scheduled, monitored pipeline with loud failure on bad data.
**Deliverables:** `<domain>_ingest` DAGs chaining land → `dbt build` → DQ checks; freshness, row-count, and null-rate gates as failing tasks; optional Great Expectations suite on a critical mart.
**Done when:** A scheduled run completes green end-to-end, and a deliberately corrupted source fails the DAG at the gate.

## Phase 5 — ML: lead-time forecast / anomaly

**Model:** Opus (approach selection) → Sonnet (impl)
**Goal:** One honest predictive component feeding a mart.
**Deliverables:** Supplier lead-time prediction or inventory anomaly detection in scikit-learn (Pandas/NumPy features); results written to a `kpi_*` or prediction mart. Use PyTorch only if you want a small lead-time regressor to demonstrate it — don't force it where boosting is the honest choice.
**Done when:** Predictions land in a mart with a documented eval metric and are queryable like any KPI.

## Phase 6 — BI dashboards

**Model:** Sonnet (dashboard design) → Haiku (repetitive panels)
**Goal:** Two surfaces for two audiences.
**Deliverables:** Grafana for ops/time-series monitoring (throughput, defect PPM over time, pipeline health/freshness) wired to Postgres; Metabase for self-service exploration over marts; exported dashboard configs committed to `infra/`.
**Done when:** Both tools render live KPIs from marts and the configs reproduce on a fresh stack.

## Phase 7 — Next.js self-service app

**Model:** Sonnet (components/data layer) → Haiku (mechanical UI)
**Goal:** A polished, read-only stakeholder surface.
**Deliverables:** App Router app querying marts via a read-only role; curated KPI views with drill-down filters; per-KPI tooltips in plain language; typed query results.
**Done when:** `npm run typecheck && npm run test` pass, app builds clean, and a non-technical reader can find a KPI and understand it without docs.

## Phase 8 — CI/CD, monitoring, README narrative

**Model:** Sonnet (workflows) → Opus (README)
**Goal:** Prove operational maturity and tell the ownership story.
**Deliverables:** GitHub Actions running `pytest` + `dbt build` (+ web typecheck/test) on PRs; a Grafana freshness/health panel as the monitoring story; root `README.md` narrating the full lifecycle — problem identification → ideation → architecture → implementation → adoption → monitoring → iteration — mirroring the role's responsibilities, and stating up front that all data is synthetic.
**Done when:** CI is green on a PR, the health panel reflects pipeline state, and the README reads as an end-to-end ownership account.
