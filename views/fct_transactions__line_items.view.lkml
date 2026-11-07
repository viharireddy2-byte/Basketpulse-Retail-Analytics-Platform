# Nested ARRAY<STRUCT> exposed as its own view. Joined with LEFT JOIN UNNEST in the explore, so
# line-level analysis never needs a second table and BigQuery reads one columnar copy of the data.
view: fct_transactions__line_items {
  dimension: product_id      { hidden: yes type: number sql: ${TABLE}.product_id ;; }
  dimension: line_number     { type: number sql: ${TABLE}.line_number ;; }
  dimension: quantity        { type: number sql: ${TABLE}.quantity ;; }
  dimension: unit_price      { type: number sql: ${TABLE}.unit_price ;; value_format_name: currency_2 }
  dimension: discount_amount { type: number sql: ${TABLE}.discount_amount ;; value_format_name: currency_2 }
  dimension: is_promoted     { type: yesno sql: ${TABLE}.discount_amount > 0 ;; }

  measure: line_count     { type: count }
  measure: line_units     { type: sum sql: ${TABLE}.quantity ;; }
  measure: line_net_sales { type: sum sql: ${TABLE}.net_amount ;; value_format_name: currency_0 }
  measure: line_margin    { type: sum sql: ${TABLE}.margin_amount ;; value_format_name: currency_0 }
  measure: line_discount  { type: sum sql: ${TABLE}.discount_amount ;; value_format_name: currency_0 }
  measure: line_margin_rate {
    type: number
    sql: SAFE_DIVIDE(${line_margin}, ${line_net_sales}) ;;
    value_format_name: pct_1
  }
  measure: promo_share_of_sales {
    type: number
    sql: SAFE_DIVIDE(SUM(IF(${TABLE}.discount_amount > 0, ${TABLE}.net_amount, 0)), ${line_net_sales}) ;;
    value_format_name: pct_1
  }
}
