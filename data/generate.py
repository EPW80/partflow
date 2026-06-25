#!/usr/bin/env python3
"""CLI entry point for the PartFlow synthetic data generator.

    python generate.py --out output --months 6 --seed 42

Writes one # SYNTHETIC DATA-headed CSV per source table into the output directory.
"""

from __future__ import annotations

import argparse
from datetime import date

from partflow_gen.config import GenConfig
from partflow_gen.pipeline import TABLE_ORDER, generate
from partflow_gen.writers import write_dataset


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PartFlow synthetic supply-chain data.")
    parser.add_argument("--out", default="output", help="output directory (default: output)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=_parse_date, default=None, help="start date YYYY-MM-DD")
    parser.add_argument("--months", type=int, default=None)
    parser.add_argument("--suppliers", type=int, default=None)
    parser.add_argument("--skus", type=int, default=None)
    args = parser.parse_args()

    overrides = {"seed": args.seed}
    if args.start is not None:
        overrides["start_date"] = args.start
    if args.months is not None:
        overrides["months"] = args.months
    if args.suppliers is not None:
        overrides["n_suppliers"] = args.suppliers
    if args.skus is not None:
        overrides["n_skus"] = args.skus

    cfg = GenConfig(**overrides)
    dataset = generate(cfg)
    paths = write_dataset(dataset, args.out)

    print(f"# SYNTHETIC DATA — seed={cfg.seed} {cfg.start_date}..{cfg.end_date}")
    for name in TABLE_ORDER:
        print(f"  {name:<24} {len(dataset[name]):>8,} rows -> {paths[name]}")


if __name__ == "__main__":
    main()
