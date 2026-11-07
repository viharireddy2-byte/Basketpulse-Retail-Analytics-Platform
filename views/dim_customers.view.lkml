view: dim_customers {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.dim_customers` ;;
  dimension: customer_id         { primary_key: yes type: number sql: ${TABLE}.customer_id ;; value_format_name: id }
  dimension: loyalty_tier        { type: string sql: ${TABLE}.loyalty_tier ;; order_by_field: loyalty_tier_rank }
  dimension: loyalty_tier_rank   { hidden: yes type: number
    sql: CASE ${TABLE}.loyalty_tier WHEN 'Basic' THEN 1 WHEN 'Silver' THEN 2 WHEN 'Gold' THEN 3 ELSE 4 END ;; }
  dimension: acquisition_channel { type: string sql: ${TABLE}.acquisition_channel ;; }
  dimension: home_store_id       { hidden: yes type: number sql: ${TABLE}.home_store_id ;; }
  dimension_group: signup        { type: time datatype: date timeframes: [date, month, year] sql: ${TABLE}.signup_date ;; }
  measure: customer_count        { type: count }
}
