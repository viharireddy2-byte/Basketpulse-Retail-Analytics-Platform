"""Opt-in warehouse operations. Run python -m operations.runner --help."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import uuid
from scripts.run_sql import BUILD, ROOT, render
from operations.sql import incremental, source_checks


def validate(project, dataset):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:.-]*', project):
        raise ValueError('invalid project identifier')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', dataset):
        raise ValueError('invalid dataset identifier')


def submit(client, sql, config, job_id, sleep=time.sleep):
    """Retry ambiguous submission with the SAME job id; never rerun a failed job."""
    from google.api_core.exceptions import Conflict, ServiceUnavailable, TooManyRequests, GatewayTimeout
    for attempt in range(3):
        try:
            return client.query(sql, job_config=config, job_id=job_id)
        except Conflict:
            return client.get_job(job_id)
        except (ServiceUnavailable, TooManyRequests, GatewayTimeout):
            if attempt == 2:
                raise
            sleep(2 ** attempt)


def execute(client, steps, config_factory, emit, run_id, dry_run=False):
    for name, sql in steps:
        job_id = 'bp_' + run_id + '_' + hashlib.sha256(name.encode()).hexdigest()[:12]
        started = time.monotonic()
        emit(dict(event='step_started', run_id=run_id, step=name, job_id=job_id))
        try:
            cfg = config_factory()
            # BigQuery dry runs are not persisted jobs; the SDK manages their IDs.
            job = client.query(sql, job_config=cfg) if dry_run else submit(client, sql, cfg, job_id)
            if not dry_run:
                job.result()  # Fail closed: no automatic replay of a failed script.
            emit(dict(event='step_estimated' if dry_run else 'step_succeeded', run_id=run_id,
                      step=name, job_id=getattr(job, 'job_id', job_id),
                      duration_seconds=round(time.monotonic()-started,3),
                      bytes_processed=getattr(job,'total_bytes_processed',None),
                      bytes_billed=getattr(job,'total_bytes_billed',None),
                      slot_ms=getattr(job,'slot_millis',None)))
        except Exception as exc:
            emit(dict(event='step_failed', run_id=run_id, step=name, job_id=job_id,
                      error_type=type(exc).__name__))
            raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', required=True)
    ap.add_argument('--dataset', default='basketpulse')
    ap.add_argument('--location', default='US')
    ap.add_argument('--action', choices=['check','incremental','refresh','capture-forecast','evaluate-forecast'], required=True)
    ap.add_argument('--start-date', type=date.fromisoformat)
    ap.add_argument('--end-date', type=date.fromisoformat)
    ap.add_argument('--maximum-bytes-billed', type=int, default=10_000_000_000)
    ap.add_argument('--job-timeout-ms', type=int, default=3_600_000)
    ap.add_argument('--min-item-support', type=int, default=300)
    ap.add_argument('--min-pair-support', type=int, default=100)
    ap.add_argument('--render-only', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--log', type=Path)
    a = ap.parse_args()
    validate(a.project, a.dataset)
    if min(a.maximum_bytes_billed,a.job_timeout_ms,a.min_item_support,a.min_pair_support) <= 0:
        ap.error('limits and support thresholds must be positive')
    if a.action in ('check','incremental','refresh'):
        if not a.start_date or not a.end_date or a.start_date > a.end_date:
            ap.error('a valid inclusive --start-date and --end-date are required')
    params = vars(a)
    if a.action == 'check':
        steps = [('quality', source_checks(params))]
    elif a.action in ('incremental','refresh'):
        steps = [('incremental_fact', incremental(params))]
        if a.action == 'refresh':
            steps += [(f, render(ROOT / f, params)) for f in BUILD[1:]]
    else:
        name = a.action.replace('-','_')
        steps = [(name, render(ROOT / 'operations/templates' / (name + '.sql'), params))]
    if a.render_only:
        for name, sql in steps:
            print(f'-- {name}\n{sql}')
        return
    from google.cloud import bigquery
    client = bigquery.Client(project=a.project, location=a.location)
    run_id = uuid.uuid4().hex
    def config():
        return bigquery.QueryJobConfig(
            dry_run=a.dry_run, use_query_cache=False,
            maximum_bytes_billed=a.maximum_bytes_billed, job_timeout_ms=a.job_timeout_ms,
            labels={'application':'basketpulse','run_id':run_id},
            query_parameters=[bigquery.ScalarQueryParameter('start_date','DATE',a.start_date),
                              bigquery.ScalarQueryParameter('end_date','DATE',a.end_date)])
    def emit(record):
        record['timestamp'] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(record)
        print(line, flush=True)
        if a.log:
            with a.log.open('a') as out:
                out.write(line + '\n')
    execute(client, steps, config, emit, run_id, a.dry_run)


if __name__ == '__main__':
    main()
