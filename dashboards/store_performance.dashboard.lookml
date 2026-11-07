- dashboard: store_performance
  title: "Store Performance Deep-Dive"
  description: "One store versus its peer group: growth, category mix, customer segments and the 28-day demand outlook."
  layout: newspaper
  preferred_viewer: dashboards-next
  filters:
  - name: Store
    title: Store
    type: field_filter
    default_value: "BasketPulse Southeast #001"
    allow_multiple_values: false
    model: basketpulse
    explore: transactions
    field: dim_stores.store_name
  - name: Period
    title: Period
    type: date_filter
    default_value: 90 days
    allow_multiple_values: false
  elements:
  - name: store_net_sales
    title: Net Sales (YoY)
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.net_sales_current, fct_transactions.net_sales_yoy]
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    row: 0
    col: 0
    width: 6
    height: 4
  - name: store_peer_percentile
    title: Sales / sq ft Percentile in Peer Group
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [store_peer_groups.peer_percentile, store_peer_groups.peer_group]
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    limit: 1
    row: 0
    col: 6
    width: 6
    height: 4
  - name: store_basket
    title: Avg Basket Value
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.avg_basket_value]
    filters: {fct_transactions.period_bucket: current}
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    row: 0
    col: 12
    width: 6
    height: 4
  - name: store_margin
    title: Gross Margin %
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.margin_rate]
    filters: {fct_transactions.period_bucket: current}
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    row: 0
    col: 18
    width: 6
    height: 4
  - name: peer_scatter
    title: All Stores by Peer Group - Sales per sq ft vs Margin
    model: basketpulse
    explore: store_category_daily
    type: looker_scatter
    fields: [dim_stores.store_name, store_peer_groups.peer_group, store_peer_groups.avg_sales_per_sq_ft, agg_daily_store_category.margin_rate]
    pivots: [store_peer_groups.peer_group]
    limit: 500
    row: 4
    col: 0
    width: 12
    height: 8
  - name: category_vs_peers
    title: Category Net Sales (this store)
    model: basketpulse
    explore: transactions
    type: looker_column
    fields: [dim_products.category, fct_transactions__line_items.line_net_sales, fct_transactions__line_items.line_margin_rate]
    filters: {fct_transactions.period_bucket: current}
    sorts: [fct_transactions__line_items.line_net_sales desc]
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    limit: 12
    row: 4
    col: 12
    width: 12
    height: 8
  - name: segment_mix
    title: Customer Segment Mix
    model: basketpulse
    explore: transactions
    type: looker_donut_multiples
    fields: [customer_segments.segment, fct_transactions.unique_customers]
    filters: {fct_transactions.period_bucket: current}
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    limit: 6
    row: 12
    col: 0
    width: 8
    height: 8
  - name: hourly_traffic
    title: Transactions by Hour of Day
    model: basketpulse
    explore: transactions
    type: looker_area
    fields: [fct_transactions.hour_of_day, fct_transactions.transactions]
    filters: {fct_transactions.period_bucket: current}
    sorts: [fct_transactions.hour_of_day]
    listen: {Store: dim_stores.store_name, Period: fct_transactions.current_period}
    limit: 24
    row: 12
    col: 8
    width: 16
    height: 8
  - name: demand_outlook
    title: 28-Day Unit Demand Forecast (with 90% interval)
    model: basketpulse
    explore: demand_forecast
    type: looker_line
    fields: [demand_forecast.forecast_date, demand_forecast.forecast_units, demand_forecast.lower_units, demand_forecast.upper_units]
    sorts: [demand_forecast.forecast_date]
    listen: {Store: dim_stores.store_name}
    limit: 28
    row: 20
    col: 0
    width: 24
    height: 8
