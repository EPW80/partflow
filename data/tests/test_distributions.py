"""Behaviors that make the data realistic, and the invariant that latent truth isn't leaked."""

from __future__ import annotations

from datetime import date


def test_otd_rate_is_plausible(dataset):
    """On-time = received on/before promised. Aggregate OTD should sit in a believable band."""
    promised = {po["po_id"]: date.fromisoformat(po["promised_date"]) for po in dataset["purchase_orders"]}
    on_time = total = 0
    for s in dataset["shipments"]:
        total += 1
        if date.fromisoformat(s["received_date"]) <= promised[s["po_id"]]:
            on_time += 1
    rate = on_time / total
    assert 0.5 < rate < 0.99, f"implausible aggregate OTD rate: {rate:.2f}"


def test_fill_never_exceeds_ordered(dataset):
    ordered = {l["po_line_id"]: l["ordered_qty"] for l in dataset["purchase_order_lines"]}
    for sl in dataset["shipment_lines"]:
        assert sl["received_qty"] <= sl["shipped_qty"]
        assert sl["shipped_qty"] <= ordered[sl["po_line_id"]], "shipped exceeds ordered"


def test_some_short_shipments_exist(dataset):
    ordered = {l["po_line_id"]: l["ordered_qty"] for l in dataset["purchase_order_lines"]}
    short = [sl for sl in dataset["shipment_lines"] if sl["shipped_qty"] < ordered[sl["po_line_id"]]]
    assert short, "expected at least some short shipments (fill < 1)"


def test_defects_are_nonnegative_and_bounded(dataset):
    saw_defect = False
    for ins in dataset["quality_inspections"]:
        assert 0 <= ins["defect_qty"] <= ins["inspected_qty"]
        saw_defect = saw_defect or ins["defect_qty"] > 0
    assert saw_defect, "expected at least some defects across inspections"


def test_stockouts_emerge(dataset):
    stockouts = [r for r in dataset["inventory_snapshots"] if r["in_stockout"]]
    assert stockouts, "expected at least some stockout days"


def test_seasonal_demand_varies(dataset):
    by_month: dict[str, int] = {}
    for r in dataset["inventory_snapshots"]:
        m = r["snapshot_date"][:7]
        by_month[m] = by_month.get(m, 0) + r["daily_demand_qty"]
    totals = list(by_month.values())
    assert max(totals) > min(totals), "demand should vary month to month"


def test_suppliers_source_does_not_leak_latent_truth(dataset):
    """OTD/defect/fill are KPIs the marts must compute — never source columns."""
    cols = set(dataset["suppliers"][0].keys())
    for leaked in {"base_otd", "defect_rate_ppm", "fill_reliability", "lead_time_mean_days"}:
        assert leaked not in cols, f"latent field {leaked} leaked into suppliers source"


def test_event_types_present(dataset):
    types = {e["event_type"] for e in dataset["material_flow_events"]}
    assert {"received", "putaway", "picked", "shipped"} <= types
