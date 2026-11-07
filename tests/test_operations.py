"""Exercise quality predicates on real SQL rows and runner failure behavior.

DuckDB executes translated portable predicates, not BigQuery DDL/transactions.
Live BigQuery integration is covered separately by test_operations_cloud.py.
"""
import re
from types import SimpleNamespace
import sys
import types

import duckdb
import pytest

from operations.sql import source_checks, incremental
from operations.runner import execute, submit, validate
from scripts.run_sql import ROOT, render

PARAMS = dict(project='test-project',dataset='test_data',location='US',
              min_item_support=300,min_pair_support=100)


def portable(sql):
    sql = re.sub(r'`test-project.test_data\.(\w+)`',r'\1',sql)
    sql = sql.replace('@start_date',"DATE '2026-01-01'").replace('@end_date',"DATE '2026-01-01'")
    return re.sub(r'TO_JSON_STRING\(STRUCT\((.*?)\)\)',r'to_json(row(\1))',sql)


def check_source(db):
    db.execute('DROP TABLE IF EXISTS source_window')
    script = portable(source_checks(PARAMS))
    for statement in script.split(';'):
        statement = re.sub(r'--[^\n]*','',statement).strip()
        if not statement:
            continue
        if statement.startswith('ASSERT '):
            expr, label = statement[7:].rsplit(' AS ',1)
            if not db.execute('SELECT ' + expr).fetchone()[0]:
                raise ValueError(label)
        else:
            db.execute(statement)


@pytest.fixture
def db():
    db = duckdb.connect()
    db.execute('''CREATE TABLE stg_line_items(transaction_id BIGINT,line_number BIGINT,
    transaction_ts TIMESTAMP,transaction_date DATE,store_id BIGINT,customer_id BIGINT,
    channel_id BIGINT,product_id BIGINT,quantity BIGINT,unit_price DECIMAL(18,2),
    unit_cost DECIMAL(18,2),discount_amount DECIMAL(18,2));
    INSERT INTO stg_line_items VALUES
    (1,1,'2026-01-01 12:00:00','2026-01-01',1,NULL,1,1,2,10,6,1),
    (1,2,'2026-01-01 12:00:00','2026-01-01',1,NULL,1,2,1,5,3,0);''')
    for table,key in [('dim_stores','store_id'),('dim_products','product_id'),
                      ('dim_customers','customer_id'),('dim_channels','channel_id')]:
        db.execute(f'CREATE TABLE {table} ({key} BIGINT)')
        db.execute(f'INSERT INTO {table} VALUES (1),(2)')
    yield db
    db.close()


def test_quality_accepts_valid_basket_and_anonymous_customer(db):
    check_source(db)


@pytest.mark.parametrize('mutation,message',[
 ('INSERT INTO stg_line_items SELECT * FROM stg_line_items LIMIT 1','duplicate transaction line'),
 ('UPDATE stg_line_items SET product_id=999','orphan product_id'),
 ('UPDATE stg_line_items SET store_id=NULL','orphan store_id'),
 ('UPDATE stg_line_items SET customer_id=999','orphan customer_id'),
 ('UPDATE stg_line_items SET quantity=0','invalid source values'),
 ('UPDATE stg_line_items SET discount_amount=100','invalid source values'),
 ('UPDATE stg_line_items SET unit_price=NULL','invalid source values'),
 ("UPDATE stg_line_items SET transaction_ts='2026-01-02'",'invalid source values'),
 ('UPDATE stg_line_items SET store_id=2 WHERE line_number=2','inconsistent basket headers'),
 ("INSERT INTO stg_line_items SELECT transaction_id,3,'2026-01-02','2026-01-02',store_id,customer_id,channel_id,product_id,quantity,unit_price,unit_cost,discount_amount FROM stg_line_items LIMIT 1",'basket spans replay boundary'),
 ('INSERT INTO dim_products VALUES(1)','invalid dim_products key'),
 ('DELETE FROM stg_line_items','empty source window'),
])
def test_quality_rejects_corruption(db,mutation,message):
    db.execute(mutation)
    with pytest.raises(ValueError,match=message):
        check_source(db)


def test_execution_stops_and_logs_failure(monkeypatch):
    calls, events = [], []
    def fake_submit(client,sql,cfg,job_id):
        calls.append(sql)
        return SimpleNamespace(result=lambda: (_ for _ in ()).throw(ValueError('bad quality')))
    monkeypatch.setattr('operations.runner.submit',fake_submit)
    with pytest.raises(ValueError):
        execute(None,[('quality','bad'),('build','must not run')],lambda:None,events.append,'run1')
    assert calls == ['bad']
    assert [e['event'] for e in events] == ['step_started','step_failed']
    assert events[-1]['error_type'] == 'ValueError'


