"""Causal event extraction and unadjusted one-minute path evaluation."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import math

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from abacus_bhishma.continuous_loader import open_continuous_dataset
from abacus_bhishma.feature_loader import load_session_anchored_vwap

SCALE = 1e-9
ANCHORS = ("globex", "asia", "london", "ny")
VIEWS = (("globex", "globex"), ("asia", "asia"), ("london", "london"),
         ("ny", "ny"), ("globex", "asia"), ("globex", "london"),
         ("globex", "ny"))
PRODUCTS = ("ES", "NQ", "GC")
YEARS = {"ES": range(2021, 2027), "NQ": range(2021, 2027),
         "GC": range(2016, 2027)}
BASE_COLUMNS = ["ts_event", "bar_close_ts", "available_at", "session_date", "product",
                "timeframe", "instrument_id", "raw_symbol", "open", "high", "low",
                "close", "price_adjustment", "min_tick"]
FEATURE_COLUMNS = BASE_COLUMNS + ["is_asia_session", "is_london_session", "is_ny_session"]
for _anchor in ANCHORS:
    FEATURE_COLUMNS += [f"{_anchor}_{suffix}" for suffix in (
        "anchor_ts", "anchor_active", "vwap", "sigma", "minutes_since_anchor",
        "exit_above_upper_2sigma", "exit_below_lower_2sigma")]
SOURCE_COLUMNS = ["ts_event", "session_date", "product", "instrument_id", "raw_symbol",
                  "open", "high", "low", "close"]


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_inputs(root: Path, lock: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    records = [lock["release_manifest"], *lock["datasets"],
               *lock["related_manifests"], lock["audit"]]
    for entry in records:
        path = root / entry.get("path", entry.get("manifest_path", ""))
        expected = entry.get("sha256", entry.get("manifest_sha256"))
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"input lock mismatch: {path}")
        checks.append({"path": str(path.relative_to(root)), "sha256": actual})
    release = json.loads((root / lock["release_manifest"]["path"]).read_text())
    if release.get("release_id") != "session_anchored_vwap__1.0.0":
        raise ValueError("pinned release identity mismatch")
    if "quality_report" in release:
        report = release["quality_report"]
        path = root / report["path"]
        actual = digest(path)
        if actual != report["sha256"]:
            raise ValueError(f"quality report checksum mismatch: {path}")
        checks.append({"path": report["path"], "sha256": actual})
    for name in ("session_anchored_vwap_2m_v1", "session_anchored_vwap_5m_v1",
                 "volume_lead_unadjusted_v1"):
        manifest = json.loads((root / "catalog/datasets" / f"{name}.json").read_text())
        for item in manifest["output_files"]:
            path = root / item["path"]
            # The source manifest also lists ancillary output; verifying all published
            # outputs is stricter than limiting the check to consumed year partitions.
            actual = digest(path)
            if actual != item["sha256"]:
                raise ValueError(f"published partition checksum mismatch: {path}")
            checks.append({"path": item["path"], "sha256": actual})
    return checks


def load_year(root: Path, product: str, year: int, timeframe: str) -> pd.DataFrame:
    table = load_session_anchored_vwap(root, product, timeframe, version="1.0.0",
                                      start_date=f"{year}-01-01", end_date=f"{year+1}-01-01",
                                      columns=FEATURE_COLUMNS)
    return table.to_pandas()


def load_source_year(root: Path, product: str, year: int) -> pd.DataFrame:
    dataset = open_continuous_dataset(root, product)
    condition = ((pc.field("session_date") >= pa.scalar(date(year, 1, 1), pa.date32())) &
                 (pc.field("session_date") < pa.scalar(date(year + 1, 1, 1), pa.date32())))
    return dataset.to_table(columns=SOURCE_COLUMNS, filter=condition).to_pandas()


def price(value: int | float) -> float:
    return float(value) * SCALE


def finite(value: Any) -> bool:
    return value is not None and not pd.isna(value) and math.isfinite(float(value))


def view_indices(frame: pd.DataFrame, window: str) -> np.ndarray:
    if window == "globex":
        return np.arange(len(frame))
    return np.flatnonzero(frame[f"is_{window}_session"].to_numpy())


def valid(row: pd.Series, anchor: str, warmup: int = 30) -> bool:
    return (row[f"{anchor}_anchor_active"] is True or
            bool(row[f"{anchor}_anchor_active"])) and (
            finite(row[f"{anchor}_vwap"]) and finite(row[f"{anchor}_sigma"]) and
            row[f"{anchor}_sigma"] > 0 and
            row[f"{anchor}_minutes_since_anchor"] >= warmup)


def split_of(day: date) -> str:
    return "development" if day.year <= 2023 else "validation" if day.year == 2024 else "final"


def reconcile(signal: pd.Series, source: pd.DataFrame, timeframe: int) -> None:
    t0, t1 = signal.ts_event, signal.bar_close_ts
    start = int(source.ts_event.searchsorted(t0))
    part = source.iloc[start:start + timeframe]
    if len(part) != timeframe or part.ts_event.iloc[0] != t0 or part.ts_event.iloc[-1] != t1 - timedelta(minutes=1):
        raise ValueError(f"missing 1m source within feature interval {t0}")
    if (part.instrument_id != signal.instrument_id).any() or (part.raw_symbol != signal.raw_symbol).any():
        raise ValueError(f"contract mismatch at {t0}")
    adj = int(signal.price_adjustment)
    expected = (int(part.open.iloc[0]), int(part.high.max()), int(part.low.min()),
                int(part.close.iloc[-1]))
    actual = tuple(int(signal[k]) - adj for k in ("open", "high", "low", "close"))
    if expected != actual:
        raise ValueError(f"adjusted/unadjusted OHLC mismatch at {t0}: {expected} != {actual}")


def barrier_outcome(path: pd.DataFrame, reference: float, direction: int,
                    distance: float) -> dict[str, Any]:
    """Four-way first passage, including open gaps and intraminute ambiguity."""
    fav, adv = reference + direction * distance, reference - direction * distance
    result = {"barrier": "neither", "barrier_minute": None,
              "pre_barrier_mfe_ticks": None, "pre_barrier_mae_ticks": None}
    if path.empty:
        return result
    opens = path.open.to_numpy() * SCALE
    highs = path.high.to_numpy() * SCALE
    lows = path.low.to_numpy() * SCALE
    favorable = highs if direction > 0 else lows
    adverse = lows if direction > 0 else highs
    hit_fav = direction * (favorable - fav) >= -1e-8
    hit_adv = direction * (adverse - adv) <= 1e-8
    hits = np.flatnonzero(hit_fav | hit_adv)
    if len(hits):
        offset = int(hits[0])
        open_fav = direction * (opens[offset] - fav) >= -1e-8
        open_adv = direction * (opens[offset] - adv) <= 1e-8
        if open_fav and not open_adv:
            label = "favorable"
        elif open_adv and not open_fav:
            label = "adverse"
        elif hit_fav[offset] and hit_adv[offset]:
            label = "ambiguous"
        else:
            label = "favorable" if hit_fav[offset] else "adverse"
        result.update(barrier=label, barrier_minute=offset, open_gap=bool(open_fav or open_adv))
    return result


def contact(path: pd.DataFrame, level: float, tick: float) -> tuple[int | None, int | None]:
    """Return (first zone-overlap index, first complete gap-through index)."""
    lower, upper = level - tick, level + tick
    if path.empty:
        return None, None
    lows, highs = path.low.to_numpy() * SCALE, path.high.to_numpy() * SCALE
    opens, closes = path.open.to_numpy() * SCALE, path.close.to_numpy() * SCALE
    hits = np.flatnonzero((lows <= upper + 1e-8) & (highs >= lower - 1e-8))
    first = int(hits[0]) if len(hits) else None
    prior = closes[:-1]
    gaps = np.flatnonzero(((prior > upper) & (opens[1:] < lower) & (highs[1:] < lower)) |
                         ((prior < lower) & (opens[1:] > upper) & (lows[1:] > upper)))
    gap = int(gaps[0] + 1) if len(gaps) else None
    if first is not None and gap is not None and gap >= first:
        gap = None
    return first, gap


def evaluate(event: dict[str, Any], feature: pd.DataFrame,
             source: pd.DataFrame, anchor: str, window_end: pd.Timestamp) -> dict[str, Any]:
    """Evaluate one completed-bar event from the first eligible 1m open."""
    signal = feature.iloc[event["feature_index"]]
    reconcile(signal, source, int(signal.timeframe[:-1]))
    start = int(source.ts_event.searchsorted(signal.available_at))
    end_time = (min(window_end, signal.available_at + timedelta(minutes=60))
                if event["strategy"] in ("C", "C_near", "A_control") else window_end)
    stop = int(source.ts_event.searchsorted(end_time))
    after = source.iloc[start:stop].reset_index(drop=True)
    event["reference_available"] = not after.empty and after.ts_event.iloc[0] == signal.available_at
    event["followup_minutes"] = len(after)
    event["window_minutes_remaining"] = int((window_end - signal.available_at).total_seconds() / 60)
    expected_minutes = int((end_time - signal.available_at).total_seconds() / 60)
    event["source_contiguous"] = bool(len(after) == expected_minutes and
                                      (len(after) == 0 or after.ts_event.iloc[-1] == end_time - timedelta(minutes=1)))
    event["contract_constant"] = bool(after.empty or
                                      ((after.instrument_id == signal.instrument_id) &
                                       (after.raw_symbol == signal.raw_symbol)).all())
    if not event["reference_available"] or not event["source_contiguous"] or not event["contract_constant"]:
        event["exclusion"] = "zero_followup" if after.empty else "source_or_contract_discontinuity"
        return event
    tick = event["tick"]
    ref = price(after.open.iloc[0])
    event["reference_price"] = ref
    event["exclusion"] = None
    event["window_evaluable"] = True
    level = event["vwap"]
    side = event["side"]
    event["already_at_frozen_target"] = side * (ref - level) <= tick + 1e-8
    if event["strategy"] in ("B", "A"):
        fidx, gap = contact(after, level, tick)
    else:
        fidx, gap = None, None
    event["frozen_contact_minute"] = fidx
    event["frozen_gap_through_minute"] = gap
    # At each 1m bar start, identify its completed feature bar and the most recent
    # previous feature close. This holds the known level through the output bar.
    evolving_idx = None
    evolving_end = None
    if event["strategy"] in ("B", "A"):
        feature_starts = feature.ts_event.to_numpy()
        source_starts = after.ts_event.to_numpy()
        known = np.searchsorted(feature_starts, source_starts, side="right") - 2
        vwap_values = feature[f"{anchor}_vwap"].to_numpy()
        adjustments = feature.price_adjustment.to_numpy()
        levels = np.full(len(after), np.nan)
        usable = known >= 0
        levels[usable] = vwap_values[known[usable]] - adjustments[known[usable]] * SCALE
        hits = np.flatnonzero((after.low.to_numpy() * SCALE <= levels + tick + 1e-8) &
                              (after.high.to_numpy() * SCALE >= levels - tick - 1e-8))
        evolving_idx = int(hits[0]) if len(hits) else None
        evolving_end = float(levels[-1]) if len(levels) and np.isfinite(levels[-1]) else None
    event["evolving_contact_minute"] = evolving_idx
    event["vwap_motion_to_end_points"] = None if evolving_end is None else evolving_end - level
    event["price_retracement_to_end_points"] = side * (ref - price(after.close.iloc[-1])) if event["strategy"] in ("B", "A") else None
    event["remaining_frozen_distance_end_ticks"] = max(0.0, side * (price(after.close.iloc[-1]) - level) / tick) if event["strategy"] in ("B", "A") else None
    event["max_extension_before_frozen_return_ticks"] = None
    until_return = after if fidx is None else after.iloc[:fidx + 1]
    if not until_return.empty:
        extreme = until_return.high.max() if side > 0 else until_return.low.min()
        event["max_extension_before_frozen_return_ticks"] = max(0.0, side * (price(extreme) - ref) / tick)
    if event["strategy"] == "A":
        outward_3sigma = level + side * 3 * event["sigma"]
        event["already_passed_3sigma"] = side * (ref - outward_3sigma) >= -1e-8
        event["hit_3sigma_before_return"] = (not event["already_passed_3sigma"] and
            side * (price(extreme) - outward_3sigma) >= -1e-8)
    for horizon in (10, 30, 60):
        key = f"h{horizon}"
        capable = event["window_minutes_remaining"] >= horizon
        event[f"{key}_evaluable"] = capable
        if not capable:
            event[f"{key}_exclusion"] = "late_event"
            continue
        part = after.iloc[:horizon]
        event[f"{key}_frozen_contact"] = fidx is not None and fidx < horizon and not event["already_at_frozen_target"]
        event[f"{key}_evolving_contact"] = evolving_idx is not None and evolving_idx < horizon
        event[f"{key}_signed_ticks"] = event["direction"] * (price(part.close.iloc[-1]) - ref) / tick
        event[f"{key}_signed_points"] = event["direction"] * (price(part.close.iloc[-1]) - ref)
        favorable = part.high.max() if event["direction"] > 0 else part.low.min()
        adverse = part.low.min() if event["direction"] > 0 else part.high.max()
        event[f"{key}_mfe_ticks"] = max(0.0, event["direction"] * (price(favorable) - ref) / tick)
        event[f"{key}_mae_ticks"] = max(0.0, -event["direction"] * (price(adverse) - ref) / tick)
        if event["strategy"] != "B":
            for factor in (0.25, 0.5, 1.0):
                size_ticks = max(1, math.ceil(factor * event["sigma"] / tick - 1e-10))
                outcome = barrier_outcome(part, ref, event["direction"], size_ticks * tick)
                tag = f"{key}_barrier_{str(factor).replace('.', 'p')}"
                event[tag] = outcome["barrier"]
                event[f"{tag}_minute"] = outcome["barrier_minute"]
                event[f"{tag}_ticks"] = size_ticks
            for size_ticks in (4, 8, 16, 32):
                tag = f"{key}_barrier_{size_ticks}ticks"
                event[tag] = barrier_outcome(part, ref, event["direction"], size_ticks * tick)["barrier"]
    event["window_frozen_contact"] = fidx is not None and not event["already_at_frozen_target"]
    event["window_evolving_contact"] = evolving_idx is not None
    return event


def _base(strategy: str, feature: pd.DataFrame, row_index: int, anchor: str,
          window: str, ordinal: int) -> dict[str, Any]:
    row = feature.iloc[row_index]
    adj = price(row.price_adjustment)
    side = 1 if price(row.close) > row[f"{anchor}_vwap"] else -1
    day = row.session_date
    return {"event_id": f"{strategy}:{row['product']}:{day}:{row['timeframe']}:{anchor}:{window}:{ordinal}",
            "strategy": strategy, "product": row["product"], "session_date": str(day),
            "year": day.year, "split": split_of(day), "timeframe": row["timeframe"],
            "anchor": anchor, "window": window, "feature_index": row_index,
            "signal_ts": row.available_at.isoformat(), "signal_bar_open": row.ts_event.isoformat(),
            "instrument_id": int(row.instrument_id), "raw_symbol": row.raw_symbol,
            "adjustment": adj, "tick": price(row.min_tick),
            "vwap": float(row[f"{anchor}_vwap"]) - adj,
            "sigma": float(row[f"{anchor}_sigma"]), "side": side,
            "direction": -side if strategy in ("A", "A_control", "B") else side,
            "distance_sigma": abs(price(row.close) - row[f"{anchor}_vwap"]) / row[f"{anchor}_sigma"],
            "distance_ticks": abs(price(row.close) - row[f"{anchor}_vwap"]) / price(row.min_tick),
            "anchor_age_minutes": int(row[f"{anchor}_minutes_since_anchor"])}


def extract_view(feature: pd.DataFrame, source: pd.DataFrame, anchor: str,
                 window: str, warmup: int = 30,
                 sensitivity_only: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract B, A, C and declared observational controls for one window."""
    indices = view_indices(feature, window)
    if len(indices) == 0:
        return [], {}
    window_end = feature.iloc[indices[-1]].bar_close_ts
    eligible = [int(i) for i in indices if valid(feature.iloc[i], anchor, warmup)]
    summary = {"product": feature.iloc[0]["product"], "session_date": str(feature.iloc[0].session_date),
               "timeframe": feature.iloc[0].timeframe, "anchor": anchor, "window": window,
               "eligible_window": True, "mature_valid": bool(eligible), "departure": False,
               "first_departure_class": "none", "already_outside_at_start": False,
               "unqualified_first_touches": 0, "gap_throughs": 0, "frozen_cycles": 0,
               "evolving_cycles": 0}
    if not eligible:
        return [], summary
    events = []
    first = eligible[0]
    first_row = feature.iloc[first]
    first_z = (price(first_row.close) - first_row[f"{anchor}_vwap"]) / first_row[f"{anchor}_sigma"]
    summary["already_outside_at_start"] = abs(first_z) > 2
    a_armed = not summary["already_outside_at_start"]
    lesser_armed = abs(first_z) <= 1
    b_primary = False
    c_departure = None
    c_side = None
    c_ordinal = 0
    near_ordinal = 0
    near_recorded = False
    a_ordinal = 0
    control_ordinal = 0
    prev_z = first_z
    prev_i = first
    for i in eligible:
        row = feature.iloc[i]
        vwap = row[f"{anchor}_vwap"]
        close = price(row.close)
        sigma = row[f"{anchor}_sigma"]
        tick = price(row.min_tick)
        z = (close - vwap) / sigma
        qualifies = abs(close - vwap) >= sigma - 1e-8 and abs(close - vwap) >= 4 * tick - 1e-8
        if i == first and qualifies or i > first and qualifies and not b_primary:
            summary["departure"] = True
            summary["first_departure_class"] = "already_away" if i == first else "fresh"
            event = _base("B", feature, i, anchor, window, 1)
            event["departure_class"] = summary["first_departure_class"]
            events.append(evaluate(event, feature, source, anchor, window_end))
            b_primary = True
        if i == first:
            if qualifies:
                c_departure, c_side = i, 1 if z > 0 else -1
                near_recorded = False
            continue
        # Strict completed-close history is checked at the later touch bar's open.
        if c_departure is not None and i > c_departure:
            prior = feature.iloc[prev_i]
            if row.ts_event - prior.ts_event != timedelta(minutes=int(row.timeframe[:-1])):
                c_departure = None
            else:
                known_vwap = prior[f"{anchor}_vwap"] - price(prior.price_adjustment)
                source_start = int(source.ts_event.searchsorted(row.ts_event))
                sub = source.iloc[source_start:source_start + int(row.timeframe[:-1])]
                touch, gap = contact(sub, known_vwap, tick)
                if touch is None and gap is None and not near_recorded and not sensitivity_only:
                    needed = 6 if row.timeframe == "2m" else 3
                    history = feature.iloc[max(0, i-needed):i]
                    times = list(history.bar_close_ts)
                    expected = [row.ts_event - timedelta(minutes=(needed-1-k)*int(row.timeframe[:-1]))
                                for k in range(needed)]
                    established_near = (len(history) == needed and times == expected and
                        all(valid(h, anchor, 0) and (window == "globex" or h[f"is_{window}_session"])
                            and c_side * (price(h.close) - h[f"{anchor}_vwap"]) > 1e-8
                            for _, h in history.iterrows()))
                    closest = price(sub.low.min()) if c_side > 0 else price(sub.high.max())
                    near_distance = c_side * (closest - known_vwap)
                    if established_near and tick < near_distance <= 3 * tick + 1e-8:
                        near_ordinal += 1
                        near = _base("C_near", feature, i, anchor, window, near_ordinal)
                        near["side"] = c_side
                        near["direction"] = c_side
                        near["known_touch_vwap"] = known_vwap
                        events.append(evaluate(near, feature, source, anchor, window_end))
                        near_recorded = True
                if touch is not None or gap is not None:
                    if gap is not None and (touch is None or gap < touch):
                        summary["gap_throughs"] += 1
                    else:
                        needed = 6 if row.timeframe == "2m" else 3
                        history = feature.iloc[max(0, i-needed):i]
                        times = list(history.bar_close_ts)
                        expected = [row.ts_event - timedelta(minutes=(needed-1-k)*int(row.timeframe[:-1]))
                                    for k in range(needed)]
                        established = (len(history) == needed and times == expected and
                                       all(valid(h, anchor, 0) and h[f"is_{window}_session"] if window != "globex" else valid(h, anchor, 0)
                                           for _, h in history.iterrows()) and
                                       all(c_side * (price(h.close) - h[f"{anchor}_vwap"]) > 1e-8
                                           for _, h in history.iterrows()))
                        if established:
                            c_ordinal += 1
                            event = _base("C", feature, i, anchor, window, c_ordinal)
                            event["side"] = c_side
                            event["direction"] = c_side
                            event["departure_feature_index"] = c_departure
                            event["known_touch_vwap"] = known_vwap
                            close_unadj = close - price(row.price_adjustment)
                            event["confirmation"] = (c_side * (close_unadj - known_vwap) > tick + 1e-8)
                            event["touch_close_class"] = ("approach_side" if event["confirmation"] else
                                "opposite_side" if c_side * (close_unadj - known_vwap) < -tick - 1e-8 else "zone")
                            events.append(evaluate(event, feature, source, anchor, window_end))
                        else:
                            summary["unqualified_first_touches"] += 1
                    c_departure = None
                    c_side = None
                    near_recorded = False
                elif c_side * z <= 0:
                    # Equality and opposite-side completed closes break the episode
                    # even when the source contains no zone-overlap print.
                    c_departure = None
                    c_side = None
                    near_recorded = False
        if c_departure is None and qualifies:
            c_departure, c_side = i, 1 if z > 0 else -1
            near_recorded = False
        # Published exit flags are nullable. Only literal true signals an A event.
        flag = (row[f"{anchor}_exit_above_upper_2sigma"] == True or
                row[f"{anchor}_exit_below_lower_2sigma"] == True)
        if a_armed and flag and prev_i == i - 1 and abs(z) > 2:
            a_ordinal += 1
            event = _base("A", feature, i, anchor, window, a_ordinal)
            events.append(evaluate(event, feature, source, anchor, window_end))
            a_armed = False
        if not a_armed and abs(z) <= 1 + 1e-10:
            a_armed = True
        if not sensitivity_only and lesser_armed and prev_i == i - 1 and abs(prev_z) <= 1 and 1 < abs(z) <= 2:
            control_ordinal += 1
            event = _base("A_control", feature, i, anchor, window, control_ordinal)
            events.append(evaluate(event, feature, source, anchor, window_end))
            lesser_armed = False
        if abs(z) <= 1:
            lesser_armed = True
        prev_i, prev_z = i, z
    # Count completed frozen/evolving departure-return cycles independently.
    if sensitivity_only:
        return events, summary
    candidates = [i for i in eligible if abs(price(feature.iloc[i].close) -
                  feature.iloc[i][f"{anchor}_vwap"]) >= max(
                  feature.iloc[i][f"{anchor}_sigma"], 4 * price(feature.iloc[i].min_tick)) - 1e-8]
    first_b = next((e for e in events if e["strategy"] == "B"), None)
    for mode in ("frozen", "evolving"):
        resume_at = feature.iloc[first].ts_event
        count = 0
        for i in candidates:
            row = feature.iloc[i]
            if row.available_at < resume_at:
                continue
            if first_b is not None and i == first_b["feature_index"]:
                outcome = first_b
            else:
                outcome = evaluate(_base("B", feature, i, anchor, window, i + 1),
                                   feature, source, anchor, window_end)
            minute = outcome.get(f"{mode}_contact_minute")
            if minute is None or outcome.get("already_at_frozen_target"):
                break
            count += 1
            resume_at = row.available_at + timedelta(minutes=minute + 1)
        summary[f"{mode}_cycles"] = count
    return events, summary


