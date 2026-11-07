view: fct_transactions {
  sql_table_name: `@{PROJECT_ID}.@{DATASET}.fct_transactions` ;;

  ############ Keys & hidden helpers ############
  dimension: transaction_id {
    primary_key: yes
    type: number
    sql: ${TABLE}.transaction_id ;;
    value_format_name: id
  }
  dimension: line_items { hidden: yes sql: ${TABLE}.line_items ;; }
  dimension: store_id    { hidden: yes type: number sql: ${TABLE}.store_id ;; }
  dimension: customer_id { hidden: yes type: number sql: ${TABLE}.customer_id ;; }
  dimension: channel_id  { hidden: yes type: number sql: ${TABLE}.channel_id ;; }

  ############ Time ############
  dimension_group: transaction {
    type: time
    datatype: date
    timeframes: [date, week, month, quarter, year, day_of_week, day_of_week_index]
    sql: ${TABLE}.transaction_date ;;
  }
  dimension: hour_of_day {
    type: number
    sql: EXTRACT(HOUR FROM ${TABLE}.transaction_ts) ;;
  }

  ############ Basket attributes ############
  dimension: basket_net_amount    { hidden: yes type: number sql: ${TABLE}.basket_net_amount ;; }
  dimension: basket_margin_amount { hidden: yes type: number sql: ${TABLE}.basket_margin_amount ;; }
  dimension: basket_units         { hidden: yes type: number sql: ${TABLE}.basket_units ;; }
  dimension: basket_lines         { type: number sql: ${TABLE}.basket_lines ;; }
  dimension: basket_size_tier {
    type: tier
    tiers: [2, 4, 8, 15]
    style: integer
    sql: ${basket_lines} ;;
  }
  dimension: is_loyalty_member { type: yesno sql: ${TABLE}.customer_id IS NOT NULL ;; }

  ############ Period-over-period (YoY) ############
  # Dashboards filter *current_period*; the explore widens the partition predicate to include the prior year.
  filter: current_period {
    type: date
    label: "Current Period"
    description: "Selects the period of interest. Prior-year comparison is derived automatically."
  }
  dimension: period_bucket {
    type: string
    hidden: yes
    sql: CASE
           WHEN {% condition current_period %} TIMESTAMP(${TABLE}.transaction_date) {% endcondition %} THEN 'current'
           WHEN ${TABLE}.transaction_date BETWEEN DATE_SUB(DATE({% date_start current_period %}), INTERVAL 1 YEAR)
                                              AND DATE_SUB(DATE({% date_end current_period %}), INTERVAL 1 YEAR) THEN 'prior_year'
         END ;;
  }

  ############ Measures ############
  measure: transactions {
    type: count
    value_format_name: decimal_0
    drill_fields: [transaction_date, dim_stores.store_name, basket_lines]
  }
  measure: unique_customers {
    type: count_distinct
    sql: ${TABLE}.customer_id ;;
    value_format_name: decimal_0
  }
  measure: net_sales {
    type: sum
    sql: ${basket_net_amount} ;;
    value_format_name: currency_0
  }
  measure: gross_margin {
    type: sum
    sql: ${basket_margin_amount} ;;
    value_format_name: currency_0
  }
  measure: margin_rate {
    type: number
    sql: SAFE_DIVIDE(${gross_margin}, ${net_sales}) ;;
    value_format_name: pct_1
  }
  measure: units {
    type: sum
    sql: ${basket_units} ;;
    value_format_name: decimal_0
  }
  measure: avg_basket_value {
    type: number
    sql: SAFE_DIVIDE(${net_sales}, ${transactions}) ;;
    value_format_name: currency_2
  }
  measure: items_per_basket {
    type: average
    sql: ${basket_lines} ;;
    value_format_name: decimal_1
  }
  measure: net_sales_current {
    type: sum
    sql: ${basket_net_amount} ;;
    filters: [period_bucket: "current"]
    value_format_name: currency_0
  }
  measure: net_sales_prior_year {
    type: sum
    sql: ${basket_net_amount} ;;
    filters: [period_bucket: "prior_year"]
    value_format_name: currency_0
  }
  measure: net_sales_yoy {
    label: "Net Sales YoY %"
    type: number
    sql: SAFE_DIVIDE(${net_sales_current}, NULLIF(${net_sales_prior_year}, 0)) - 1 ;;
    value_format_name: pct_1
  }
  measure: transactions_current {
    type: count
    filters: [period_bucket: "current"]
  }
  measure: transactions_prior_year {
    type: count
    filters: [period_bucket: "prior_year"]
  }
  measure: transactions_yoy {
    label: "Transactions YoY %"
    type: number
    sql: SAFE_DIVIDE(${transactions_current}, NULLIF(${transactions_prior_year}, 0)) - 1 ;;
    value_format_name: pct_1
  }
}
