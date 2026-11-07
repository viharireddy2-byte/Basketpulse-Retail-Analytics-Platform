# Pipeline operations

The `operations` package provides source validation, partition replay, execution
controls, and forecast monitoring alongside the full-build scripts. Both command
paths share the fact transformation. Cloud integration requires a configured GCP
environment; live deployment validation remains pending.

## Prerequisites and first run

Install `requirements-gcp.txt`. Authenticate using Application Default Credentials.
Create and load tables and run the existing full build once. The incremental path
requires the existing fact schema; it never runs destructive setup DDL.

```bash
python -m operations.runner --project my-project --action check \
  --start-date 2026-06-01 --end-date 2026-06-30 --render-only
python -m operations.runner --project my-project --action check \
  --start-date 2026-06-01 --end-date 2026-06-30 --log operations.jsonl
python -m operations.runner --project my-project --action refresh \
  --start-date 2026-06-01 --end-date 2026-06-30 \
  --maximum-bytes-billed 10000000000 --job-timeout-ms 3600000 --log operations.jsonl
```

Dates are inclusive. `check` only runs source assertions. `incremental` validates
source then replaces the fact partitions. `refresh` does that and rebuilds all
existing marts and models in dependency order, preserving the existing full-build
semantics for derived outputs. Support thresholds remain configurable.

## Source contract and replay

The staging window must contain the **complete desired contents of each target
partition**, not just the newest events. Existing staging ingestion still truncates
on load; this module does not turn the legacy loader into an append/CDC loader.
Reject empty windows to prevent accidental deletion; intentional empty partition
removal requires a separately reviewed maintenance operation.

Checks reject duplicate `(transaction_id,line_number)` keys, bad amounts and
quantities, timestamp/date mismatch, inconsistent basket headers, null/duplicate
dimension keys, and missing dimension references. Anonymous customers remain valid.
Cross-boundary basket IDs are rejected. Fact publication performs delete + insert,
line-count, basket-count, and sales reconciliation inside one BigQuery transaction.
A repeated window replaces its contents without appending duplicates. Corrections
and late data are handled by replaying the complete affected window. Source schema
is an explicit contract: unexpected schema changes should fail rather than silently
reorder columns. These checks assume positive-sale retail transactions; returns need
an explicitly versioned contract before ingestion.

## Failures and costs

Each step emits JSON started/succeeded/failed events, a run ID, job ID, duration,
processed/billed bytes, and slot milliseconds. Redirect stdout to managed logging
or retain `--log` durably. Logs omit SQL and exception messages to avoid accidental
data disclosure. Investigate failures by job ID in BigQuery.

Submission retries are bounded (three attempts, 1s/2s backoff), reuse the same job ID,
and recover an already-created job after an ambiguous submission. Failed warehouse
jobs are not automatically replayed. A failed step stops all later steps. Run IDs
are new per invocation; operators must check prior job status before rerunning after
process loss. Serialize writers with your scheduler (one concurrent run). Concurrent
mutating BigQuery transactions may abort; investigate, then replay the complete window.

The per-query byte limit and requested job timeout apply to this new command only.
The byte cap is not a total pipeline or BQML spending cap. Dry-run results for scripts
are incomplete estimates; temporary tables and DDL prevent full validation. Use billing
budgets and reservations in your deployment as appropriate. `--render-only` needs no
cloud SDK or credentials and performs no warehouse operations.

Fact publication is atomic; **the entire mart/model refresh is not atomic**. A later
failure may leave derived tables on different generations. Rerun refresh after fixing
the cause. For coordinated publication, build versioned datasets and switch consumers
only after all validations pass. The original Looker cache watermarks do not detect
historical corrections reliably; invalidate caches after backfills or wait for their
maximum age. Coordinated publication and backfill-triggered cache invalidation are
not automated.

## Forecast monitoring

```bash
python -m operations.runner --project my-project --action capture-forecast
# On later days, after a complete actuals load:
python -m operations.runner --project my-project --action evaluate-forecast
```

Capture snapshots only future forecast dates, retaining the first forecast per UTC
issue day and series-date. Run after each forecast build, before any target-day data
arrives. History is separate from the existing forecast table, so regular rebuilds
do not overwrite it. Evaluation reports MAE, WAPE, interval coverage, evaluated point
count and missing-actual count per issue day/store/category. WAPE is NULL for zero
aggregate actual demand; missing series-days are not assumed to be zero. Evaluation
excludes the current UTC day; only run against complete actuals. Metrics compare to
currently published actuals, so backfills can revise metrics. This is prospective
monitoring; rolling-origin backtesting and model accuracy results are not included. Synthetic historical
fixtures will not produce prospective observations until data dates move forward.

## Verification and rollout

```bash
make test lint
BASKETPULSE_TEST_PROJECT=my-isolated-test-project python -m pytest tests/test_operations_cloud.py -q
```

The opt-in cloud test creates a uniquely named disposable dataset, verifies repeated
replay, unaffected dates, rejection of corrupt source, and transaction rollback after
an injected reconciliation failure; it deletes the dataset in `finally`. It requires
billing and credentials, so normal CI skips it. Local quality tests execute translated
predicates in DuckDB; they do not validate BigQuery syntax or transaction behavior.

Use separate development and production identities/datasets. Give the pipeline job
creation permission at project scope and write permission only on its target dataset;
Looker should have read-only data access. Prefer short-lived workload identity over
committed keys. No row-level store authorization is provided: deploy Looker access
filters/user attributes or warehouse row policies before sharing restricted data.
Configure your scheduler for one writer and send failed-run events to your alerting
system. Scheduling, alert routing, and infrastructure provisioning require deployment
configuration. Live cloud validation remains pending.

## Metric and dashboard limitations

| Area | Current behavior | Validation or correction needed |
|---|---|---|
| Store average basket value | Store peer features divide sales by category-level transaction counts; multi-category baskets can be counted more than once. | Calculate the feature at basket grain and test multi-category fixtures. |
| Weekly sales | The feature divides annual-window sales by `365 / 7`, including partial-history datasets. | Define the intended observation window before changing normalization. |
| Prior-year date boundaries | The period bucket uses an inclusive prior-year end while the explore uses an exclusive upper bound. | Validate one-day, month-end, and leap-year windows against known totals. |
| Segment labels | Labels follow average monetary ranking; tied ranks can skip labels and low spend alone does not establish lapsing behavior. | Validate centroid recency and frequency and define deterministic labels. |
| Dashboard defaults | Relative date filters and a default store name may not match the generated dataset. | Set filters to available dates and stores before checking dashboard totals. |
| Cache refresh | Maximum-date and calendar-week triggers do not detect every backfill or failed ML refresh. | Invalidate caches after corrections and verify refresh completion. |

These limitations apply to the existing metric definitions. Source-quality gates
and transactional fact replay do not correct semantic-layer calculations.