def run(root: Path, progress=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_events, all_windows = [], []
    for product in PRODUCTS:
        for year in YEARS[product]:
            source_year = load_source_year(root, product, year)
            if source_year.empty:
                continue
            source_groups = {d: group.reset_index(drop=True) for d, group in source_year.groupby("session_date", sort=False)}
            for timeframe in ("2m", "5m"):
                features = load_year(root, product, year, timeframe)
                for day, frame in features.groupby("session_date", sort=False):
                    source = source_groups.get(day)
                    if source is None:
                        raise ValueError(f"missing source day: {product} {day}")
                    frame = frame.reset_index(drop=True)
                    for anchor, window in VIEWS:
                        events, summary = extract_view(frame, source, anchor, window)
                        all_events.extend(events)
                        if summary:
                            all_windows.append(summary)
            if progress:
                progress(product, year, len(all_events), len(all_windows))
    return pd.DataFrame(all_events), pd.DataFrame(all_windows)


def run_year(root: Path, product: str, year: int, output: Path,
             warmup: int = 30, sensitivity_only: bool = False) -> dict[str, Any]:
    source_year = load_source_year(root, product, year)
    if source_year.empty:
        return {"product": product, "year": year, "events": 0, "windows": 0}
    source_groups = {d: group.reset_index(drop=True) for d, group in source_year.groupby("session_date", sort=False)}
    events, windows = [], []
    for timeframe in ("2m", "5m"):
        features = load_year(root, product, year, timeframe)
        for day, frame in features.groupby("session_date", sort=False):
            source = source_groups.get(day)
            if source is None:
                raise ValueError(f"missing source day: {product} {day}")
            frame = frame.reset_index(drop=True)
            for anchor, window in VIEWS:
                found, summary = extract_view(frame, source, anchor, window,
                                             warmup=warmup, sensitivity_only=sensitivity_only)
                events.extend(found)
                if summary:
                    windows.append(summary)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(events).to_parquet(output / f"events_{product}_{year}.parquet", index=False)
    pd.DataFrame(windows).to_parquet(output / f"windows_{product}_{year}.parquet", index=False)
    return {"product": product, "year": year, "events": len(events), "windows": len(windows)}
