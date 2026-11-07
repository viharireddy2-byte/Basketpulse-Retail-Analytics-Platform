-- Q4: category margin for the last 7 days (needs line-level detail + product dimension)
SELECT p.category, SUM(f.quantity * f.unit_price - f.discount_amount) AS net_sales,
       SUM(f.quantity * (f.unit_price - f.unit_cost) - f.discount_amount) AS margin
FROM `{{table}}` AS f JOIN `{{dataset}}.dim_products` AS p USING (product_id)
WHERE f.transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 7 DAY)
GROUP BY p.category ORDER BY margin DESC;
