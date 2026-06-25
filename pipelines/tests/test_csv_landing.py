"""CSV drop landing — correctness and idempotency."""

from __future__ import annotations

import os

import pytest

from ingestion.loaders import land_csv_table
from ingestion.schema import PRIMARY_KEYS


@pytest.fixture()
def conn(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SET search_path TO raw_landing_test")
    return pg_conn


def test_land_suppliers_csv(conn, data_output_dir):
    path = os.path.join(data_output_dir, "suppliers.csv")
    if not os.path.exists(path):
        pytest.skip("data/output/suppliers.csv not found — run data/generate.py first")
    n = land_csv_table(conn, "raw_suppliers", path)
    conn.commit()
    assert n == 40

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_suppliers")
        assert cur.fetchone()[0] == 40


def test_csv_landing_is_idempotent(conn, data_output_dir):
    path = os.path.join(data_output_dir, "purchase_orders.csv")
    if not os.path.exists(path):
        pytest.skip("data/output/purchase_orders.csv not found")

    n1 = land_csv_table(conn, "raw_purchase_orders", path)
    conn.commit()
    n2 = land_csv_table(conn, "raw_purchase_orders", path)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_purchase_orders")
        count = cur.fetchone()[0]

    assert count == n1, "row count changed on second run"
    assert count == n2, "upsert returned wrong count on re-run"


def test_landed_at_updates_on_rerun(conn, data_output_dir):
    path = os.path.join(data_output_dir, "shipments.csv")
    if not os.path.exists(path):
        pytest.skip("data/output/shipments.csv not found")

    land_csv_table(conn, "raw_shipments", path)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT max(_landed_at) FROM raw_shipments")
        ts1 = cur.fetchone()[0]

    # Tiny sleep to ensure clock advances.
    import time; time.sleep(0.05)
    land_csv_table(conn, "raw_shipments", path)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT max(_landed_at) FROM raw_shipments")
        ts2 = cur.fetchone()[0]

    assert ts2 > ts1, "_landed_at should advance on re-land"


def test_all_source_domains_land(conn, data_output_dir):
    csv_tables = [
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
    for table, filename in csv_tables:
        path = os.path.join(data_output_dir, filename)
        if not os.path.exists(path):
            pytest.skip(f"{filename} not found")
        land_csv_table(conn, table, path)
    conn.commit()

    with conn.cursor() as cur:
        for table, _ in csv_tables:
            cur.execute(f"SELECT count(*) FROM {table}")
            assert cur.fetchone()[0] > 0, f"{table} is empty after landing"
