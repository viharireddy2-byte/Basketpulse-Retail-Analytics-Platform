-- Customer behavioural features over a trailing 365-day window ending at the latest loaded day.
DECLARE as_of DATE DEFAULT (SELECT MAX(transaction_date) FROM `{{project}}.{{dataset}}.fct_transactions`);

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.customer_features`
CLUSTER BY customer_id
AS
WITH cat_breadth AS (
  SELECT t.customer_id, COUNT(DISTINCT p.category) AS distinct_categories
  FROM `{{project}}.{{dataset}}.fct_transactions` AS t, UNNEST(t.line_items) AS li
  JOIN `{{project}}.{{dataset}}.dim_products` AS p ON li.product_id = p.product_id
  WHERE t.transaction_date > DATE_SUB(as_of, INTERVAL 365 DAY) AND t.customer_id IS NOT NULL
  GROUP BY 1
), base AS (
  SELECT
    customer_id,
    MIN(transaction_date)                          AS first_purchase_date,
    MAX(transaction_date)                          AS last_purchase_date,
    COUNT(*)                                       AS frequency,
    SUM(basket_net_amount)                         AS monetary,
    SAFE_DIVIDE(SUM(basket_net_amount), COUNT(*))  AS avg_basket_value,
    SAFE_DIVIDE(SUM(basket_margin_amount), SUM(basket_net_amount)) AS margin_rate
  FROM `{{project}}.{{dataset}}.fct_transactions`
  WHERE transaction_date > DATE_SUB(as_of, INTERVAL 365 DAY) AND customer_id IS NOT NULL
  GROUP BY customer_id
)
SELECT b.*, DATE_DIFF(as_of, b.last_purchase_date, DAY) AS recency_days, c.distinct_categories, as_of AS as_of_date
FROM base AS b JOIN cat_breadth AS c USING (customer_id);
