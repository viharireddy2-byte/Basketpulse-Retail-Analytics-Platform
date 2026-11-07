"""BigQuery layout benchmark: flat/unpartitioned vs flat/partitioned vs nested/partitioned+clustered.

    python benchmarks/bench.py --project my-proj --dataset basketpulse --runs 5
    python benchmarks/bench.py --project my-proj --report-only results/bench_<ts>.json

Writes results/bench_<timestamp>.json and docs/BENCHMARKS_BIGQUERY.md (measured values only).
Cache is disabled; every timing is a real job. Needs `pip install google-cloud-bigquery`.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "benchmarks" / "queries"

VARIANTS = {  # name -> (table, query flavour, description)
    "flat_unpartitioned": ("bench_line_items_flat", "flat", "Flat line items, no partitioning or clustering (baseline)"),
    "flat_partitioned": ("stg_line_items", "flat", "Flat line items, partitioned by day"),
    "nested_part_clustered": ("fct_transactions", "nested", "Nested baskets, partitioned by day, clustered (store, customer, channel)"),
}


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (q in 0..100)."""
    if not values:
        raise ValueError("no values")
    v = sorted(values)
    k = (len(v) - 1) * q / 100
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return str(n)


def summarise(results: list[dict]) -> list[dict]:
    """Collapse per-run rows into per (query, variant) medians and compute speed-up vs baseline."""
    out: dict[tuple[str, str], dict] = {}
    for r in results:
        out.setdefault((r["query"], r["variant"]), {"query": r["query"], "variant": r["variant"], "runs": []})["runs"].append(r)
    rows = []
    for (q, v), d in out.items():
        runs = d["runs"]
        rows.append(dict(query=q, variant=v, n=len(runs),
                         p50_s=statistics.median(x["elapsed_s"] for x in runs),
                         p95_s=percentile([x["elapsed_s"] for x in runs], 95),
                         bytes_billed=statistics.median(x["bytes_billed"] for x in runs),
                         slot_ms=statistics.median(x["slot_ms"] for x in runs)))
    base = {r["query"]: r for r in rows if r["variant"] == "flat_unpartitioned"}
    for r in rows:
        b = base.get(r["query"])
        r["bytes_reduction_x"] = (b["bytes_billed"] / r["bytes_billed"]) if b and r["bytes_billed"] else None
        r["speedup_x"] = (b["p50_s"] / r["p50_s"]) if b and r["p50_s"] else None
    return sorted(rows, key=lambda r: (r["query"], list(VARIANTS).index(r["variant"])))


def render_markdown(meta: dict, rows: list[dict]) -> str:
    lines = [
        "# Benchmark results (measured)", "",
        f"Run at `{meta['run_at']}` on project `{meta['project']}` ({meta['location']}), on-demand pricing, "
        f"query cache disabled, {meta['runs']} runs per cell.", "",
        f"Dataset: **{meta['transactions']:,}** transactions / **{meta['line_items']:,}** line items.", "",
        "| Query | Layout | p50 | p95 | Bytes billed | Slot-ms | Bytes vs baseline | Speed-up |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        red = f"{r['bytes_reduction_x']:.1f}x" if r["bytes_reduction_x"] else "-"
        sp = f"{r['speedup_x']:.1f}x" if r["speedup_x"] else "-"
        lines.append(f"| {r['query']} | {r['variant']} | {r['p50_s']:.2f}s | {r['p95_s']:.2f}s | "
                     f"{fmt_bytes(r['bytes_billed'])} | {int(r['slot_ms']):,} | {red} | {sp} |")
    return "\n".join(lines) + "\n"


def run(args) -> None:
    from google.cloud import bigquery
    c = bigquery.Client(project=args.project, location=args.location)
    ds = f"{args.project}.{args.dataset}"
    c.query(f"CREATE OR REPLACE TABLE `{ds}.bench_line_items_flat` AS SELECT * FROM `{ds}.stg_line_items`").result()
    as_of = list(c.query(f"SELECT CAST(MAX(transaction_date) AS STRING) d FROM `{ds}.fct_transactions`").result())[0].d
    store = list(c.query(f"SELECT store_id FROM `{ds}.fct_transactions` WHERE transaction_date > DATE_SUB(DATE '{as_of}', INTERVAL 7 DAY) "
                         f"GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1 OFFSET 5").result())[0].store_id
    cust = list(c.query(f"SELECT customer_id FROM `{ds}.fct_transactions` WHERE transaction_date > DATE_SUB(DATE '{as_of}', INTERVAL 365 DAY) "
                        f"AND customer_id IS NOT NULL GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1 OFFSET 1000").result())[0].customer_id
    counts = list(c.query(f"SELECT COUNT(*) tx, SUM(basket_lines) li FROM `{ds}.fct_transactions`").result())[0]
    results = []
    for qfile in sorted({p.name.split(".")[0] for p in QUERIES.glob("*.sql")}):
        for vname, (table, flavour, _) in VARIANTS.items():
            sql = (QUERIES / f"{qfile}.{flavour}.sql").read_text()
            for k, v in dict(table=f"{ds}.{table}", dataset=ds, as_of=as_of, store_id=store, customer_id=cust).items():
                sql = sql.replace("{{" + k + "}}", str(v))
            for i in range(args.runs + 1):  # first run is a warm-up and is discarded
                t0 = time.perf_counter()
                job = c.query(sql, job_config=bigquery.QueryJobConfig(use_query_cache=False))
                job.result()
                el = time.perf_counter() - t0
                if i:
                    results.append(dict(query=qfile, variant=vname, elapsed_s=el, bytes_billed=job.total_bytes_billed or 0,
                                        slot_ms=job.slot_millis or 0))
                print(f"{qfile:24s} {vname:24s} run {i}: {el:6.2f}s {fmt_bytes(job.total_bytes_billed or 0)}")
    meta = dict(run_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), project=args.project, location=args.location,
                runs=args.runs, transactions=int(counts.tx), line_items=int(counts.li))
    save(meta, results)


def save(meta: dict, results: list[dict]) -> None:
    (ROOT / "benchmarks" / "results").mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "benchmarks" / "results" / f"bench_{stamp}.json").write_text(json.dumps(dict(meta=meta, results=results), indent=2))
    (ROOT / "docs" / "BENCHMARKS_BIGQUERY.md").write_text(render_markdown(meta, summarise(results)))
    print("wrote docs/BENCHMARKS_BIGQUERY.md")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project")
    ap.add_argument("--dataset", default="basketpulse")
    ap.add_argument("--location", default="US")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--report-only", type=Path, help="re-render docs/BENCHMARKS_BIGQUERY.md from a saved results JSON")
    a = ap.parse_args()
    if a.report_only:
        d = json.loads(a.report_only.read_text())
        (ROOT / "docs" / "BENCHMARKS_BIGQUERY.md").write_text(render_markdown(d["meta"], summarise(d["results"])))
        return
    if not a.project:
        ap.error("--project is required")
    run(a)


if __name__ == "__main__":
    main()
