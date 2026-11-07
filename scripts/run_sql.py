"""Render and execute the BasketPulse SQL pipeline against BigQuery.

    python scripts/run_sql.py --project my-proj --setup                                       # ONE-TIME: create dataset + empty tables
    python scripts/run_sql.py --project my-proj --dataset basketpulse --location US          # rebuild fact, marts, BQML (safe to re-run)
    python scripts/run_sql.py --project my-proj --dry-run                                     # validate + estimate bytes
    python scripts/run_sql.py --project my-proj --render-only                                 # print rendered SQL
    python scripts/run_sql.py --project my-proj --only sql/bqml/01_customer_segments.sql

Requires: pip install google-cloud-bigquery (not needed for --render-only).
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One-time DDL. It uses CREATE OR REPLACE, so it must NOT be part of the default (re)build or it would wipe loaded data.
SETUP = ["sql/01_schema.sql"]

# Rebuild steps, safe to re-run. Order matters: marts feed BQML models, which feed LookML-facing tables.
BUILD = [
    "sql/02_fct_transactions.sql",
    "sql/marts/01_agg_daily_store_category.sql",
    "sql/marts/02_customer_features.sql",
    "sql/bqml/01_customer_segments.sql",
    "sql/bqml/02_store_peer_groups.sql",
    "sql/bqml/03_demand_forecast.sql",
    "sql/marts/03_basket_affinity.sql",
]
PIPELINE = SETUP + BUILD


def render(path: Path, params: dict[str, str]) -> str:
    sql = path.read_text()
    for k, v in params.items():
        sql = sql.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{\w+\}\}", sql)
    if left:
        raise ValueError(f"{path}: unresolved template variables {sorted(set(left))}")
    return sql


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--dataset", default="basketpulse")
    ap.add_argument("--location", default="US")
    ap.add_argument("--min-item-support", type=int, default=300, help="min baskets per item for affinity (scale with data)")
    ap.add_argument("--min-pair-support", type=int, default=100, help="min baskets per pair for affinity")
    ap.add_argument("--setup", action="store_true", help="run one-time DDL only (drops and recreates empty tables!)")
    ap.add_argument("--only", help="run a single file from the pipeline")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    a = ap.parse_args()

    params = dict(project=a.project, dataset=a.dataset, location=a.location,
                  min_item_support=a.min_item_support, min_pair_support=a.min_pair_support)
    files = [a.only] if a.only else (SETUP if a.setup else BUILD)
    if a.render_only:
        for f in files:
            print(f"-- ===== {f} =====\n{render(ROOT / f, params)}")
        return 0

    from google.cloud import bigquery  # lazy import
    client = bigquery.Client(project=a.project, location=a.location)
    for f in files:
        sql = render(ROOT / f, params)
        t0 = time.perf_counter()
        cfg = bigquery.QueryJobConfig(dry_run=a.dry_run, use_query_cache=False)
        job = client.query(sql, job_config=cfg)
        if a.dry_run:
            print(f"[dry-run] {f}: would process {job.total_bytes_processed or 0:,} bytes")
            continue
        job.result()
        print(f"[ok] {f}  {time.perf_counter() - t0:7.1f}s  billed={job.total_bytes_billed or 0:,} B  "
              f"slot_ms={job.slot_millis or 0:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
