import subprocess
import sys
from pathlib import Path

import pytest

from scripts.run_sql import BUILD, PIPELINE, ROOT, SETUP, render

PARAMS = dict(project="p", dataset="d", location="US", min_item_support=300, min_pair_support=100)


def test_pipeline_covers_every_sql_file():
    on_disk = {p.relative_to(ROOT).as_posix() for p in (ROOT / "sql").rglob("*.sql")}
    assert on_disk == set(PIPELINE)


def test_pipeline_order_respects_dependencies():
    idx = {f: i for i, f in enumerate(PIPELINE)}
    assert idx["sql/01_schema.sql"] < idx["sql/02_fct_transactions.sql"] < idx["sql/marts/01_agg_daily_store_category.sql"]
    assert idx["sql/marts/02_customer_features.sql"] < idx["sql/bqml/01_customer_segments.sql"]
    assert idx["sql/marts/01_agg_daily_store_category.sql"] < idx["sql/bqml/02_store_peer_groups.sql"]
    assert idx["sql/marts/01_agg_daily_store_category.sql"] < idx["sql/bqml/03_demand_forecast.sql"]


def test_all_sql_renders_without_unresolved_variables():
    for f in PIPELINE:
        sql = render(ROOT / f, PARAMS)
        assert "{{" not in sql and "`p.d." in sql


def test_render_rejects_unknown_variable(tmp_path):
    p = tmp_path / "x.sql"
    p.write_text("SELECT '{{nope}}'")
    with pytest.raises(ValueError):
        render(p, PARAMS)


def test_every_bigquery_object_read_by_lookml_is_created_by_sql():
    import re
    created = set()
    for f in PIPELINE:
        created |= set(re.findall(r"(?:TABLE|MODEL) `\{\{project\}\}\.\{\{dataset\}\}\.(\w+)`", (ROOT / f).read_text()))
    used = set()
    for v in (ROOT / "views").glob("*.view.lkml"):
        used |= set(re.findall(r"@\{DATASET\}\.(\w+)`", v.read_text()))
    assert used <= created, used - created


def test_lookml_lint_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "lint_lookml.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_default_build_never_contains_destructive_schema_ddl():
    assert "sql/01_schema.sql" in SETUP and "sql/01_schema.sql" not in BUILD
    for f in BUILD:
        text = (ROOT / f).read_text()
        for dim in ("dim_stores", "dim_products", "dim_customers", "dim_channels", "stg_line_items"):
            assert f"CREATE OR REPLACE TABLE `{{{{project}}}}.{{{{dataset}}}}.{dim}`" not in text, (f, dim)
