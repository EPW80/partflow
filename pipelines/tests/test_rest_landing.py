"""REST catalog landing — correctness and idempotency."""

from __future__ import annotations

import pytest

from ingestion.loaders import land_rest_records
from ingestion.sources import fetch_supplier_catalog


@pytest.fixture()
def conn(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SET search_path TO raw_landing_test")
    return pg_conn


def test_rest_lands_supplier_catalog(conn):
    suppliers, skus = fetch_supplier_catalog(seed=42, n_suppliers=10, n_skus=50)
    n_sup = land_rest_records(conn, "raw_suppliers", suppliers)
    n_sku = land_rest_records(conn, "raw_skus", skus)
    conn.commit()

    assert n_sup == 10
    assert n_sku == 50

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_suppliers")
        assert cur.fetchone()[0] == 10
        cur.execute("SELECT count(*) FROM raw_skus")
        assert cur.fetchone()[0] == 50


def test_rest_landing_is_idempotent(conn):
    suppliers, _ = fetch_supplier_catalog(seed=99, n_suppliers=5, n_skus=20)
    land_rest_records(conn, "raw_suppliers", suppliers)
    conn.commit()
    land_rest_records(conn, "raw_suppliers", suppliers)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_suppliers")
        assert cur.fetchone()[0] == 5


def test_rest_updates_existing_rows(conn):
    # Land v1 with one name, v2 with the same ID but different name — last write wins.
    v1 = [{"supplier_id": "SUP-0001", "supplier_name": "Acme", "country": "US",
            "tier": "preferred", "category": "fasteners",
            "promised_lead_time_days": "14", "onboarded_date": "2022-01-01"}]
    v2 = [{"supplier_id": "SUP-0001", "supplier_name": "Acme Corp", "country": "US",
            "tier": "strategic", "category": "fasteners",
            "promised_lead_time_days": "14", "onboarded_date": "2022-01-01"}]

    land_rest_records(conn, "raw_suppliers", v1)
    conn.commit()
    land_rest_records(conn, "raw_suppliers", v2)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT supplier_name, tier FROM raw_suppliers WHERE supplier_id = 'SUP-0001'")
        row = cur.fetchone()
    assert row[0] == "Acme Corp"
    assert row[1] == "strategic"
