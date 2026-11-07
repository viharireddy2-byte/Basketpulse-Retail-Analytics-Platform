# Data dictionary

All objects live in one BigQuery dataset (default `basketpulse`). Grain and keys are stated for each table.

## Raw / staging

| Table | Grain | Partition / cluster | Notes |
|---|---|---|---|
| `stg_line_items` | 1 row per basket line | partition `transaction_date` | Loaded from generator CSVs. Source for `fct_transactions`. |
| `dim_stores` | 1 row per store | cluster `region, format` | `format` in Hypermarket / Supermarket / Express. |
| `dim_products` | 1 row per SKU | cluster `category` | 12 categories; `unit_cost` is hidden in LookML. |
| `dim_customers` | 1 row per loyalty customer | cluster `loyalty_tier` | Anonymous baskets have `customer_id IS NULL` in facts. |
| `dim_channels` | 1 row per channel | - | In-Store, Online Delivery, Click & Collect. |

## Core fact

### `fct_transactions` (grain: 1 row per transaction)
Partitioned by `transaction_date` (DAY), clustered by `store_id, customer_id, channel_id`.

| Column | Type | Description |
|---|---|---|
| `transaction_id` | INT64 | Primary key |
| `transaction_ts` / `transaction_date` | TIMESTAMP / DATE | Event time and partition column |
| `store_id`, `customer_id`, `channel_id` | INT64 | FKs. `customer_id` is NULL for non-loyalty baskets |
| `line_items` | ARRAY<STRUCT> | `line_number, product_id, quantity, unit_price, unit_cost, discount_amount, net_amount, margin_amount` |
| `basket_lines`, `basket_units` | INT64 | Pre-computed basket rollups |
| `basket_net_amount`, `basket_margin_amount` | NUMERIC | Pre-computed so most queries never UNNEST |

## Marts and ML outputs

| Object | Grain | Built by | Purpose |
|---|---|---|---|
| `agg_daily_store_category` | store x category x day | `sql/marts/01` | Fast cube for dashboards and forecasting input |
| `customer_features` | customer | `sql/marts/02` | Trailing-365d recency, frequency, monetary, basket value, margin rate, category breadth |
| `customer_segments_kmeans` (MODEL) | - | `sql/bqml/01` | k-means, k=4, standardized features |
| `customer_segments` | customer | `sql/bqml/01` | Segment label assigned by centroid spend rank: Champions, Loyal Regulars, Casual Shoppers, Lapsing / Low Value |
| `store_features`, `store_peer_kmeans` (MODEL) | store | `sql/bqml/02` | Peer clustering inputs and model (k=5) |
| `store_peer_groups` | store | `sql/bqml/02` | Peer group and sales-per-sq-ft percentile within group |
| `demand_forecast_arima` (MODEL) | store x category series | `sql/bqml/03` | ARIMA_PLUS with holiday effects |
| `demand_forecast` | store x category x day | `sql/bqml/03` | 28-day units forecast with 90% interval |
| `basket_affinity` | product pair | `sql/marts/03` | Support, confidence (both directions), lift, avg basket margin over trailing 90d |

## Metric definitions

| Metric | Definition |
|---|---|
| Net sales | `quantity * unit_price - discount_amount`, summed |
| Gross margin | Net sales minus `quantity * unit_cost` |
| Margin rate | Gross margin / net sales |
| Avg basket value | Net sales / transactions |
| YoY % | (current-period value / same-window prior-year value) - 1 |
| Lift (A,B) | P(A and B) / (P(A) * P(B)); > 1 means bought together more than chance |
| Confidence (A to B) | P(B given A) |
| Bundle candidate | Lift >= 2 and average basket margin >= $15 |
| At-risk customer | Recency > 60 days with >= 6 purchases in the trailing year |
