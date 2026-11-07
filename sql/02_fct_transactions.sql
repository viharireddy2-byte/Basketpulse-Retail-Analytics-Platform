-- BasketPulse :: 02 nested fact table.
-- One row per basket; line items are an ARRAY<STRUCT>. Partitioned by day, clustered by the two
-- columns every store/customer drill-down filters on. Basket rollups are pre-computed so the
-- dashboards rarely need to UNNEST.
CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.fct_transactions`
PARTITION BY transaction_date
CLUSTER BY store_id, customer_id, channel_id
OPTIONS (description = 'Nested basket-level fact table. Grain: 1 row per transaction.')
AS
SELECT
  transaction_id,
  ANY_VALUE(transaction_ts)   AS transaction_ts,
  ANY_VALUE(transaction_date) AS transaction_date,
  ANY_VALUE(store_id)         AS store_id,
  ANY_VALUE(customer_id)      AS customer_id,
  ANY_VALUE(channel_id)       AS channel_id,
  ARRAY_AGG(STRUCT(
      line_number, product_id, quantity, unit_price, unit_cost, discount_amount,
      ROUND(quantity * unit_price - discount_amount, 2)                AS net_amount,
      ROUND(quantity * unit_price - discount_amount - quantity * unit_cost, 2) AS margin_amount)
    ORDER BY line_number)       AS line_items,
  COUNT(*)                      AS basket_lines,
  SUM(quantity)                 AS basket_units,
  ROUND(SUM(quantity * unit_price - discount_amount), 2)                      AS basket_net_amount,
  ROUND(SUM(quantity * unit_price - discount_amount - quantity * unit_cost), 2) AS basket_margin_amount
FROM `{{project}}.{{dataset}}.stg_line_items`
GROUP BY transaction_id;
