"""CSV output carries the synthetic header and round-trips; generation is reproducible."""

from __future__ import annotations

import csv
from datetime import date

from partflow_gen.config import GenConfig
from partflow_gen.pipeline import TABLE_ORDER, generate
from partflow_gen.writers import SYNTHETIC_HEADER, write_dataset


def test_every_file_has_synthetic_header_and_round_trips(dataset, tmp_path):
    paths = write_dataset(dataset, str(tmp_path))
    for name in TABLE_ORDER:
        with open(paths[name]) as f:
            first = f.readline().rstrip("\n")
            assert first == SYNTHETIC_HEADER, f"{name}.csv missing synthetic header"
            rows = list(csv.DictReader(f))  # header line already consumed
        assert len(rows) == len(dataset[name]), f"{name}.csv row count mismatch"


def test_determinism_same_seed_identical():
    cfg = GenConfig(seed=99, months=2, n_suppliers=5, n_skus=30)
    a = generate(cfg)
    b = generate(cfg)
    assert a == b, "same seed should produce identical data"


def test_different_seed_differs():
    base = GenConfig(seed=1, months=2, n_suppliers=5, n_skus=30)
    other = GenConfig(seed=2, months=2, n_suppliers=5, n_skus=30)
    assert generate(base)["purchase_orders"] != generate(other)["purchase_orders"]


def test_dataset_spans_multiple_months(dataset):
    months = {po["order_date"][:7] for po in dataset["purchase_orders"]}
    assert len(months) >= 3, f"expected a multi-month span, saw {sorted(months)}"


def test_horizon_respected(dataset, small_config):
    end = small_config.end_date
    for snap in dataset["inventory_snapshots"]:
        assert date.fromisoformat(snap["snapshot_date"]) < end
