"""Analytical partition-pruning estimates (NOT measurements).

Partition pruning is deterministic: a query that filters N of D daily partitions reads ~N/D of the
partitioned column bytes. This script prints that fraction for the benchmark queries so expectations can
be compared with `bench.py` measurements. Clustering effects depend on data layout and are intentionally
NOT estimated here - measure them.

    python benchmarks/estimate.py --days 730 --transactions 50000000
"""
from __future__ import annotations

import argparse

QUERY_WINDOWS_DAYS = {"q1_store_28d": 28, "q2_customer_12m": 365, "q3_region_month_13m": 395, "q4_category_margin_7d": 7}


def pruning_fraction(window_days: int, total_days: int) -> float:
    if total_days <= 0 or window_days < 0:
        raise ValueError("days must be positive")
    return min(window_days, total_days) / total_days


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=730, help="days of history loaded (partitions)")
    ap.add_argument("--transactions", type=int, default=50_000_000)
    ap.add_argument("--avg-lines", type=float, default=6.24, help="line items per transaction (generator default ~6.2)")
    a = ap.parse_args()
    print(f"{a.days} daily partitions, {a.transactions:,} tx, ~{int(a.transactions * a.avg_lines):,} lines")
    print(f"{'query':<24}{'window(d)':>10}{'partitions read':>17}{'fraction scanned':>18}{'expected reduction':>20}")
    for q, w in QUERY_WINDOWS_DAYS.items():
        f = pruning_fraction(w, a.days)
        print(f"{q:<24}{w:>10}{min(w, a.days):>17}{f:>17.1%}{1 / f:>19.1f}x")


if __name__ == "__main__":
    main()
