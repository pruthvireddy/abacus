"""Study derivation; does not alter a released calendar or inherit VWAP eligibility."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from abacus_bhishma.session_anchored_vwap import expected_minutes, holiday_sessions
from .core import MINUTE

NY = ZoneInfo("America/New_York")

def stamp(day, minute):
    return pd.Timestamp(datetime.combine(pd.Timestamp(day).date(), time(minute // 60, minute % 60), NY)).value

def assign_days(timestamps):
    local = pd.to_datetime(timestamps, utc=True).tz_convert(NY)
    # Unlike the retained release, the early GC 17:00-17:15 belongs to its actual day.
    day = local.tz_localize(None).normalize() + pd.to_timedelta((local.hour >= 18).astype(int), unit="D")
    return day.strftime("%Y-%m-%d").to_numpy()

def previous_weekday(day):
    d = pd.Timestamp(day).date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()

def week(day):
    d = pd.Timestamp(day).normalize()
    return (d - pd.Timedelta(days=d.weekday())).strftime("%Y-%m-%d")

def expected(product, day):
    return expected_minutes(product, pd.Timestamp(day).date())

def max_missing_run(present):
    missing = np.flatnonzero(~present)
    if not len(missing):
        return 0
    cuts = np.flatnonzero(np.diff(missing) > 1) + 1
    return max(map(len, np.split(missing, cuts)))

def holidays(product):
    return {d.isoformat(): "; ".join(v) for d, v in holiday_sessions(product, 2010, 2026).items()}
