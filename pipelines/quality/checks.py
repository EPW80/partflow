"""Reusable data-quality check primitives.

Every check raises DataQualityError on violation so the calling Airflow task fails
the DAG (ADR-0003: gates fail loudly, never log-and-continue). Each function takes an
open connection and returns a short result string on success (useful for task logs).

Checks accept an optional `schema` so the same code runs against the production
`public` schema and an isolated test schema.
"""

from __future__ import annotations

import psycopg2.extensions


class DataQualityError(Exception):
    """Raised when a data-quality gate fails. Fails the Airflow task and the DAG."""


def _qualified(schema: str | None, table: str) -> str:
    return f"{schema}.{table}" if schema else table


def check_row_count(
    conn: psycopg2.extensions.connection,
    table: str,
    min_rows: int,
    schema: str | None = None,
) -> str:
    rel = _qualified(schema, table)
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {rel}")
        count = cur.fetchone()[0]
    if count < min_rows:
        raise DataQualityError(
            f"row_count: {rel} has {count} rows, expected >= {min_rows}"
        )
    return f"row_count OK: {rel} = {count} (>= {min_rows})"


def check_freshness(
    conn: psycopg2.extensions.connection,
    table: str,
    max_age_hours: float,
    landed_at_col: str = "_landed_at",
    schema: str | None = None,
) -> str:
    rel = _qualified(schema, table)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT extract(epoch FROM now() - max({landed_at_col})) / 3600.0 FROM {rel}"
        )
        age_hours = cur.fetchone()[0]
    if age_hours is None:
        raise DataQualityError(f"freshness: {rel} has no rows / no {landed_at_col}")
    if age_hours > max_age_hours:
        raise DataQualityError(
            f"freshness: {rel} newest row is {age_hours:.1f}h old, max {max_age_hours}h"
        )
    return f"freshness OK: {rel} newest row {age_hours:.2f}h old (<= {max_age_hours}h)"


def check_null_rate(
    conn: psycopg2.extensions.connection,
    table: str,
    column: str,
    max_null_rate: float,
    schema: str | None = None,
) -> str:
    rel = _qualified(schema, table)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT count(*), count(*) FILTER (WHERE {column} IS NULL) FROM {rel}"
        )
        total, nulls = cur.fetchone()
    if total == 0:
        raise DataQualityError(f"null_rate: {rel} is empty, cannot evaluate {column}")
    rate = nulls / total
    if rate > max_null_rate:
        raise DataQualityError(
            f"null_rate: {rel}.{column} is {rate:.3%} null, max {max_null_rate:.3%}"
        )
    return f"null_rate OK: {rel}.{column} = {rate:.3%} null (<= {max_null_rate:.3%})"
