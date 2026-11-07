# Deployment

## Prerequisites
- A GCP project with billing enabled and the BigQuery and Cloud Storage APIs on
- `gcloud` authenticated (`gcloud auth application-default login`)
- Python 3.12, `make`
- Looker instance with a BigQuery connection (for the dashboard layer)

IAM for the identity running the pipeline: `roles/bigquery.jobUser`, `roles/bigquery.dataEditor` on the dataset,
`roles/storage.objectAdmin` on the bucket. BQML needs no extra role. The Looker service account needs `bigquery.dataViewer` on the dataset
and `bigquery.jobUser` on the project.

## 1. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-gcp.txt -r requirements-dev.txt
make test lint
```

## 2. Create the bucket
```bash
export PROJECT=my-gcp-project BUCKET=my-basketpulse-data LOCATION=US
gcloud storage buckets create gs://$BUCKET --project=$PROJECT --location=$LOCATION
```

## 3. Generate data
| Target | Command | Transactions |
|---|---|---:|
| Smoke test | `python -m datagen.generate --profile tiny --out data/tiny` | 20 K |
| Dev | `make data-dev` | 1 M |
| Standard | `make data-standard` | 10 M |
| XL | `make data-xl` | 50 M |

For XL, split the date range across processes with distinct `--end-date` windows and `--seed` values, or run on a larger VM.

## 4. Create tables, load, build
```bash
python scripts/run_sql.py --project $PROJECT --setup                            # ONE-TIME: dataset + empty tables
make load PROJECT=$PROJECT BUCKET=$BUCKET DATA=dev                             # GCS upload + BigQuery load jobs
python scripts/run_sql.py --project $PROJECT --dry-run                          # validate the rebuild steps
python scripts/run_sql.py --project $PROJECT --min-item-support 300 --min-pair-support 100   # rebuild: fact, marts, BQML (re-runnable)
```
`--setup` drops and recreates the empty tables, so run it once; the default run never touches the loaded tables.
Scale affinity thresholds with volume: roughly 0.03% of baskets for item support and 0.01% for pair support over the 90-day window
(for the 1 M profile try `--min-item-support 40 --min-pair-support 15`). The pipeline prints billed bytes and slot-ms per step.

Cost guard: set a project or dataset-level maximum bytes billed, and always run `--dry-run` first on large data.

## 5. Looker
1. Create a BigQuery connection in Looker named `basketpulse_bigquery` (or choose your own and override the constant).
2. Create a LookML project and import this repository (or push it to a Git repo Looker can read).
3. In the project's `manifest.lkml`, set `PROJECT_ID` (required) and `DATASET` (if you changed it).
4. Run Looker's LookML validator, then open the **Executive Overview**, **Store Performance** and **Basket Affinity** dashboards from the LookML dashboards folder.
5. For the Store Performance default filter, make sure the store name exists in your data (the dashboard defaults to `BasketPulse Southeast #001`; change it if your generated store 1 is in another region).

## 6. Refresh schedule
Run `python scripts/run_sql.py` from Cloud Scheduler + Cloud Run Job, or as scheduled queries per file, in the pipeline order printed in
`scripts/run_sql.py`. Marts and `fct_transactions` daily; the BQML files weekly (the `weekly_ml` datagroup matches that cadence).

## 7. Benchmarks (optional)
```bash
make bench PROJECT=$PROJECT      # writes docs/BENCHMARKS_BIGQUERY.md and benchmarks/results/*.json
```

## 8. Tear down
```bash
bq rm -r -f -d $PROJECT:basketpulse && gcloud storage rm -r gs://$BUCKET
```
