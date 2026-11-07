-- Q1: one store, trailing 28 days: sales, margin, baskets (operational store-manager query)
SELECT COUNT(DISTINCT transaction_id) AS baskets,
       SUM(quantity * unit_price - discount_amount) AS net_sales,
       SUM(quantity * (unit_price - unit_cost) - discount_amount) AS margin
FROM `{{table}}`
WHERE store_id = {{store_id}} AND transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 28 DAY);
