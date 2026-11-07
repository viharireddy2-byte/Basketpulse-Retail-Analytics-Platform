-- Q3: group-level monthly sales by region over 13 months (executive trend; large scan)
SELECT DATE_TRUNC(f.transaction_date, MONTH) AS month, s.region,
       SUM(f.quantity * f.unit_price - f.discount_amount) AS net_sales
FROM `{{table}}` AS f JOIN `{{dataset}}.dim_stores` AS s USING (store_id)
WHERE f.transaction_date > DATE_SUB(DATE '{{as_of}}', INTERVAL 395 DAY)
GROUP BY 1, 2 ORDER BY 1, 2;
