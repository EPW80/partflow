"""Idempotent landing functions for the three source patterns.

All three functions write into raw_* tables using UPSERT (INSERT ... ON CONFLICT DO UPDATE)
keyed on the source's natural primary key. This guarantees:
  - Re-running for the same data yields identical row counts (not blind append).
  - A partial re-run (e.g. after a crash mid-batch) is safe.
  - The _landed_at column advances on each upsert so DQ freshness gates work.

Source shapes:
  land_csv_table   — bulk batch files from a CSV drop (the main ingest path).
  land_rest_records — JSON records fetched from a supplier REST endpoint.
  land_webhook_event — single event dict from a real-time webhook call.

None of these functions open a connection; callers own the connection lifecycle
so they can batch multiple tables in one transaction or use Airflow's hook.
"""

from __future__ import annotations

import csv
from typing import Iterable

import psycopg2.extensions
import psycopg2.extras

from .schema import PRIMARY_KEYS

# Column name reserved for the technical landing timestamp — excluded from source comparison.
_LANDED_AT = "_landed_at"


def _build_upsert(table: str, columns: list[str]) -> str:
    """Build a parameterised UPSERT for the given table and source columns."""
    pk_cols = PRIMARY_KEYS[table]
    non_pk = [c for c in columns if c not in pk_cols]

    col_list = ", ".join(columns)
    placeholder = ", ".join(f"%({c})s" for c in columns)
    conflict_target = ", ".join(pk_cols)

    if non_pk:
        update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in non_pk)
        update_set += f", {_LANDED_AT} = now()"
        conflict_action = f"DO UPDATE SET {update_set}"
    else:
        # All columns are part of the PK — nothing to update, but refresh the timestamp.
        conflict_action = f"DO UPDATE SET {_LANDED_AT} = now()"

    return (
        f"INSERT INTO {table} ({col_list}, {_LANDED_AT}) "
        f"VALUES ({placeholder}, now()) "
        f"ON CONFLICT ({conflict_target}) {conflict_action}"
    )


def land_csv_table(
    conn: psycopg2.extensions.connection,
    table: str,
    csv_path: str,
    batch_size: int = 2000,
) -> int:
    """Land a # SYNTHETIC DATA CSV into a raw_* table. Returns rows upserted."""
    rows_upserted = 0
    with open(csv_path, newline="") as f:
        first = f.readline()
        if not first.startswith("#"):
            # Put non-comment first line back if the file lacks the header.
            # (Shouldn't happen with valid generator output, but guard defensively.)
            f.seek(0)
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        if not columns:
            return 0
        columns = list(columns)
        sql = _build_upsert(table, columns)
        batch: list[dict] = []
        with conn.cursor() as cur:
            for row in reader:
                batch.append(row)
                if len(batch) >= batch_size:
                    psycopg2.extras.execute_batch(cur, sql, batch)
                    rows_upserted += len(batch)
                    batch = []
            if batch:
                psycopg2.extras.execute_batch(cur, sql, batch)
                rows_upserted += len(batch)
    return rows_upserted


def land_rest_records(
    conn: psycopg2.extensions.connection,
    table: str,
    records: Iterable[dict],
) -> int:
    """Land a list of dicts (JSON API response) into a raw_* table. Returns rows upserted."""
    records = list(records)
    if not records:
        return 0
    columns = [k for k in records[0] if k != _LANDED_AT]
    sql = _build_upsert(table, columns)
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, records)
    return len(records)


def land_webhook_event(
    conn: psycopg2.extensions.connection,
    table: str,
    event: dict,
) -> int:
    """Land a single webhook payload dict. Returns 1 on upsert, 0 if event is empty."""
    if not event:
        return 0
    columns = [k for k in event if k != _LANDED_AT]
    sql = _build_upsert(table, columns)
    with conn.cursor() as cur:
        cur.execute(sql, event)
    return 1
