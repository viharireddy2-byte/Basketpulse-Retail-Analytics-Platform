include: "/views/*.view.lkml"

############ Core explore: baskets, lines, customers, stores ############
explore: transactions {
  from: fct_transactions
  view_name: fct_transactions
  label: "Transactions & Baskets"
  description: "Basket-level facts with optional line-item (UNNEST) detail, store, product, customer and segment context."

  # Partition-pruned window: current period plus the matching prior-year window for YoY.
  always_filter: {
    filters: [fct_transactions.current_period: "last 30 days"]
  }
  sql_always_where:
        ${fct_transactions.transaction_date} >= DATE_SUB(DATE({% date_start fct_transactions.current_period %}), INTERVAL 1 YEAR)
    AND ${fct_transactions.transaction_date} <  DATE({% date_end fct_transactions.current_period %}) ;;

  join: fct_transactions__line_items {
    view_label: "Line Items"
    sql: LEFT JOIN UNNEST(${fct_transactions.line_items}) AS fct_transactions__line_items ;;
    relationship: one_to_many
  }
  join: dim_products {
    sql_on: ${fct_transactions__line_items.product_id} = ${dim_products.product_id} ;;
    relationship: many_to_one
  }
  join: dim_stores {
    sql_on: ${fct_transactions.store_id} = ${dim_stores.store_id} ;;
    relationship: many_to_one
  }
  join: store_peer_groups {
    sql_on: ${fct_transactions.store_id} = ${store_peer_groups.store_id} ;;
    relationship: many_to_one
  }
  join: dim_customers {
    sql_on: ${fct_transactions.customer_id} = ${dim_customers.customer_id} ;;
    relationship: many_to_one
  }
  join: customer_segments {
    sql_on: ${fct_transactions.customer_id} = ${customer_segments.customer_id} ;;
    relationship: many_to_one
  }
}

############ Fast cube explore ############
explore: store_category_daily {
  from: agg_daily_store_category
  view_name: agg_daily_store_category
  label: "Store x Category (Daily Cube)"
  always_filter: { filters: [agg_daily_store_category.transaction_date: "last 90 days"] }
  join: dim_stores {
    sql_on: ${agg_daily_store_category.store_id} = ${dim_stores.store_id} ;;
    relationship: many_to_one
  }
  join: store_peer_groups {
    sql_on: ${agg_daily_store_category.store_id} = ${store_peer_groups.store_id} ;;
    relationship: many_to_one
  }
}
