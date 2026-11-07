- dashboard: executive_overview
  title: "Executive Overview"
  description: "Group performance, regional and store movers, category mix and customer segments."
  layout: newspaper
  preferred_viewer: dashboards-next
  crossfilter_enabled: true
  filters:
  - name: Period
    title: Period
    type: date_filter
    default_value: 30 days
    allow_multiple_values: false
  - name: Region
    title: Region
    type: field_filter
    default_value: ""
    allow_multiple_values: true
    model: basketpulse
    explore: transactions
    field: dim_stores.region
  elements:
  - name: kpi_net_sales
    title: Net Sales
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.net_sales_current, fct_transactions.net_sales_yoy]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    custom_color_enabled: true
    show_comparison: false
    row: 0
    col: 0
    width: 6
    height: 4
  - name: kpi_transactions
    title: Transactions
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.transactions_current, fct_transactions.transactions_yoy]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    row: 0
    col: 6
    width: 6
    height: 4
  - name: kpi_basket_value
    title: Avg Basket Value
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.avg_basket_value]
    filters: {fct_transactions.period_bucket: current}
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    row: 0
    col: 12
    width: 6
    height: 4
  - name: kpi_margin_rate
    title: Gross Margin %
    model: basketpulse
    explore: transactions
    type: single_value
    fields: [fct_transactions.margin_rate]
    filters: {fct_transactions.period_bucket: current}
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    row: 0
    col: 18
    width: 6
    height: 4
  - name: weekly_sales_trend
    title: Weekly Net Sales (current vs prior-year window)
    model: basketpulse
    explore: transactions
    type: looker_column
    fields: [fct_transactions.transaction_week, fct_transactions.net_sales]
    fill_fields: [fct_transactions.transaction_week]
    sorts: [fct_transactions.transaction_week]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 200
    row: 4
    col: 0
    width: 14
    height: 8
  - name: sales_by_region
    title: Net Sales & YoY by Region
    model: basketpulse
    explore: transactions
    type: looker_grid
    fields: [dim_stores.region, fct_transactions.net_sales_current, fct_transactions.net_sales_yoy, fct_transactions.margin_rate]
    sorts: [fct_transactions.net_sales_current desc]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 10
    row: 4
    col: 14
    width: 10
    height: 8
  - name: top_stores
    title: Top 10 Stores by YoY Growth
    model: basketpulse
    explore: transactions
    type: looker_grid
    fields: [dim_stores.store_name, dim_stores.format, fct_transactions.net_sales_current, fct_transactions.net_sales_yoy]
    filters: {fct_transactions.net_sales_prior_year: ">0"}
    sorts: [fct_transactions.net_sales_yoy desc]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 10
    row: 12
    col: 0
    width: 12
    height: 8
  - name: bottom_stores
    title: Bottom 10 Stores by YoY Growth
    model: basketpulse
    explore: transactions
    type: looker_grid
    fields: [dim_stores.store_name, dim_stores.format, fct_transactions.net_sales_current, fct_transactions.net_sales_yoy]
    filters: {fct_transactions.net_sales_prior_year: ">0"}
    sorts: [fct_transactions.net_sales_yoy asc]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 10
    row: 12
    col: 12
    width: 12
    height: 8
  - name: category_mix
    title: Category Net Sales & Margin Rate
    model: basketpulse
    explore: transactions
    type: looker_bar
    fields: [dim_products.category, fct_transactions__line_items.line_net_sales, fct_transactions__line_items.line_margin_rate]
    filters: {fct_transactions.period_bucket: current}
    sorts: [fct_transactions__line_items.line_net_sales desc]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 12
    row: 20
    col: 0
    width: 12
    height: 8
  - name: segment_value
    title: Customer Segments by Annual Spend
    model: basketpulse
    explore: transactions
    type: looker_pie
    fields: [customer_segments.segment, fct_transactions.net_sales]
    filters: {fct_transactions.period_bucket: current}
    sorts: [fct_transactions.net_sales desc]
    listen: {Period: fct_transactions.current_period, Region: dim_stores.region}
    limit: 6
    row: 20
    col: 12
    width: 12
    height: 8
