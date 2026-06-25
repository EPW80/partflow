"""Shared fixtures for ingestion integration tests.

Tests use the live Postgres stack (localhost:5433). The suite creates a
dedicated `raw_landing_test` schema, runs all tests within it, then drops
it on teardown — so tests never touch the production `public` schema and
always start from a clean slate.

Skip gracefully if Postgres isn't reachable (e.g. stack is down).
"""

from __future__ import annotations

import os

import psycopg2
import pytest

_TEST_SCHEMA = "raw_landing_test"
_DSN = os.environ.get(
    "PARTFLOW_DATABASE_URL",
    "postgresql://partflow:partflow@localhost:5433/partflow",
)


def _pg_available() -> bool:
    try:
        conn = psycopg2.connect(_DSN, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


# Skip the whole suite if Postgres isn't up.
if not _pg_available():
    pytest.skip("Postgres not reachable — start the stack with docker compose up", allow_module_level=True)


@pytest.fixture(scope="session")
def pg_conn():
    """Session-scoped connection inside the test schema.

    Creates the test schema, applies raw_* DDL there, yields the connection,
    then drops the entire schema on teardown.
    """
    from ingestion.schema import _DDL

    conn = psycopg2.connect(_DSN)
    conn.autocommit = False

    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {_TEST_SCHEMA}")
        cur.execute(f"SET search_path TO {_TEST_SCHEMA}")
        for ddl in _DDL:
            cur.execute(ddl)
    conn.commit()

    # Patch the env so loaders also use our test schema via SET search_path.
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {_TEST_SCHEMA}")
    conn.commit()

    yield conn

    # Teardown: wipe the test schema entirely.
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {_TEST_SCHEMA} CASCADE")
    conn.close()


@pytest.fixture(autouse=True)
def truncate_between_tests(pg_conn):
    """Truncate all test tables before each test for isolation."""
    yield
    with pg_conn.cursor() as cur:
        cur.execute(f"SET search_path TO {_TEST_SCHEMA}")
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = %s",
            (_TEST_SCHEMA,),
        )
        tables = [r[0] for r in cur.fetchall()]
        if tables:
            cur.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
    pg_conn.commit()


@pytest.fixture(scope="session")
def data_output_dir() -> str:
    """Path to generated CSVs — requires data/generate.py to have been run."""
    import os
    here = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(here, "../../data/output"))
