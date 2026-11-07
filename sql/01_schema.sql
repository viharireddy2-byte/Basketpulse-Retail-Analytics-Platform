-- BasketPulse :: 01 schema. Rendered by scripts/run_sql.py ({{project}}, {{dataset}}, {{location}}).
CREATE SCHEMA IF NOT EXISTS `{{project}}.{{dataset}}` OPTIONS (location = '{{location}}');

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.dim_stores` (
  store_id INT64 NOT NULL, store_name STRING, region STRING, state STRING,
  latitude FLOAT64, longitude FLOAT64, format STRING, sq_ft INT64, opened_date DATE
) CLUSTER BY region, format;

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.dim_products` (
  product_id INT64 NOT NULL, product_name STRING, category STRING, subcategory STRING,
  brand STRING, unit_price NUMERIC, unit_cost NUMERIC
) CLUSTER BY category;

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.dim_customers` (
  customer_id INT64 NOT NULL, signup_date DATE, loyalty_tier STRING,
  acquisition_channel STRING, home_store_id INT64
) CLUSTER BY loyalty_tier;

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.dim_channels` (channel_id INT64 NOT NULL, channel_name STRING);

-- Staging table for flat line items (one row per basket line), loaded from GCS by scripts/load_data.py.
CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.stg_line_items` (
  transaction_id INT64 NOT NULL, line_number INT64, transaction_ts TIMESTAMP, transaction_date DATE,
  store_id INT64, customer_id INT64, channel_id INT64, product_id INT64,
  quantity INT64, unit_price NUMERIC, unit_cost NUMERIC, discount_amount NUMERIC
) PARTITION BY transaction_date
  OPTIONS (description = 'Raw flat line items; source for fct_transactions');
