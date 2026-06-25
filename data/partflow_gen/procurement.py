"""Generate the procurement flow: purchase orders -> shipments -> quality inspections.

Supplier latent params drive the realism:
- on-time delivery is a Bernoulli(base_otd) per shipment; lead time is scaled around the
  promised target depending on whether the draw was on-time or late.
- fill shortfalls are a Bernoulli(1 - fill_reliability) per shipment line.
- defects are Binomial(received_qty, defect_rate_ppm/1e6) per inspection.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from faker import Faker
from numpy.random import Generator

from .config import GenConfig
from .model import Sku, Supplier, season_multiplier

CARRIERS = ["DHL", "FedEx", "UPS", "Maersk", "DB Schenker", "regional-LTL"]
DISPOSITIONS_OK = "accept"


def generate_purchase_orders(
    cfg: GenConfig, rng: Generator, suppliers: list[Supplier], skus: list[Sku]
) -> tuple[list[dict], list[dict]]:
    skus_by_supplier: dict[str, list[Sku]] = defaultdict(list)
    for sku in skus:
        skus_by_supplier[sku.primary_supplier_id].append(sku)
    suppliers_with_skus = [s for s in suppliers if skus_by_supplier[s.supplier_id]]

    purchase_orders: list[dict] = []
    po_lines: list[dict] = []
    po_seq = 0
    line_seq = 0

    week_start = cfg.start_date
    while week_start < cfg.end_date:
        n_pos = int(rng.poisson(cfg.pos_per_week * season_multiplier(week_start, cfg.seasonal_amplitude)))
        for _ in range(n_pos):
            supplier = suppliers_with_skus[int(rng.integers(0, len(suppliers_with_skus)))]
            order_date = week_start + timedelta(days=int(rng.integers(0, 7)))
            if order_date >= cfg.end_date:
                continue
            po_seq += 1
            po_id = f"PO-{po_seq:06d}"
            promised_date = order_date + timedelta(days=supplier.promised_lead_time_days)

            n_lines = 1 + int(rng.poisson(cfg.lines_per_po_mean - 1))
            catalog = skus_by_supplier[supplier.supplier_id]
            chosen = rng.choice(len(catalog), size=min(n_lines, len(catalog)), replace=False)
            for idx in chosen:
                sku = catalog[int(idx)]
                line_seq += 1
                cover_days = float(rng.uniform(7, 21))
                season = season_multiplier(order_date, cfg.seasonal_amplitude)
                ordered_qty = max(1, int(round(sku.base_daily_demand * cover_days * season)))
                po_lines.append(
                    {
                        "po_line_id": f"POL-{line_seq:07d}",
                        "po_id": po_id,
                        "sku_id": sku.sku_id,
                        "ordered_qty": ordered_qty,
                        "unit_price": round(sku.unit_cost * float(rng.uniform(0.95, 1.15)), 2),
                    }
                )
            purchase_orders.append(
                {
                    "po_id": po_id,
                    "supplier_id": supplier.supplier_id,
                    "order_date": order_date.isoformat(),
                    "promised_date": promised_date.isoformat(),
                    "status": "open",  # finalized after shipments
                }
            )
        week_start += timedelta(days=7)

    return purchase_orders, po_lines


def _draw_received_date(cfg: GenConfig, rng: Generator, supplier: Supplier, order_date: date) -> date:
    promised = max(1, supplier.promised_lead_time_days)
    if rng.random() < supplier.base_otd:
        lead = promised * float(rng.uniform(0.6, 1.0))
    else:
        lead = promised * float(rng.uniform(1.05, 1.6))
    lead = max(1, int(round(lead)))
    return order_date + timedelta(days=lead)


def generate_shipments(
    cfg: GenConfig,
    rng: Generator,
    suppliers: list[Supplier],
    purchase_orders: list[dict],
    po_lines: list[dict],
) -> tuple[list[dict], list[dict]]:
    suppliers_by_id = {s.supplier_id: s for s in suppliers}
    lines_by_po: dict[str, list[dict]] = defaultdict(list)
    for line in po_lines:
        lines_by_po[line["po_id"]].append(line)

    shipments: list[dict] = []
    shipment_lines: list[dict] = []
    ship_seq = 0
    sline_seq = 0

    for po in purchase_orders:
        supplier = suppliers_by_id[po["supplier_id"]]
        order_date = date.fromisoformat(po["order_date"])
        po_line_rows = lines_by_po[po["po_id"]]
        if not po_line_rows:
            continue

        # ~20% of multi-line POs split across two partial shipments.
        if len(po_line_rows) > 1 and rng.random() < 0.2:
            split = int(rng.integers(1, len(po_line_rows)))
            groups = [po_line_rows[:split], po_line_rows[split:]]
        else:
            groups = [po_line_rows]

        for group in groups:
            received_date = _draw_received_date(cfg, rng, supplier, order_date)
            transit = int(rng.integers(1, 5))
            ship_date = received_date - timedelta(days=transit)
            if ship_date < order_date:
                ship_date = order_date
            ship_seq += 1
            shipment_id = f"SHP-{ship_seq:06d}"
            shipments.append(
                {
                    "shipment_id": shipment_id,
                    "po_id": po["po_id"],
                    "carrier": str(rng.choice(CARRIERS)),
                    "ship_date": ship_date.isoformat(),
                    "received_date": received_date.isoformat(),
                }
            )
            for line in group:
                if rng.random() < supplier.fill_reliability:
                    shipped = line["ordered_qty"]
                else:
                    shipped = max(1, int(round(line["ordered_qty"] * float(rng.uniform(0.5, 0.95)))))
                sline_seq += 1
                shipment_lines.append(
                    {
                        "shipment_line_id": f"SHL-{sline_seq:07d}",
                        "shipment_id": shipment_id,
                        "po_line_id": line["po_line_id"],
                        "sku_id": line["sku_id"],
                        "shipped_qty": shipped,
                        "received_qty": shipped,
                        "received_date": received_date.isoformat(),
                    }
                )

    return shipments, shipment_lines


def finalize_po_status(
    purchase_orders: list[dict], po_lines: list[dict], shipment_lines: list[dict]
) -> None:
    """Mark a PO 'closed' once every line is fully received; otherwise 'open'. In place."""
    ordered_by_line = {line["po_line_id"]: line["ordered_qty"] for line in po_lines}
    line_to_po = {line["po_line_id"]: line["po_id"] for line in po_lines}
    received_by_line: dict[str, int] = defaultdict(int)
    for sl in shipment_lines:
        received_by_line[sl["po_line_id"]] += sl["received_qty"]

    lines_by_po: dict[str, list[str]] = defaultdict(list)
    for line in po_lines:
        lines_by_po[line["po_id"]].append(line["po_line_id"])

    for po in purchase_orders:
        line_ids = lines_by_po[po["po_id"]]
        fully = line_ids and all(
            received_by_line[lid] >= ordered_by_line[lid] for lid in line_ids
        )
        po["status"] = "closed" if fully else "open"


def generate_quality_inspections(
    cfg: GenConfig, rng: Generator, suppliers: list[Supplier], skus: list[Sku],
    shipment_lines: list[dict],
) -> list[dict]:
    suppliers_by_id = {s.supplier_id: s for s in suppliers}
    # sku -> supplier, to look up the defect rate driving the inspection
    supplier_of_sku = {sku.sku_id: sku.primary_supplier_id for sku in skus}

    inspections: list[dict] = []
    insp_seq = 0
    for sl in shipment_lines:
        # Inspect ~85% of received lines (the rest pass on supplier certification).
        if rng.random() > 0.85:
            continue
        received_date = date.fromisoformat(sl["received_date"])
        if received_date >= cfg.end_date:
            continue
        supplier = suppliers_by_id[supplier_of_sku[sl["sku_id"]]]
        inspected_qty = sl["received_qty"]
        p_defect = min(0.5, supplier.defect_rate_ppm / 1_000_000.0 * float(rng.uniform(0.5, 1.5)))
        defect_qty = int(rng.binomial(inspected_qty, p_defect))
        insp_seq += 1
        defect_share = defect_qty / inspected_qty if inspected_qty else 0.0
        if defect_share == 0:
            disposition = DISPOSITIONS_OK
        elif defect_share < 0.05:
            disposition = "rework"
        else:
            disposition = "reject"
        inspections.append(
            {
                "inspection_id": f"INS-{insp_seq:07d}",
                "shipment_line_id": sl["shipment_line_id"],
                "sku_id": sl["sku_id"],
                "inspection_date": (received_date + timedelta(days=int(rng.integers(0, 3)))).isoformat(),
                "inspected_qty": inspected_qty,
                "defect_qty": defect_qty,
                "disposition": disposition,
            }
        )
    return inspections
