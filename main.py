"""FastAPI app. All endpoints are read-only over the cached Elexon data."""
from __future__ import annotations

from datetime import date, time

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, data, decision, metrics

app = FastAPI(title="UK Wind Forecast Decision Support", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _cutoff(value: str) -> time:
    try:
        return config.parse_cutoff(value)
    except Exception:
        raise HTTPException(422, f"cutoff must be HH:MM, got {value!r}")


def _table(cutoff: str) -> pd.DataFrame:
    try:
        actuals, forecasts, _ = data.load()
    except FileNotFoundError:
        raise HTTPException(503, "Data not ingested yet. Run scripts/ingest.py")
    return decision.build_decision_table(actuals, forecasts, _cutoff(cutoff))


def _range(table: pd.DataFrame, start: date | None, end: date | None) -> pd.DataFrame:
    start = start or config.FIRST_DELIVERY_DAY
    end = end or config.LAST_DELIVERY_DAY
    return table[(table["delivery_day"] >= start) & (table["delivery_day"] <= end)]


def _nan_to_none(records: list[dict]) -> list[dict]:
    return [{k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()} for r in records]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    try:
        _, _, meta = data.load()
    except FileNotFoundError:
        meta = {"source": "missing"}
    return {
        "default_cutoff": config.DEFAULT_CUTOFF,
        "timezone": config.LOCAL_TZ,
        "first_delivery_day": config.FIRST_DELIVERY_DAY.isoformat(),
        "last_delivery_day": config.LAST_DELIVERY_DAY.isoformat(),
        "data": meta,
        "error_convention": "error = forecast - actual (MW); positive = over-forecast",
    }


@app.get("/api/decision")
def decision_view(
    day: date = Query(..., description="Delivery day (UK local), e.g. 2026-01-15"),
    cutoff: str = Query(config.DEFAULT_CUTOFF, description="HH:MM UK time on D-1"),
):
    """Forecast visible at the cutoff for each half-hour of `day`, vs actual."""
    if not (config.FIRST_DELIVERY_DAY <= day <= config.LAST_DELIVERY_DAY):
        raise HTTPException(422, "day outside the January-2026 decision window")
    table = _table(cutoff)
    rows = table[table["delivery_day"] == day].copy()
    band = decision.uncertainty_band(table, day)

    slots = []
    for r in rows.itertuples():
        fc = None if pd.isna(r.forecast) else float(r.forecast)
        slot = {
            "startTime": r.startTime.isoformat(),
            "actual": float(r.actual),
            "forecast": fc,
            "publishTime": None if pd.isna(r.publishTime) else r.publishTime.isoformat(),
            "horizon_h": None if pd.isna(r.horizon_h) else round(float(r.horizon_h), 2),
            "band_low": None,
            "band_high": None,
        }
        if fc is not None and band:
            slot["band_low"] = max(0.0, fc - band["hi_error"])
            slot["band_high"] = fc - band["lo_error"]
        slots.append(slot)

    have = rows.dropna(subset=["forecast"])
    return {
        "delivery_day": day.isoformat(),
        "cutoff_local": cutoff,
        "cutoff_utc": decision.cutoff_utc(day, _cutoff(cutoff)).isoformat(),
        "band": band,
        "slots": slots,
        "summary": {
            "slots_total": len(rows),
            "slots_with_forecast": len(have),
            "forecast_energy_mwh": float(have["forecast"].sum() * 0.5),
            "actual_energy_mwh": float(have["actual"].sum() * 0.5),
            "day_metrics": metrics.summarize(rows),
        },
    }


@app.get("/api/metrics")
def metrics_overall(
    start: date | None = None,
    end: date | None = None,
    cutoff: str = Query(config.DEFAULT_CUTOFF),
):
    t = _range(_table(cutoff), start, end)
    return {"cutoff_local": cutoff, "summary": metrics.summarize(t), "histogram": metrics.error_histogram(t)}


@app.get("/api/metrics/daily")
def metrics_daily(start: date | None = None, end: date | None = None, cutoff: str = Query(config.DEFAULT_CUTOFF)):
    t = _range(_table(cutoff), start, end)
    return _nan_to_none(metrics.by_group(t, "delivery_day"))


@app.get("/api/metrics/by-hour")
def metrics_by_hour(start: date | None = None, end: date | None = None, cutoff: str = Query(config.DEFAULT_CUTOFF)):
    t = _range(_table(cutoff), start, end)
    return _nan_to_none(metrics.by_hour_of_day(t))


@app.get("/api/metrics/by-horizon")
def metrics_by_horizon(start: date | None = None, end: date | None = None):
    try:
        actuals, forecasts, _ = data.load()
    except FileNotFoundError:
        raise HTTPException(503, "Data not ingested yet. Run scripts/ingest.py")
    return _nan_to_none(
        metrics.by_horizon(
            actuals, forecasts, start or config.FIRST_DELIVERY_DAY, end or config.LAST_DELIVERY_DAY
        )
    )


@app.get("/api/errors")
def errors_timeseries(start: date | None = None, end: date | None = None, cutoff: str = Query(config.DEFAULT_CUTOFF)):
    """Per-slot decision-time error series for charting."""
    t = _range(_table(cutoff), start, end).dropna(subset=["forecast"])
    return [
        {"startTime": r.startTime.isoformat(), "actual": float(r.actual), "forecast": float(r.forecast), "error": float(r.error)}
        for r in t.itertuples()
    ]


# Serve the built React app from the same container (registered last so /api/* wins).
if config.STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.STATIC_DIR, html=True), name="web")
