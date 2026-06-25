"""Webhook event landing — single-event upsert, idempotency, stream ingestion."""

from __future__ import annotations

import pytest

from ingestion.loaders import land_webhook_event
from ingestion.sources import stream_webhook_events


@pytest.fixture()
def conn(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SET search_path TO raw_landing_test")
    return pg_conn


def test_single_webhook_event_lands(conn):
    event = {
        "event_id": "WH-TEST-0001",
        "event_type": "received",
        "sku_id": "SKU-00001",
        "qty": "100",
        "event_ts": "2025-03-15",
        "reference_type": "webhook",
        "reference_id": "WH-SRC-00001",
    }
    n = land_webhook_event(conn, "raw_material_flow_events", event)
    conn.commit()

    assert n == 1
    with conn.cursor() as cur:
        cur.execute("SELECT qty FROM raw_material_flow_events WHERE event_id = 'WH-TEST-0001'")
        assert cur.fetchone()[0] == "100"


def test_webhook_landing_is_idempotent(conn):
    event = {
        "event_id": "WH-TEST-IDEM",
        "event_type": "shipped",
        "sku_id": "SKU-00042",
        "qty": "50",
        "event_ts": "2025-04-01",
        "reference_type": "webhook",
        "reference_id": "WH-SRC-00042",
    }
    land_webhook_event(conn, "raw_material_flow_events", event)
    conn.commit()
    land_webhook_event(conn, "raw_material_flow_events", event)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_material_flow_events WHERE event_id = 'WH-TEST-IDEM'")
        assert cur.fetchone()[0] == 1


def test_webhook_stream_ingestion(conn):
    n_total = 0
    for event in stream_webhook_events(seed=77, n_events=50):
        n_total += land_webhook_event(conn, "raw_material_flow_events", event)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_material_flow_events")
        db_count = cur.fetchone()[0]
    assert db_count == 50
    assert n_total == 50


def test_webhook_stream_is_idempotent(conn):
    events = list(stream_webhook_events(seed=88, n_events=30))
    for e in events:
        land_webhook_event(conn, "raw_material_flow_events", e)
    conn.commit()

    for e in events:
        land_webhook_event(conn, "raw_material_flow_events", e)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM raw_material_flow_events")
        assert cur.fetchone()[0] == 30, "idempotent re-run should not add rows"
