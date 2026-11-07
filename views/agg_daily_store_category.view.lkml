# Pre-aggregated cube; powers fast tiles and is the actuals side of forecast-vs-actual.
view: agg_daily_store_category {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.agg_daily_store_category` ;;
  dimension: row_key {
    primary_key: yes
    hidden: yes
    sql: CONCAT(CAST(${TABLE}.transaction_date AS STRING), '|', CAST(${TABLE}.store_id AS STRING), '|', ${TABLE}.category) ;;
  }
  dimension: store_id { hidden: yes type: number sql: ${TABLE}.store_id ;; }
  dimension: category { type: string sql: ${TABLE}.category ;; }
  dimension_group: transaction { type: time datatype: date timeframes: [date, week, month, quarter, year] sql: ${TABLE}.transaction_date ;; }
  measure: transactions  { type: sum sql: ${TABLE}.transactions ;; value_format_name: decimal_0 }
  measure: units         { type: sum sql: ${TABLE}.units ;; value_format_name: decimal_0 }
  measure: net_sales     { type: sum sql: ${TABLE}.net_sales ;; value_format_name: currency_0 }
  measure: gross_margin  { type: sum sql: ${TABLE}.gross_margin ;; value_format_name: currency_0 }
  measure: margin_rate   { type: number sql: SAFE_DIVIDE(${gross_margin}, ${net_sales}) ;; value_format_name: pct_1 }
}
