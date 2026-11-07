SELECT COUNT(*) AS baskets, SUM(basket_net_amount) AS net_sales, SUM(basket_margin_amount) AS margin
FROM `{{table}}`
WHERE store_id = {{store_id}} AND transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 28 DAY);
