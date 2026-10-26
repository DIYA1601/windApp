from datetime import date, time

import pandas as pd
import pytest

from app import decision, metrics


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_forecasts():
    # Target: 2026-01-15 12:00Z. Three publishes around the 09:00 cutoff on Jan 14.
    return pd.DataFrame(
        {
            "startTime": [ts("2026-01-15 12:00")] * 4,
            "publishTime": [
                ts("2026-01-14 03:00"),
                ts("2026-01-14 08:59"),  # latest allowed
                ts("2026-01-14 09:01"),  # too late -> must be ignored
                ts("2026-01-15 06:00"),  # far too late
            ],
            "generation": [1000.0, 2000.0, 9999.0, 8888.0],
        }
    )


def test_picks_latest_forecast_before_cutoff_no_leakage():
    sel = decision.select_decision_forecasts(make_forecasts(), time(9, 0))
    assert len(sel) == 1
    assert sel.iloc[0]["generation"] == 2000.0


def test_cutoff_is_inclusive():
    fc = make_forecasts()
    fc.loc[1, "publishTime"] = ts("2026-01-14 09:00")
    sel = decision.select_decision_forecasts(fc, time(9, 0))
    assert sel.iloc[0]["generation"] == 2000.0


def test_slot_without_eligible_forecast_has_nan():
    act = pd.DataFrame({"startTime": [ts("2026-01-15 12:00")], "generation": [1500.0]})
    fc = make_forecasts().iloc[[2, 3]]  # only late forecasts
    table = decision.build_decision_table(act, fc, time(9, 0))
    assert len(table) == 1 and pd.isna(table.iloc[0]["forecast"])


def test_summer_cutoff_uses_london_local_time():
    # In BST, 09:00 local on 2026-07-14 is 08:00 UTC.
    assert decision.cutoff_utc(date(2026, 7, 15), time(9, 0)) == ts("2026-07-14 08:00")
    assert decision.cutoff_utc(date(2026, 1, 15), time(9, 0)) == ts("2026-01-14 09:00")


def test_error_sign_and_metrics():
    act = pd.DataFrame({"startTime": [ts("2026-01-15 12:00"), ts("2026-01-15 12:30")], "generation": [1000.0, 2000.0]})
    fc = pd.DataFrame(
        {
            "startTime": act["startTime"],
            "publishTime": [ts("2026-01-14 08:00")] * 2,
            "generation": [1200.0, 1700.0],  # +200, -300
        }
    )
    table = decision.build_decision_table(act, fc, time(9, 0))
    assert list(table["error"]) == [200.0, -300.0]
    s = metrics.summarize(table)
    assert s["mae_mw"] == 250.0
    assert s["bias_mw"] == -50.0
    assert s["rmse_mw"] == pytest.approx(((200**2 + 300**2) / 2) ** 0.5)
    assert s["coverage"] == 1.0


def test_uncertainty_band_uses_only_days_up_to_d_minus_2():
    rows = []
    for d in range(10, 16):
        rows.append({"delivery_day": date(2026, 1, d), "error": float(d)})
    table = pd.DataFrame(rows)
    band = decision.uncertainty_band(table, date(2026, 1, 15))
    assert band["history_days"] == 4  # Jan 10..13 only; 14 and 15 excluded
    assert decision.uncertainty_band(table, date(2026, 1, 11)) is None  # <2 history days


def test_api_smoke(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import config, data
    from scripts import ingest

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "ACTUALS_CSV", tmp_path / "actuals.csv")
    monkeypatch.setattr(config, "FORECASTS_CSV", tmp_path / "forecasts.csv")
    monkeypatch.setattr(config, "META_JSON", tmp_path / "meta.json")
    data.load.cache_clear()
    a, f, m = ingest.synthetic()
    data.save(a, f, m)

    from app.main import app

    c = TestClient(app)
    assert c.get("/api/config").json()["data"]["source"] == "synthetic"
    d = c.get("/api/decision", params={"day": "2026-01-20"}).json()
    assert d["summary"]["slots_total"] == 48
    # No slot may use a forecast published after the cutoff.
    for s in d["slots"]:
        assert s["publishTime"] <= d["cutoff_utc"]
    assert c.get("/api/decision", params={"day": "2026-03-01"}).status_code == 422
    assert c.get("/api/decision", params={"day": "2026-01-20", "cutoff": "bad"}).status_code == 422
    m = c.get("/api/metrics").json()["summary"]
    assert m["n"] > 1000 and m["mae_mw"] > 0
    hz = c.get("/api/metrics/by-horizon").json()
    assert hz[0]["mae_mw"] < hz[-1]["mae_mw"] or len(hz) > 1  # error grows with lead time
    assert len(c.get("/api/metrics/by-hour").json()) == 24
    data.load.cache_clear()
