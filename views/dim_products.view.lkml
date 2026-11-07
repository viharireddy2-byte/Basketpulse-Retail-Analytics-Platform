view: dim_products {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.dim_products` ;;
  dimension: product_id   { primary_key: yes type: number sql: ${TABLE}.product_id ;; value_format_name: id }
  dimension: product_name { type: string sql: ${TABLE}.product_name ;; }
  dimension: category     { type: string sql: ${TABLE}.category ;; }
  dimension: subcategory  { type: string sql: ${TABLE}.subcategory ;; }
  dimension: brand        { type: string sql: ${TABLE}.brand ;; }
  dimension: list_price   { type: number sql: ${TABLE}.unit_price ;; value_format_name: currency_2 }
  dimension: unit_cost    { hidden: yes type: number sql: ${TABLE}.unit_cost ;; }
  measure: product_count  { type: count }
}
