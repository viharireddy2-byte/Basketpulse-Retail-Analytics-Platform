# BQML k-means output (see sql/bqml/01_customer_segments.sql).
view: customer_segments {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.customer_segments` ;;
  dimension: customer_id { primary_key: yes hidden: yes type: number sql: ${TABLE}.customer_id ;; }
  dimension: segment {
    type: string
    sql: ${TABLE}.segment ;;
    order_by_field: segment_rank
  }
  dimension: segment_rank {
    hidden: yes
    type: number
    sql: CASE ${TABLE}.segment WHEN 'Champions' THEN 1 WHEN 'Loyal Regulars' THEN 2 WHEN 'Casual Shoppers' THEN 3 ELSE 4 END ;;
  }
  dimension: recency_days   { type: number sql: ${TABLE}.recency_days ;; }
  dimension: frequency      { type: number sql: ${TABLE}.frequency ;; }
  dimension: monetary       { type: number sql: ${TABLE}.monetary ;; value_format_name: currency_0 }
  dimension: distinct_categories { type: number sql: ${TABLE}.distinct_categories ;; }
  dimension: is_at_risk     { type: yesno sql: ${TABLE}.recency_days > 60 AND ${TABLE}.frequency >= 6 ;; }

  measure: segment_customers   { type: count }
  measure: avg_recency_days    { type: average sql: ${TABLE}.recency_days ;; value_format_name: decimal_1 }
  measure: avg_frequency       { type: average sql: ${TABLE}.frequency ;; value_format_name: decimal_1 }
  measure: avg_annual_spend    { type: average sql: ${TABLE}.monetary ;; value_format_name: currency_0 }
  measure: total_annual_spend  { type: sum sql: ${TABLE}.monetary ;; value_format_name: currency_m }
  measure: at_risk_customers   { type: count filters: [is_at_risk: "yes"] }
}
