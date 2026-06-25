"""In-memory domain objects and shared helpers.

`Supplier` and `Sku` carry **latent** generative parameters (true on-time probability,
defect rate, daily demand) that drive the rest of the simulation but are NOT emitted to the
source files — those are the hidden truth the marts must *recompute* from events. Each object
exposes `source_row()` returning only the columns a real source system would expose.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


def season_multiplier(day: date, amplitude: float) -> float:
    """Annual demand seasonality: a sinusoid peaking mid-year, trough at year boundaries."""
    doy = day.timetuple().tm_yday
    return 1.0 + amplitude * math.sin(2.0 * math.pi * (doy - 80) / 365.0)


@dataclass
class Supplier:
    supplier_id: str
    supplier_name: str
    country: str
    tier: str
    category: str
    promised_lead_time_days: int
    onboarded_date: date
    # latent (generation-only, never written to the source file)
    lead_time_mean_days: float
    base_otd: float
    defect_rate_ppm: float
    fill_reliability: float

    def source_row(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "country": self.country,
            "tier": self.tier,
            "category": self.category,
            "promised_lead_time_days": self.promised_lead_time_days,
            "onboarded_date": self.onboarded_date.isoformat(),
        }


@dataclass
class Sku:
    sku_id: str
    description: str
    category: str
    primary_supplier_id: str
    unit_cost: float
    unit_of_measure: str
    abc_class: str
    # latent
    base_daily_demand: float

    def source_row(self) -> dict:
        return {
            "sku_id": self.sku_id,
            "description": self.description,
            "category": self.category,
            "primary_supplier_id": self.primary_supplier_id,
            "unit_cost": round(self.unit_cost, 2),
            "unit_of_measure": self.unit_of_measure,
            "abc_class": self.abc_class,
        }
