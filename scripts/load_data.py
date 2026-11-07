"""Upload generated data to GCS and load it into BigQuery.

    python scripts/load_data.py --project my-proj --bucket my-bucket --data data/xl

Requires: pip install google-cloud-bigquery google-cloud-storage
"""
from __future__ import annotations

import argparse
from pathlib import Path


def upload_dir(bucket, local: Path, prefix: str) -> int:
    from concurrent.futures import ThreadPoolExecutor
    files = [p for p in local.rglob("*") if p.is_file()]
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(lambda p: bucket.blob(f"{prefix}/{p.relative_to(local).as_posix()}").upload_from_filename(str(p)), files))
    return len(files)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--dataset", default="basketpulse")
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--prefix", default="basketpulse")
    ap.add_argument("--skip-upload", action="store_true")
    a = ap.parse_args()

    from google.cloud import bigquery, storage
    bq = bigquery.Client(project=a.project)
    if not a.skip_upload:
        n = upload_dir(storage.Client(project=a.project).bucket(a.bucket), a.data, a.prefix)
        print(f"uploaded {n} files to gs://{a.bucket}/{a.prefix}/")
    base = f"gs://{a.bucket}/{a.prefix}"
    dims = ["dim_stores", "dim_products", "dim_customers", "dim_channels"]
    for t in dims:
        job = bq.load_table_from_uri(
            f"{base}/{t}.csv", f"{a.project}.{a.dataset}.{t}",
            job_config=bigquery.LoadJobConfig(source_format="CSV", skip_leading_rows=1,
                                              write_disposition="WRITE_TRUNCATE"))
        job.result(); print(f"loaded {t}: {job.output_rows:,} rows")
    # Files carry an explicit transaction_date column, so no Hive-partition discovery is required.
    # The destination table (created by sql/01_schema.sql) is day-partitioned; BigQuery routes rows itself.
    job = bq.load_table_from_uri(
        f"{base}/line_items/*", f"{a.project}.{a.dataset}.stg_line_items",
        job_config=bigquery.LoadJobConfig(source_format="CSV", skip_leading_rows=1,
                                          write_disposition="WRITE_TRUNCATE"))
    job.result(); print(f"loaded stg_line_items: {job.output_rows:,} rows")


if __name__ == "__main__":
    main()
