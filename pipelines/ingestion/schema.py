"""CREATE TABLE DDL and metadata for every raw_* landing table.

Rules:
- All source columns are TEXT — land as-received, no type coercion here.
  The staging layer in dbt owns casting.
- _landed_at records when the row was last written; used by DQ freshness gates.
- Every table declares its primary key so the loader can build ON CONFLICT upserts.
- inventory_snapshots has a composite PK (snapshot_date, sku_id).

Call apply_schema(conn) once on stack startup or in a DAG init task.
"""

from __future__ import annotations

import psycopg2.extensions

# Maps table_name -> list of PK column names.
# Used by loaders.py to build idempotent UPSERT statements.
PRIMARY_KEYS: dict[str, list[str]] = {
    "raw_suppliers":            ["supplier_id"],
    "raw_skus":                 ["sku_id"],
    "raw_purchase_orders":      ["po_id"],
    "raw_purchase_order_lines": ["po_line_id"],
    "raw_shipments":            ["shipment_id"],
    "raw_shipment_lines":       ["shipment_line_id"],
    "raw_quality_inspections":  ["inspection_id"],
    "raw_inventory_snapshots":  ["snapshot_date", "sku_id"],
    "raw_material_flow_events": ["event_id"],
}

# DDL in dependency order (matches Phase 1 generator output).
_DDL = [
    """
    CREATE TABLE IF NOT EXISTS raw_suppliers (
        supplier_id              TEXT NOT NULL,
        supplier_name            TEXT,
        country                  TEXT,
        tier                     TEXT,
        category                 TEXT,
        promised_lead_time_days  TEXT,
        onboarded_date           TEXT,
        _landed_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (supplier_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_skus (
        sku_id               TEXT NOT NULL,
        description          TEXT,
        category             TEXT,
        primary_supplier_id  TEXT,
        unit_cost            TEXT,
        unit_of_measure      TEXT,
        abc_class            TEXT,
        _landed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (sku_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_purchase_orders (
        po_id          TEXT NOT NULL,
        supplier_id    TEXT,
        order_date     TEXT,
        promised_date  TEXT,
        status         TEXT,
        _landed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (po_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_purchase_order_lines (
        po_line_id   TEXT NOT NULL,
        po_id        TEXT,
        sku_id       TEXT,
        ordered_qty  TEXT,
        unit_price   TEXT,
        _landed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (po_line_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_shipments (
        shipment_id    TEXT NOT NULL,
        po_id          TEXT,
        carrier        TEXT,
        ship_date      TEXT,
        received_date  TEXT,
        _landed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (shipment_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_shipment_lines (
        shipment_line_id  TEXT NOT NULL,
        shipment_id       TEXT,
        po_line_id        TEXT,
        sku_id            TEXT,
        shipped_qty       TEXT,
        received_qty      TEXT,
        received_date     TEXT,
        _landed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (shipment_line_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_quality_inspections (
        inspection_id     TEXT NOT NULL,
        shipment_line_id  TEXT,
        sku_id            TEXT,
        inspection_date   TEXT,
        inspected_qty     TEXT,
        defect_qty        TEXT,
        disposition       TEXT,
        _landed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (inspection_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_inventory_snapshots (
        snapshot_date     TEXT NOT NULL,
        sku_id            TEXT NOT NULL,
        on_hand_qty       TEXT,
        daily_demand_qty  TEXT,
        in_stockout       TEXT,
        _landed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (snapshot_date, sku_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_material_flow_events (
        event_id        TEXT NOT NULL,
        event_type      TEXT,
        sku_id          TEXT,
        qty             TEXT,
        event_ts        TEXT,
        reference_type  TEXT,
        reference_id    TEXT,
        _landed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (event_id)
    )
    """,
]


def apply_schema(conn: psycopg2.extensions.connection) -> None:
    """Create raw_* tables if they don't exist. Safe to call on every run."""
    with conn.cursor() as cur:
        for ddl in _DDL:
            cur.execute(ddl)
    conn.commit()
