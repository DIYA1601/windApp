"""Thin client for the Elexon Insights (BMRS) stream endpoints.

Base URL is open, no API key required. Stream endpoints return a plain JSON
array. NOTE: parameter names below follow the documented stream pattern
(settlementDate* for FUELHH, publishDateTime* for WINDFOR) but should be
confirmed against the live Swagger at
https://bmrs.elexon.co.uk/api-documentation before the final run. Requests
are chunked into short windows because stream endpoints cap the range.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
CHUNK_DAYS = 7
TIMEOUT_S = 60


def _get(path: str, params: dict) -> list[dict]:
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT_S)
    resp.raise_for_status()
    payload = resp.json()
    # Stream endpoints return a bare list; be tolerant of {"data": [...]}.
    return payload["data"] if isinstance(payload, dict) else payload


def _windows(start: date, end: date, step: int = CHUNK_DAYS):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=step - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actual_wind(start: date, end: date) -> pd.DataFrame:
    """FUELHH, WIND only, by settlement date (inclusive). Columns: startTime, generation."""
    rows: list[dict] = []
    for a, b in _windows(start, end):
        rows += _get(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": a.isoformat(),
                "settlementDateTo": b.isoformat(),
                "fuelType": "WIND",
            },
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["startTime", "generation"])
    df = df[df["fuelType"] == "WIND"]  # defensive: filter again client-side
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.drop_duplicates("startTime", keep="last")
    return df[["startTime", "generation"]].sort_values("startTime").reset_index(drop=True)


def fetch_wind_forecasts(pub_start: date, pub_end: date) -> pd.DataFrame:
    """WINDFOR by publish time. Columns: startTime, publishTime, generation."""
    rows: list[dict] = []
    for a, b in _windows(pub_start, pub_end):
        frm = datetime(a.year, a.month, a.day, tzinfo=timezone.utc)
        to = datetime(b.year, b.month, b.day, tzinfo=timezone.utc) + timedelta(days=1)
        rows += _get(
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": frm.strftime("%Y-%m-%dT%H:%MZ"),
                "publishDateTimeTo": to.strftime("%Y-%m-%dT%H:%MZ"),
            },
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["startTime", "publishTime", "generation"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.drop_duplicates(["startTime", "publishTime"], keep="last")
    return (
        df[["startTime", "publishTime", "generation"]]
        .sort_values(["startTime", "publishTime"])
        .reset_index(drop=True)
    )
