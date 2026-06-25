"""Database connection helpers.

All work happens inside functions — no connections are opened at import time
(Airflow re-parses every DAG file on a schedule; top-level connections cause
silent scheduler stalls).

Host-side DSN defaults to port 5433 because the stack maps Postgres there to
avoid clashing with a local install (see infra/docker-compose.yml). Inside
Airflow containers the PARTFLOW_DATABASE_URL env var overrides to postgres:5432.
"""

from __future__ import annotations

import contextlib
import os
from typing import Generator

import psycopg2
import psycopg2.extras


def get_dsn() -> str:
    return os.environ.get(
        "PARTFLOW_DATABASE_URL",
        "postgresql://partflow:partflow@localhost:5433/partflow",
    )


@contextlib.contextmanager
def connection() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = psycopg2.connect(get_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
