"""Scoring-only scheduled-slot masks; causal feature/entry state is untouched."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

NY = "America/New_York"


def boundary(value):
    stamp = pd.Timestamp(value)
    return stamp.tz_localize(NY).tz_convert("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


@dataclass(frozen=True)
class ScoringPeriod:
    phase: str
    fold_id: str
    start: object
    end: object
    embargo_slots: int = 100

    def __post_init__(self):
        if self.phase not in ("development", "validation", "final", "recent"):
            raise ValueError("explicit known scoring phase required")
        if boundary(self.start) < boundary("2018-01-01") or boundary(self.end) <= boundary(self.start):
            raise ValueError("invalid scoring boundaries or warmup outcomes requested")
        if self.embargo_slots < 0:
            raise ValueError("negative scheduled-slot embargo")


def scoring_periods(cfg, phase):
    """The development surface includes six half-years; selection uses four."""
    n = int(cfg["canonical_start_embargo_slots"])
    if phase == "development":
        folds = cfg.get("development_surface_folds", [dict(id="2018H1", start="2018-01-01", end="2018-07-01"),
                 dict(id="2018H2", start="2018-07-01", end="2019-01-01")] + cfg["development_folds"])
    elif phase == "validation":
        folds = cfg["validation_folds"]
    elif phase in ("final", "recent"):
        folds = [dict(id=phase, **cfg["periods"][phase])]
    else:
        raise ValueError("explicit known scoring phase required")
    return tuple(ScoringPeriod(phase, f["id"], f["start"], f["end"], n) for f in folds)


def period_roster(bars, period):
    """Return original full-roster ordinals, including unusable scheduled slots."""
    starts = pd.to_datetime(bars.timestamp, utc=True).array.asi8
    if len(starts) > 1 and np.any(np.diff(starts) <= 0):
        raise ValueError("single-cell canonical roster must be unique and ordered")
    return np.flatnonzero((starts >= boundary(period.start).value) & (starts < boundary(period.end).value))


def event_masks(bars, events, horizons, period):
    """No OHLC is inspected here. Endpoint masks precede path calculations."""
    slots = period_roster(bars, period)
    opens = pd.to_datetime(bars.timestamp, utc=True).array.asi8
    closes = pd.to_datetime(bars.available_at, utc=True).array.asi8
    scoped = events.loc[(pd.to_datetime(events.timestamp, utc=True) >= boundary(period.start)) &
                        (pd.to_datetime(events.timestamp, utc=True) < boundary(period.end))].copy()
    idx = scoped.signal_idx.to_numpy(dtype=np.int64)
    if len(idx) and (np.any(idx < 0) or np.any(idx >= len(bars)) or
                    np.any(opens[idx] != pd.to_datetime(scoped.timestamp, utc=True).array.asi8)):
        raise ValueError("event signal_idx must retain its full causal roster ordinal")
    embargo_end = slots[min(period.embargo_slots, len(slots)) - 1] + 1 if len(slots) and period.embargo_slots else (slots[0] if len(slots) else 0)
    embargo = idx < embargo_end
    frames = []
    for h in sorted(set(map(int, horizons))):
        if h < 1:
            raise ValueError("positive horizons required")
        terminal = idx + h
        exists = terminal < len(bars)
        purge = np.zeros(len(idx), dtype=bool)
        purge[exists] = closes[terminal[exists]] > boundary(period.end).value
        # At an explicitly retained endpoint, a nonexisting required terminal
        # slot necessarily extends past the scoring endpoint. Otherwise it is
        # a true data-edge censor and is retained for the path scorer.
        if len(closes) and closes[-1] >= boundary(period.end).value:
            purge[~exists] = True
        frame = scoped.copy()
        atr = pd.to_numeric(frame.entry_atr, errors="coerce").to_numpy(float)
        frame["period_id"], frame["fold_id"] = period.phase, period.fold_id
        frame["horizon"] = h
        frame["start_embargo"] = embargo
        frame["endpoint_purge"] = purge
        frame["atr_support"] = np.isfinite(atr) & (atr > 0)
        frame["score_eligible"] = ~embargo & ~purge
        frame["mask_reason"] = np.select([embargo, purge], ["start_embargo", "period_endpoint_purge"], default="")
        frame["terminal_signal_idx"] = terminal
        frames.append(frame)
    audit = dict(period_id=period.phase, fold_id=period.fold_id,
                 start_utc=boundary(period.start).isoformat(), end_utc=boundary(period.end).isoformat(),
                 canonical_slots=len(slots), embargo_requested=period.embargo_slots,
                 embargo_actual=min(period.embargo_slots, len(slots)),
                 first_signal_idx=int(slots[0]) if len(slots) else None,
                 last_signal_idx=int(slots[-1]) if len(slots) else None,
                 first_timestamp=bars.timestamp.iloc[slots[0]] if len(slots) else pd.NaT,
                 embargo_last_timestamp=bars.timestamp.iloc[slots[min(period.embargo_slots, len(slots))-1]] if len(slots) and period.embargo_slots else pd.NaT,
                 first_post_embargo_timestamp=bars.timestamp.iloc[slots[period.embargo_slots]] if len(slots) > period.embargo_slots else pd.NaT,
                 last_timestamp=bars.timestamp.iloc[slots[-1]] if len(slots) else pd.NaT)
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), audit


def calendar_weeks(start, end):
    """All NY Monday weeks intersecting [start,end), including empty weeks."""
    first = boundary(start).tz_convert(NY).normalize().tz_localize(None)
    last = (boundary(end) - pd.Timedelta(nanoseconds=1)).tz_convert(NY).normalize().tz_localize(None)
    first -= pd.Timedelta(days=first.weekday())
    last -= pd.Timedelta(days=last.weekday())
    return tuple(pd.date_range(first, last, freq="W-MON").strftime("%Y-%m-%d"))
