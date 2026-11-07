- dashboard: basket_affinity
  title: "Basket Affinity & Bundle Opportunities"
  description: "Which products are bought together, weighted by basket margin - bundle and promotion candidates."
  layout: newspaper
  preferred_viewer: dashboards-next
  filters:
  - name: Category A
    title: Anchor Category
    type: field_filter
    default_value: ""
    allow_multiple_values: true
    model: basketpulse
    explore: basket_affinity
    field: product_a.category
  - name: Min Lift
    title: Min Lift
    type: number_filter
    default_value: ">=1.5"
  elements:
  - name: kpi_pairs
    title: Qualifying Product Pairs
    model: basketpulse
    explore: basket_affinity
    type: single_value
    fields: [basket_affinity.pair_count]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    row: 0
    col: 0
    width: 8
    height: 4
  - name: kpi_bundles
    title: Bundle Candidates (lift >= 2, margin >= $15)
    model: basketpulse
    explore: basket_affinity
    type: single_value
    fields: [basket_affinity.bundle_candidates]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    row: 0
    col: 8
    width: 8
    height: 4
  - name: kpi_avg_lift
    title: Average Lift
    model: basketpulse
    explore: basket_affinity
    type: single_value
    fields: [basket_affinity.avg_lift]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    row: 0
    col: 16
    width: 8
    height: 4
  - name: bundle_table
    title: Top Bundle Candidates
    model: basketpulse
    explore: basket_affinity
    type: looker_grid
    fields: [product_a.product_name, product_b.product_name, basket_affinity.lift, basket_affinity.confidence_a_to_b,
             basket_affinity.pair_tx, basket_affinity.avg_basket_margin]
    filters: {basket_affinity.is_bundle_candidate: "Yes"}
    sorts: [basket_affinity.avg_basket_margin desc]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    limit: 25
    row: 4
    col: 0
    width: 14
    height: 10
  - name: lift_vs_margin
    title: Lift vs Basket Margin
    model: basketpulse
    explore: basket_affinity
    type: looker_scatter
    fields: [basket_affinity.lift, basket_affinity.avg_basket_margin, product_a.category]
    pivots: [product_a.category]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    limit: 500
    row: 4
    col: 14
    width: 10
    height: 10
  - name: category_pair_matrix
    title: Category-to-Category Affinity (avg lift)
    model: basketpulse
    explore: basket_affinity
    type: looker_grid
    fields: [product_a.category, product_b.category, basket_affinity.avg_lift, basket_affinity.total_pair_baskets]
    sorts: [basket_affinity.avg_lift desc]
    listen: {Category A: product_a.category, Min Lift: basket_affinity.lift}
    limit: 50
    row: 14
    col: 0
    width: 14
    height: 8
  - name: lift_distribution
    title: Pairs by Lift Tier
    model: basketpulse
    explore: basket_affinity
    type: looker_column
    fields: [basket_affinity.lift_tier, basket_affinity.pair_count]
    sorts: [basket_affinity.lift_tier]
    listen: {Category A: product_a.category}
    limit: 10
    row: 14
    col: 14
    width: 10
    height: 8
