-- BQML k-means customer segmentation (k = 4) + dynamic, rank-based segment naming.
CREATE OR REPLACE MODEL `{{project}}.{{dataset}}.customer_segments_kmeans`
OPTIONS (model_type = 'kmeans', num_clusters = 4, kmeans_init_method = 'KMEANS++',
         standardize_features = TRUE, max_iterations = 30, early_stop = TRUE)
AS
SELECT recency_days, frequency, monetary, avg_basket_value, margin_rate, distinct_categories
FROM `{{project}}.{{dataset}}.customer_features`;

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.customer_segments`
CLUSTER BY segment
AS
WITH scored AS (
  SELECT f.customer_id, f.recency_days, f.frequency, f.monetary, f.avg_basket_value, f.distinct_categories,
         f.last_purchase_date, f.first_purchase_date, f.as_of_date, p.CENTROID_ID AS centroid_id
  FROM ML.PREDICT(MODEL `{{project}}.{{dataset}}.customer_segments_kmeans`,
                  (SELECT * FROM `{{project}}.{{dataset}}.customer_features`)) AS p
  JOIN `{{project}}.{{dataset}}.customer_features` AS f USING (customer_id)
), centroid_rank AS (   -- names follow behaviour, not arbitrary centroid ids
  SELECT centroid_id,
         RANK() OVER (ORDER BY AVG(monetary) DESC) AS value_rank
  FROM scored GROUP BY centroid_id
)
SELECT s.*,
  CASE r.value_rank WHEN 1 THEN 'Champions' WHEN 2 THEN 'Loyal Regulars'
                    WHEN 3 THEN 'Casual Shoppers' ELSE 'Lapsing / Low Value' END AS segment
FROM scored AS s JOIN centroid_rank AS r USING (centroid_id);
