include: "/views/*.view.lkml"

explore: demand_forecast {
  label: "Demand Forecast (28-day)"
  persist_with: weekly_ml
  join: dim_stores {
    sql_on: ${demand_forecast.store_id} = ${dim_stores.store_id} ;;
    relationship: many_to_one
  }
}
