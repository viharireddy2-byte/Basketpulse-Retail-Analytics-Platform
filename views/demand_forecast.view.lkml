# 28-day ARIMA_PLUS forecast per store x category (see sql/bqml/03_demand_forecast.sql).
view: demand_forecast {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.demand_forecast` ;;
  dimension: forecast_key {
    primary_key: yes
    hidden: yes
    sql: CONCAT(CAST(${TABLE}.store_id AS STRING), '|', ${TABLE}.category, '|', CAST(${TABLE}.forecast_date AS STRING)) ;;
  }
  dimension: store_id { hidden: yes type: number sql: ${TABLE}.store_id ;; }
  dimension: category { type: string sql: ${TABLE}.category ;; }
  dimension_group: forecast { type: time datatype: date timeframes: [date, week, month] sql: ${TABLE}.forecast_date ;; }
  measure: forecast_units { type: sum sql: ${TABLE}.forecast_units ;; value_format_name: decimal_0 }
  measure: lower_units    { type: sum sql: ${TABLE}.lower_units ;; value_format_name: decimal_0 }
  measure: upper_units    { type: sum sql: ${TABLE}.upper_units ;; value_format_name: decimal_0 }
}
