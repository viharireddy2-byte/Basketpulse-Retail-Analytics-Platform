-- Pre-aggregated store x category x day cube: serves ~80% of dashboard tiles without touching the fact table.
CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.agg_daily_store_category`
PARTITION BY transaction_date
CLUSTER BY store_id, category
AS
SELECT
  t.transaction_date, t.store_id, p.category,
  COUNT(DISTINCT t.transaction_id)                 AS transactions,
  SUM(li.quantity)                                 AS units,
  SUM(li.net_amount)                               AS net_sales,
  SUM(li.margin_amount)                            AS gross_margin
FROM `{{project}}.{{dataset}}.fct_transactions` AS t,
     UNNEST(t.line_items) AS li
JOIN `{{project}}.{{dataset}}.dim_products` AS p ON li.product_id = p.product_id
GROUP BY 1, 2, 3;
