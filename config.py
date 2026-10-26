
"""Central configuration. Everything tunable lives here or in env vars."""
import os
from datetime import date, time
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
ACTUALS_CSV = DATA_DIR / "actuals.csv"
FORECASTS_CSV = DATA_DIR / "forecasts.csv"
META_JSON = DATA_DIR / "meta.json"
STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parents[1] / "static"))

LOCAL_TZ = "Europe/London"

# ASSUMPTION (verify and state in README/video): the buyer's information
# cutoff on day D-1, in UK local time. Forecasts published after this are
# NOT visible when the day-ahead decision is made. Overridable per request.
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:00")

# Decisions are made in January 2026 -> delivery days are 2 Jan .. 1 Feb 2026.
FIRST_DECISION_DAY = date(2026, 1, 1)
LAST_DECISION_DAY = date(2026, 1, 31)
FIRST_DELIVERY_DAY = date(2026, 1, 2)
LAST_DELIVERY_DAY = date(2026, 2, 1)

# MAPE is meaningless near zero output, so ignore slots below this actual.
MAPE_MIN_ACTUAL_MW = float(os.getenv("MAPE_MIN_ACTUAL_MW", "100"))

# Band history: minimum number of prior fully-known delivery days needed
# before we show an empirical uncertainty band for a day.
MIN_BAND_HISTORY_DAYS = 2


def parse_cutoff(value: str) -> time:
    """Parse 'HH:MM' into a time, raising ValueError on bad input."""
    hh, mm = value.split(":")
    return time(int(hh), int(mm))
