"""Independent source-path audit and event evidence enrichment."""

from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .engine import (SCALE, barrier_outcome, load_source_year, load_year,
                     price)


def enrich_year(root: Path, product: str, year: int, stage: Path) -> dict:
    file = stage / "events" / f"events_{product}_{year}.parquet"
    if not file.exists():
        return {"product": product, "year": year, "status": "no_partition"}
    events = pd.read_parquet(file)
    mapping = {"B": "vwap_return_after_departure", "A": "vwap_extreme_fade",
               "A_control": "vwap_extreme_fade", "C": "vwap_first_retest_bounce",
               "C_near": "vwap_first_retest_bounce"}
    events["strategy_id"] = events.strategy.map(mapping)
    events["event_role"] = events.strategy.map({"B": "primary", "A": "primary",
        "A_control": "lesser_departure_control", "C": "primary", "C_near": "near_approach_control"})
    events["episode_id"] = events.event_id + ":episode"
    events["market_bar_key"] = (events["product"] + ":" + events.session_date + ":" +
                                events.timeframe + ":" + events.signal_bar_open + ":" + events.raw_symbol)
    events["market_minute_key"] = (events["product"] + ":" + events.session_date + ":" +
                                   events.signal_ts)
    events["feature_partition"] = events.timeframe.map(lambda tf:
        f"data/features/bars/{tf}/feature_set=session_anchored_vwap/version=1.0.0/"
        f"product={product}/year={year}/part-000.parquet")
    events["source_partition"] = (
        f"data/curated/continuous/1m/product={product}/roll=volume_lead_v1/"
        f"variant=unadjusted/year={year}/part-000.parquet")
    source = load_source_year(root, product, year)
    source_by_day = {str(day): group.reset_index(drop=True)
                     for day, group in source.groupby("session_date", sort=False)}
    adjustments_checked = 0
    feature_bars_reconciled = 0
    for timeframe in ("2m", "5m"):
        features = load_year(root, product, year, timeframe)
        if not (features.available_at == features.bar_close_ts).all():
            raise ValueError(f"feature availability mismatch: {product} {year} {timeframe}")
        distinct = features.groupby("session_date").price_adjustment.nunique()
        if (distinct != 1).any():
            raise ValueError(f"nonconstant session adjustment: {product} {year} {timeframe}")
        adjustments_checked += len(distinct)
        count = int(timeframe[:-1])
        for day, part in features.groupby("session_date", sort=False):
            raw = source_by_day.get(str(day))
            if raw is None or len(raw) != len(part) * count:
                raise ValueError(f"source/feature bar count mismatch: {product} {day} {timeframe}")
            part = part.reset_index(drop=True)
            if not np.array_equal(raw.ts_event.to_numpy()[::count], part.ts_event.to_numpy()):
                raise ValueError(f"source/feature boundaries mismatch: {product} {day} {timeframe}")
            expected = (raw.open.to_numpy()[::count],
                        raw.high.to_numpy().reshape(-1, count).max(axis=1),
                        raw.low.to_numpy().reshape(-1, count).min(axis=1),
                        raw.close.to_numpy()[count - 1::count])
            adjustment = part.price_adjustment.to_numpy()
            for name, values in zip(("open", "high", "low", "close"), expected):
                if not np.array_equal(part[name].to_numpy() - adjustment, values):
                    raise ValueError(f"source/feature {name} mismatch: {product} {day} {timeframe}")
            if not np.array_equal(raw.instrument_id.to_numpy()[::count], part.instrument_id.to_numpy()) or (
                not np.array_equal(raw.raw_symbol.to_numpy()[::count], part.raw_symbol.to_numpy())):
                raise ValueError(f"source/feature contract mismatch: {product} {day} {timeframe}")
            feature_bars_reconciled += len(part)
    if ("source_reference_audited" in events.columns and "h30_half_retracement" in events.columns
            and "pre_return_extension_lower_ticks" in events.columns
            and "h30_barrier_open_gap" in events.columns
            and "hit_3sigma_pre_return_lower" in events.columns):
        valid = events[events.exclusion.isna()]
        if (valid.source_reference_audited == True).all():
            temp = file.with_suffix(".enriched.parquet")
            events.to_parquet(temp, index=False)
            temp.replace(file)
            return {"product": product, "year": year, "events": len(events),
                    "references_audited": len(valid),
                    "session_adjustment_views_checked": adjustments_checked,
                    "feature_bars_reconciled": feature_bars_reconciled,
                    "status": "previously_enriched_and_verified"}
    columns = {}
    for h in (10, 30, 60):
        for suffix in ("pre_barrier_mfe_ticks", "pre_barrier_mae_ticks"):
            columns[f"h{h}_{suffix}"] = [None] * len(events)
        columns[f"h{h}_barrier_open_gap"] = [None] * len(events)
    for name in ("window_barrier_0p5", "window_barrier_minute", "window_mfe_ticks",
                 "window_mae_ticks", "window_barrier_open_gap", "source_reference_audited"):
        columns[name] = [None] * len(events)
    for name in ("h30_half_retracement", "h30_half_retracement_minute"):
        columns[name] = [None] * len(events)
    for name in ("pre_return_extension_lower_ticks", "pre_return_extension_upper_ticks"):
        columns[name] = [None] * len(events)
    for name in ("hit_3sigma_pre_return_lower", "hit_3sigma_pre_return_upper"):
        columns[name] = [None] * len(events)
    for ticks in (4, 8, 16, 32):
        columns[f"favorable_{ticks}ticks_first_minute"] = [None] * len(events)
    audited = 0
    for idx, event in enumerate(events.itertuples(index=False)):
        if event.exclusion is not None and not pd.isna(event.exclusion):
            continue
        day = source_by_day.get(event.session_date)
        if day is None:
            raise ValueError(f"source missing {event.event_id}")
        signal = pd.Timestamp(event.signal_ts)
        start = int(day.ts_event.searchsorted(signal))
        minutes = int(event.window_minutes_remaining)
        path = day.iloc[start:start + minutes]
        if len(path) != minutes or path.ts_event.iloc[0] != signal or (
            path.instrument_id != event.instrument_id).any() or (
            path.raw_symbol != event.raw_symbol).any():
            raise ValueError(f"source path mismatch {event.event_id}")
        if not math.isclose(price(path.open.iloc[0]), event.reference_price, abs_tol=1e-8):
            raise ValueError(f"reference open mismatch {event.event_id}")
        columns["source_reference_audited"][idx] = True
        audited += 1
        if event.strategy in ("A", "B") and minutes >= 30:
            side = int(event.side)
            ref_distance = side * (event.reference_price - event.vwap)
            if ref_distance > event.tick and not event.already_at_frozen_target:
                halfway = event.reference_price - side * .5 * ref_distance
                segment = path.iloc[:30]
                contacts = np.flatnonzero((segment.low.to_numpy() * SCALE <= halfway + 1e-8)
                                          if side > 0 else
                                          (segment.high.to_numpy() * SCALE >= halfway - 1e-8))
                columns["h30_half_retracement"][idx] = bool(len(contacts))
                columns["h30_half_retracement_minute"][idx] = int(contacts[0]) if len(contacts) else None
        if event.strategy in ("A", "B"):
            contact_minute = event.frozen_contact_minute
            stop = minutes if pd.isna(contact_minute) else int(contact_minute) + 1
            before = path.iloc[:max(0, stop - 1)] if not pd.isna(contact_minute) else path
            through = path.iloc[:stop]
            side = int(event.side)
            def extension(segment):
                if segment.empty:
                    return 0.0
                extreme = segment.high.max() if side > 0 else segment.low.min()
                return max(0.0, side * (price(extreme) - event.reference_price) / event.tick)
            columns["pre_return_extension_lower_ticks"][idx] = extension(before)
            columns["pre_return_extension_upper_ticks"][idx] = extension(through)
            if event.strategy == "A" and not event.already_passed_3sigma:
                outward = event.vwap + side * 3 * event.sigma
                def crossed(segment):
                    if segment.empty:
                        return False
                    extreme = segment.high.max() if side > 0 else segment.low.min()
                    return bool(side * (price(extreme) - outward) >= -1e-8)
                columns["hit_3sigma_pre_return_lower"][idx] = crossed(before)
                columns["hit_3sigma_pre_return_upper"][idx] = crossed(through)
        if event.strategy not in ("A", "C", "A_control", "C_near"):
            continue
        tick, direction, ref = event.tick, int(event.direction), event.reference_price
        distance = math.ceil(.5 * event.sigma / tick - 1e-10) * tick
        outcome = barrier_outcome(path, ref, direction, distance)
        columns["window_barrier_0p5"][idx] = outcome["barrier"]
        columns["window_barrier_minute"][idx] = outcome["barrier_minute"]
        columns["window_barrier_open_gap"][idx] = outcome.get("open_gap", False)
        favorable = path.high.max() if direction > 0 else path.low.min()
        adverse = path.low.min() if direction > 0 else path.high.max()
        columns["window_mfe_ticks"][idx] = max(0.0, direction * (price(favorable) - ref) / tick)
        columns["window_mae_ticks"][idx] = max(0.0, -direction * (price(adverse) - ref) / tick)
        highs = path.high.to_numpy() * SCALE
        lows = path.low.to_numpy() * SCALE
        for size in (4, 8, 16, 32):
            target = ref + direction * size * tick
            hits = np.flatnonzero((highs >= target - 1e-8) if direction > 0 else
                                 (lows <= target + 1e-8))
            columns[f"favorable_{size}ticks_first_minute"][idx] = int(hits[0]) if len(hits) else None
        for h in (10, 30, 60):
            if minutes < h:
                continue
            horizon_outcome = barrier_outcome(path.iloc[:h], ref, direction, distance)
            columns[f"h{h}_barrier_open_gap"][idx] = horizon_outcome.get("open_gap", False)
            barrier_minute = getattr(event, f"h{h}_barrier_0p5_minute")
            stop = h if pd.isna(barrier_minute) else min(h, int(barrier_minute) + 1)
            part = path.iloc[:stop]
            fav = part.high.max() if direction > 0 else part.low.min()
            adv = part.low.min() if direction > 0 else part.high.max()
            columns[f"h{h}_pre_barrier_mfe_ticks"][idx] = max(0.0, direction * (price(fav) - ref) / tick)
            columns[f"h{h}_pre_barrier_mae_ticks"][idx] = max(0.0, -direction * (price(adv) - ref) / tick)
    for name, values in columns.items():
        events[name] = values
    temp = file.with_suffix(".enriched.parquet")
    events.to_parquet(temp, index=False)
    temp.replace(file)
    return {"product": product, "year": year, "events": len(events),
            "references_audited": audited, "session_adjustment_views_checked": adjustments_checked,
            "feature_bars_reconciled": feature_bars_reconciled}
