-- Peer-group stores by size, throughput and mix so store managers are compared like-for-like.
CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.store_features` AS
WITH recent AS (SELECT MAX(transaction_date) AS d FROM `{{project}}.{{dataset}}.agg_daily_store_category`)
SELECT s.store_id, s.sq_ft,
  SUM(a.net_sales) / (365 / 7)                                            AS weekly_sales,
  SAFE_DIVIDE(SUM(a.net_sales), SUM(a.transactions))                       AS avg_basket_value,
  SAFE_DIVIDE(SUM(a.gross_margin), SUM(a.net_sales))                       AS margin_rate,
  SAFE_DIVIDE(SUM(IF(a.category = 'Fresh Produce', a.net_sales, 0)), SUM(a.net_sales)) AS fresh_share,
  SAFE_DIVIDE(SUM(a.net_sales), s.sq_ft)                                   AS sales_per_sq_ft
FROM `{{project}}.{{dataset}}.agg_daily_store_category` AS a
JOIN `{{project}}.{{dataset}}.dim_stores` AS s USING (store_id), recent
WHERE a.transaction_date > DATE_SUB(recent.d, INTERVAL 365 DAY)
GROUP BY s.store_id, s.sq_ft;

CREATE OR REPLACE MODEL `{{project}}.{{dataset}}.store_peer_kmeans`
OPTIONS (model_type = 'kmeans', num_clusters = 5, standardize_features = TRUE, kmeans_init_method = 'KMEANS++')
AS SELECT sq_ft, weekly_sales, avg_basket_value, margin_rate, fresh_share FROM `{{project}}.{{dataset}}.store_features`;

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.store_peer_groups` AS
SELECT f.store_id, CONCAT('Peer group ', CAST(p.CENTROID_ID AS STRING)) AS peer_group,
       f.weekly_sales, f.avg_basket_value, f.margin_rate, f.sales_per_sq_ft,
       PERCENT_RANK() OVER (PARTITION BY p.CENTROID_ID ORDER BY f.sales_per_sq_ft) AS peer_percentile
FROM ML.PREDICT(MODEL `{{project}}.{{dataset}}.store_peer_kmeans`,
                (SELECT * FROM `{{project}}.{{dataset}}.store_features`)) AS p
JOIN `{{project}}.{{dataset}}.store_features` AS f USING (store_id);
