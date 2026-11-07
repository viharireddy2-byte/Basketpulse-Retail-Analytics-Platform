# Like-for-like store comparison (see sql/bqml/02_store_peer_groups.sql).
view: store_peer_groups {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.store_peer_groups` ;;
  dimension: store_id        { primary_key: yes hidden: yes type: number sql: ${TABLE}.store_id ;; }
  dimension: peer_group      { type: string sql: ${TABLE}.peer_group ;; }
  dimension: peer_percentile { type: number sql: ${TABLE}.peer_percentile ;; value_format_name: percent_0 }
  dimension: performance_band {
    type: string
    sql: CASE WHEN ${TABLE}.peer_percentile >= 0.75 THEN 'Top quartile'
              WHEN ${TABLE}.peer_percentile >= 0.25 THEN 'Mid pack' ELSE 'Bottom quartile' END ;;
  }
  dimension: sales_per_sq_ft { type: number sql: ${TABLE}.sales_per_sq_ft ;; value_format_name: currency_0 }
  measure: avg_sales_per_sq_ft { type: average sql: ${TABLE}.sales_per_sq_ft ;; value_format_name: currency_0 }
  measure: peer_store_count    { type: count }
}
