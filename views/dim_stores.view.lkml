view: dim_stores {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.dim_stores` ;;
  dimension: store_id   { primary_key: yes hidden: yes type: number sql: ${TABLE}.store_id ;; }
  dimension: store_name { type: string sql: ${TABLE}.store_name ;; link: {
      label: "Store performance dashboard"
      url: "/dashboards-next/basketpulse::store_performance?Store={{ value | url_encode }}"
    } }
  dimension: region     { type: string sql: ${TABLE}.region ;; }
  dimension: state      { type: string map_layer_name: us_states sql: ${TABLE}.state ;; }
  dimension: format     { type: string sql: ${TABLE}.format ;; }
  dimension: sq_ft      { type: number sql: ${TABLE}.sq_ft ;; value_format_name: decimal_0 }
  dimension: sq_ft_tier { type: tier tiers: [5000, 20000, 40000, 70000] style: integer sql: ${sq_ft} ;; }
  dimension: location   { type: location sql_latitude: ${TABLE}.latitude ;; sql_longitude: ${TABLE}.longitude ;; }
  dimension_group: opened { type: time datatype: date timeframes: [date, year] sql: ${TABLE}.opened_date ;; }
  measure: store_count { type: count }
  measure: total_sq_ft { type: sum sql: ${sq_ft} ;; value_format_name: decimal_0 }
}
