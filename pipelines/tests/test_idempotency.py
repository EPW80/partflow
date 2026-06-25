"""Full-load idempotency: the Phase 2 gate test.

A complete run across all nine source domains followed by a second identical
run must yield the same row counts — not one extra row.
"""

from __future__ import annotations

import os

import pytest

from ingestion.loaders import land_csv_table, land_rest_records, land_webhook_event
from ingestion.sources import fetch_supplier_catalog, stream_webhook_events

ALL_CSV_TABLES = [
    ("raw_suppliers",            "suppliers.csv"),
    ("raw_skus",                 "skus.csv"),
    ("raw_purchase_orders",      "purchase_orders.csv"),
    ("raw_purchase_order_lines", "purchase_order_lines.csv"),
    ("raw_shipments",            "shipments.csv"),
    ("raw_shipment_lines",       "shipment_lines.csv"),
    ("raw_quality_inspections",  "quality_inspections.csv"),
    ("raw_inventory_snapshots",  "inventory_snapshots.csv"),
    ("raw_material_flow_events", "material_flow_events.csv"),
]


@pytest.fixture()
def conn(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SET search_path TO raw_landing_test")
    return pg_conn


def _full_load(conn, data_dir: str) -> None:
    for table, filename in ALL_CSV_TABLES:
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            pytest.skip(f"{filename} not found — run data/generate.py first")
        land_csv_table(conn, table, path)
    conn.commit()

    suppliers, skus = fetch_supplier_catalog(seed=42)
    land_rest_records(conn, "raw_suppliers", suppliers)
    land_rest_records(conn, "raw_skus", skus)
    conn.commit()

    for event in stream_webhook_events(seed=42, n_events=200):
        land_webhook_event(conn, "raw_material_flow_events", event)
    conn.commit()


def _row_counts(conn) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table, _ in ALL_CSV_TABLES:
            cur.execute(f"SELECT count(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    return counts


def test_full_load_idempotent(conn, data_output_dir):
    _full_load(conn, data_output_dir)
    counts_after_run1 = _row_counts(conn)

    _full_load(conn, data_output_dir)
    counts_after_run2 = _row_counts(conn)

    assert counts_after_run1 == counts_after_run2, (
        f"Row counts changed on second run:\n"
        f"  run 1: {counts_after_run1}\n"
        f"  run 2: {counts_after_run2}"
    )


def test_all_domains_populated(conn, data_output_dir):
    _full_load(conn, data_output_dir)
    counts = _row_counts(conn)
    for table, count in counts.items():
        assert count > 0, f"{table} is empty after a full load"
