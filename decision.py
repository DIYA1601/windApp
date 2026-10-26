"""Core logic: which forecast was *available* when the buyer had to decide?

For a delivery slot on local day D, the day-ahead purchase is made on D-1 at
`cutoff` (UK local time). The buyer sees the latest forecast for that slot
with publishTime <= cutoff(D-1). Anything published later is unavailable and
must not be used (that would be look-ahead leakage).
"""
from __future__ import annotations

from datetime import date, time, timedelta

import pandas as pd

from . import config


def cutoff_utc(delivery_day: date, cutoff: time) -> pd.Timestamp:
    """UTC instant of `cutoff` local time on the day before `delivery_day`."""
    local = pd.Timestamp.combine(delivery_day - timedelta(days=1), cutoff)
    local = local.tz_localize(config.LOCAL_TZ, ambiguous=True, nonexistent="shift_forward")
    return local.tz_convert("UTC")


def _delivery_day(ts: pd.Series) -> pd.Series:
    """UK-local calendar date of each timestamp (object dtype of datetime.date)."""
    return ts.dt.tz_convert(config.LOCAL_TZ).dt.date


def select_decision_forecasts(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """Per startTime, the latest forecast published at or before the cutoff.

    Slots with no eligible forecast are simply absent from the result.
    """
    if forecasts.empty:
        return forecasts.assign(delivery_day=pd.Series(dtype=object))
    fc = forecasts.copy()
    fc["delivery_day"] = _delivery_day(fc["startTime"])
    cutoffs = {d: cutoff_utc(d, cutoff) for d in fc["delivery_day"].unique()}
    fc["cutoff_utc"] = fc["delivery_day"].map(cutoffs)
    eligible = fc[fc["publishTime"] <= fc["cutoff_utc"]]
    if eligible.empty:
        return eligible
    idx = eligible.groupby("startTime")["publishTime"].idxmax()
    return eligible.loc[idx].reset_index(drop=True)


def build_decision_table(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    cutoff: time,
    first_day: date = config.FIRST_DELIVERY_DAY,
    last_day: date = config.LAST_DELIVERY_DAY,
) -> pd.DataFrame:
    """One row per actual half-hour slot in range, joined to its decision-time forecast.

    Columns: startTime, delivery_day, actual, forecast, publishTime,
    error (= forecast - actual; positive means over-forecast), horizon_h.
    Slots lacking a forecast keep NaN forecast/error so coverage is visible.
    """
    act = actuals.rename(columns={"generation": "actual"}).copy()
    act["delivery_day"] = _delivery_day(act["startTime"])
    act = act[(act["delivery_day"] >= first_day) & (act["delivery_day"] <= last_day)]

    sel = select_decision_forecasts(forecasts, cutoff)
    sel = sel[["startTime", "publishTime", "generation"]].rename(columns={"generation": "forecast"})
    table = act.merge(sel, on="startTime", how="left")
    table["error"] = table["forecast"] - table["actual"]
    table["horizon_h"] = (table["startTime"] - table["publishTime"]).dt.total_seconds() / 3600
    return table.sort_values("startTime").reset_index(drop=True)


def uncertainty_band(table: pd.DataFrame, day: date, lo_q: float = 0.05, hi_q: float = 0.95):
    """Empirical (lo_q, hi_q) error quantiles using only days fully known on D-1.

    At the decision time on D-1, actuals for D-1 are incomplete, so history is
    restricted to delivery days <= D-2. Returns None if too little history.
    """
    hist = table[(table["delivery_day"] <= day - timedelta(days=2)) & table["error"].notna()]
    if hist["delivery_day"].nunique() < config.MIN_BAND_HISTORY_DAYS:
        return None
    return {
        "lo_error": float(hist["error"].quantile(lo_q)),
        "hi_error": float(hist["error"].quantile(hi_q)),
        "history_days": int(hist["delivery_day"].nunique()),
    }
