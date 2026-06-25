"""Shared fixtures: a small but statistically meaningful dataset generated once per session."""

from __future__ import annotations

from datetime import date

import pytest

from partflow_gen.config import GenConfig
from partflow_gen.pipeline import generate


@pytest.fixture(scope="session")
def small_config() -> GenConfig:
    # Small enough to be fast, large enough for distribution assertions to be stable.
    return GenConfig(
        seed=7,
        start_date=date(2025, 1, 1),
        months=3,
        n_suppliers=8,
        n_skus=60,
    )


@pytest.fixture(scope="session")
def dataset(small_config: GenConfig) -> dict[str, list[dict]]:
    return generate(small_config)
