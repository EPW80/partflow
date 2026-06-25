#!/usr/bin/env python3
"""Standalone landing runner — exercises all three source patterns.

    python land.py --data ../data/output

Applies the raw_* schema, lands all CSVs from the data output directory,
then demonstrates the REST and webhook patterns on top.
Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import argparse
import os
import sys

from ingestion.db import connection
from ingestion.loaders import land_csv_table, land_rest_records, land_webhook_event
from ingestion.schema import apply_schema
from ingestion.sources import fetch_supplier_catalog, stream_webhook_events

# Table -> source CSV name, in dependency order.
CSV_TABLES = [
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


def run(data_dir: str) -> None:
    with connection() as conn:
        print("Applying raw_* schema ...")
        apply_schema(conn)

        print(f"\n── CSV drop from {data_dir} ──")
        for table, filename in CSV_TABLES:
            path = os.path.join(data_dir, filename)
            if not os.path.exists(path):
                print(f"  SKIP {table}: {path} not found (run data/generate.py first)")
                continue
            n = land_csv_table(conn, table, path)
            conn.commit()
            print(f"  {table:<30} {n:>8,} rows upserted")

        print("\n── REST catalog (fake supplier API) ──")
        suppliers, skus = fetch_supplier_catalog(seed=42)
        n_sup = land_rest_records(conn, "raw_suppliers", suppliers)
        n_sku = land_rest_records(conn, "raw_skus", skus)
        conn.commit()
        print(f"  raw_suppliers (REST)           {n_sup:>8,} rows upserted")
        print(f"  raw_skus      (REST)           {n_sku:>8,} rows upserted")

        print("\n── Webhook stream (fake real-time events) ──")
        n_events = 0
        for event in stream_webhook_events(seed=42, n_events=200):
            n_events += land_webhook_event(conn, "raw_material_flow_events", event)
        conn.commit()
        print(f"  raw_material_flow_events (WH)  {n_events:>8,} events upserted")

        print("\n── Counts in Postgres ──")
        with conn.cursor() as cur:
            for table, _ in CSV_TABLES:
                cur.execute(f"SELECT count(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  {table:<30} {count:>8,}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Land PartFlow synthetic data into raw_* tables.")
    parser.add_argument("--data", default="../data/output", help="path to generator output dir")
    args = parser.parse_args()
    try:
        run(args.data)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
