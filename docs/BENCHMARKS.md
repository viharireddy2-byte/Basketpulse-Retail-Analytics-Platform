# Benchmarks

This page separates three kinds of numbers. They are never mixed.

| Kind | Meaning | Where |
|---|---|---|
| **Measured** | Actually run, on the machine described | Section 1 |
| **Analytical** | Deterministic math (e.g. partition pruning), not a measurement | Section 2 |
| **Not yet run** | Needs a BigQuery project; harness included | Section 3 |

## 1. Measured: synthetic data generator

Environment: 1 vCPU, 3 GB RAM sandbox, Python 3.12.3, NumPy 2.5.4, pandas 3.0.6, gzip level 1 output, seed 42.
Commands: `python -m datagen.generate --profile tiny|dev`.

| Profile | Transactions | Line items | Days | Wall time | Throughput | Peak RSS | Output (gzip CSV) |
|---|---:|---:|---:|---:|---:|---:|---:|
| tiny | 20,000 | 127,493 | 60 | 0.62 s | 32.1k tx/s | - | 1.8 MB |
| dev | 1,000,000 | 6,239,966 | 365 | 25.7 s | 38.9k tx/s | 126 MB | 104 MB |

Memory stays flat because the generator is partition-at-a-time (one day in memory), so peak RSS does not grow with total volume.

Characteristics of the generated `dev` dataset (computed from the files, not assumed):
6.24 lines per basket, $43.39 average basket value, 29.5% gross margin, 3.9% of sales on promotion,
88.0% of baskets tied to a loyalty customer, 87,998 distinct active customers, $43.4 M total net sales.

**Extrapolation (linear, not measured):** the `xl` profile (50 M transactions, ~312 M line items, 730 daily partitions) would take
about 21 minutes on one core (50 M / 38.9k tx/s) and produce roughly 5 GB of gzip CSV. Runs parallelise trivially by splitting `--days`
across processes; the generator is deterministic per seed, so this is a straightforward follow-up.

## 2. Analytical: partition pruning

`python benchmarks/estimate.py --days 730 --transactions 50000000`

| Query | Date window | Partitions read | Fraction of partitioned data scanned | Expected byte reduction vs unpartitioned |
|---|---:|---:|---:|---:|
| Q1 store, 28 days | 28 d | 28 / 730 | 3.8% | 26.1x |
| Q2 customer, 12 months | 365 d | 365 / 730 | 50.0% | 2.0x |
| Q3 region trend, 13 months | 395 d | 395 / 730 | 54.1% | 1.8x |
| Q4 category margin, 7 days | 7 d | 7 / 730 | 1.0% | 104.3x |

This is an upper bound on what *partitioning alone* saves and assumes data is uniform across days. The effect of **clustering**
(on `store_id, customer_id`) and of the **nested layout** (reading `basket_net_amount` instead of every line) is layout-dependent
and is deliberately not estimated: measure it with Section 3.

## 3. BigQuery measurements: not yet run

No BigQuery run has been performed for this repository yet, so there are no BigQuery timings here. The harness is included and
writes its own results page, `docs/BENCHMARKS_BIGQUERY.md`, with raw per-run JSON in `benchmarks/results/`:

```bash
make data-standard DATA=standard && make load DATA=standard && make build
make bench          # 4 queries x 3 layouts x (5 runs + 1 discarded warm-up), query cache off
```

Layouts compared: (a) flat line items, unpartitioned (baseline); (b) flat, partitioned by day; (c) nested baskets, partitioned by day and
clustered by `store_id, customer_id, channel_id`. It reports p50/p95 latency, bytes billed, slot-ms, and the ratio against the baseline.
