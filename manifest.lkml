project_name: "basketpulse"

################ Constants (override per environment with `export: override_required`) ################
constant: CONNECTION_NAME {
  value: "basketpulse_bigquery"
  export: override_required
}

constant: PROJECT_ID {
  value: "my-gcp-project"
  export: override_required
}

constant: DATASET {
  value: "basketpulse"
  export: override_optional
}

constant: CURRENCY_SYMBOL {
  value: "$"
  export: override_optional
}
