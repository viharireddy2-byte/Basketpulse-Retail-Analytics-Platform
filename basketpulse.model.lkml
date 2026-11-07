connection: "@{CONNECTION_NAME}"
label: "BasketPulse Retail Analytics"

include: "/explores/*.explore.lkml"
include: "/dashboards/*.dashboard.lookml"

############ Named value formats ############
named_value_format: currency_0 { value_format: "\"@{CURRENCY_SYMBOL}\"#,##0" }
named_value_format: currency_2 { value_format: "\"@{CURRENCY_SYMBOL}\"#,##0.00" }
named_value_format: currency_m { value_format: "\"@{CURRENCY_SYMBOL}\"#,##0.0,,\" M\"" }
named_value_format: currency_k { value_format: "\"@{CURRENCY_SYMBOL}\"#,##0.0,\" K\"" }
named_value_format: count_m    { value_format: "#,##0.0,,\" M\"" }
named_value_format: pct_1      { value_format: "0.0%" }

############ Datagroups (cache policy) ############
# Data lands once per day; dashboards re-run only after the loaded watermark advances.
datagroup: daily_load {
  sql_trigger: SELECT MAX(transaction_date) FROM `@{PROJECT_ID}.@{DATASET}.agg_daily_store_category` ;;
  max_cache_age: "24 hours"
}

# BQML tables are rebuilt weekly.
datagroup: weekly_ml {
  sql_trigger: SELECT EXTRACT(ISOWEEK FROM CURRENT_DATE()) ;;
  max_cache_age: "168 hours"
}
