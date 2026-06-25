"""Write source tables to CSV, each prefixed with the mandatory # SYNTHETIC DATA header.

The header is line 1; the CSV header row follows. Phase 2 ingestion reads with a
comment-skipping reader (`comment='#'`). Booleans are written lowercase so Postgres casts
them cleanly.
"""

from __future__ import annotations

import csv
import os

SYNTHETIC_HEADER = "# SYNTHETIC DATA"


def _format(value: object) -> object:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_table(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="") as f:
        f.write(SYNTHETIC_HEADER + "\n")
        if not rows:
            return
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _format(v) for k, v in row.items()})


def write_dataset(dataset: dict[str, list[dict]], outdir: str) -> dict[str, str]:
    os.makedirs(outdir, exist_ok=True)
    paths: dict[str, str] = {}
    for name, rows in dataset.items():
        path = os.path.join(outdir, f"{name}.csv")
        write_table(rows, path)
        paths[name] = path
    return paths
