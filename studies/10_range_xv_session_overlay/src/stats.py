"""Small session-cluster estimators and fixed New York session boundaries."""
from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd


SEGMENTS = ("asia", "london", "new_york")
ALL_SEGMENTS = (*SEGMENTS, "transition")
Z95 = NormalDist().inv_cdf(.975)


def segment(clock: str) -> str:
    """Assign a normalized New York completion wall time, half-open."""
    if not isinstance(clock, str) or len(clock) < 8:
        raise ValueError(f"unavailable completion clock: {clock!r}")
    time = clock[-8:]
    if not (len(time) == 8 and time[2] == ":" and time[5] == ":"):
        raise ValueError(f"invalid completion clock: {clock!r}")
    if "03:00:00" <= time < "09:30:00":
        return "london"
    if "09:30:00" <= time < "16:00:00":
        return "new_york"
    if "16:00:00" <= time < "18:00:00":
        return "transition"
    return "asia"


def named_window(window: str) -> str:
    return {"asia": "asia", "london_pre_ny": "london",
            "ny_morning": "new_york", "ny_afternoon": "new_york",
            "transition": "transition"}[window]


def grouped(data: pd.DataFrame, values: np.ndarray | pd.Series) -> pd.DataFrame:
    values = np.asarray(values, dtype=float)
    if len(values) != len(data) or not np.isfinite(values).all():
        raise ValueError("nonfinite or misaligned values")
    if not len(data):
        return pd.DataFrame(columns=["n", "total"], dtype=float)
    return pd.DataFrame({"session_date": data.session_date.to_numpy(),
                         "value": values}).groupby("session_date").value.agg(
                             n="size", total="sum").astype(float)


def estimate(data: pd.DataFrame, *, scale: float = 1.0,
             z: float = Z95, clamp_rate: bool = False) -> dict:
    n = int(data.n.sum())
    count = int(len(data))
    if not n:
        return {"numerator": 0, "denominator": 0, "session_dates": 0,
                "events_per_session": None, "estimate": None, "ci_low": None,
                "ci_high": None, "se": None}
    total = float(data.total.sum())
    mu = total / n
    score = data.total.to_numpy() - mu * data.n.to_numpy()
    se = float(np.sqrt(count / (count - 1) * np.sum(score ** 2) / n ** 2)) if count > 1 else None
    low = scale * (mu - z * se) if se is not None else None
    high = scale * (mu + z * se) if se is not None else None
    if clamp_rate and low is not None:
        low, high = max(0.0, low), min(scale, high)
    return {"numerator": total, "denominator": n, "session_dates": count,
            "events_per_session": n / count, "estimate": scale * mu,
            "ci_low": low, "ci_high": high, "se": scale * se if se is not None else None}


def difference(a: pd.DataFrame, b: pd.DataFrame, *, scale: float,
               family: int) -> dict:
    ea, eb = estimate(a), estimate(b)
    if not ea["denominator"] or not eb["denominator"]:
        return {"baseline_numerator": eb["numerator"],
                "baseline_denominator": eb["denominator"],
                "baseline_session_dates": eb["session_dates"],
                "baseline_estimate": eb["estimate"], "difference": None,
                "difference_ci_low": None, "difference_ci_high": None,
                "family_ci_low": None, "family_ci_high": None}
    dates = a.index.union(b.index)
    aa, bb = a.reindex(dates, fill_value=0), b.reindex(dates, fill_value=0)
    ma, mb = ea["estimate"], eb["estimate"]
    score = ((aa.total - ma * aa.n) / ea["denominator"] -
             (bb.total - mb * bb.n) / eb["denominator"])
    g = len(dates)
    se = float(np.sqrt(g / (g - 1) * np.sum(score.to_numpy() ** 2))) if g > 1 else None
    delta = scale * (ma - mb)
    z_family = NormalDist().inv_cdf(1 - .05 / (2 * family))
    return {"baseline_numerator": eb["numerator"],
            "baseline_denominator": eb["denominator"],
            "baseline_session_dates": eb["session_dates"],
            "baseline_estimate": scale * mb, "difference": delta,
            "difference_ci_low": delta - scale * Z95 * se if se is not None else None,
            "difference_ci_high": delta + scale * Z95 * se if se is not None else None,
            "family_ci_low": delta - scale * z_family * se if se is not None else None,
            "family_ci_high": delta + scale * z_family * se if se is not None else None}


def family_interval(row: dict, family: int, *, clamp_rate: bool = False) -> tuple[float | None, float | None]:
    if row["se"] is None:
        return None, None
    z = NormalDist().inv_cdf(1 - .05 / (2 * family))
    low, high = row["estimate"] - z * row["se"], row["estimate"] + z * row["se"]
    if clamp_rate:
        low, high = max(0.0, low), min(1.0, high)
    return low, high


def supported(row: dict) -> bool:
    return (row["denominator"] >= 300 and row["session_dates"] >= 100 and
            row["events_per_session"] >= 2)
