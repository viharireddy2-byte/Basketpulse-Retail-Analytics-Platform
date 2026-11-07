-- Evaluate only archived future predictions after actuals arrive.
-- Coverage is explicit; absent series-days are not silently scored as zero.
CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.forecast_evaluation`
CLUSTER BY store_id,category AS
SELECT h.issued_date,h.store_id,h.category,
 COUNT(*) AS predicted_points, COUNT(a.units) AS evaluated_points,
 COUNTIF(a.units IS NULL) AS missing_actual_points,
 AVG(ABS(h.forecast_units-a.units)) AS mae,
 SAFE_DIVIDE(SUM(ABS(h.forecast_units-a.units)),SUM(ABS(a.units))) AS wape,
 AVG(IF(a.units IS NULL,NULL,IF(a.units BETWEEN h.lower_units AND h.upper_units,1.0,0.0))) AS interval_coverage,
 CURRENT_TIMESTAMP() AS evaluated_at
FROM `{{project}}.{{dataset}}.forecast_history` h
LEFT JOIN `{{project}}.{{dataset}}.agg_daily_store_category` a
 ON h.forecast_date=a.transaction_date AND h.store_id=a.store_id AND h.category=a.category
WHERE h.forecast_date < CURRENT_DATE('UTC')
GROUP BY 1,2,3;
