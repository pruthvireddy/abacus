"""Causal signal selection and unadjusted long-side path measurements."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from abacus_sahadeva.cooldown import accepted_bar_indices


MINUTE_NS = 60_000_000_000
FIVE_NS = 5 * MINUTE_NS
PRICE_SCALE = 1e-9


def accepted_indices(candidates: np.ndarray, cooldown: int) -> np.ndarray:
    """Adapt a chart-bar candidate mask to Sahadeva's fixed-bar cooldown."""
    if cooldown < 0:
        raise ValueError("cooldown must be nonnegative")
    return accepted_bar_indices(np.flatnonzero(candidates), cooldown)


def classify_path(index: int, horizon: int, ts_ns: np.ndarray, complete: np.ndarray,
                  symbol: np.ndarray, adjustment: np.ndarray) -> str:
    """Return an exclusion reason or 'valid' for signal plus H future bars."""
    end = index + horizon
    if end >= len(ts_ns):
        return "insufficient_future_bars"
    if np.any(np.diff(ts_ns[index:end + 1]) != FIVE_NS):
        return "time_gap"
    if not np.all(complete[index:end + 1]):
        return "partial_or_mixed_bar"
    if np.any(symbol[index:end + 1] != symbol[index]):
        return "contract_change"
    if not np.all(adjustment[index:end + 1] == adjustment[index]):
        return "adjustment_change"
    return "valid"


def analyze(bars: pd.DataFrame, bands: pd.DataFrame, cooldowns: list[int],
            horizons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(bars) != len(bands) or not bars.ts_event.equals(bands.ts_event):
        raise ValueError("bar and band releases do not align one-to-one")
    ts_ns = bars.ts_event.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    if np.any(np.diff(ts_ns) <= 0):
        raise ValueError("source timestamps must increase strictly")
    available_ns = bands.available_at.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    if np.any(available_ns != ts_ns + FIVE_NS):
        raise ValueError("feature available_at must equal completed bar close")
    adj = bars.price_adjustment.to_numpy(dtype=np.float64)
    symbol = bars.raw_symbol.fillna("").to_numpy(dtype=object)
    complete = ((bars.source_bar_count.to_numpy() == 5) &
                ~bars.is_partial_bar.to_numpy() &
                ~bars.is_mixed_contract_bar.to_numpy() &
                ~bars.is_mixed_adjustment_bar.to_numpy() &
                ~bars.contains_roll.to_numpy() &
                np.isfinite(adj) & (symbol != ""))
    close_adj = bars.close.to_numpy(dtype=np.float64) * PRICE_SCALE
    lower = bands.lower_outer_3sigma.to_numpy(dtype=np.float64)
    candidates = complete & np.isfinite(lower) & (close_adj <= lower)
    raw_open = (bars.open.to_numpy(dtype=np.float64) - adj) * PRICE_SCALE
    raw_high = (bars.high.to_numpy(dtype=np.float64) - adj) * PRICE_SCALE
    raw_low = (bars.low.to_numpy(dtype=np.float64) - adj) * PRICE_SCALE
    raw_close = (bars.close.to_numpy(dtype=np.float64) - adj) * PRICE_SCALE
    signal_close_ny = (bars.ts_event + pd.Timedelta(minutes=5)).dt.tz_convert("America/New_York")
    years = signal_close_ny.dt.year.to_numpy()
    session = bars.session_date.astype(str).to_numpy()
    iso = signal_close_ny.dt.isocalendar()
    weeks = (iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)).to_numpy()
    rows = []
    cohort = []
    for cooldown in cooldowns:
        indices = accepted_indices(candidates, cooldown)
        counts = Counter(map(int, years[indices]))
        for year, count in counts.items():
            cohort.append({"year": year, "cooldown": cooldown,
                           "raw_candidates": int(np.count_nonzero(candidates & (years == year))),
                           "accepted_signals": count})
        for index in indices:
            for horizon in horizons:
                status = classify_path(index, horizon, ts_ns, complete, symbol, adj)
                row = {"signal_ts_utc": bars.ts_event.iloc[index].isoformat(),
                       "signal_close_ny": signal_close_ny.iloc[index].isoformat(),
                       "session_date": session[index], "iso_week": weeks[index],
                       "year": int(years[index]), "cooldown": cooldown,
                       "horizon": horizon, "status": status,
                       "signal_close_adjusted": close_adj[index],
                       "lower_outer_adjusted": lower[index],
                       "raw_symbol": symbol[index], "entry_unadjusted": None,
                       "mae_points": None, "mfe_points": None,
                       "terminal_points": None}
                if status == "valid":
                    end = index + horizon
                    entry = raw_open[index + 1]
                    row.update(entry_unadjusted=entry,
                               mae_points=max(0.0, entry - float(np.min(raw_low[index + 1:end + 1]))),
                               mfe_points=max(0.0, float(np.max(raw_high[index + 1:end + 1])) - entry),
                               terminal_points=float(raw_close[end] - entry))
                rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(cohort)


def _cluster_interval(frame: pd.DataFrame, column: str) -> tuple[float | None, float | None]:
    """Approximate 95% interval for a mean, clustering repeated events by ISO week."""
    grouped = frame.groupby("iso_week")[column].agg(["sum", "count"])
    groups = len(grouped)
    if groups < 10:
        return None, None
    mean = frame[column].mean()
    score = grouped["sum"] - mean * grouped["count"]
    se = np.sqrt(groups / (groups - 1) * np.square(score).sum()) / len(frame)
    return float(mean - 1.96 * se), float(mean + 1.96 * se)


def summarize(ledger: pd.DataFrame, cohort: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, cooldown, horizon), all_rows in ledger.groupby(["year", "cooldown", "horizon"], sort=True):
        valid = all_rows.loc[all_rows.status == "valid"]
        base = cohort.loc[(cohort.year == year) & (cohort.cooldown == cooldown)].iloc[0]
        row = {"year": int(year), "cooldown": int(cooldown), "horizon": int(horizon),
               "raw_candidates": int(base.raw_candidates), "accepted_signals": int(base.accepted_signals),
               "valid_n": len(valid), "sessions": valid.session_date.nunique(),
               "weeks": valid.iso_week.nunique()}
        for status in ("insufficient_future_bars", "time_gap", "partial_or_mixed_bar", "contract_change", "adjustment_change"):
            row[status] = int((all_rows.status == status).sum())
        for column in ("mae_points", "mfe_points", "terminal_points"):
            values = valid[column]
            label = column.removesuffix("_points")
            row[f"mean_{label}"] = float(values.mean()) if len(valid) else None
            row[f"median_{label}"] = float(values.median()) if len(valid) else None
            row[f"p90_{label}"] = float(values.quantile(.9)) if len(valid) else None
            lo, hi = _cluster_interval(valid, column) if len(valid) else (None, None)
            row[f"mean_{label}_ci_low"] = lo
            row[f"mean_{label}_ci_high"] = hi
        row["terminal_positive_rate"] = float((valid.terminal_points > 0).mean()) if len(valid) else None
        rows.append(row)
    return pd.DataFrame(rows)
