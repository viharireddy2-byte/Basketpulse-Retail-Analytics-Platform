-- Preserve predictions BEFORE observing their target dates. Repeated captures
-- on the same day retain the first prediction; no in-place rewriting of history.
CREATE TABLE IF NOT EXISTS `{{project}}.{{dataset}}.forecast_history` (
  issued_date DATE, forecast_date DATE, store_id INT64, category STRING,
  forecast_units FLOAT64, lower_units FLOAT64, upper_units FLOAT64,
  captured_at TIMESTAMP
) PARTITION BY issued_date CLUSTER BY store_id, category;
ASSERT NOT EXISTS (
 SELECT forecast_date,store_id,category FROM `{{project}}.{{dataset}}.demand_forecast`
 GROUP BY 1,2,3 HAVING COUNT(*) > 1
) AS 'duplicate forecast grain';
MERGE `{{project}}.{{dataset}}.forecast_history` t
USING (SELECT CURRENT_DATE('UTC') issued_date, f.*, CURRENT_TIMESTAMP() captured_at
 FROM `{{project}}.{{dataset}}.demand_forecast` f
 WHERE forecast_date > CURRENT_DATE('UTC')) s
ON t.issued_date=s.issued_date AND t.forecast_date=s.forecast_date
 AND t.store_id=s.store_id AND t.category=s.category
WHEN NOT MATCHED THEN INSERT
 (issued_date,forecast_date,store_id,category,forecast_units,lower_units,upper_units,captured_at)
 VALUES(s.issued_date,s.forecast_date,s.store_id,s.category,s.forecast_units,s.lower_units,s.upper_units,s.captured_at);
