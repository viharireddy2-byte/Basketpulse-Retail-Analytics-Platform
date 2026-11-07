import gzip
import hashlib
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datagen.generate import generate, day_weights
from datetime import date

CFG = dict(transactions=6_000, stores=8, products=500, days=30)


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("bp")
    manifest = generate(out, seed=7, end=date(2026, 6, 30), verbose=False, **CFG)
    files = sorted((out / "line_items").rglob("part.csv.gz"))
    lines = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    return out, manifest, lines


def test_exact_transaction_count(dataset):
    _, manifest, lines = dataset
    assert manifest["transactions"] == CFG["transactions"]
    assert lines["transaction_id"].nunique() == CFG["transactions"]
    assert len(lines) == manifest["line_items"]


def test_one_partition_per_day(dataset):
    out, _, _ = dataset
    assert len(list((out / "line_items").glob("dt=*"))) == CFG["days"]


def test_referential_integrity(dataset):
    out, _, lines = dataset
    stores = pd.read_csv(out / "dim_stores.csv")
    products = pd.read_csv(out / "dim_products.csv")
    customers = pd.read_csv(out / "dim_customers.csv")
    assert set(lines["store_id"]) <= set(stores["store_id"])
    assert set(lines["product_id"]) <= set(products["product_id"])
    assert set(lines["customer_id"].dropna().astype(int)) <= set(customers["customer_id"])


def test_transaction_level_columns_are_constant_within_basket(dataset):
    _, _, lines = dataset
    g = lines.groupby("transaction_id")[["store_id", "transaction_ts", "channel_id"]].nunique()
    assert (g == 1).all().all()


def test_anonymous_share_and_money_sanity(dataset):
    _, _, lines = dataset
    tx = lines.drop_duplicates("transaction_id")
    assert 0.08 < tx["customer_id"].isna().mean() < 0.16
    assert (lines["unit_cost"] < lines["unit_price"]).all()
    assert (lines["discount_amount"] >= 0).all()
    assert (lines["quantity"] >= 1).all()


def test_deterministic_for_same_seed(tmp_path):
    h = []
    for i in range(2):
        out = tmp_path / str(i)
        generate(out, seed=11, end=date(2026, 6, 30), verbose=False, transactions=1500, stores=4, products=200, days=7)
        h.append(hashlib.md5(b"".join(gzip.open(f).read() for f in sorted((out / "line_items").rglob("*.gz")))).hexdigest())
    assert h[0] == h[1]


def test_baskets_contain_real_cooccurrence_structure(dataset):
    """Bakery+Dairy should co-occur far above independence (lift > 1.3) thanks to the breakfast mission."""
    out, _, lines = dataset
    cat = pd.read_csv(out / "dim_products.csv").set_index("product_id")["category"]
    lines = lines.assign(category=lines["product_id"].map(cat))
    baskets = lines.groupby("transaction_id")["category"].agg(set)
    n = len(baskets)
    sup = Counter(c for b in baskets for c in b)
    pairs = Counter(p for b in baskets for p in combinations(sorted(b), 2))
    p = ("Bakery", "Dairy & Eggs")
    lift = (pairs[p] / n) / ((sup["Bakery"] / n) * (sup["Dairy & Eggs"] / n))
    assert lift > 1.3, lift


def test_weekend_peaks():
    w = day_weights(date(2026, 1, 5), 14)  # starts Monday
    assert w[5] > w[1] and w.sum() == pytest.approx(1.0)
