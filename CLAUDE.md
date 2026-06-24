# PartFlow — Supply Chain Operations Data Platform

Synthetic supply chain ops data → orchestrated ETL → KPIs → self-service dashboards.
A full-lifecycle demo of data-engineering ownership: ingest, transform, model, surface, monitor, iterate.

## Map

- `data/` synthetic generator + source simulators
- `pipelines/` Airflow DAGs + raw landing — see `pipelines/CLAUDE.md`
- `transform/` dbt: staging → marts → KPIs — see `transform/CLAUDE.md`
- `web/` Next.js self-service app — see `web/CLAUDE.md`
- `infra/` docker-compose: Postgres, Airflow, Grafana, Metabase
- `BUILD_PLAN.md` phased plan + model-routing table

## Invariants

- IMPORTANT: All data is synthetic. Never wire a real supplier/vendor API or any real PII. Generated files must carry a `# SYNTHETIC DATA` header.
- IMPORTANT: Postgres is the single source of truth. Marts are the only contract the web app and BI tools read from.
- KPI definitions live ONLY in `transform/` marts. Don't recompute a KPI anywhere else — read the mart column.
- Conventional commits (`feat`/`fix`/`chore`/`docs`/`refactor`). One logical change per commit.
- Run the touched layer's tests before committing (each module's file says how).
- Secrets via env vars only. Don't commit `.env`; keep keys documented in `.env.example`.

## Boundaries

- Don't blur layers: `pipelines/` lands raw, `transform/` models it, `web/` + BI read marts. Presentation code never computes business logic.
- For KPI formulas and definitions, see `transform/models/marts/README.md`.

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues on `EPW80/partflow` (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Self-improvement

After I correct you, update the _narrowest_ applicable CLAUDE.md so the mistake can't recur. Don't duplicate a rule across files.
