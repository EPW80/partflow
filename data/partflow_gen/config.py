"""Generation configuration: seed, horizon, volumes, and distribution parameters.

A frozen dataclass so a run is fully described by one value; tests use a small config
and the CLI uses the defaults. All randomness derives from `seed`, so runs are reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class GenConfig:
    # Reproducibility
    seed: int = 42

    # Horizon
    start_date: date = date(2025, 1, 1)
    months: int = 6

    # Population sizes
    n_suppliers: int = 40
    n_skus: int = 500

    # Purchase-order volume
    pos_per_week: float = 60.0          # mean POs/week across all suppliers
    lines_per_po_mean: float = 3.0      # Poisson mean (min 1 line)
    line_qty_mean: float = 120.0        # mean ordered qty per line (scaled by season)

    # Supplier latent-quality ranges (drawn once per supplier)
    lead_time_min_days: int = 7
    lead_time_max_days: int = 45
    otd_min: float = 0.70               # worst supplier on-time probability
    otd_max: float = 0.99               # best supplier on-time probability
    defect_ppm_min: float = 200.0       # best supplier baseline defect rate
    defect_ppm_max: float = 15000.0     # worst supplier baseline defect rate
    fill_reliability_min: float = 0.90  # worst supplier full-fill probability
    fill_reliability_max: float = 0.999

    # Seasonality (annual sinusoid on demand)
    seasonal_amplitude: float = 0.35    # +/- 35% swing across the year

    # Inventory simulation
    initial_cover_days: float = 30.0    # starting on-hand ~= this many days of demand

    @property
    def end_date(self) -> date:
        # Approx month length is fine for a synthetic horizon.
        return self.start_date + timedelta(days=int(self.months * 30))

    @property
    def horizon_days(self) -> int:
        return (self.end_date - self.start_date).days
