"""Generate the root reference entities: suppliers and SKUs."""

from __future__ import annotations

from datetime import timedelta

from faker import Faker
from numpy.random import Generator

from .config import GenConfig
from .model import Sku, Supplier

SUPPLIER_TIERS = ["strategic", "preferred", "approved", "probationary"]
SUPPLIER_CATEGORIES = [
    "raw materials", "fasteners", "electronics", "packaging",
    "castings", "machined parts", "subassemblies", "consumables",
]
SKU_CATEGORIES = SUPPLIER_CATEGORIES
UOM = ["each", "box", "kg", "meter", "liter", "roll"]


def generate_suppliers(cfg: GenConfig, rng: Generator, faker: Faker) -> list[Supplier]:
    suppliers: list[Supplier] = []
    for i in range(cfg.n_suppliers):
        lead_mean = float(rng.uniform(cfg.lead_time_min_days, cfg.lead_time_max_days))
        # Promised lead time is the contractual target the supplier commits to: a little
        # above their true mean (suppliers pad their quotes).
        promised = int(round(lead_mean * float(rng.uniform(1.0, 1.2))))
        onboard_offset = int(rng.integers(180, 2000))
        suppliers.append(
            Supplier(
                supplier_id=f"SUP-{i + 1:04d}",
                supplier_name=faker.company(),
                country=faker.country(),
                tier=str(rng.choice(SUPPLIER_TIERS, p=[0.15, 0.35, 0.35, 0.15])),
                category=str(rng.choice(SUPPLIER_CATEGORIES)),
                promised_lead_time_days=promised,
                onboarded_date=cfg.start_date - timedelta(days=onboard_offset),
                lead_time_mean_days=lead_mean,
                base_otd=float(rng.uniform(cfg.otd_min, cfg.otd_max)),
                defect_rate_ppm=float(rng.uniform(cfg.defect_ppm_min, cfg.defect_ppm_max)),
                fill_reliability=float(
                    rng.uniform(cfg.fill_reliability_min, cfg.fill_reliability_max)
                ),
            )
        )
    return suppliers


def generate_skus(
    cfg: GenConfig, rng: Generator, faker: Faker, suppliers: list[Supplier]
) -> list[Sku]:
    # ABC classification: ~20% A (high demand), 30% B, 50% C — the classic Pareto split.
    abc_classes = ["A", "B", "C"]
    abc_p = [0.2, 0.3, 0.5]
    abc_demand_mult = {"A": 6.0, "B": 2.5, "C": 1.0}

    skus: list[Sku] = []
    for i in range(cfg.n_skus):
        # Assign first n_suppliers SKUs one-to-each so every supplier has >=1 SKU;
        # the rest are assigned at random.
        if i < len(suppliers):
            supplier = suppliers[i]
        else:
            supplier = suppliers[int(rng.integers(0, len(suppliers)))]
        abc = str(rng.choice(abc_classes, p=abc_p))
        base_demand = float(rng.gamma(2.0, 3.0)) * abc_demand_mult[abc]
        skus.append(
            Sku(
                sku_id=f"SKU-{i + 1:05d}",
                description=f"{faker.word().capitalize()} {faker.word()} {rng.integers(100, 999)}",
                category=supplier.category if rng.random() < 0.7 else str(rng.choice(SKU_CATEGORIES)),
                primary_supplier_id=supplier.supplier_id,
                unit_cost=float(rng.lognormal(mean=2.5, sigma=0.8)),
                unit_of_measure=str(rng.choice(UOM)),
                abc_class=abc,
                base_daily_demand=max(0.2, base_demand),
            )
        )
    return skus