def test_execution_records_job_metrics(monkeypatch):
    events = []
    job = SimpleNamespace(result=lambda:None,job_id='server_job',total_bytes_processed=123,
                          total_bytes_billed=456,slot_millis=789)
    monkeypatch.setattr('operations.runner.submit',lambda *args: job)
    execute(None,[('quality','sql')],lambda:None,events.append,'run1')
    assert events[-1]['bytes_billed'] == 456
    assert events[-1]['slot_ms'] == 789


@pytest.fixture
def api_exceptions(monkeypatch):
    # No GCP dependency needed to test the submission state machine locally.
    module = types.ModuleType('google.api_core.exceptions')
    for name in ['Conflict','ServiceUnavailable','TooManyRequests','GatewayTimeout']:
        setattr(module,name,type(name,(Exception,),{}))
    monkeypatch.setitem(sys.modules,'google.api_core.exceptions',module)
    return module


def test_ambiguous_submission_uses_same_job_id(api_exceptions):
    ids, sleeps = [], []
    class Client:
        def query(self,sql,job_config,job_id):
            ids.append(job_id)
            if len(ids) == 1:
                raise api_exceptions.ServiceUnavailable()
            raise api_exceptions.Conflict()
        def get_job(self,job_id):
            assert job_id == ids[0]
            return 'existing_job'
    assert submit(Client(),'sql',None,'stable-id',sleeps.append) == 'existing_job'
    assert ids == ['stable-id','stable-id'] and sleeps == [1]


def test_retries_are_bounded(api_exceptions):
    attempts = []
    class Client:
        def query(self,*args,**kwargs):
            attempts.append(1)
            raise api_exceptions.TooManyRequests()
    with pytest.raises(api_exceptions.TooManyRequests):
        submit(Client(),'sql',None,'id',lambda _:None)
    assert len(attempts) == 3


@pytest.mark.parametrize('project,dataset',[('p`; DELETE','safe'),('p','d.x'),('p',''),('p',"d'bad")])
def test_invalid_identifiers_are_rejected(project,dataset):
    with pytest.raises(ValueError):
        validate(project,dataset)


def test_templates_render_and_legacy_fact_select_is_shared():
    sql = incremental(PARAMS)
    assert 'BEGIN TRANSACTION;' in sql and 'COMMIT TRANSACTION;' in sql
    assert 'CREATE OR REPLACE TABLE' not in sql
    assert sql.index('duplicate transaction line') < sql.index('DELETE FROM')
    assert 'ARRAY_AGG(STRUCT(' in sql and 'FROM source_window' in sql
    for path in (ROOT/'operations/templates').glob('*.sql'):
        assert '{{' not in render(path,PARAMS)


def test_forecast_metrics_handle_zero_actual_and_missing_series(db):
    db.execute('''CREATE TABLE forecast_history(issued_date DATE,forecast_date DATE,store_id BIGINT,
    category VARCHAR,forecast_units DOUBLE,lower_units DOUBLE,upper_units DOUBLE);
    INSERT INTO forecast_history VALUES
    ('2026-01-01','2026-01-02',1,'a',12,5,15),
    ('2026-01-01','2026-01-03',1,'a',8,5,15),
    ('2026-01-01','2026-01-04',1,'a',10,5,15),
    ('2026-01-01','2026-01-02',2,'b',5,1,10);
    CREATE TABLE agg_daily_store_category(transaction_date DATE,store_id BIGINT,category VARCHAR,units BIGINT);
    INSERT INTO agg_daily_store_category VALUES('2026-01-02',1,'a',10),('2026-01-03',1,'a',0),('2026-01-02',2,'b',0);''')
    sql = render(ROOT/'operations/templates/evaluate_forecast.sql',PARAMS)
    sql = portable(sql[sql.index('\nSELECT'):])
    sql = sql.replace("CURRENT_DATE('UTC')", "DATE '2026-02-01'").replace("CURRENT_TIMESTAMP()", "CURRENT_TIMESTAMP")
    sql = sql.replace('SAFE_DIVIDE(SUM(ABS(h.forecast_units-a.units)),SUM(ABS(a.units)))',
                      'SUM(ABS(h.forecast_units-a.units))/NULLIF(SUM(ABS(a.units)),0)')
    rows = {row[1]:row for row in db.execute(sql).fetchall()}
    assert rows[1][3:6] == (3,2,1)
    assert rows[1][6:9] == pytest.approx((5,1,0.5))
    assert rows[2][7] is None
