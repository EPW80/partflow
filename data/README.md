# data/ — Synthetic Generator & Source Simulators

Generates the synthetic supply-chain dataset the pipeline ingests. **All data is synthetic** —
every generated CSV's first line is `# SYNTHETIC DATA`. The entity model and the realistic
distributions are specified in [docs/adr/0001-supply-chain-source-data-model.md](../docs/adr/0001-supply-chain-source-data-model.md).

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python generate.py --out output            # defaults: 6 months, seed 42
.venv/bin/python generate.py --months 12 --seed 7    # override horizon / seed
```

Output (gitignored — regenerable) is one CSV per source table in `output/`:

| Table | Grain | Drives |
| ----- | ----- | ------ |
| `suppliers` | supplier | scorecard, OTD, lead time |
| `skus` | SKU | inventory, defect PPM |
| `purchase_orders` / `purchase_order_lines` | PO header / line | PO cycle time, fill rate |
| `shipments` / `shipment_lines` | delivery / line | lead time, OTD, fill rate |
| `quality_inspections` | inspection | defect PPM |
| `inventory_snapshots` | SKU-day | inventory turns, days of supply, stockout frequency |
| `material_flow_events` | movement event | throughput |

Supplier on-time rate, defect rate, and demand are **latent** generation parameters — they
drive the simulation but are deliberately *not* emitted as source columns. The marts must
recompute those KPIs from events; the source never hands them the answer.

## Layout

- `partflow_gen/` — generator package: `config` (knobs), `model` (domain objects + seasonality),
  `entities` (suppliers, SKUs), `procurement` (POs → shipments → inspections),
  `operations` (inventory snapshots, events), `pipeline` (orchestration), `writers` (CSV + header).
- `generate.py` — CLI entry point.
- `tests/` — referential-integrity, distribution, and determinism tests.

## Test before commit

```bash
.venv/bin/python -m pytest
```
