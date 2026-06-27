"""partflow_ingest — end-to-end ingestion DAG.

Chain: land raw (per-domain TaskGroups) -> dbt build -> data-quality gates.
Each gate is a task that raises on violation, failing the DAG loudly (ADR-0003).

DAG-parse safety: no DB/network calls or heavy imports at top level — every import
that touches ingestion/quality/psycopg2 happens inside a task callable.
"""

from __future__ import annotations

import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

log = logging.getLogger(__name__)

DATA_DIR = "/opt/airflow/data/output"

# (raw table, source CSV) grouped by domain. Mirrors the Phase 2 landing map.
DOMAINS: dict[str, list[tuple[str, str]]] = {
    "reference": [
        ("raw_suppliers", "suppliers.csv"),
        ("raw_skus", "skus.csv"),
    ],
    "procurement": [
        ("raw_purchase_orders", "purchase_orders.csv"),
        ("raw_purchase_order_lines", "purchase_order_lines.csv"),
        ("raw_shipments", "shipments.csv"),
        ("raw_shipment_lines", "shipment_lines.csv"),
        ("raw_quality_inspections", "quality_inspections.csv"),
    ],
    "inventory": [
        ("raw_inventory_snapshots", "inventory_snapshots.csv"),
        ("raw_material_flow_events", "material_flow_events.csv"),
    ],
}


def _apply_schema() -> None:
    from ingestion.db import connection
    from ingestion.schema import apply_schema

    with connection() as conn:
        apply_schema(conn)
    log.info("raw_* schema applied")


def _land_table(table: str, filename: str) -> None:
    import os

    from ingestion.db import connection
    from ingestion.loaders import land_csv_table

    path = os.path.join(DATA_DIR, filename)
    with connection() as conn:
        n = land_csv_table(conn, table, path)
        conn.commit()
    log.info("landed %s rows into %s", n, table)


def _gate_row_counts() -> None:
    from ingestion.db import connection
    from quality.specs import run_row_count_gate

    with connection() as conn:
        for line in run_row_count_gate(conn):
            log.info(line)


def _gate_freshness() -> None:
    from ingestion.db import connection
    from quality.specs import run_freshness_gate

    with connection() as conn:
        for line in run_freshness_gate(conn):
            log.info(line)


def _gate_null_rates() -> None:
    from ingestion.db import connection
    from quality.specs import run_null_rate_gate

    with connection() as conn:
        for line in run_null_rate_gate(conn):
            log.info(line)


def _gate_mart_quality() -> None:
    from ingestion.db import connection
    from quality.mart_expectations import run_mart_expectations

    with connection() as conn:
        for line in run_mart_expectations(conn, marts_schema="marts"):
            log.info(line)


with DAG(
    dag_id="partflow_ingest",
    description="Land synthetic supply-chain sources, build KPI marts, gate on data quality.",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["partflow", "ingestion", "dbt", "data-quality"],
    default_args={"retries": 1},
) as dag:

    apply_schema = PythonOperator(
        task_id="apply_raw_schema",
        python_callable=_apply_schema,
    )

    land_groups = []
    for domain, tables in DOMAINS.items():
        with TaskGroup(group_id=f"land_{domain}") as tg:
            for table, filename in tables:
                # task id e.g. land_purchase_orders (drop the raw_ prefix)
                PythonOperator(
                    task_id=f"land_{table.removeprefix('raw_')}",
                    python_callable=_land_table,
                    op_kwargs={"table": table, "filename": filename},
                )
        land_groups.append(tg)

    build_marts = BashOperator(
        task_id="build_marts",
        bash_command=(
            "cd /opt/airflow/dbt && "
            "/opt/dbt-venv/bin/dbt build --profiles-dir . --target dev"
        ),
    )

    gate_freshness = PythonOperator(task_id="gate_freshness", python_callable=_gate_freshness)
    gate_row_counts = PythonOperator(task_id="gate_row_counts", python_callable=_gate_row_counts)
    gate_null_rates = PythonOperator(task_id="gate_null_rates", python_callable=_gate_null_rates)
    gate_mart_quality = PythonOperator(task_id="gate_mart_quality", python_callable=_gate_mart_quality)

    # apply schema -> land all domains -> build marts -> gates in series
    apply_schema >> land_groups >> build_marts
    build_marts >> gate_freshness >> gate_row_counts >> gate_null_rates >> gate_mart_quality
