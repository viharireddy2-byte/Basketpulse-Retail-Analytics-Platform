include: "/views/*.view.lkml"

explore: basket_affinity {
  label: "Basket Affinity"
  description: "Product-pair co-purchase strength (lift, confidence) weighted by basket margin."
  persist_with: weekly_ml

  join: product_a {
    from: dim_products
    view_label: "Product A"
    sql_on: ${basket_affinity.product_a_id} = ${product_a.product_id} ;;
    relationship: many_to_one
  }
  join: product_b {
    from: dim_products
    view_label: "Product B"
    sql_on: ${basket_affinity.product_b_id} = ${product_b.product_id} ;;
    relationship: many_to_one
  }
}
