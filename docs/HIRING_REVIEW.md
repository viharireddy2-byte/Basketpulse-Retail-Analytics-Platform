# Strict hiring-manager review

## Verdict

**Original submission: 6.5/10 as a junior BI/data-engineering portfolio project;
3/10 for demonstrated production readiness.** These are subjective review scores,
not a hiring probability or an official FAANG rubric. I would consider discussing
it in a junior interview, but would not accept it as proof of operating a production
analytics platform. It is a warehouse/BI project rather than a standalone application.

The revised version improves operational design and test depth. Its readiness score
cannot honestly jump to production-ready while warehouse SQL and Looker behavior
remain unverified. The strongest next improvement is measured deployment evidence,
not more technology names. This project alone does not establish senior-level scope.

## What earns credit

- Explicit basket grain, nested line items, date partitioning and clustering tied to access patterns.
- Business questions connect to the marts, semantic layer and dashboards.
- Deterministic synthetic data includes recognizable shopping behavior and supports repeatable experiments.
- Affinity pruning addresses pair explosion rather than blindly cross-joining the catalog.
- The README distinguishes measured generator results from analytical warehouse estimates.
- Cloud dependencies are optional; local generator and static checks remain runnable.

## Major red flags and status

| Finding | Hiring implication | This revision |
|---|---|---|
| SQL, BQML, LookML and dashboards never validated on their target systems | Central product behavior is unproven | Added opt-in real BigQuery integration test and manual workflow; actual execution still required |
| No quality gate ahead of fact publication | Duplicates, orphans, inconsistent basket headers can silently distort KPIs | Added executable source assertions and count/sales reconciliation |
| Full table rebuild is the only fact update path | Weak recovery and late-data story | Added transactional complete-partition replay; legacy ingestion still truncates |
| No durable forecast history/evaluation | Having an ARIMA model does not demonstrate predictive value | Added prospective snapshots and MAE/WAPE/interval coverage; no accuracy results claimed |
| Operational scripts lack structured run context and bounded cost controls | Difficult incident triage and cost attribution | Added per-step JSON events, job metrics, byte limits, requested timeouts, same-ID submission recovery |
| Static CI checks do not execute warehouse semantics | A green badge does not mean dashboards work | Added corruption tests using SQL predicates and cloud transaction test; Looker validator still needed |
| No measured BigQuery benchmark output | XL generation support is not proof of warehouse performance at XL | Existing benchmark harness retained; publish actual results before claiming speedups |
| Multi-table publication and cache invalidation are incomplete | Readers can see mixed generations after failure or stale backfills | Explicit limitation and recovery runbook; versioned publication remains a deployment task |

## Specific correctness concerns preserved for compatibility

These are concrete review findings, not newly delivered behavior. Existing SQL and
LookML were left unchanged under the requirement to preserve current behavior.

1. **Store peer average basket value has a grain problem.** In
   `sql/bqml/02_store_peer_groups.sql`, `SUM(net_sales)/SUM(transactions)` uses
   category-level counts. A basket containing multiple categories is counted once
   in each category, understating store-wide basket value. Derive that feature at
   basket grain in a versioned metric change and test multi-category baskets.
2. **Weekly sales assumes a full year.** Dividing by `(365 / 7)` understates weekly
   throughput for tiny/partial-history profiles. Decide whether the feature means
   observed-week run rate or fixed annual-window sales before changing it.
3. **Prior-year boundary alignment needs a live query test.**
   `fct_transactions.period_bucket` uses inclusive `BETWEEN` for the prior-year end,
   while the explore uses an exclusive upper bound. Test one-day, month-end and
   leap-year filters against known fixtures before trusting YoY.
4. **Segment names overstate the model interpretation.** Labels are assigned from
   monetary ranking alone; a low monetary cluster is not necessarily lapsing, and
   tied ranks can skip labels. Validate centroids/recency and use deterministic
   naming before presenting segments as validated behavior.
5. **Default dashboard dates can miss synthetic data.** Relative-to-today filters
   and a hard-coded store name need validation against the generated dataset.
6. **Cache triggers are not publication markers.** Maximum transaction date does
   not change for historical corrections; calendar week is not evidence that a
   weekly ML rebuild succeeded. Explicitly invalidate caches after backfills.

## What I would ask in an interview

- Explain why each metric is additive or non-additive at basket/category/store grain.
- Show the same replay twice with no duplicates, then inject a failure and prove rollback.
- Show a real query plan/job report comparing identical result sets across layouts.
- Demonstrate whether forecasts beat a seasonal-naive baseline on held-out periods.
- Explain partial-publication recovery, schema evolution, restricted store access and cost ownership.
- Identify which results came from synthetic data and which were actually measured in the cloud.

## Required evidence before calling it production-ready

1. Execute the disposable cloud integration test and retain job IDs/results.
2. Run the complete original warehouse pipeline and validate every BQML output.
3. Run Looker's validator; exercise all dashboard filters and drill paths with known KPI fixtures.
4. Make a reviewed, versioned correction for the semantic issues above; they must not be hidden behind additional features.
5. Publish measured benchmark results with data volume, query equivalence, execution environment and costs.
6. Configure single-writer scheduling, durable logs/alerts, least-privilege identities, data-access restrictions, and versioned dataset publication.
7. Accumulate prospective forecast results or implement leakage-free rolling-origin backtests and a seasonal baseline.

## Validation in this environment

44 local tests passed, including the original tests and additional quality/retry/
monitoring tests. One cloud integration test is intentionally skipped without an
explicit test project. DuckDB tests translate portable quality expressions and
forecast arithmetic; they do not validate BigQuery scripts, DDL, BQML, or LookML.
The generator smoke test and static LookML lint were also run. No GCP or Looker
credentials were available, and no deployed services or benchmark measurements
were fabricated.
