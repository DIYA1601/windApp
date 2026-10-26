"""Accuracy metrics. Sign convention: error = forecast - actual (MW).

Positive bias = forecast too high, so a buyer relying on it under-procures
thermal power and is exposed to imbalance prices. Negative = over-procures.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

HORIZON_EDGES_H = [0, 6, 12, 18, 24, 30, 36, 42, 48, 72, 168, 10_000]


def summarize(df: pd.DataFrame) -> dict:
    """Aggregate metrics over rows that have both forecast and actual."""
    total = len(df)
    d = df.dropna(subset=["forecast", "actual"])
    n = len(d)
    if n == 0:
        return {"n": 0, "n_slots_total": total, "coverage": 0.0}
    err = d["error"].to_numpy()
    abs_err = np.abs(err)
    mean_actual = float(d["actual"].mean())
    big = d[d["actual"] >= config.MAPE_MIN_ACTUAL_MW]
    mape = (
        float((np.abs(big["error"]) / big["actual"]).mean() * 100) if len(big) else None
    )
    return {
        "n": n,
        "n_slots_total": total,
        "coverage": n / total if total else 0.0,
        "mean_actual_mw": mean_actual,
        "mae_mw": float(abs_err.mean()),
        "rmse_mw": float(np.sqrt((err**2).mean())),
        "bias_mw": float(err.mean()),
        "mape_pct": mape,
        "mape_min_actual_mw": config.MAPE_MIN_ACTUAL_MW,
        "nmae_pct": float(abs_err.mean() / mean_actual * 100) if mean_actual > 0 else None,
        "p50_abs_error_mw": float(np.percentile(abs_err, 50)),
        "p90_abs_error_mw": float(np.percentile(abs_err, 90)),
        "p95_abs_error_mw": float(np.percentile(abs_err, 95)),
        "max_abs_error_mw": float(abs_err.max()),
        "error_p05_mw": float(np.percentile(err, 5)),
        "error_p95_mw": float(np.percentile(err, 95)),
    }


def by_group(df: pd.DataFrame, key: str) -> list[dict]:
    out = []
    for k, g in df.groupby(key, sort=True):
        s = summarize(g)
        if s["n"]:
            out.append({key: k if not hasattr(k, "isoformat") else k.isoformat(), **s})
    return out


def by_hour_of_day(df: pd.DataFrame) -> list[dict]:
    d = df.copy()
    d["hour"] = d["startTime"].dt.tz_convert(config.LOCAL_TZ).dt.hour
    return by_group(d, "hour")


def error_histogram(df: pd.DataFrame, bins: int = 30) -> dict:
    err = df["error"].dropna().to_numpy()
    if len(err) == 0:
        return {"edges": [], "counts": []}
    counts, edges = np.histogram(err, bins=bins)
    return {"edges": edges.tolist(), "counts": counts.tolist()}


def by_horizon(actuals: pd.DataFrame, forecasts: pd.DataFrame, start_day, end_day) -> list[dict]:
    """Error vs lead time using ALL forecasts (not just the decision-time one).

    Shows how accuracy improves as the publish time approaches delivery, which
    quantifies the cost of an earlier cutoff.
    """
    act = actuals.rename(columns={"generation": "actual"})
    f = forecasts.merge(act, on="startTime", how="inner").rename(columns={"generation": "forecast"})
    day = f["startTime"].dt.tz_convert(config.LOCAL_TZ).dt.date
    f = f[(day >= start_day) & (day <= end_day)].copy()
    f["horizon_h"] = (f["startTime"] - f["publishTime"]).dt.total_seconds() / 3600
    f = f[f["horizon_h"] >= 0]
    f["error"] = f["forecast"] - f["actual"]
    f["bucket"] = pd.cut(f["horizon_h"], bins=HORIZON_EDGES_H, right=False)
    out = []
    for b, g in f.groupby("bucket", observed=True):
        s = summarize(g)
        if s["n"]:
            out.append({"horizon_from_h": float(b.left), "horizon_to_h": float(b.right), **s})
    return out
