SELECT transaction_date, COUNT(*) AS baskets, SUM(basket_net_amount) AS spend
FROM `{{table}}`
WHERE customer_id = {{customer_id}} AND transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 365 DAY)
GROUP BY transaction_date ORDER BY transaction_date;
