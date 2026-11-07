"""Static reference data: categories, shopping missions, regions.

A *mission* is a latent shopping intent (e.g. "weekly shop", "BBQ"). Baskets are
drawn from a mission-specific category mix, which creates realistic product
co-purchase structure for the affinity models to discover.
"""
from __future__ import annotations

import numpy as np

# name, price_low, price_high, gross_margin_mean, products_share
CATEGORIES = [
    ("Fresh Produce", 0.6, 6.0, 0.32, 0.10),
    ("Bakery", 1.0, 8.0, 0.45, 0.06),
    ("Dairy & Eggs", 1.0, 9.0, 0.25, 0.08),
    ("Meat & Seafood", 3.0, 28.0, 0.22, 0.09),
    ("Pantry", 0.8, 14.0, 0.28, 0.18),
    ("Snacks", 1.0, 7.0, 0.38, 0.10),
    ("Beverages", 0.9, 12.0, 0.35, 0.10),
    ("Frozen", 2.0, 15.0, 0.30, 0.07),
    ("Household", 2.0, 24.0, 0.33, 0.08),
    ("Personal Care", 2.0, 22.0, 0.42, 0.07),
    ("Baby", 3.0, 35.0, 0.27, 0.04),
    ("Pet", 2.0, 40.0, 0.36, 0.03),
]
CATEGORY_NAMES = [c[0] for c in CATEGORIES]
N_CAT = len(CATEGORIES)

# mission -> (category weights, basket-size lambda, mission prior)
MISSIONS = {
    "weekly_shop": ({"Fresh Produce": 3, "Dairy & Eggs": 3, "Meat & Seafood": 2, "Pantry": 4,
                     "Bakery": 1, "Frozen": 1, "Household": 1, "Beverages": 1}, 9.0, 0.30),
    "breakfast":   ({"Bakery": 4, "Dairy & Eggs": 4, "Fresh Produce": 2, "Beverages": 3, "Pantry": 1}, 3.5, 0.14),
    "bbq":         ({"Meat & Seafood": 5, "Beverages": 4, "Snacks": 3, "Fresh Produce": 2, "Bakery": 1}, 6.0, 0.10),
    "family":      ({"Baby": 4, "Household": 3, "Dairy & Eggs": 2, "Pantry": 2, "Snacks": 1, "Personal Care": 1}, 6.5, 0.12),
    "pet_owner":   ({"Pet": 6, "Household": 1, "Snacks": 1, "Beverages": 1}, 2.5, 0.05),
    "quick_snack": ({"Snacks": 5, "Beverages": 5}, 1.2, 0.17),
    "wellness":    ({"Personal Care": 4, "Fresh Produce": 3, "Beverages": 1, "Dairy & Eggs": 1}, 3.0, 0.12),
}
MISSION_NAMES = list(MISSIONS)
MISSION_PRIOR = np.array([MISSIONS[m][2] for m in MISSION_NAMES])
MISSION_PRIOR = MISSION_PRIOR / MISSION_PRIOR.sum()
MISSION_LAMBDA = np.array([MISSIONS[m][1] for m in MISSION_NAMES])


def mission_category_cdf() -> np.ndarray:
    """(n_missions, n_categories) cumulative category probabilities."""
    mat = np.zeros((len(MISSION_NAMES), N_CAT))
    for i, m in enumerate(MISSION_NAMES):
        for cat, w in MISSIONS[m][0].items():
            mat[i, CATEGORY_NAMES.index(cat)] = w
    mat /= mat.sum(axis=1, keepdims=True)
    return np.cumsum(mat, axis=1)


# region -> (lat, lon, share of stores, states)
REGIONS = {
    "Northeast": (41.5, -73.5, 0.20, ["NY", "MA", "PA", "NJ"]),
    "Southeast": (33.5, -82.5, 0.24, ["GA", "FL", "NC", "TN"]),
    "Midwest":   (41.0, -88.0, 0.22, ["IL", "OH", "MI", "MN"]),
    "Southwest": (33.0, -104.0, 0.16, ["TX", "AZ", "NM", "OK"]),
    "West":      (38.0, -120.0, 0.18, ["CA", "WA", "OR", "NV"]),
}

# name -> (share, sq_ft_low, sq_ft_high, traffic multiplier)
STORE_FORMATS = {
    "Hypermarket": (0.15, 60000, 110000, 2.6),
    "Supermarket": (0.50, 25000, 55000, 1.0),
    "Express":     (0.35, 3000, 9000, 0.35),
}

CHANNELS = [(1, "In-Store"), (2, "Online Delivery"), (3, "Click & Collect")]
CHANNEL_P = np.array([0.82, 0.11, 0.07])

LOYALTY_TIERS = ["Basic", "Silver", "Gold", "Platinum"]
ACQ_CHANNELS = ["Organic", "Referral", "Paid Social", "Email", "In-Store Signup"]

HOUR_WEIGHTS = np.array([0, 0, 0, 0, 0, 0.2, 1, 2.5, 4, 5, 6, 7, 8, 7, 6, 6, 7, 9, 10, 8, 5, 3, 1, 0.2])
HOUR_WEIGHTS = HOUR_WEIGHTS / HOUR_WEIGHTS.sum()
WEEKDAY_FACTOR = np.array([0.90, 0.88, 0.92, 0.98, 1.10, 1.28, 1.05])  # Mon..Sun
