"""The gate behavior: every foreign key resolves and every primary key is unique."""

from __future__ import annotations

import pytest

# table -> primary key column
PRIMARY_KEYS = {
    "suppliers": "supplier_id",
    "skus": "sku_id",
    "purchase_orders": "po_id",
    "purchase_order_lines": "po_line_id",
    "shipments": "shipment_id",
    "shipment_lines": "shipment_line_id",
    "quality_inspections": "inspection_id",
    "material_flow_events": "event_id",
}

# (child table, fk column) -> (parent table, parent key)
FOREIGN_KEYS = [
    ("skus", "primary_supplier_id", "suppliers", "supplier_id"),
    ("purchase_orders", "supplier_id", "suppliers", "supplier_id"),
    ("purchase_order_lines", "po_id", "purchase_orders", "po_id"),
    ("purchase_order_lines", "sku_id", "skus", "sku_id"),
    ("shipments", "po_id", "purchase_orders", "po_id"),
    ("shipment_lines", "shipment_id", "shipments", "shipment_id"),
    ("shipment_lines", "po_line_id", "purchase_order_lines", "po_line_id"),
    ("shipment_lines", "sku_id", "skus", "sku_id"),
    ("quality_inspections", "shipment_line_id", "shipment_lines", "shipment_line_id"),
    ("quality_inspections", "sku_id", "skus", "sku_id"),
    ("inventory_snapshots", "sku_id", "skus", "sku_id"),
    ("material_flow_events", "sku_id", "skus", "sku_id"),
]


@pytest.mark.parametrize("table,key", PRIMARY_KEYS.items())
def test_primary_key_unique(dataset, table, key):
    ids = [row[key] for row in dataset[table]]
    assert len(ids) == len(set(ids)), f"{table}.{key} has duplicates"
    assert all(ids), f"{table}.{key} has empty values"


@pytest.mark.parametrize("child,fk,parent,pk", FOREIGN_KEYS)
def test_foreign_key_resolves(dataset, child, fk, parent, pk):
    parent_ids = {row[pk] for row in dataset[parent]}
    orphans = [row[fk] for row in dataset[child] if row[fk] not in parent_ids]
    assert not orphans, f"{child}.{fk} has {len(orphans)} orphan(s) not in {parent}.{pk}"


def test_inventory_snapshot_grain_unique(dataset):
    grain = [(r["snapshot_date"], r["sku_id"]) for r in dataset["inventory_snapshots"]]
    assert len(grain) == len(set(grain)), "inventory_snapshots not unique on (date, sku)"


def test_all_tables_non_empty(dataset):
    for name, rows in dataset.items():
        assert rows, f"{name} is empty"
