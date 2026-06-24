# data/ — Synthetic Generator & Source Simulators

Generates the synthetic supply-chain dataset and the source files the pipeline ingests.
**All data is synthetic** — every generated file carries a `# SYNTHETIC DATA` header.
Built in Phase 1 (data model + generator).

Planned contents:
- `generate.py` — Faker + realistic distributions (lead-time variance, seasonal demand,
  defect rates) producing a coherent multi-month dataset with referential integrity.
- `output/` — generated source files (CSV drop, REST/webhook payloads); gitignored.

See [BUILD_PLAN.md](../BUILD_PLAN.md) Phase 1 and [CONTEXT.md](../CONTEXT.md) for the entities.
