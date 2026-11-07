SELECT p.category, SUM(li.net_amount) AS net_sales, SUM(li.margin_amount) AS margin
FROM `{{table}}` AS f, UNNEST(f.line_items) AS li
JOIN `{{dataset}}.dim_products` AS p ON li.product_id = p.product_id
WHERE f.transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 7 DAY)
GROUP BY p.category ORDER BY margin DESC;
