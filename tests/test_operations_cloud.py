"""Opt-in billable BigQuery tests; always use a disposable, unique dataset.

BASKETPULSE_TEST_PROJECT=my-project python -m pytest tests/test_operations_cloud.py -q
Requires ADC credentials and requirements-gcp.txt. Never targets a user dataset.
"""
from datetime import date
import os
import uuid

import pytest

from operations.sql import incremental
from scripts.run_sql import ROOT, render

pytestmark = pytest.mark.skipif(not os.getenv('BASKETPULSE_TEST_PROJECT'), reason='BigQuery project not configured')


def test_atomic_replay_and_bad_source_preserves_published_fact():
    from google.cloud import bigquery
    project = os.environ['BASKETPULSE_TEST_PROJECT']
    dataset = 'bp_test_' + uuid.uuid4().hex
    location = os.getenv('BASKETPULSE_TEST_LOCATION','US')
    client = bigquery.Client(project=project,location=location)
    params = dict(project=project,dataset=dataset,location=location)
    prefix = f'`{project}.{dataset}'
    def query(sql,parameters=()):
        return list(client.query(sql,job_config=bigquery.QueryJobConfig(
            maximum_bytes_billed=1_000_000_000,query_parameters=list(parameters))).result())
    bounds = [bigquery.ScalarQueryParameter('start_date','DATE',date(2026,1,1)),
              bigquery.ScalarQueryParameter('end_date','DATE',date(2026,1,1))]
    try:
        query(render(ROOT/'sql/01_schema.sql',params))
        query(f'''INSERT INTO {prefix}.dim_stores`(store_id) VALUES(1);
        INSERT INTO {prefix}.dim_products`(product_id) VALUES(1);
        INSERT INTO {prefix}.dim_channels`(channel_id) VALUES(1);
        INSERT INTO {prefix}.stg_line_items` VALUES
        (1,1,TIMESTAMP '2026-01-01 12:00:00+00',DATE '2026-01-01',1,NULL,1,1,2,10,6,1),
        (2,1,TIMESTAMP '2026-01-02 12:00:00+00',DATE '2026-01-02',1,NULL,1,1,1,10,6,0);''')
        query(render(ROOT/'sql/02_fct_transactions.sql',params))
        query(incremental(params),bounds)
        query(incremental(params),bounds)
        rows = query(f'SELECT transaction_id,basket_net_amount FROM {prefix}.fct_transactions` ORDER BY 1')
        assert [(r.transaction_id,float(r.basket_net_amount)) for r in rows] == [(1,19),(2,10)]
        query(f'UPDATE {prefix}.stg_line_items` SET quantity=0 WHERE transaction_id=1')
        with pytest.raises(Exception,match='invalid source values'):
            query(incremental(params),bounds)
        assert query(f'SELECT SUM(basket_net_amount) n FROM {prefix}.fct_transactions`')[0].n == 29
        # Force reconciliation failure INSIDE the transaction, after DELETE + INSERT.
        # Changing candidate only simulates a faulty transformation.
        query(f'UPDATE {prefix}.stg_line_items` SET quantity=2 WHERE transaction_id=1')
        broken = incremental(params).replace('BEGIN TRANSACTION;',
                  'UPDATE candidate SET basket_lines=basket_lines+1;\nBEGIN TRANSACTION;')
        with pytest.raises(Exception,match='line count reconciliation'):
            query(broken,bounds)
        assert query(f'SELECT SUM(basket_net_amount) n FROM {prefix}.fct_transactions`')[0].n == 29
    finally:
        client.delete_dataset(f'{project}.{dataset}',delete_contents=True,not_found_ok=True)
