"""Parameterized BigQuery scripts sharing the legacy fact transformation."""
from scripts.run_sql import ROOT, render


def source_checks(params):
    p = f"`{params['project']}.{params['dataset']}"
    return f"""
CREATE TEMP TABLE source_window AS
SELECT * FROM {p}.stg_line_items`
WHERE transaction_date BETWEEN @start_date AND @end_date;
ASSERT (SELECT COUNT(*) > 0 FROM source_window) AS 'empty source window';
ASSERT NOT EXISTS (
 SELECT transaction_id, line_number FROM source_window
 GROUP BY 1,2 HAVING COUNT(*) != 1
) AS 'duplicate transaction line';
ASSERT NOT EXISTS (
 SELECT 1 FROM source_window WHERE transaction_id IS NULL OR line_number IS NULL
 OR transaction_ts IS NULL OR transaction_date IS NULL OR line_number < 1
 OR DATE(transaction_ts) != transaction_date OR quantity IS NULL OR quantity <= 0
 OR unit_price IS NULL OR unit_price < 0 OR unit_cost IS NULL OR unit_cost < 0
 OR discount_amount IS NULL OR discount_amount < 0 OR discount_amount > quantity * unit_price
) AS 'invalid source values';
ASSERT NOT EXISTS (
 SELECT transaction_id FROM source_window GROUP BY 1
 HAVING COUNT(DISTINCT TO_JSON_STRING(STRUCT(transaction_ts,transaction_date,store_id,customer_id,channel_id))) > 1
) AS 'inconsistent basket headers';
-- IDs must not straddle dates, including outside the replay window.
ASSERT NOT EXISTS (
 SELECT 1 FROM {p}.stg_line_items` s JOIN
 (SELECT DISTINCT transaction_id FROM source_window) w USING(transaction_id)
 WHERE s.transaction_date IS NULL OR s.transaction_date NOT BETWEEN @start_date AND @end_date
) AS 'basket spans replay boundary';
""" + "\n".join(
        f"""ASSERT NOT EXISTS (SELECT {key} FROM {p}.{table}` GROUP BY 1
 HAVING {key} IS NULL OR COUNT(*) != 1) AS 'invalid {table} key';
ASSERT NOT EXISTS (SELECT 1 FROM source_window s LEFT JOIN {p}.{table}` d
 ON s.{key}=d.{key} WHERE {'s.' + key + ' IS NOT NULL AND ' if key == 'customer_id' else ''}d.{key} IS NULL)
 AS 'orphan {key}';"""
        for table, key in [('dim_stores','store_id'), ('dim_products','product_id'),
                           ('dim_customers','customer_id'), ('dim_channels','channel_id')])


def incremental(params):
    legacy = render(ROOT / 'sql/02_fct_transactions.sql', params)
    select = legacy[legacy.index('\nSELECT\n'):]
    select = select.replace(f"`{params['project']}.{params['dataset']}.stg_line_items`", 'source_window')
    table = f"`{params['project']}.{params['dataset']}.fct_transactions`"
    return source_checks(params) + '\nCREATE TEMP TABLE candidate AS\n' + select + f"""
-- A BigQuery transaction makes delete + insert and reconciliation atomic.
BEGIN TRANSACTION;
ASSERT NOT EXISTS (
 SELECT 1 FROM {table} t JOIN candidate c USING(transaction_id)
 WHERE t.transaction_date NOT BETWEEN @start_date AND @end_date
) AS 'existing basket outside replay window';
DELETE FROM {table} WHERE transaction_date BETWEEN @start_date AND @end_date;
INSERT INTO {table} SELECT * FROM candidate;
ASSERT (SELECT COUNT(*) FROM source_window) =
 (SELECT COALESCE(SUM(basket_lines),0) FROM {table}
 WHERE transaction_date BETWEEN @start_date AND @end_date) AS 'line count reconciliation';
ASSERT (SELECT ROUND(SUM(quantity * unit_price - discount_amount),2) FROM source_window) =
 (SELECT SUM(basket_net_amount) FROM {table}
 WHERE transaction_date BETWEEN @start_date AND @end_date) AS 'sales reconciliation';
ASSERT (SELECT COUNT(DISTINCT transaction_id) FROM source_window) =
 (SELECT COUNT(*) FROM {table} WHERE transaction_date BETWEEN @start_date AND @end_date)
 AS 'basket count reconciliation';
COMMIT TRANSACTION;
"""
