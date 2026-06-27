"""Data-quality gate behavior: pass on good data, raise on corrupted data.

Includes the Phase 4 done-when scenario: a corrupted source trips a gate (raises).
Runs against the isolated raw_landing_test schema from conftest.
"""

from __future__ import annotations

import pytest

from ingestion.loaders import land_rest_records
from ingestion.sources import fetch_supplier_catalog
from quality.checks import (
    DataQualityError,
    check_freshness,
    check_null_rate,
    check_row_count,
)


@pytest.fixture()
def conn(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SET search_path TO raw_landing_test")
    return pg_conn


def _land_suppliers(conn, n=20):
    suppliers, _ = fetch_supplier_catalog(seed=5, n_suppliers=n, n_skus=1)
    land_rest_records(conn, "raw_suppliers", suppliers)
    conn.commit()


# ── row count ────────────────────────────────────────────────────────────────
def test_row_count_passes(conn):
    _land_suppliers(conn, n=20)
    msg = check_row_count(conn, "raw_suppliers", min_rows=10)
    assert "OK" in msg


def test_row_count_fails_on_empty_table(conn):
    with pytest.raises(DataQualityError, match="row_count"):
        check_row_count(conn, "raw_suppliers", min_rows=10)


# ── freshness ────────────────────────────────────────────────────────────────
def test_freshness_passes_after_landing(conn):
    _land_suppliers(conn)
    msg = check_freshness(conn, "raw_suppliers", max_age_hours=48)
    assert "OK" in msg


def test_freshness_fails_when_stale(conn):
    _land_suppliers(conn)
    # Backdate the landing timestamp beyond the window.
    with conn.cursor() as cur:
        cur.execute("UPDATE raw_suppliers SET _landed_at = now() - interval '100 hours'")
    conn.commit()
    with pytest.raises(DataQualityError, match="freshness"):
        check_freshness(conn, "raw_suppliers", max_age_hours=48)


# ── null rate ────────────────────────────────────────────────────────────────
def test_null_rate_passes_on_clean_data(conn):
    _land_suppliers(conn)
    msg = check_null_rate(conn, "raw_suppliers", "country", max_null_rate=0.0)
    assert "OK" in msg


def test_corrupted_source_trips_null_rate_gate(conn):
    """Phase 4 done-when: a corrupted source fails the DAG at the gate."""
    _land_suppliers(conn)
    # Corrupt: blank out a business-critical column on some rows.
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE raw_suppliers SET country = NULL "
            "WHERE supplier_id IN (SELECT supplier_id FROM raw_suppliers LIMIT 3)"
        )
    conn.commit()
    with pytest.raises(DataQualityError, match="null_rate"):
        check_null_rate(conn, "raw_suppliers", "country", max_null_rate=0.0)
