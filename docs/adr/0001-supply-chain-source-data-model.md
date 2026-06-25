# Supply-chain source data model

Phase 1 needs an entity model that (a) is realistic enough that every KPI in
[CONTEXT.md](../../CONTEXT.md) can be derived downstream, and (b) has clean referential
integrity so `transform/` can join it without guessing. This ADR fixes that model. It
describes the **source** shape the generator emits and Phase 2 lands as `raw_*`; the
dimensional mart shape is a separate, later decision (Phase 3). All data is synthetic.

## Entities and keys

Nine source tables, in dependency order (each only references tables above it):

| Table | Grain / PK | Key foreign keys | Exists to support |
| ----- | ---------- | ---------------- | ----------------- |
| `suppliers` | one supplier — `supplier_id` | — | supplier scorecard, OTD, lead time |
| `skus` | one stock-keeping unit — `sku_id` | `primary_supplier_id` → suppliers | inventory, defect PPM, fill rate |
| `purchase_orders` | one PO header — `po_id` | `supplier_id` → suppliers | PO cycle time, OTD |
| `purchase_order_lines` | one PO line — `po_line_id` | `po_id` → POs, `sku_id` → skus | fill rate, ordered qty |
| `shipments` | one delivery — `shipment_id` | `po_id` → POs | lead time, OTD |
| `shipment_lines` | one shipped line — `shipment_line_id` | `shipment_id` → shipments, `po_line_id` → PO lines | fill rate (received vs ordered) |
| `quality_inspections` | one inspection — `inspection_id` | `shipment_line_id` → shipment lines | defect PPM |
| `inventory_snapshots` | one SKU-day — (`snapshot_date`,`sku_id`) | `sku_id` → skus | inventory turns, days of supply, stockout frequency |
| `material_flow_events` | one movement event — `event_id` | `sku_id` → skus | throughput (event stream) |

### Why this shape

- **Header/line split for POs and shipments.** Fill rate and defect PPM are line-level
  (per SKU), but OTD and cycle time are header-level (per delivery/order). Splitting headers
  from lines lets each KPI aggregate at its natural grain without double-counting.
- **Shipments reference POs, not the reverse.** One PO can be fulfilled by several partial
  shipments — the realistic case that makes fill rate and OTD interesting. A shipment line
  points back at the exact PO line it fulfils, so received-vs-ordered is unambiguous.
- **Inventory as daily snapshots, not derived.** Days-of-supply and stockout frequency need a
  dense daily on-hand series. We materialize snapshots directly (not as a running balance the
  marts must reconstruct) so the source already answers "what was on hand on day D."
- **Events are a separate append-only stream.** Throughput is measured over discrete movement
  events (`received`/`putaway`/`picked`/`shipped`), which don't fit the snapshot or order grain.

## Realistic distributions (what makes it not-uniform-noise)

Each **supplier carries latent quality parameters** drawn once, so suppliers are persistently
good or bad — that's what the supplier scorecard must surface:

- `lead_time_mean_days` (7–45) and a variance factor; actual transit per shipment is drawn
  from a Gamma around that mean, so OTD varies by supplier and by luck.
- `base_otd` reliability and `defect_rate_ppm` baseline; better suppliers ship on time and clean.
- `fill_reliability`; occasional short shipments (received < ordered) cluster on weak suppliers.

Demand is **seasonal**: a monthly multiplier (annual sinusoid + noise) drives PO frequency and
line quantities, so inventory draw-down and stockouts track a believable cycle rather than a
flat rate. Inventory snapshots are simulated as receipts (from shipments) minus seasonal
consumption, clamped at zero, so stockouts emerge endogenously rather than being sprinkled in.

## Materialization

- The generator writes **one CSV per table** into `data/output/` (gitignored — regenerable).
- Every file's first line is `# SYNTHETIC DATA`; the CSV header follows. Ingestion reads with
  `comment='#'`-style skipping. This satisfies the repo invariant that every generated file is
  labelled synthetic, and keeps Phase 2 landing trivial (one raw table per file).
- Generation is **seeded** (default seed fixed) so a run is reproducible; the seed and date
  range are CLI flags.

## Consequences

- Phase 2 lands these nine files into nine `raw_*` tables verbatim — no shaping.
- Phase 3 marts join along the FKs above; every CONTEXT.md KPI has a derivation path.
- If a KPI later needs a field this model lacks, the fix is to extend the generator + this ADR,
  not to invent the column mid-pipeline.
