"""Great-Expectations-style assertion suite over the headline mart.

Validates kpi_supplier_scorecard — the most-consumed KPI table — beyond what dbt's
column tests cover, asserting cross-row and value-range expectations. Raises
DataQualityError on the first failed expectation (ADR-0003). GE itself is the
production swap-in; this keeps the image light.
"""

from __future__ import annotations

import psycopg2.extensions

from .checks import DataQualityError

_MART = "kpi_supplier_scorecard"


def run_mart_expectations(
    conn: psycopg2.extensions.connection,
    marts_schema: str = "marts",
) -> list[str]:
    rel = f"{marts_schema}.{_MART}"
    results: list[str] = []

    with conn.cursor() as cur:
        # 1. No null supplier_id.
        cur.execute(f"SELECT count(*) FROM {rel} WHERE supplier_id IS NULL")
        if cur.fetchone()[0] > 0:
            raise DataQualityError(f"{rel}: null supplier_id present")
        results.append("expect supplier_id not null: OK")

        # 2. supplier_id unique.
        cur.execute(f"SELECT count(*) - count(DISTINCT supplier_id) FROM {rel}")
        if cur.fetchone()[0] != 0:
            raise DataQualityError(f"{rel}: duplicate supplier_id")
        results.append("expect supplier_id unique: OK")

        # 3. Rates within [0,1].
        cur.execute(
            f"SELECT count(*) FROM {rel} "
            f"WHERE otd_rate NOT BETWEEN 0 AND 1 OR fill_rate NOT BETWEEN 0 AND 1"
        )
        if cur.fetchone()[0] > 0:
            raise DataQualityError(f"{rel}: otd_rate/fill_rate out of [0,1]")
        results.append("expect rates in [0,1]: OK")

        # 4. Composite score within [0,100].
        cur.execute(f"SELECT count(*) FROM {rel} WHERE composite_score NOT BETWEEN 0 AND 100")
        if cur.fetchone()[0] > 0:
            raise DataQualityError(f"{rel}: composite_score out of [0,100]")
        results.append("expect composite_score in [0,100]: OK")

        # 5. One scorecard row per supplier dimension row.
        cur.execute(f"SELECT count(*) FROM {rel}")
        scorecard_rows = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM {marts_schema}.dim_supplier")
        dim_rows = cur.fetchone()[0]
        if scorecard_rows != dim_rows:
            raise DataQualityError(
                f"{rel}: {scorecard_rows} rows != {dim_rows} suppliers in dim_supplier"
            )
        results.append(f"expect row-per-supplier: OK ({scorecard_rows})")

    return results
