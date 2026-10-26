# Video scripts (max 10 min total, unlisted YouTube)

Record the real app on real data. Fill the bracketed numbers from your own results.

## Part 1: client pitch (about 4.5 min)

**0:00 The problem (30s)** "Every morning you commit to tomorrow's power before you know how much wind you'll get.
Wind is weather-driven, so you buy against a forecast. Two questions: what does the forecast say at the moment you
decide, and how far can you trust it?"

**0:30 Decision day view (90s)** Open Decision day, pick a windy day. "Teal is the forecast you could see at [09:00]
on the day before. We deliberately hide anything published later. The shaded band is the range the forecast has
landed in 9 times out of 10 on earlier days. Amber is what actually happened." Read the headline sentence aloud.
Move the cut-off earlier and later: "this shows what waiting for a newer forecast is worth."

**2:00 Accuracy view (120s)** Open Forecast accuracy. "Across January the average miss is [X] MW, about [Y]% of
output. On a bad half-hour it's [P90] MW. The forecast runs [high/low] by [bias] MW, so relying on it alone leaves
you [short/over-bought]." Show the day-by-day bars (point at the worst day), the time-of-day chart, and the
lead-time chart ("a forecast published [N] hours earlier is [Z]% worse").

**4:00 Close (30s)** "Buy against the forecast, but hold a reserve of about [P90] MW for the wind miss. Next steps:
add demand and price data to size the exact thermal purchase."

## Part 2: tech lead review (about 5 min)

**0:00 Architecture (60s)** One container: FastAPI serves JSON under /api and the built React app. Data is ingested
once from Elexon into CSV and committed, so the deployed app has no runtime dependency on Elexon. Show the repo tree.

**1:00 Core logic (120s)** Open `backend/app/decision.py`. `cutoff_utc` converts 09:00 London on D-1 to UTC (DST
safe). `select_decision_forecasts` filters `publishTime <= cutoff` then takes the latest per `startTime`.
`build_decision_table` left-joins to actuals so missing forecasts stay visible as coverage, not silently dropped.
Show `tests/test_core.py::test_picks_latest_forecast_before_cutoff_no_leakage`.

**3:00 Metrics and band (60s)** `metrics.py`: sign convention, MAPE floor, by-hour and by-horizon. The uncertainty
band uses only days <= D-2 to avoid look-ahead.

**4:00 Frontend and practices (60s)** `api.js` and the `useAsync` hook, the two views, Docker multi-stage build,
CI, README assumptions, and the AI-tool disclosure. State the open assumptions: cut-off time, forecast resolution.
