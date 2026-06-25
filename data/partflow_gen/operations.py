"""Generate operational series: daily inventory snapshots and material-flow events.

Inventory is simulated forward: opening cover + receipts (from shipments) - seasonal demand,
clamped at zero. Stockouts therefore emerge from the supply/demand balance rather than being
sprinkled in. Outbound events are derived by aggregating that same daily demand to weekly grain.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from numpy.random import Generator

from .config import GenConfig
from .model import Sku, season_multiplier


def generate_inventory_snapshots(
    cfg: GenConfig, rng: Generator, skus: list[Sku], shipment_lines: list[dict]
) -> list[dict]:
    receipts: dict[tuple[str, date], float] = defaultdict(float)
    for sl in shipment_lines:
        rd = date.fromisoformat(sl["received_date"])
        if cfg.start_date <= rd < cfg.end_date:
            receipts[(sl["sku_id"], rd)] += sl["received_qty"]

    snapshots: list[dict] = []
    for sku in skus:
        on_hand = sku.base_daily_demand * cfg.initial_cover_days
        d = cfg.start_date
        while d < cfg.end_date:
            on_hand += receipts.get((sku.sku_id, d), 0.0)
            season = season_multiplier(d, cfg.seasonal_amplitude)
            demand = int(rng.poisson(max(0.0, sku.base_daily_demand * season)))
            on_hand = max(0.0, on_hand - demand)
            snapshots.append(
                {
                    "snapshot_date": d.isoformat(),
                    "sku_id": sku.sku_id,
                    "on_hand_qty": int(round(on_hand)),
                    "daily_demand_qty": demand,
                    "in_stockout": on_hand <= 0,
                }
            )
            d += timedelta(days=1)
    return snapshots


def generate_material_flow_events(
    cfg: GenConfig,
    rng: Generator,
    shipments: list[dict],
    shipment_lines: list[dict],
    inventory_snapshots: list[dict],
) -> list[dict]:
    ship_by_id = {s["shipment_id"]: s for s in shipments}
    events: list[dict] = []
    seq = 0

    def emit(event_type: str, sku_id: str, qty: int, ts: date, ref_type: str, ref_id: str) -> None:
        nonlocal seq
        seq += 1
        events.append(
            {
                "event_id": f"EVT-{seq:08d}",
                "event_type": event_type,
                "sku_id": sku_id,
                "qty": qty,
                "event_ts": ts.isoformat(),
                "reference_type": ref_type,
                "reference_id": ref_id,
            }
        )

    # Inbound: each received shipment line produces a receive then a putaway.
    for sl in shipment_lines:
        rd = date.fromisoformat(sl["received_date"])
        if not (cfg.start_date <= rd < cfg.end_date):
            continue
        carrier_ref = sl["shipment_id"]
        emit("received", sl["sku_id"], sl["received_qty"], rd, "shipment", carrier_ref)
        # putaway lands 0-1 days after receipt
        putaway_ts = rd + timedelta(days=int(rng.integers(0, 2)))
        if putaway_ts >= cfg.end_date:
            putaway_ts = rd
        emit("putaway", sl["sku_id"], sl["received_qty"], putaway_ts, "shipment", carrier_ref)
        _ = ship_by_id  # shipments kept for future reference enrichment

    # Outbound: aggregate daily demand to weekly grain, emit a pick then a ship.
    weekly: dict[tuple[str, date], int] = defaultdict(int)
    for snap in inventory_snapshots:
        d = date.fromisoformat(snap["snapshot_date"])
        week_start = d - timedelta(days=d.weekday())
        weekly[(snap["sku_id"], week_start)] += snap["daily_demand_qty"]

    for (sku_id, week_start), qty in weekly.items():
        if qty <= 0:
            continue
        ship_ts = min(week_start + timedelta(days=6), cfg.end_date - timedelta(days=1))
        ref = f"WK-{week_start.isoformat()}"
        emit("picked", sku_id, qty, ship_ts, "demand", ref)
        emit("shipped", sku_id, qty, ship_ts, "demand", ref)

    events.sort(key=lambda e: (e["event_ts"], e["event_id"]))
    return events
