"""Scalable synthetic retail data generator.

Writes dimension tables as CSV and fact line items as one gzip CSV per day
(``line_items/dt=YYYY-MM-DD/part.csv.gz``), ready for BigQuery load jobs with
Hive-style partition discovery. Everything is vectorised with NumPy and seeded,
so a given (seed, size) always yields the same dataset.

Usage:
    python -m datagen.generate --profile dev --out data/dev
    python -m datagen.generate --transactions 50000000 --out data/xl
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .catalog import (ACQ_CHANNELS, CATEGORIES, CHANNEL_P, CHANNELS, HOUR_WEIGHTS, LOYALTY_TIERS,
                      MISSION_LAMBDA, MISSION_NAMES, MISSION_PRIOR, REGIONS, STORE_FORMATS,
                      WEEKDAY_FACTOR, mission_category_cdf)

PROFILES = {  # transactions, stores, products, days
    "tiny": dict(transactions=20_000, stores=12, products=800, days=60),
    "dev": dict(transactions=1_000_000, stores=60, products=4_000, days=365),
    "standard": dict(transactions=10_000_000, stores=200, products=12_000, days=730),
    "xl": dict(transactions=50_000_000, stores=400, products=20_000, days=730),
}


# ----------------------------------------------------------------------------- dimensions
def build_stores(n: int, rng: np.random.Generator, end: date) -> pd.DataFrame:
    regions = list(REGIONS)
    shares = np.array([REGIONS[r][2] for r in regions])
    region = rng.choice(regions, size=n, p=shares / shares.sum())
    fmts = list(STORE_FORMATS)
    fmt = rng.choice(fmts, size=n, p=np.array([STORE_FORMATS[f][0] for f in fmts]))
    lo = np.array([STORE_FORMATS[f][1] for f in fmt])
    hi = np.array([STORE_FORMATS[f][2] for f in fmt])
    rows = []
    for i in range(n):
        lat, lon, _, states = REGIONS[region[i]]
        rows.append((i + 1, f"BasketPulse {region[i]} #{i + 1:03d}", region[i], states[i % len(states)],
                     round(lat + rng.normal(0, 2.2), 5), round(lon + rng.normal(0, 3.0), 5), fmt[i],
                     int(rng.integers(lo[i], hi[i])),
                     (end - timedelta(days=int(rng.integers(400, 6000)))).isoformat()))
    return pd.DataFrame(rows, columns=["store_id", "store_name", "region", "state", "latitude",
                                       "longitude", "format", "sq_ft", "opened_date"])


def build_products(n: int, rng: np.random.Generator) -> pd.DataFrame:
    shares = np.array([c[4] for c in CATEGORIES])
    counts = np.maximum(1, np.round(shares / shares.sum() * n).astype(int))
    counts[0] += n - counts.sum()
    frames, pid = [], 1
    for (name, plo, phi, margin, _), cnt in zip(CATEGORIES, counts):
        price = np.round(np.exp(rng.uniform(np.log(plo), np.log(phi), cnt)), 2)
        m = np.clip(rng.normal(margin, 0.06, cnt), 0.05, 0.7)
        frames.append(pd.DataFrame({
            "product_id": np.arange(pid, pid + cnt), "category": name,
            "brand": [f"Brand {int(b):02d}" for b in rng.integers(1, 60, cnt)],
            "unit_price": price, "unit_cost": np.round(price * (1 - m), 2)}))
        pid += cnt
    df = pd.concat(frames, ignore_index=True)
    df["product_name"] = [f"{c} item {i}" for c, i in zip(df["category"], df["product_id"])]
    df["subcategory"] = [f"{c} / group {(i % 7) + 1}" for c, i in zip(df["category"], df["product_id"])]
    return df[["product_id", "product_name", "category", "subcategory", "brand", "unit_price", "unit_cost"]]


def build_customers(n: int, start: date, end: date, rng: np.random.Generator):
    span = (end - start).days
    pre = 540  # customers may have signed up before the data window
    signup_off = rng.integers(-pre, span, n)
    life = rng.integers(60, 1400, n)
    churn_off = np.where(rng.random(n) < 0.45, signup_off + life, 10**6)  # ~45% eventually churn
    mission = rng.choice(len(MISSION_NAMES), n, p=MISSION_PRIOR)
    propensity = rng.lognormal(0, 0.9, n)
    tier = rng.choice(LOYALTY_TIERS, n, p=[0.55, 0.25, 0.15, 0.05])
    df = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "signup_date": (np.datetime64(start) + signup_off.astype("timedelta64[D]")).astype(str),
        "loyalty_tier": tier,
        "acquisition_channel": rng.choice(ACQ_CHANNELS, n),
        "home_store_id": 0,
        "preferred_mission": np.array(MISSION_NAMES)[mission],
    })
    return df, signup_off, churn_off, mission, propensity


# ----------------------------------------------------------------------------- facts
def day_weights(start: date, days: int) -> np.ndarray:
    d = np.array([start + timedelta(days=i) for i in range(days)])
    wd = WEEKDAY_FACTOR[[x.weekday() for x in d]]
    doy = np.array([x.timetuple().tm_yday for x in d])
    season = 1 + 0.18 * np.exp(-((doy - 355) % 365 / 12) ** 2) + 0.06 * np.sin(2 * np.pi * (doy - 80) / 365)
    growth = 1 + 0.12 * np.arange(days) / max(days, 365)
    w = wd * season * growth
    return w / w.sum()


def generate(out: Path, transactions: int, stores: int, products: int, days: int, seed: int = 42,
             end: date | None = None, compress: bool = True, verbose: bool = True) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    end = end or date(2026, 10, 31)
    start = end - timedelta(days=days - 1)
    out.mkdir(parents=True, exist_ok=True)

    n_customers = max(500, transactions // 10)
    dim_s = build_stores(stores, rng, end)
    dim_p = build_products(products, rng)
    dim_c, signup, churn, c_mission, c_prop = build_customers(n_customers, start, end, rng)
    dim_c["home_store_id"] = rng.integers(1, stores + 1, n_customers)
    pd.DataFrame(CHANNELS, columns=["channel_id", "channel_name"]).to_csv(out / "dim_channels.csv", index=False)
    dim_s.to_csv(out / "dim_stores.csv", index=False)
    dim_p.to_csv(out / "dim_products.csv", index=False)
    dim_c.drop(columns=["preferred_mission"]).to_csv(out / "dim_customers.csv", index=False)

    # store traffic: format multiplier x lognormal noise, plus a per-store growth slope
    fmt_mult = dim_s["format"].map(lambda f: STORE_FORMATS[f][3]).to_numpy()
    store_base = fmt_mult * rng.lognormal(0, 0.25, stores)
    store_slope = rng.uniform(-0.15, 0.30, stores)  # annual growth drift -> real top/bottom movers

    # product lookup by category (contiguous id ranges)
    cat_codes = pd.Categorical(dim_p["category"], categories=[c[0] for c in CATEGORIES]).codes
    cat_start = np.array([np.where(cat_codes == k)[0][0] for k in range(len(CATEGORIES))])
    cat_size = np.bincount(cat_codes, minlength=len(CATEGORIES))
    price = dim_p["unit_price"].to_numpy()
    cost = dim_p["unit_cost"].to_numpy()
    mission_cdf = mission_category_cdf()
    cust_cdf = np.cumsum(c_prop / c_prop.sum())

    weights = day_weights(start, days)
    per_day = np.floor(weights * transactions).astype(np.int64)
    per_day[np.argmax(weights)] += transactions - per_day.sum()

    tx_counter, line_total = 0, 0
    (out / "line_items").mkdir(exist_ok=True)
    for di in range(days):
        n = int(per_day[di])
        if n == 0:
            continue
        day = start + timedelta(days=di)
        # --- who / where
        sp = store_base * (1 + store_slope * di / 365.0)
        sp = np.clip(sp, 1e-3, None)
        store_idx = np.searchsorted(np.cumsum(sp / sp.sum()), rng.random(n)).clip(0, stores - 1)
        cust = np.searchsorted(cust_cdf, rng.random(n)).clip(0, n_customers - 1)
        for _ in range(3):  # re-draw customers who are not active on this day
            bad = (signup[cust] > di) | (churn[cust] < di)
            if not bad.any():
                break
            cust[bad] = np.searchsorted(cust_cdf, rng.random(int(bad.sum()))).clip(0, n_customers - 1)
        anonymous = rng.random(n) < 0.12  # no loyalty card
        # --- mission & basket size
        mission = np.where(rng.random(n) < 0.65, c_mission[cust], rng.choice(len(MISSION_NAMES), n, p=MISSION_PRIOR))
        n_items = np.clip(1 + rng.poisson(MISSION_LAMBDA[mission]), 1, 40)
        total = int(n_items.sum())
        tx_of_item = np.repeat(np.arange(n), n_items)
        line_no = np.arange(total) - np.repeat(np.cumsum(n_items) - n_items, n_items) + 1
        # --- category then product (zipf-like popularity inside category)
        cat = (rng.random(total)[:, None] > mission_cdf[mission[tx_of_item]]).sum(axis=1).clip(0, len(CATEGORIES) - 1)
        pos = np.floor(cat_size[cat] * rng.random(total) ** 2.2).astype(np.int64)
        pidx = cat_start[cat] + np.minimum(pos, cat_size[cat] - 1)
        qty = 1 + (rng.random(total) < 0.2) + 2 * (rng.random(total) < 0.04)
        pid = dim_p["product_id"].to_numpy()[pidx]
        # --- deterministic promo calendar: ~6% of product-weeks at 15-30% off
        week = day.toordinal() // 7
        promo = ((pid * 31 + week * 17) % 17 == 0)
        disc_pct = 0.15 + ((pid * 7 + week) % 16) / 100.0
        discount = np.where(promo, np.round(price[pidx] * qty * disc_pct, 2), 0.0)
        # --- timestamps (per transaction)
        secs = rng.choice(24, n, p=HOUR_WEIGHTS) * 3600 + rng.integers(0, 3600, n)
        ts = (np.datetime64(day) + secs.astype("timedelta64[s]")).astype("datetime64[s]").astype(str)
        ts = np.char.replace(ts, "T", " ")
        channel = rng.choice([c[0] for c in CHANNELS], n, p=CHANNEL_P)
        txid = tx_counter + 1 + np.arange(n, dtype=np.int64)
        cust_out = np.where(anonymous, 0, cust + 1)  # 0 -> NULL later
        df = pd.DataFrame({
            "transaction_id": txid[tx_of_item], "line_number": line_no,
            "transaction_ts": ts[tx_of_item], "transaction_date": day.isoformat(),
            "store_id": store_idx[tx_of_item] + 1,
            "customer_id": pd.array(np.where(cust_out[tx_of_item] == 0, -1, cust_out[tx_of_item])),
            "channel_id": channel[tx_of_item], "product_id": pid,
            "quantity": qty, "unit_price": price[pidx], "unit_cost": cost[pidx], "discount_amount": discount})
        df["customer_id"] = df["customer_id"].astype("Int64").mask(df["customer_id"] < 0)
        part = out / "line_items" / f"dt={day.isoformat()}"
        part.mkdir(parents=True, exist_ok=True)
        fn = part / ("part.csv.gz" if compress else "part.csv")
        if compress:
            with gzip.open(fn, "wt", compresslevel=1, newline="") as fh:
                df.to_csv(fh, index=False, float_format="%.2f")
        else:
            df.to_csv(fn, index=False, float_format="%.2f")
        tx_counter += n
        line_total += total
        if verbose and (di % 30 == 0 or di == days - 1):
            el = time.perf_counter() - t0
            print(f"[{di + 1:>4}/{days}] {tx_counter:>12,} tx  {line_total:>13,} lines  "
                  f"{tx_counter / el:>10,.0f} tx/s", flush=True)

    elapsed = time.perf_counter() - t0
    size = sum(f.stat().st_size for f in (out / "line_items").rglob("part.csv*"))
    manifest = dict(generator_version=__version__, seed=seed, start_date=start.isoformat(), end_date=end.isoformat(),
                    days=days, transactions=tx_counter, line_items=line_total, stores=stores, products=products,
                    customers=n_customers, line_item_bytes_on_disk=size, gzip=compress,
                    elapsed_seconds=round(elapsed, 2), tx_per_second=round(tx_counter / elapsed, 1))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=PROFILES, default="dev")
    ap.add_argument("--transactions", type=int)
    ap.add_argument("--stores", type=int)
    ap.add_argument("--products", type=int)
    ap.add_argument("--days", type=int)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end-date", type=date.fromisoformat, default=None)
    ap.add_argument("--no-compress", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cfg = dict(PROFILES[a.profile])
    for k in ("transactions", "stores", "products", "days"):
        if getattr(a, k) is not None:
            cfg[k] = getattr(a, k)
    m = generate(a.out, seed=a.seed, end=a.end_date, compress=not a.no_compress, **cfg)
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
