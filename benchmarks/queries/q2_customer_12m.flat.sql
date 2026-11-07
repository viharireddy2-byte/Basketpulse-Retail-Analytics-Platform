-- Q2: single-customer 12-month history (CRM lookup)
SELECT transaction_date, COUNT(DISTINCT transaction_id) AS baskets,
       SUM(quantity * unit_price - discount_amount) AS spend
FROM `{{table}}`
WHERE customer_id = {{customer_id}} AND transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 365 DAY)
GROUP BY transaction_date ORDER BY transaction_date;
