"""Declarative data-quality specs — adding a gate is data, not code (ADR-0003).

ROW_COUNT_MINS / FRESHNESS / NULL_RATE_CHECKS drive the three operational gates.
The runner functions execute every check for a gate and raise on the FIRST failure,
having logged each result. Tasks call run_<gate>(conn, schema).
"""

from __future__ import annotations

import psycopg2.extensions

from .checks import check_freshness, check_null_rate, check_row_count

# Minimum plausible row counts per raw table (well below normal volume — catches
# empty/truncated drops, not normal variation).
ROW_COUNT_MINS: dict[str, int] = {
    "raw_suppliers": 10,
    "raw_skus": 100,
    "raw_purchase_orders": 100,
    "raw_purchase_order_lines": 100,
    "raw_shipments": 100,
    "raw_shipment_lines": 100,
    "raw_quality_inspections": 100,
    "raw_inventory_snapshots": 1000,
    "raw_material_flow_events": 1000,
}

# Tables whose freshness matters, with the max age tolerated.
FRESHNESS_MAX_AGE_HOURS = 48.0
FRESHNESS_TABLES = list(ROW_COUNT_MINS.keys())

# Business-critical columns that must not be null (table, column, max_null_rate).
NULL_RATE_CHECKS: list[tuple[str, str, float]] = [
    ("raw_suppliers", "supplier_id", 0.0),
    ("raw_skus", "sku_id", 0.0),
    ("raw_skus", "primary_supplier_id", 0.0),
    ("raw_purchase_orders", "supplier_id", 0.0),
    ("raw_purchase_orders", "order_date", 0.0),
    ("raw_purchase_orders", "promised_date", 0.0),
    ("raw_purchase_order_lines", "po_id", 0.0),
    ("raw_purchase_order_lines", "sku_id", 0.0),
    ("raw_shipments", "po_id", 0.0),
    ("raw_shipments", "received_date", 0.0),
    ("raw_shipment_lines", "received_qty", 0.0),
    ("raw_inventory_snapshots", "on_hand_qty", 0.0),
]


def run_row_count_gate(conn: psycopg2.extensions.connection, schema: str | None = None) -> list[str]:
    results = []
    for table, min_rows in ROW_COUNT_MINS.items():
        results.append(check_row_count(conn, table, min_rows, schema=schema))
    return results


def run_freshness_gate(conn: psycopg2.extensions.connection, schema: str | None = None) -> list[str]:
    results = []
    for table in FRESHNESS_TABLES:
        results.append(check_freshness(conn, table, FRESHNESS_MAX_AGE_HOURS, schema=schema))
    return results


def run_null_rate_gate(conn: psycopg2.extensions.connection, schema: str | None = None) -> list[str]:
    results = []
    for table, column, max_rate in NULL_RATE_CHECKS:
        results.append(check_null_rate(conn, table, column, max_rate, schema=schema))
    return results
