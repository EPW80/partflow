"""Simulated external sources for the three landing patterns.

In production these would be real integrations (HTTP clients, webhook endpoints).
Here they generate synthetic payloads that exercise the landing functions without
hitting any real API. All data produced is synthetic.

  fetch_supplier_catalog(seed, n_suppliers, n_skus)
      Simulates a paginated supplier REST API returning a product catalog.
      Returns (supplier_rows, sku_rows) — dicts shaped like the raw_* columns.

  stream_webhook_events(seed, n_events)
      Simulates a webhook stream of real-time material-flow events.
      Yields one dict per event; callers land each with land_webhook_event().
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from typing import Iterator

_SUPPLIER_CATEGORIES = [
    "raw materials", "fasteners", "electronics", "packaging",
    "castings", "machined parts", "subassemblies", "consumables",
]
_COUNTRIES = ["US", "DE", "CN", "JP", "KR", "MX", "IN", "FR", "GB", "BR"]
_TIERS = ["strategic", "preferred", "approved", "probationary"]
_UOM = ["each", "box", "kg", "meter", "liter", "roll"]
_ABC = ["A", "B", "C"]
_CARRIERS = ["DHL", "FedEx", "UPS", "Maersk", "DB Schenker"]
_EVENT_TYPES = ["received", "putaway", "picked", "shipped"]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def fetch_supplier_catalog(
    seed: int = 42,
    n_suppliers: int = 40,
    n_skus: int = 500,
) -> tuple[list[dict], list[dict]]:
    """Simulate a supplier REST catalog API response.

    Returns (supplier_rows, sku_rows) as lists of string-valued dicts —
    shaped to match raw_suppliers and raw_skus columns.
    All values are strings because the raw layer lands as-received (no type coercion).
    """
    rng = _rng(seed)
    base_date = date(2023, 1, 1)

    suppliers: list[dict] = []
    for i in range(n_suppliers):
        onboarded = base_date - timedelta(days=rng.randint(180, 2000))
        suppliers.append(
            {
                "supplier_id": f"SUP-{i + 1:04d}",
                "supplier_name": f"Supplier {i + 1} Corp",
                "country": rng.choice(_COUNTRIES),
                "tier": rng.choice(_TIERS),
                "category": rng.choice(_SUPPLIER_CATEGORIES),
                "promised_lead_time_days": str(rng.randint(7, 45)),
                "onboarded_date": onboarded.isoformat(),
            }
        )

    skus: list[dict] = []
    for i in range(n_skus):
        sup = suppliers[i % len(suppliers)]
        cost = round(rng.lognormvariate(2.5, 0.8), 2)
        skus.append(
            {
                "sku_id": f"SKU-{i + 1:05d}",
                "description": f"Part {i + 1} assembly item",
                "category": sup["category"],
                "primary_supplier_id": sup["supplier_id"],
                "unit_cost": str(cost),
                "unit_of_measure": rng.choice(_UOM),
                "abc_class": rng.choice(_ABC),
            }
        )

    return suppliers, skus


def stream_webhook_events(
    seed: int = 42,
    n_events: int = 200,
    start_date: date = date(2025, 1, 1),
) -> Iterator[dict]:
    """Simulate a stream of real-time material-flow webhook events.

    Yields one event dict per call, shaped like raw_material_flow_events columns.
    Event IDs are deterministic (hash of seed + index) so re-running the same seed
    produces identical events — landing is idempotent on event_id.
    """
    rng = _rng(seed)
    for i in range(n_events):
        # Deterministic event_id so re-streaming the same webhook is safe to re-land.
        event_id = f"WH-{hashlib.sha1(f'{seed}:{i}'.encode()).hexdigest()[:10].upper()}"
        event_date = start_date + timedelta(days=rng.randint(0, 180))
        sku_num = rng.randint(1, 500)
        yield {
            "event_id": event_id,
            "event_type": rng.choice(_EVENT_TYPES),
            "sku_id": f"SKU-{sku_num:05d}",
            "qty": str(rng.randint(1, 500)),
            "event_ts": event_date.isoformat(),
            "reference_type": "webhook",
            "reference_id": f"WH-SRC-{i:05d}",
        }
