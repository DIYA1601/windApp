"""Fetch Elexon data for the January-2026 decision window and cache it as CSV.

    python -m scripts.ingest              # live Elexon data (needs internet)
    python -m scripts.ingest --synthetic  # DEMO ONLY: fake data for offline dev

Synthetic data is clearly flagged in data/meta.json ("source": "synthetic") and
surfaced by /api/config so it can never be mistaken for real data.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from app import config, data

# Actuals cover delivery days; forecasts cover everything published from a
# couple of days before the first decision to the last cutoff.
ACT_START, ACT_END = config.FIRST_DELIVERY_DAY, date(2026, 2, 1)
FC_PUB_START, FC_PUB_END = date(2025, 12, 28), date(2026, 2, 1)


def live() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    from app import elexon

    actuals = elexon.fetch_actual_wind(ACT_START, ACT_END)
    forecasts = elexon.fetch_wind_forecasts(FC_PUB_START, FC_PUB_END)
    meta = {"source": "elexon", "fetched_at": datetime.now(timezone.utc).isoformat()}
    return actuals, forecasts, meta


def synthetic(seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Smooth AR-ish wind curve; forecast error grows with lead time."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-12-28", "2026-02-02", freq="30min", tz="UTC")
    walk = np.cumsum(rng.normal(0, 180, len(idx)))
    walk = (walk - walk.min()) / (walk.max() - walk.min())
    truth = np.clip(500 + walk * 14000 + rng.normal(0, 150, len(idx)), 0, 20000)
    series = pd.Series(truth, index=idx)

    actuals = series[(series.index >= "2026-01-01") & (series.index < "2026-02-02")]
    actuals = actuals.rename("generation").rename_axis("startTime").reset_index()

    rows = []
    for pub in pd.date_range("2025-12-28", "2026-02-01", freq="3h", tz="UTC"):
        targets = idx[(idx > pub) & (idx <= pub + pd.Timedelta(hours=48))]
        lead_h = (targets - pub).total_seconds() / 3600
        noise = rng.normal(0, 1, len(targets)) * (250 + 90 * lead_h)
        gen = np.clip(series.loc[targets].to_numpy() + noise, 0, None)
        rows.append(pd.DataFrame({"startTime": targets, "publishTime": pub, "generation": gen}))
    forecasts = pd.concat(rows, ignore_index=True)
    return actuals, forecasts, {"source": "synthetic", "warning": "DEMO DATA - NOT REAL ELEXON DATA"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    a, f, m = synthetic() if args.synthetic else live()
    data.save(a, f, m)
    print(f"saved {len(a)} actual rows, {len(f)} forecast rows, source={m['source']}")
