-- Multi-series ARIMA_PLUS: one model, one series per (store, category). 28-day horizon, 90% interval.
CREATE OR REPLACE MODEL `{{project}}.{{dataset}}.demand_forecast_arima`
OPTIONS (model_type = 'ARIMA_PLUS', time_series_timestamp_col = 'transaction_date',
         time_series_data_col = 'units', time_series_id_col = ['store_id', 'category'],
         auto_arima = TRUE, data_frequency = 'DAILY', holiday_region = 'US', decompose_time_series = TRUE)
AS
SELECT transaction_date, store_id, category, units
FROM `{{project}}.{{dataset}}.agg_daily_store_category`
WHERE transaction_date > DATE_SUB((SELECT MAX(transaction_date) FROM `{{project}}.{{dataset}}.agg_daily_store_category`), INTERVAL 365 DAY);

CREATE OR REPLACE TABLE `{{project}}.{{dataset}}.demand_forecast`
PARTITION BY forecast_date CLUSTER BY store_id, category
AS
SELECT DATE(forecast_timestamp) AS forecast_date, store_id, category,
       forecast_value AS forecast_units, prediction_interval_lower_bound AS lower_units,
       prediction_interval_upper_bound AS upper_units
FROM ML.FORECAST(MODEL `{{project}}.{{dataset}}.demand_forecast_arima`, STRUCT(28 AS horizon, 0.9 AS confidence_level));
