"""Load the cached Elexon data from CSV. The deployed app never calls Elexon."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from . import config


def save(actuals: pd.DataFrame, forecasts: pd.DataFrame, meta: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    actuals.to_csv(config.ACTUALS_CSV, index=False)
    forecasts.to_csv(config.FORECASTS_CSV, index=False)
    config.META_JSON.write_text(json.dumps(meta, indent=2))


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (actuals, forecasts, meta). Raises FileNotFoundError if not ingested."""
    actuals = pd.read_csv(config.ACTUALS_CSV, parse_dates=["startTime"])
    forecasts = pd.read_csv(config.FORECASTS_CSV, parse_dates=["startTime", "publishTime"])
    for df, cols in ((actuals, ["startTime"]), (forecasts, ["startTime", "publishTime"])):
        for c in cols:
            if df[c].dt.tz is None:
                df[c] = df[c].dt.tz_localize("UTC")
    meta = json.loads(config.META_JSON.read_text()) if config.META_JSON.exists() else {}
    return actuals, forecasts, meta
