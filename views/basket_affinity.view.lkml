# Pairwise co-purchase metrics (see sql/marts/03_basket_affinity.sql).
view: basket_affinity {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.basket_affinity` ;;
  dimension: pair_key {
    primary_key: yes
    hidden: yes
    sql: CONCAT(CAST(${TABLE}.product_a AS STRING), '-', CAST(${TABLE}.product_b AS STRING)) ;;
  }
  dimension: product_a_id { hidden: yes type: number sql: ${TABLE}.product_a ;; }
  dimension: product_b_id { hidden: yes type: number sql: ${TABLE}.product_b ;; }
  dimension: pair_tx            { label: "Baskets With Both" type: number sql: ${TABLE}.pair_tx ;; }
  dimension: support            { type: number sql: ${TABLE}.support ;; value_format: "0.000%" }
  dimension: confidence_a_to_b  { type: number sql: ${TABLE}.confidence_a_to_b ;; value_format_name: percent_1 }
  dimension: lift               { type: number sql: ${TABLE}.lift ;; value_format: "0.00" }
  dimension: avg_basket_margin  { type: number sql: ${TABLE}.avg_basket_margin ;; value_format_name: currency_2 }
  dimension: lift_tier { type: tier tiers: [1, 1.5, 2, 3, 5] style: relational sql: ${lift} ;; }
  dimension: is_bundle_candidate {
    type: yesno
    sql: ${TABLE}.lift >= 2 AND ${TABLE}.avg_basket_margin >= 15 ;;
    description: "Strong co-purchase signal (lift >= 2) in baskets worth at least $15 margin."
  }

  measure: pair_count         { type: count }
  measure: max_lift           { type: max sql: ${lift} ;; value_format: "0.00" }
  measure: avg_lift           { type: average sql: ${lift} ;; value_format: "0.00" }
  measure: total_pair_baskets { type: sum sql: ${pair_tx} ;; value_format_name: decimal_0 }
  measure: avg_pair_basket_margin { type: average sql: ${avg_basket_margin} ;; value_format_name: currency_2 }
  measure: bundle_candidates  { type: count filters: [is_bundle_candidate: "yes"] }
}
