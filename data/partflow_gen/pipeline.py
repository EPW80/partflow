"""Orchestrate generation in dependency order and return one dict of source tables."""

from __future__ import annotations

import numpy as np
from faker import Faker

from .config import GenConfig
from .entities import generate_skus, generate_suppliers
from .operations import generate_inventory_snapshots, generate_material_flow_events
from .procurement import (
    finalize_po_status,
    generate_purchase_orders,
    generate_quality_inspections,
    generate_shipments,
)

# Emission order = dependency order (each table only references earlier ones).
TABLE_ORDER = [
    "suppliers",
    "skus",
    "purchase_orders",
    "purchase_order_lines",
    "shipments",
    "shipment_lines",
    "quality_inspections",
    "inventory_snapshots",
    "material_flow_events",
]


def generate(cfg: GenConfig) -> dict[str, list[dict]]:
    rng = np.random.default_rng(cfg.seed)
    faker = Faker()
    faker.seed_instance(cfg.seed)

    suppliers = generate_suppliers(cfg, rng, faker)
    skus = generate_skus(cfg, rng, faker, suppliers)
    purchase_orders, po_lines = generate_purchase_orders(cfg, rng, suppliers, skus)
    shipments, shipment_lines = generate_shipments(cfg, rng, suppliers, purchase_orders, po_lines)
    finalize_po_status(purchase_orders, po_lines, shipment_lines)
    inspections = generate_quality_inspections(cfg, rng, suppliers, skus, shipment_lines)
    inventory = generate_inventory_snapshots(cfg, rng, skus, shipment_lines)
    events = generate_material_flow_events(cfg, rng, shipments, shipment_lines, inventory)

    return {
        "suppliers": [s.source_row() for s in suppliers],
        "skus": [s.source_row() for s in skus],
        "purchase_orders": purchase_orders,
        "purchase_order_lines": po_lines,
        "shipments": shipments,
        "shipment_lines": shipment_lines,
        "quality_inspections": inspections,
        "inventory_snapshots": inventory,
        "material_flow_events": events,
    }
